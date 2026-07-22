#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export AKS_FLEX_NODE_REPOSITORY="example/AKSFlexNode"
# shellcheck source=install.sh
source "${SCRIPT_DIR}/install.sh"

test_dir=$(mktemp -d)
trap 'rm -rf "${test_dir}"' EXIT

asset="aks-flex-node-linux-amd64.tar.gz"
binary="aks-flex-node-linux-amd64"
printf '#!/bin/sh\necho test\n' > "${test_dir}/${binary}"
chmod 0755 "${test_dir}/${binary}"
tar -czf "${test_dir}/${asset}" -C "${test_dir}" "${binary}"
(
    cd "${test_dir}"
    sha256sum "${asset}" > checksums.txt
)

AKS_FLEX_NODE_DOWNLOAD_URL="file://${test_dir}/${asset}"
AKS_FLEX_NODE_CHECKSUMS_URL="file://${test_dir}/checksums.txt"
downloaded=$(download_binary vtest linux amd64)
test -x "${downloaded}"
test "${REPO}" = "example/AKSFlexNode"

printf '%064d  %s\n' 0 "${asset}" > "${test_dir}/bad-checksums.txt"
if (
    AKS_FLEX_NODE_CHECKSUMS_URL="file://${test_dir}/bad-checksums.txt"
    download_binary vtest linux amd64 >/dev/null 2>&1
); then
    echo "download_binary accepted a corrupt checksum" >&2
    exit 1
fi

echo "install checksum tests passed"