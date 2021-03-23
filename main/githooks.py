#!/usr/bin/env python3
'''
Module for a git hook.

'''

from collections import defaultdict
from pathlib import Path
import os
import platform
import re
import subprocess
import unittest
import sys


# Absolute file size limit (in MB) - it's 100MB on github.com
HARD_SIZE_THRESHOLD = 99.0
# Internal file size limit (in MB) - allow if commit message includes marker
SOFT_SIZE_THRESHOLD = 10.0
# Large file marker in commit message
LARGE_FILE_MARKER = 'LARGE_FILE'
# Check file content if it has these extensions
CHECKED_EXTS = [
        '.bat',
        '.c',
        '.cgi',
        '.cmake',
        '.cpp',
        '.cs',
        '.css',
        '.F',
        '.f',
        '.h',
        '.inc',
        '.inl',
        '.java',
        '.js',
        '.php',
        '.pri',
        '.pro',
        '.ps1',
        '.py',
        '.sed',
        '.sh',
        '.svc',
        '.tpl',
        ]
# File types that need a terminating newline
TERMINATING_NEWLINE_EXTS = ['.c', '.cpp', '.h', '.inl']


def _get_output(command, cwd='.'):
    return subprocess.check_output(command, shell=True, cwd=cwd).decode()


def _is_github_event():
    if 'GITHUB_EVENT_NAME' in os.environ:
        return True
    return False


def _skip(filename, msg):
    print(f'SKIP {filename}: {msg}')


def _fail(msg):
    print(f'COMMIT FAIL: {msg}')


def _is_windows():
    return platform.system() == 'Windows'


def get_user():
    '''Get user making the commit'''
    if _is_github_event():
        return os.environ['GITHUB_ACTOR']
    else:
        output = _get_output('git var GIT_AUTHOR_IDENT')
        match = re.match(r'^(.+) <', output)
        return match.group(1)


def get_branch():
    '''Get current branch'''
    if _is_github_event():
        if os.environ['GITHUB_EVENT_NAME'] == 'pull_request':
            return os.environ['GITHUB_HEAD_REF']
        else:
            return os.environ['GITHUB_REF'].split('/')[-1]
    else:
        return _get_output('git branch').split()[-1]


def get_sha():
    '''Get the commit sha'''
    return _get_output(f'git rev-parse {get_branch()}')


def get_event():
    '''Get the git event'''
    if _is_github_event():
        return os.environ['GITHUB_EVENT_NAME']
    else:
        return 'commit'


def get_branch_files():
    '''Get all files in branch'''
    branch = get_branch()
    return _get_output(f'git ls-tree -r {branch} --name-only').splitlines()


def add_file_to_index(filename):
    '''Add file to current commit'''
    return _get_output(f'git add {filename}')


def get_commit_files():
    '''Get files in current commit

    Return a dictionary:
        'M': <list of modified files>
        'A': <list of new files>

    '''
    if _is_github_event():
        if os.environ['GITHUB_EVENT_NAME'] == 'pull_request':
            output = _get_output(f'git diff --name-status remotes/origin/{os.environ["GITHUB_BASE_REF"]}..remotes/origin/{os.environ["GITHUB_HEAD_REF"]} --')
        else:
            output = _get_output('git diff --name-status HEAD~.. --')
    else:
        output = _get_output('git diff-index HEAD --cached')
    result = defaultdict(list)
    for line in output.splitlines():
        parts = line.split()
        if parts[-2] in ['M', 'A']:
            result[parts[-2]].append(parts[-1])
    return result


def parse_diff_header(header_line):
    changed_lines = []
    match = parse_diff_header.pattern.match(header_line)
    start = int(match.group(1))
    if match.group(2):
        for num in range(int(match.group(3))):
            changed_lines.append(start + num)
    else:
        changed_lines.append(start)
    return changed_lines
parse_diff_header.pattern = re.compile(r'^@@\s[^\s]+\s\+?(\d+)(,(\d+))?\s@@.*')


class TestParseDiffHeaderPattern(unittest.TestCase):
    def test_various_strings(self):
        def _test(input, output):
            self.assertListEqual(output, parse_diff_header(input))
        _test('@@ -142 +178,3 @@', [178, 179, 180])
        _test('@@ -142 +178,7 @@', [178, 179, 180, 181, 182, 183, 184])


def get_changed_lines(modified_file):
    '''New and modified lines in modified file in current commit'''
    if _is_github_event():
        if os.environ['GITHUB_EVENT_NAME'] == 'pull_request':
            output = _get_output(
                    f'git diff --unified=0 remotes/origin/{os.environ["GITHUB_BASE_REF"]}..remotes/origin/{os.environ["GITHUB_HEAD_REF"]} -- {modified_file}')
        else:
            output = _get_output(
                    f'git diff --unified=0 HEAD~ {modified_file}')
    else:
        output = _get_output(
                f'git diff-index HEAD --unified=0 {modified_file}')

    lines = []
    for line in output.splitlines():
        if not line.startswith('@@'):
            continue
        lines.extend(parse_diff_header(line))
    return lines


def get_config_setting(setting):
    '''Get the value of a config setting'''
    try:
        return _get_output(f'git config --get {setting}').strip()
    except subprocess.CalledProcessError:
        return None


def check_eol(files):
    '''Check line endings if autocrlf is not configured correctly.

    If autocrlf is configured as recommended, we skip this check.

    Recommended configuration:
        1. On Windows: `git config --global core.autocrlf true`
        2. Otherwise (including WSL): `git config --global core.autocrlf input`

    Otherwise check all the text files for LF line endings.
    '''
    autocrlf = get_config_setting('core.autocrlf')
    if _is_windows():
        if autocrlf == 'true':
            return 0
    else:
        if autocrlf == 'input':
            return 0

    # As the client environment is not configured with autocrlf
    # we need to ensure that every text file does not contain CRLF.
    for filename in files:
        try:
            with open(filename, 'rb') as fileobj:
                data = fileobj.read().decode()
        except UnicodeDecodeError:
            continue

        # Skip binary file
        if '\0' in data:
            continue

        if data.find('\r\n') != -1:
            _fail(f'Bad line endings in {filename}')
            return 1
    return 0


def check_do_not_merge_in_file(filename, new_file=False):
    '''Check for "do not merge" in a filename'''
    with open(filename, 'rb') as fileobj:
        lines = fileobj.read().decode().splitlines(True)

    if new_file:
        line_nums = range(1, len(lines)+1)
    else:
        line_nums = get_changed_lines(filename)

    for line_num in line_nums:
        try:
            line = lines[line_num-1]
        except IndexError as exc:
            print(f'Error {exc}: {line_num-1} in {filename}')
            continue
        if 'do not merge' in line.lower():
            _fail(f'Found DO NOT MERGE in "{filename}".\n'
                  'Run "git merge --abort" to start again, '
                  f'or remove {filename} from index before completing the '
                  'merge with "git commit".')
            return 1

    return 0


def check_do_not_merge(files, new_files=False):
    '''Check for "do not merge" in files

    This check is case insensitive.

    Note that if found this will abort the merge, leaving it in a merge
    conflict resolution state. User should either simply
        1. Run "git merge --abort", or
        2. Fix the issue (eg. by removing the offending file or part from the
           index) before doing "git commit" to complete the merge.

    '''
    retval = 0
    for filename in files:
        retval += check_do_not_merge_in_file(filename, new_files)
    return retval


def trim_trailing_whitespace(string):
    '''Return a string with trailing white spaces removed'''
    return trim_trailing_whitespace.pattern.sub(r"\1", string)
trim_trailing_whitespace.pattern = re.compile(r"\s*?(\r?\n|$)")


class TestTrailingWhitespacePattern(unittest.TestCase):
    def test_various_strings(self):
        def _test(input, output=None):
            if output is None:
                output = input
            self.assertEqual(output, trim_trailing_whitespace(input))
        _test('')
        _test('\n')
        _test('\r\n')
        _test('a')
        _test(' a')
        _test('  a')
        _test('1234')
        _test(u'abcd\xe9')
        _test(' ', '')
        _test(' \n', '\n')
        _test(' \r\n', '\r\n')
        _test(' a ', ' a')
        _test('  a ', '  a')
        _test(' a \r\n  b   \n c\n ', ' a\r\n  b\n c\n')
        _test(u'abcd\xe9 ', u'abcd\xe9')


def trim_trailing_whitespace_in_file(filename, new_file, in_place):
    '''Remove trailing white spaces in new and modified lines in a filename'''
    try:
        with open(filename, 'rb') as fileobj:
            lines = fileobj.read().decode().splitlines(True)
    except UnicodeDecodeError:
        return

    if new_file:
        line_nums = range(1, len(lines)+1)
    else:
        line_nums = get_changed_lines(filename)

    modified_file = False   # if trimming white space in place
    modified_lines = []     # if flagging instead of trimming in place

    for line_num in line_nums:
        try:
            before = lines[line_num-1]
        except IndexError as exc:
            print(f'Error {exc}: {line_num} in {filename}')
            continue
        after = trim_trailing_whitespace(before)
        if before != after:
            if in_place:
                print(f'   Fixed line {line_num}')
                modified_file = True
                lines[line_num-1] = after
            else:
                modified_lines.append(str(line_num))

    if modified_file:
        with open(filename, 'wb') as fileobj:
            lines = ''.join(lines)
            fileobj.write(lines.encode())
        add_file_to_index(filename)

    if modified_lines:
        _fail(f'Found trailing white space in {filename} at lines: '
              ','.join(modified_lines))
        return 1

    return 0


def remove_trailing_white_space(files, new_files=False, in_place=True):
    '''Remove trailing white spaces in all new and modified lines'''
    retval = 0
    for filename in files:
        retval += trim_trailing_whitespace_in_file(filename, new_files,
                                                   in_place)
    return retval


def check_filename(filepath):
    # We permit repository paths to be up to 50 characters long excluding the
    # final slash character.
    # Windows allows paths with up to 259 characters (260 including a
    # terminating null char)
    max_subpath_chars = 208

    # It's easy to add files on Linux that will make the repository unusable
    # on Windows.
    # Windows filename rules are here:
    # http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247.aspx#naming_conventions
    # This checks for those cases and stops the commit if found.

    # Filename must not contain these characters
    ILLEGAL_CHARS = frozenset('\\/:*?"<>|')
    # These names are reserved on Windows
    DEVICE_NAMES = frozenset([
        'con', 'prn', 'aux', 'nul',
        'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
        'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
        ])

    filename = Path(filepath).name
    for ch in filename:
        if ch in ILLEGAL_CHARS or ord(ch) <= 31:
            _fail(f'Illegal character "{ch}" in filename "{filename}".')
            return 1

    if Path(filename).stem in DEVICE_NAMES:
        _fail(f'Illegal filename "{filename}" - reserved on Windows.\n')
        return 1

    if filepath[-1] == '.' or filepath[-1].isspace():
        _fail(f'Illegal file name "{filepath}" - '
              'names are not permitted to end with "." or whitespace.')
        return 1

    try:
        filepath.encode('ascii')
    except UnicodeDecodeError:
        _fail(f'Illegal path "{filepath}" - '
              'only ASCII characters are permitted.')
        return 1

    if len(filepath) > max_subpath_chars:
        _fail(f'File path "{filepath}" is too long, it must be '
              f'{max_subpath_chars} characters or less.')
        return 1

    return 0


def check_filenames(files):
    '''Check file path and name meet requirement.

    For file path, specifically that it's all ASCII and roughly within max
    length on Windows.

    For file name, check for case conflict, that it does not include illegal
    characters or Windows reserved namess, and does not end in a period or
    whitespace.

    '''

    # This issue is only possible on Linux
    if not _is_windows():
        manifest_lower2case = {f.lower(): f for f in get_branch_files()}
        commit_files = get_commit_files()
        for commit_type in commit_files:
            for f in commit_files[commit_type]:
                flower = f.lower()
                if (flower in manifest_lower2case and
                        manifest_lower2case[flower] != f):
                    _fail(f'Case-folding collision between "{f}" and '
                          f'"{manifest_lower2case[flower]}"')
                    return 1
                else:
                    manifest_lower2case[flower] = f

    retval = 0
    for filepath in files:
        retval += check_filename(filepath)
    return retval


def check_username():
    '''Check username of person making the commit

    In git, this is the *author* of the commit.

    Check for reasonable username (ie. made up of alphabets), and that it's
    not a build service account or root account.

    '''

    username = get_user()
    if re.search(r'root|buildman|[^a-zA-Z ]', username) is not None:
        message = 'Bad username "' + username + '"\n'
        if username == 'buildman' or username == 'root':
            message += 'buildman or root user should not be used'
        else:
            message += 'To set this up see https://docs.github.com/en/github/using-git/setting-your-username-in-git'
        _fail(message)
        return 1

    return 0


def check_file_content(filename, data):
    if 'do not commit' in data.lower():
        _fail(f'Found DO NOT COMMIT in "{filename}". '
              'Remove file from index.')
        return 1

    if '\t' in data:
        _fail(f'Found tab characters in "{filename}". Replace with spaces.')
        return 1

    # For file types that need a terminating newline
    if any(map(lambda ext: filename.endswith(ext), TERMINATING_NEWLINE_EXTS)):
        if not data.endswith('\n'):
            _fail(f'Missing terminating newline in {filename}')
            return 1

    # NOTE: Not checking eol

    # Detect common C++ errors that the build-checkers have encountered.
    if any(map(lambda ext: filename.endswith(ext), ['.cpp', '.h', '.inl'])):
        num = 0
        for line in data.splitlines():
            num += 1
            if cpp_include_backslash_pattern.search(line):
                _fail(f'{filename}:{num} - Backslash in #include')
                return 1
            if cpp_throw_std_exception_pattern.search(line):
                _fail(f'{filename}:{num} - std::exception thrown')
                return 1

    return 0
cpp_include_backslash_pattern = re.compile('^\\s*\\#\\s*include\\s*[\\"\\<][^\\"\\>]*\\\\', re.MULTILINE)
cpp_throw_std_exception_pattern = re.compile(r'\bthrow\s+(std\s*::\s*)?exception\s*\(')


class TestCppIncludeBackslashPattern(unittest.TestCase):
    def test_no_path_separator(self):
        self.assertIsNone(
                cpp_include_backslash_pattern.search('#include <iostream>'))
        self.assertIsNone(
                cpp_include_backslash_pattern.search('#include "header.h"'))

    def test_commented_out(self):
        self.assertIsNone(
                cpp_include_backslash_pattern.search('//#include "a\\b"'))

    def test_multiline(self):
        self.assertIsNotNone(
                cpp_include_backslash_pattern.search(
                    'a\nb\n#include "a\\b"\nc\nd\n'))

    def do_test_with_each_separator(self, *args):
        good = "/".join(args)
        bad = "\\".join(args)
        self.assertIsNone(cpp_include_backslash_pattern.search(good))
        self.assertIsNotNone(cpp_include_backslash_pattern.search(bad))

    def test_angle_brackets(self):
        self.do_test_with_each_separator('#include <some', 'path>')

    def test_quotes(self):
        self.do_test_with_each_separator('#include "another', 'file"')

    def test_unusual_characters(self):
        self.do_test_with_each_separator(
                '#include "1', "! 2£$€%^&()", "-_=+[{]};'@#~,.", '`¬¦"')

    def test_space(self):
        self.do_test_with_each_separator(' #include "a', 'b"')
        self.do_test_with_each_separator('  #include "c', 'd"')
        self.do_test_with_each_separator('     #include "e', 'f"')
        self.do_test_with_each_separator('\t#include "e', 'f"')
        self.do_test_with_each_separator('# include "g', 'h"')
        self.do_test_with_each_separator('#  include "i', 'j"')
        self.do_test_with_each_separator('#include"i', 'j"')
        self.do_test_with_each_separator('#include<k', 'l>')
        self.do_test_with_each_separator(
                '     #      include           "       m      ',
                '  n        "     ')

    def test_comment(self):
        self.do_test_with_each_separator(
                '#include "x', 'y"// back\\slashes\\ in comment')


class TestCppThrowStdExceptionPattern(unittest.TestCase):
    def test_find(self):
        self.assertIsNotNone(
                cpp_throw_std_exception_pattern.search(
                    'throw std::exception();'))
        self.assertIsNotNone(
                cpp_throw_std_exception_pattern.search(
                    'throw exception("string")'))
        self.assertIsNotNone(
                cpp_throw_std_exception_pattern.search('throw exception()'))
        self.assertIsNotNone(
                cpp_throw_std_exception_pattern.search(
                    ' {throw exception();}//comment'))

    def test_spaces(self):
        self.assertIsNotNone(
                cpp_throw_std_exception_pattern.search(
                    ' throw  std   ::    exception     (   )  '))

    def test_dont_find_runtime_error(self):
        self.assertIsNone(
                cpp_throw_std_exception_pattern.search(
                    'throw std::runtime_error();'))

    def test_dont_find_variable_named_exception(self):
        self.assertIsNone(
                cpp_throw_std_exception_pattern.search('throw exception'))
        self.assertIsNone(
                cpp_throw_std_exception_pattern.search('throw exception;'))

    def test_dont_find_catch_exception(self):
        self.assertIsNone(
                cpp_throw_std_exception_pattern.search(
                    'catch (std::exception)'))

    def test_match_word_boundaries(self):
        self.assertIsNone(
                cpp_throw_std_exception_pattern.search('throw exceptionblah'))
        self.assertIsNone(
                cpp_throw_std_exception_pattern.search('rethrow exception'))


def get_file_content(filename):
    '''Return the content of a file.

    We do so if:
        1. Filename has certain extensions
        2. The content can be read
        3. It's a text file

    Otherwise return None
    '''
    # Skip file if extension is not in the checked list
    if not any([filename.endswith(checked_ext)
                for checked_ext in CHECKED_EXTS]):
        _skip(filename, 'File extension is excluded')
        return

    # NOTE: ignored_patterns not implemented

    try:
        data = Path(filename).read_text()
    except Exception as exc:
        print(f'Error {exc}: reading {filename}')
        return

    # Skip binary file
    if '\0' in data:
        _skip(filename, 'Not a text file')
        return

    return data


def check_content(files):
    '''Check content of files.

    This only applies to files meeting the conditions:
        1. Filename has certain extensions
        2. The content can be read
        3. It's a text file

    We check that:
        1. It does non contain "DO NOT COMMIT" (case insensitive)
        2. It does not contain tab
        3. For C / C++ source files:
            a. It has no missing newline at the end
            b. It has no backslash in #include
            c. It does not throw std::exception

    '''
    retval = 0

    for filename in files:
        data = get_file_content(filename)
        if data is not None:
            retval += check_file_content(filename, data)

    return retval


def check_commit_msg(message, files):
    '''Check commit message (and file size).

    Abort if file size exceeds hard (github.com) limit.

    If file size exceeds our soft (internal) limit, flag up if commit message
    does not contain required marker.

    '''
    for filename in files:
        size = Path(filename).stat().st_size / 1024**2
        if size > HARD_SIZE_THRESHOLD:
            _fail(f'{filename} is larger than the github limit. '
                  'Remove file from index.')
            return 1
        elif size > SOFT_SIZE_THRESHOLD:
            if LARGE_FILE_MARKER not in message:
                _fail(f'{filename} is larger than {SOFT_SIZE_THRESHOLD} MB.'
                      f' Add "{LARGE_FILE_MARKER}" to commit message, '
                      'or remove file from index.')
                return 1

    return 0


def commit_hook(merge=False):
    retval = 0
    files = get_commit_files()

    print(' Auto remove trailing white space ...')
    remove_trailing_white_space(files['M'])
    remove_trailing_white_space(files['A'], new_files=True)

    print(' Check username ...')
    retval += check_username()

    if merge:
        print(' Check do not merge ...')
        retval += check_do_not_merge(files['M'])
        retval += check_do_not_merge(files['A'], new_files=True)
    else:
        print(' Check filenames ...')
        retval += check_filenames(files['M'] + files['A'])

        print(' Check line endings ...')
        retval += check_eol(files['M'] + files['A'])

        print(' Check file content ...')
        retval += check_content(files['M'] + files['A'])

    return retval


def commit_msg_hook():
    retval = 0
    files = get_commit_files()
    commit_message = Path(sys.argv[1]).read_text()

    print(' Check commit message ...')
    retval += check_commit_msg(commit_message, files['M'] + files['A'])

    return retval
