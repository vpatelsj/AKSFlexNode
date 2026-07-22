# AKS Flex Config Helper

`scripts/aks-flex-config` is a workstation-side helper for generating AKS Flex Node config files from AKS cluster metadata.

The helper uses Azure CLI and `kubectl` to prepare cluster-side bootstrap material. It can render a standalone config for manual installation or a complete checksum-verified shell/cloud-init payload for a released AKS Flex Node version.

## Prerequisites

- Azure CLI authenticated to the subscription that contains the AKS cluster.
- `python3` on the workstation.
- `kubectl` on the workstation for `setup-node-rbac` and `--bootstrap-token` config generation.
- Permission to run `az aks get-credentials --admin` and create Kubernetes `ClusterRoleBinding` and bootstrap token `Secret` objects.

## Save The Helper

```bash
curl -fsSLo ./aks-flex-config https://raw.githubusercontent.com/Azure/AKSFlexNode/main/scripts/aks-flex-config
chmod +x ./aks-flex-config
```

## Shared Cluster Arguments

Most commands use the same AKS cluster selectors:

```bash
RESOURCE_GROUP="<resource-group>"
CLUSTER_NAME="<cluster-name>"
SUBSCRIPTION_ID="<subscription-id>"
AGENT_POOL_NAME="${AGENT_POOL_NAME:-aksflexnodes}"
```

| Flag | Required | Description |
|------|----------|-------------|
| `--resource-group` | yes | Resource group that contains the AKS cluster. |
| `--cluster-name` | yes | AKS cluster name. |
| `--subscription` | no | Azure subscription ID or name. Defaults to the current Azure CLI account subscription. |

## Prepare And Bootstrap A Node

`prepare-node` is the release-oriented bootstrap-token workflow. It:

1. Loads AKS admin credentials and applies AKS Flex Node bootstrap RBAC.
2. Installs the version-pinned in-cluster Flex Controller and waits for it.
3. Creates a 24-hour bootstrap token and publishes the node's machine goal.
4. Emits a shell script or cloud-init document containing the node config.
5. Makes the target verify the released agent archive checksum, install required host packages, run preflight, and start the agent.

Generate cloud-init before creating an Ubuntu 22.04 or 24.04 VM:

```bash
AKS_FLEX_NODE_VERSION="<release-tag>"
NODE_NAME="flex-node-1"
NODE_PRIVATE_IP="10.92.1.4"

./aks-flex-config prepare-node \
  --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER_NAME" \
  --subscription "$SUBSCRIPTION_ID" \
  --agent-pool-name "$AGENT_POOL_NAME" \
  --node-name "$NODE_NAME" \
  --node-ip "$NODE_PRIVATE_IP" \
  --aks-flex-node-version "$AKS_FLEX_NODE_VERSION" \
  --variant cloud-init \
  --output ./aks-flex-node-cloud-init.yaml
```

Pass the resulting file as VM custom data. For an already-running host, select `--variant script` and run the output as root:

```bash
./aks-flex-config prepare-node \
  --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER_NAME" \
  --subscription "$SUBSCRIPTION_ID" \
  --node-name "$NODE_NAME" \
  --node-ip "$NODE_PRIVATE_IP" \
  --aks-flex-node-version "$AKS_FLEX_NODE_VERSION" \
  --variant script \
  --output ./aks-flex-node-bootstrap.sh

sudo bash ./aks-flex-node-bootstrap.sh
```

Both output variants contain a bootstrap token and are written with mode `0600`. Delete the local payload after provisioning. The token expires after 24 hours. Use `--controller-manifest-url` for a trusted mirror, or `--skip-controller-install` only when the matching controller is already installed.

The command pins the tested runtime defaults. Override `--oci-image`, `--containerd-version`, `--runc-version`, `--cni-version`, or `--npd-version` only as a coordinated compatibility change.

## Setup Node RBAC

Run this once per cluster for bootstrap-token joins:

```bash
./aks-flex-config setup-node-rbac \
  --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER_NAME" \
  --subscription "$SUBSCRIPTION_ID"
```

This applies the bootstrap-related `ClusterRoleBinding` objects for the `system:bootstrappers:aks-flex-node` group.

## Generate Node Config

`generate-node-config` fetches AKS metadata and renders a config file. It requires exactly one auth mode.

Use `--output <path>` to write a config file with mode `0600`. If omitted, the config is written to stdout.
The helper writes `azure.resourceManagerEndpoint` with the public ARM endpoint and writes the selected agent pool name to `azure.targetAgentPoolName`. If `--agent-pool-name` is omitted, it defaults to the historical `aksflexnodes` pool name.

| Flag | Required | Description |
|------|----------|-------------|
| `--agent-pool-name` | no | FlexNode agent pool name written into the generated config. Defaults to `aksflexnodes`. |

### Bootstrap Token

```bash
./aks-flex-config generate-node-config \
  --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER_NAME" \
  --subscription "$SUBSCRIPTION_ID" \
  --agent-pool-name "$AGENT_POOL_NAME" \
  --bootstrap-token \
  --output ./aks-flex-node-config.json
```

Bootstrap-token mode creates a Kubernetes bootstrap token `Secret`, reads the AKS API server and CA data from kubeconfig, and includes those values plus the AKS DNS service IP in the generated config.

### Managed Identity

```bash
./aks-flex-config generate-node-config \
  --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER_NAME" \
  --subscription "$SUBSCRIPTION_ID" \
  --agent-pool-name "$AGENT_POOL_NAME" \
  --identity \
  --output ./aks-flex-node-config.json
```

For user-assigned managed identity, pass the client ID with `--username`:

```bash
./aks-flex-config generate-node-config \
  --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER_NAME" \
  --subscription "$SUBSCRIPTION_ID" \
  --agent-pool-name "$AGENT_POOL_NAME" \
  --identity \
  --username "<managed-identity-client-id>" \
  --output ./aks-flex-node-config.json
```

### Service Principal

Service principal flags follow the `az login --service-principal` convention:

```bash
./aks-flex-config generate-node-config \
  --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER_NAME" \
  --subscription "$SUBSCRIPTION_ID" \
  --agent-pool-name "$AGENT_POOL_NAME" \
  --service-principal \
  --username "<client-id>" \
  --password "<client-secret>" \
  --tenant "<tenant-id>" \
  --output ./aks-flex-node-config.json
```

`--tenant` defaults to the current Azure CLI tenant when omitted.

### Azure Arc

```bash
./aks-flex-config generate-node-config \
  --resource-group "$RESOURCE_GROUP" \
  --cluster-name "$CLUSTER_NAME" \
  --subscription "$SUBSCRIPTION_ID" \
  --agent-pool-name "$AGENT_POOL_NAME" \
  --arc \
  --arc-machine-name "<arc-machine-name>" \
  --arc-resource-group "<arc-resource-group>" \
  --arc-location "<arc-location>" \
  --output ./aks-flex-node-config.json
```

## Copy To Host

After generating the config, copy it to the target host and place it under `/etc/aks-flex-node/config.json` with restrictive permissions:

```bash
TARGET_HOST="<user>@<host>"

scp ./aks-flex-node-config.json "$TARGET_HOST:/tmp/aks-flex-node-config.json"
```

On the target host:

```bash
sudo su
install -d -m 0755 /etc/aks-flex-node
install -m 0600 /tmp/aks-flex-node-config.json /etc/aks-flex-node/config.json
```

Then start AKS Flex Node with a standard `022` umask. The config file stays `0600`, while bootstrap-created nspawn rootfs paths remain traversable by non-root service users such as `dbus`:

```bash
umask 022
aks-flex-node start --config /etc/aks-flex-node/config.json
```
