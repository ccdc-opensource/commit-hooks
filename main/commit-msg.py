#!/usr/bin/env python3
'''
A hook to check commit massage.

This is currently used to decide if large file should be commited.

'''

import githooks

if __name__ == '__main__':
    exit(githooks.commit_msg_hook())
