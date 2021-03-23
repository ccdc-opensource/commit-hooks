#!/usr/bin/env python3
'''
This is a github action entry point.

This github action does some checks on changed files.

'''

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'main'))
import githooks

if __name__ == '__main__':

    print(f'Checking {githooks.get_event()} commit {githooks.get_sha()} '
          f'by {githooks.get_user()} in {githooks.get_branch()}')

    files = githooks.get_commit_files()

    retval = 0

    retval += githooks.remove_trailing_white_space(files['M'], in_place=False)
    retval += githooks.remove_trailing_white_space(files['A'], new_files=True,
                                                   in_place=False)
    retval += githooks.check_do_not_merge(files['M'])
    retval += githooks.check_do_not_merge(files['A'], new_files=True)
    retval += githooks.check_filenames(files['M'] + files['A'])
    retval += githooks.check_eol(files['M'] + files['A'])
    retval += githooks.check_content(files['M'] + files['A'])

    sys.exit(retval)
