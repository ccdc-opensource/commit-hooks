#!/usr/bin/env python3
'''
This is a github action entry point.

'''

import os
import sys

sys.path.insert(0, './main')
import githooks

if __name__ == '__main__':

#    for k,v in os.environ.items():
#        print(f'{k}: {v}')
    print(f'Checking {githooks.get_event()} by {githooks.get_user()} '
          f'in {githooks.get_branch()}')

    print(os.environ.get('INPUT_FILES', ''))
    print(os.environ.get('INPUT_NEW_FILES', 0))
    files = os.environ.get('INPUT_FILES', '')
    new_files = bool(int(os.environ.get('INPUT_NEW_FILES', 0)))
    print(files)
    print(files.split(','))
    print(new_files)

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
