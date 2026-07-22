#!/usr/bin/env python3

import argparse
import base64
import importlib.machinery
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock


def load_module():
    path = pathlib.Path(__file__).with_name("aks-flex-config")
    loader = importlib.machinery.SourceFileLoader("aks_flex_config", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


config = load_module()


def prepare_args(**overrides):
    values = {
        "node_name": "flex-node-1",
        "node_ip": "10.92.1.4",
        "aks_flex_node_version": "v0.1.5-rc.1",
        "log_level": "info",
        "oci_image": config.DEFAULT_OCI_IMAGE,
        "containerd_version": config.DEFAULT_CONTAINERD_VERSION,
        "runc_version": config.DEFAULT_RUNC_VERSION,
        "cni_version": config.DEFAULT_CNI_VERSION,
        "npd_version": config.DEFAULT_NPD_VERSION,
        "resource_group": "rg",
        "cluster_name": "aks",
        "subscription": "sub",
        "agent_pool_name": "aksflexnodes",
        "controller_version": None,
        "controller_manifest_url": None,
        "skip_controller_install": False,
        "variant": "cloud-init",
        "output": "-",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class ConfigTests(unittest.TestCase):
    def test_render_bootstrap_config_pins_runtime_and_machine_backend(self):
        args = prepare_args()
        metadata = {
            "subscription_id": "00000000-0000-0000-0000-000000000000",
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "agent_pool_name": "aksflexnodes",
            "resource_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/aks",
            "location": "eastus2",
            "kubernetes_version": "1.35.0",
            "dns_service_ip": "10.94.0.10",
        }
        cluster_data = {
            "token": "abcdef.0123456789abcdef",
            "server_url": "https://example.hcp.eastus2.azmk8s.io:443",
            "ca_cert_data": "Y2E=",
        }

        rendered = config.render_bootstrap_config(args, metadata, cluster_data)

        self.assertEqual(rendered["agent"]["machineClient"]["mode"], "in-cluster")
        self.assertTrue(rendered["agent"]["requireMachineRegistration"])
        self.assertEqual(rendered["agent"]["nodeName"], "flex-node-1")
        self.assertEqual(rendered["node"]["kubelet"]["nodeIP"], "10.92.1.4")
        self.assertEqual(rendered["components"]["containerd"], config.DEFAULT_CONTAINERD_VERSION)
        self.assertEqual(rendered["components"]["runc"], config.DEFAULT_RUNC_VERSION)
        self.assertEqual(rendered["networking"]["cniVersion"], config.DEFAULT_CNI_VERSION)
        self.assertEqual(rendered["bootstrap"]["ociImage"], config.DEFAULT_OCI_IMAGE)

    def test_render_machine_goal_uses_expected_resource_id(self):
        args = prepare_args()
        metadata = {
            "resource_id": "/subscriptions/s/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/aks",
            "agent_pool_name": "aksflexnodes",
            "kubernetes_version": "1.35.0",
        }
        goal = config.render_machine_goal(args, metadata)
        self.assertEqual(
            goal["id"],
            "/subscriptions/s/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/aks/agentPools/aksflexnodes/machines/flex-node-1",
        )
        self.assertEqual(goal["properties"]["kubernetes"]["orchestratorVersion"], "1.35.0")

    def test_ensure_machine_goal_preserves_existing_configmap(self):
        args = prepare_args()
        metadata = {
            "resource_id": "/subscriptions/s/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/aks",
            "agent_pool_name": "aksflexnodes",
            "kubernetes_version": "1.35.0",
        }
        calls = []
        original_run = config.run
        config.run = lambda command, **kwargs: calls.append((command, kwargs)) or "existing"
        try:
            config.ensure_machine_goal(args, metadata)
        finally:
            config.run = original_run

        self.assertEqual(calls[0][0][-3:], ["get", "configmap", "aks-flex-machines"])
        self.assertFalse(any("create" in call[0] for call in calls))
        patch = json.loads(calls[-1][0][-1])
        self.assertIn("flex-node-1.json", patch["data"])

    def test_ensure_machine_goal_creates_missing_configmap(self):
        args = prepare_args()
        metadata = {
            "resource_id": "/subscriptions/s/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/aks",
            "agent_pool_name": "aksflexnodes",
            "kubernetes_version": "1.35.0",
        }
        calls = []
        original_run = config.run

        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            if "get" in command:
                raise subprocess.CalledProcessError(1, command)
            return ""

        config.run = fake_run
        try:
            config.ensure_machine_goal(args, metadata)
        finally:
            config.run = original_run

        self.assertTrue(any("create" in call[0] for call in calls))
        self.assertEqual(calls[-1][0][3:6], ["patch", "configmap", "aks-flex-machines"])

    def test_bootstrap_script_verifies_checksum_and_preserves_secret_config(self):
        node_config = {"azure": {"bootstrapToken": {"token": "abcdef.0123456789abcdef"}}}
        script = config.render_bootstrap_script(node_config, "v0.1.5-rc.1")
        self.assertIn("sha256sum --check --strict", script)
        self.assertIn("umask 077", script)
        self.assertIn('chmod 0600 "${config_tmp}"', script)
        self.assertIn('mv -f "${config_tmp}" /etc/aks-flex-node/config.json', script)
        self.assertIn("aks-flex-node preflight", script)
        self.assertIn("umask 022", script)
        self.assertIn("already converged", script)
        self.assertIn("refusing an in-place overwrite", script)
        encoded = script.split("printf '%s' '", 1)[1].split("' | base64", 1)[0]
        self.assertEqual(json.loads(base64.b64decode(encoded)), node_config)

    def test_cloud_init_embeds_bootstrap_script(self):
        script = "#!/bin/bash\necho ready\n"
        cloud_init = config.render_cloud_init(script)
        encoded = cloud_init.split("content: ", 1)[1].splitlines()[0]
        self.assertEqual(base64.b64decode(encoded).decode(), script)
        self.assertIn("permissions: \"0700\"", cloud_init)

    def test_sensitive_output_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "node" / "cloud-init.yaml"
            config.write_sensitive_text("secret\n", str(output))
            self.assertEqual(output.read_text(), "secret\n")
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_argument_validation(self):
        self.assertEqual(config.validate_node_name("flex-node-1"), "flex-node-1")
        self.assertEqual(config.validate_ip_address("10.0.0.4"), "10.0.0.4")
        self.assertEqual(config.validate_release_version("v0.1.5-rc.1"), "v0.1.5-rc.1")
        with self.assertRaises(argparse.ArgumentTypeError):
            config.validate_node_name("Flex_Node")
        with self.assertRaises(argparse.ArgumentTypeError):
            config.validate_node_name("site.-node")
        with self.assertRaises(argparse.ArgumentTypeError):
            config.validate_ip_address("not-an-ip")
        with self.assertRaises(argparse.ArgumentTypeError):
            config.validate_release_version("latest")

    def test_prepare_node_orchestrates_cluster_and_payload(self):
        args = prepare_args()
        metadata = {
            "subscription_id": "sub",
            "tenant_id": "tenant",
            "resource_id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.ContainerService/managedClusters/aks",
            "location": "eastus2",
            "kubernetes_version": "1.35.0",
            "dns_service_ip": "10.0.0.10",
        }
        cluster_data = {
            "token": "abcdef.0123456789abcdef",
            "server_url": "https://example.hcp.eastus2.azmk8s.io:443",
            "ca_cert_data": "Y2E=",
        }

        with (
            mock.patch.object(config, "require_command") as require_command,
            mock.patch.object(config, "load_admin_kubeconfig") as load_kubeconfig,
            mock.patch.object(config, "run") as run,
            mock.patch.object(config, "ensure_flex_controller") as ensure_controller,
            mock.patch.object(config, "cluster_metadata", return_value=metadata),
            mock.patch.object(config, "bootstrap_cluster_data", return_value=cluster_data),
            mock.patch.object(config, "ensure_machine_goal") as ensure_goal,
            mock.patch.object(config, "write_sensitive_text") as write_output,
        ):
            config.prepare_node(args)

        self.assertEqual(require_command.call_count, 2)
        load_kubeconfig.assert_called_once_with(args)
        run.assert_called_once_with(["kubectl", "apply", "-f", "-"], input_text=config.RBAC_MANIFEST)
        ensure_controller.assert_called_once_with("v0.1.5-rc.1", None)
        ensure_goal.assert_called_once()
        payload, output_path = write_output.call_args.args
        self.assertTrue(payload.startswith("#cloud-config\n"))
        self.assertEqual(output_path, "-")

    def test_release_bom_enumerates_artifacts_and_runtime_contract(self):
        args = argparse.Namespace(
            aks_flex_node_version="v0.1.5-rc.1",
            git_commit="abcdef123456",
            controller_digest="sha256:" + "1" * 64,
            unbounded_version="v0.1.24-rc.9",
        )
        bom = config.render_release_bom(args)
        self.assertEqual(bom["release"]["tag"], "v0.1.5-rc.1")
        self.assertEqual(bom["unboundedModuleVersion"], "v0.1.24-rc.9")
        self.assertEqual(bom["controllerImage"]["digest"], "sha256:" + "1" * 64)
        self.assertIn("aks-flex-config", bom["artifacts"])
        self.assertIn("aks-flex-controller-v0.1.5-rc.1.yaml", bom["artifacts"])
        self.assertEqual(
            bom["nodeBootstrapDefaults"]["containerdVersion"],
            config.DEFAULT_CONTAINERD_VERSION,
        )


if __name__ == "__main__":
    unittest.main()