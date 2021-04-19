#!/usr/bin/env python3
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

    message = os.environ['INPUT_COMMITMESSAGE']
    print(f'Commit message: {message}')

    print(f'Checking commit {githooks.get_sha()} by {githooks.get_user()} in {githooks.get_branch()}')

    files = githooks.get_commit_files()
    print(f'Checking {githooks.get_event()} modified files:')
    print('  ' + '\n  '.join(files['M']))
    print(f'Checking {githooks.get_event()} new files:')
    print('  ' + '\n  '.join(files['A']))

    retval = 0

    retval += githooks.check_commit_msg(message, files['M'] + files['A'])

    if githooks._is_pull_request():
        retval += githooks.check_do_not_merge(files['M'])
        retval += githooks.check_do_not_merge(files['A'], new_files=True)

    retval += githooks.remove_trailing_white_space(files['M'], dry_run=True)
    retval += githooks.remove_trailing_white_space(files['A'], new_files=True,
                                                   dry_run=True)
    retval += githooks.check_filenames(files['M'] + files['A'])
    retval += githooks.check_eol(files['M'] + files['A'])
    retval += githooks.check_content(files['M'] + files['A'])

    sys.exit(retval)
