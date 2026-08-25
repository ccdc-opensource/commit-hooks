#!/usr/bin/env bash
#
# This code is Copyright (C) 2026 The Cambridge Crystallographic Data Centre
# (CCDC) of 12 Union Road, Cambridge CB2 1EZ, UK and a proprietary work of CCDC.
# This code may not be used, reproduced, translated, modified, disassembled or
# copied, except in accordance with a valid licence agreement with CCDC and may
# not be disclosed or redistributed in any form, either in whole or in part, to
# any third party. All copies of this code made in accordance with a valid
# licence agreement as referred to above must contain this copyright notice.
#
# No representations, warranties, or liabilities are expressed or implied in the
# supply of this code by CCDC, its servants or agents, except where such
# exclusion or limitation is prohibited, void or unenforceable under governing
# law.
#
set -euo pipefail
command -v copywrite >/dev/null 2>&1 || { echo "copywrite not found on PATH"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_PATH="${HOOK_ROOT}/main/copywrite/.copywrite.hcl"

export COPYWRITE_HOOK_ROOT="${HOOK_ROOT}"
copywrite headers --config="${CONFIG_PATH}" --plan