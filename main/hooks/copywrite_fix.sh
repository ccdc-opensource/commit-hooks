#!/usr/bin/env bash
set -euo pipefail
command -v copywrite >/dev/null 2>&1 || { echo "copywrite not found on PATH"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_PATH="${HOOK_ROOT}/main/copywrite/.copywrite.hcl"

export COPYWRITE_HOOK_ROOT="${HOOK_ROOT}"
copywrite headers --config="${CONFIG_PATH}"
