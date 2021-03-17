#!/usr/bin/env python3
'''
This is a github action entry point.

This github action does some checks on changed files.

'''

import os
import sys

sys.path.insert(0, './main')
import githooks

if __name__ == '__main__':

    print(f'Checking {githooks.get_event()} by {githooks.get_user()} '
          f'in {githooks.get_branch()}')

    files = os.environ.get('INPUT_FILES', '')
    new_files = bool(int(os.environ.get('INPUT_NEW_FILES', 0)))

    retval = 0

    if files:
        for filepath in files.split(','):
            githooks.trim_trailing_whitespace_in_file(filepath, new_files)

            retval += githooks.check_do_not_merge_in_file(filepath, new_files)
            retval += githooks.check_filename(filepath)
            data = githooks.get_file_content(filepath)
            if data is not None:
                retval += githooks.check_file_content(filepath, data)

    sys.exit(retval)
