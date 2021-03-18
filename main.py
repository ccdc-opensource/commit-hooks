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

    print(f'Checking {githooks.get_event()} commit {githooks.get_sha()} '
          f'by {githooks.get_user()} in {githooks.get_branch()}')

    #    for k,v in os.environ.items():
    #        if k.startswith('GITHUB_'):
    #            print(f'{k}: {v}')

    files = os.environ.get('INPUT_FILES', '')
    new_files = bool(int(os.environ.get('INPUT_NEW_FILES', 0)))

    retval = 0

    if files:
        for filepath in files.split(','):
            print(filepath)
            retval += githooks.trim_trailing_whitespace_in_file(
                    filepath, new_file=new_files, in_place=False)
            retval += githooks.check_do_not_merge_in_file(filepath, new_files)
            retval += githooks.check_filename(filepath)
            data = githooks.get_file_content(filepath)
            if data is not None:
                retval += githooks.check_file_content(filepath, data)

    sys.exit(retval)
