#!/usr/bin/env python3
#
# This code is Copyright (C) 2026 The Cambridge Crystallographic Data Centre (CCDC)
# of 12 Union Road, Cambridge CB2 1EZ, UK and a proprietary work of CCDC. This
# code may not be used, reproduced, translated, modified, disassembled or
# copied, except in accordance with a valid licence agreement with CCDC and
# may NOT be disclosed or redistributed in any form, either in whole or in
# part, to any third party. All copies of this code made in accordance with a
# valid licence agreement as referred to above must contain this copyright
# notice.
#
# No representations, warranties, or liabilities are expressed or implied in
# the supply of this code by CCDC, its servants or agents, except where such
# exclusion or limitation is prohibited, void or unenforceable under governing
# law.
#
'''
A hook to check commit massage.

This is currently used to decide if large file should be commited.

'''

import githooks

if __name__ == '__main__':
    exit(githooks.commit_msg_hook())
