#!/usr/bin/env python3
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
'''
This is a github action entry point.

This github action does some checks on changed files.

'''

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'main'))
import githooks

if __name__ == '__main__':

    message = os.getenv('INPUT_COMMITMESSAGE')

    print(f'Checking commit {githooks.get_sha()} by {githooks.get_user()} in {githooks.get_branch()}')
    print(f'Commit message: {message}')

    files = githooks.get_commit_files()
    repo = githooks.get_repo()
    print(f'Checking {githooks.get_event()} modified files:')
    print('  ' + '\n  '.join(files['M']))
    print(f'Checking {githooks.get_event()} new files:')
    print('  ' + '\n  '.join(files['A']))

    retval = 0

    retval += githooks.check_commit_msg(message, files['M'] + files['A'], repo)

    if githooks._is_pull_request():
        retval += githooks.check_do_not_merge(files['M'])
        retval += githooks.check_do_not_merge(files['A'], new_files=True)

    retval += githooks.check_filenames(files['M'] + files['A'])
    retval += githooks.check_eol(files['M'] + files['A'])
    retval += githooks.check_content(files['M'] + files['A'])

    sys.exit(retval)
