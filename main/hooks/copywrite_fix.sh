#!/usr/bin/env bash
set -euo pipefail
command -v copywrite >/dev/null 2>&1 || { echo "copywrite not found on PATH"; exit 1; }
copywrite headers --config="$(dirname "${BASH_SOURCE[0]}")/main/copywrite/.copywrite.hcl"