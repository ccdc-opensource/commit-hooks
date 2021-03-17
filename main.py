#!/usr/bin/env python3
'''
This is a github action entry point.

'''

import sys

sys.path.insert(0, './main')
import githooks

if __name__ == '__main__':

    #import os
    #for k,v in os.environ.items():
    #    print(f'{k}: {v}')
    print(f'Checking {githooks.get_event()} by {githooks.get_user()}'
          f'in {githooks.get_branch()}')

    filepath = sys.argv[1]
    githooks.trim_trailing_whitespace_in_file(filepath, True)

    retval = 0
    retval += githooks.check_do_not_merge_in_file(filepath, True)
    retval += githooks.check_filename(filepath)
    data = githooks.get_file_content(filepath)
    if data is not None:
        retval += githooks.check_file_content(filepath, data)

    sys.exit(retval)
