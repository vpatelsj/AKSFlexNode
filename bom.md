Below is the complete artifact inventory for the experiment. Nothing else should be downloaded without first updating this list.

Define:

```text
FLEX_VERSION=v0.1.5.alpha-4
UNBOUNDED_VERSION=v0.1.24-rc.9
K8S_VERSION=<selected during Step 1>
ARCH=amd64
```

**AKSFlexNode Release Assets**

Public base URL:

```text
https://github.com/vpatelsj/AKSFlexNode/releases/download/v0.1.5.alpha-4/
```

All 11 assets:

```text
aks-flex-config
aks-flex-controller-v0.1.5.alpha-4.yaml
aks-flex-controller-v0.1.5.alpha-4.yaml.bundle.json
aks-flex-node-linux-amd64.tar.gz
aks-flex-node-linux-amd64.tar.gz.spdx.json
aks-flex-node-linux-arm64.tar.gz
aks-flex-node-linux-arm64.tar.gz.spdx.json
aks-flex-node-release-bom-v0.1.5.alpha-4.json
aks-flex-node-release-bom-v0.1.5.alpha-4.json.bundle.json
checksums.txt
checksums.txt.bundle.json
```

For this experiment, we will download only the helper, controller manifest/bundle, amd64 binary/SBOM, BOM/bundle, and checksums/bundle.

**AKSFlexNode Image**

```text
ghcr.io/vpatelsj/aks-flex-controller:v0.1.5.alpha-4
sha256:4091beaa9e6d7f6474dca4df82158a5195cf8f520fca23c6c9d7eedf4bb8e516
```

Platforms: `linux/amd64`, `linux/arm64`.

**Unbounded Release Assets**

`rc.9` is currently a draft, so workstation assets require authenticated download:

```bash
gh release download -R Azure/unbounded v0.1.24-rc.9
```

All 38 assets:

```text
checksums.txt
checksums.txt.bundle.json
kubectl-unbounded-{darwin,linux}-{amd64,arm64}.tar.gz
kubectl-unbounded-{darwin,linux}-{amd64,arm64}.tar.gz.sbom.json
unbounded-agent-linux-{amd64,arm64}.tar.gz
unbounded-agent-linux-{amd64,arm64}.tar.gz.sbom.json
unbounded-manifests-v0.1.24-rc.9.tar.gz
unbounded-manifests-v0.1.24-rc.9.tar.gz.bundle.json
unbounded-operator-v0.1.24-rc.9.yaml
unbounded-operator-v0.1.24-rc.9.yaml.bundle.json
unbounded-release-bom-v0.1.24-rc.9.json
unbounded-release-bom-v0.1.24-rc.9.json.bundle.json
unbounded-storage-linux-{amd64,arm64}.tar.gz
unbounded-storage-linux-{amd64,arm64}.tar.gz.sha256
unbounded-storage-linux-{amd64,arm64}.tar.gz.spdx.json
unbounded-storage-linux-{amd64,arm64}.tar.gz.bundle.json
unbounded.yaml
sbom-{gantry,host-ubuntu2404,machina,machine-ops-controller,metalman,netboot,orca,unbounded-operator,unbounded-storage-supervisor}.spdx.json
```

We will download only Linux amd64 `kubectl-unbounded`, manifests, operator manifest, BOM, checksums, and their bundles. We will **not** use `unbounded-agent` because AKSFlexNode owns the host lifecycle.

**Unbounded Images Used**

```text
unbounded-operator:v0.1.24-rc.9
sha256:1c66cfa5c75b05a6cc597029c470bbb14c5a6f59a2e8947c8d658c9fe849cf6e

unbounded-net-controller:v0.1.24-rc.9
sha256:16cf510f4cda5a9e84f91c8d94c486e4ae32354add482d35f04c7d9ca504b139

unbounded-net-node:v0.1.24-rc.9
sha256:e586953da71102cd194232739cf0a49148f619199b4fe54ea29e61b3d03c1fa8

gantry:v0.1.24-rc.9
sha256:6fb3017d273508e0ca9fe9a5cf42f44312118bc383f8bea7bf1b45bc7645e4ca
```

All come from `ghcr.io/azure/<name>:v0.1.24-rc.9` and support amd64/arm64.

**Released but Not Pulled**

These components remain disabled:

```text
machina
machine-ops-controller
metalman
netboot
orca
unbounded-storage-supervisor
host-ubuntu2404
unbounded-agent
unbounded-storage binaries
```

Their release references exist, but they are outside this experiment.

**FlexNode Runtime Downloads**

The VM join payload pulls:

```text
AKSFlexNode binary  v0.1.5.alpha-4  GitHub fork release
Rootfs              v20260619       ghcr.io/azure/agent-ubuntu2404
Rootfs digest       sha256:962aa78fd297b465ce3b134e3943e090a0ae79008e8caca809e372a1eaceb5f6
containerd          2.0.4           github.com/containerd/containerd/releases
runc                1.1.12          github.com/opencontainers/runc/releases
CNI plugins         1.5.1           github.com/containernetworking/plugins/releases
NPD                 v1.35.1         github.com/kubernetes/node-problem-detector/releases
crictl              K8S minor.0     github.com/kubernetes-sigs/cri-tools/releases
kubelet             K8S_VERSION     https://dl.k8s.io
kubectl             K8S_VERSION     https://dl.k8s.io
kube-proxy binary   K8S_VERSION     https://dl.k8s.io
pause image         3.9             mcr.microsoft.com/oss/v2/kubernetes/pause
pause digest        sha256:be5ab7d7af9eec377fd13bbd650fe6e1427fc3f8b61a09edd3b5276c506db624
```

Unbounded-Net images additionally contain CNI plugins `v1.9.1`, but the installer skips binaries already installed by AKSFlexNode. The effective FlexNode CNI binaries may therefore remain `v1.5.1`; this is a known version mismatch to observe.

**Additional Cluster Images**

```text
kube-proxy: mcr.microsoft.com/oss/v2/kubernetes/kube-proxy:v${K8S_VERSION}
Gantry helper: mcr.microsoft.com/cbl-mariner/busybox:2.0
Gantry helper digest: sha256:e4fb4d51fc9b70d6cdc1ce66a0af02ab40554d2ca632e1d188fabc760e432fdd
```

Azure CNI, CoreDNS, AKS kube-proxy, and other managed add-ons are selected and pulled by AKS. Their exact references can only be recorded after cluster creation.