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
'''Check and fix full CCDC copyright and licence headers.'''

import argparse
import codecs
from datetime import datetime
from io import BytesIO
from pathlib import Path, PurePosixPath
import re
import sys
import tokenize


HASH_EXTENSIONS = {'.py', '.sh', '.bash', '.yaml', '.yml'}
SLASH_EXTENSIONS = {'.js', '.ts', '.cs', '.cpp', '.cxx', '.cc', '.h', '.hpp'}
IGNORED_DIRECTORIES = {
    '.git', '.github', 'test', 'tests', 'templates', 'bin', 'obj', 'packages',
    'node_modules', 'dist', 'build', '.venv', 'venv', '__pycache__'
}
IGNORED_SUFFIXES = ('.designer.cs', '.g.cs', '.min.js', '.lock')
TEMPLATE_DIRECTORY = Path(__file__).resolve().parent / 'copywrite' / 'headers'
PYTHON_ENCODING_PATTERN = re.compile(r'^[ \t\f]*#.*?coding[:=][ \t]*[-\w.]+')
LEGACY_HEADER_PATTERN = re.compile(
    r'^(#|//) Copyright The Cambridge Crystallographic Data Centre '
    r'\(CCDC\) \d{4}(?:, \d{4})?\r?\n?$'
)


def _comment_style(filename):
    path = PurePosixPath(str(filename).replace('\\', '/'))
    lower_name = path.name.lower()
    if any(part.lower() in IGNORED_DIRECTORIES for part in path.parts):
        return None
    if lower_name.endswith(IGNORED_SUFFIXES) or '.generated.' in lower_name:
        return None
    if path.suffix.lower() in HASH_EXTENSIONS:
        return 'hash'
    if path.suffix.lower() in SLASH_EXTENSIONS:
        return 'slash'
    return None


def _render_header(style, newline='\n', year=None):
    template_path = TEMPLATE_DIRECTORY / f'ccdc_{style}.tmpl'
    template = template_path.read_text(encoding='utf-8')
    rendered = template.replace('{{ .Year }}', str(year or datetime.now().year))
    return rendered.replace('\n', newline)


def _decode_content(filename, data):
    if not isinstance(data, bytes):
        return data, None
    if data.startswith(codecs.BOM_UTF8):
        encoding = 'utf-8-sig'
    elif str(filename).lower().endswith('.py'):
        encoding, _ = tokenize.detect_encoding(BytesIO(data).readline)
    else:
        encoding = 'utf-8'
    return data.decode(encoding), encoding


def _header_offset(filename, text, style):
    lines = text.splitlines(keepends=True)
    has_shebang = bool(lines and lines[0].startswith('#!'))
    if not str(filename).lower().endswith('.py'):
        return len(lines[0]) if has_shebang else 0

    candidate_indexes = [1] if has_shebang else range(min(2, len(lines)))
    for index in candidate_indexes:
        if index < len(lines) and PYTHON_ENCODING_PATTERN.match(lines[index]):
            return sum(len(line) for line in lines[:index + 1])
    return len(lines[0]) if has_shebang else 0


def _header_line_matches(actual, expected):
    if 'This code is Copyright (C)' in expected:
        marker = expected.split(' ', 1)[0]
        pattern = (
            rf'{re.escape(marker)} This code is Copyright \(C\) '
            r'(?:\d{4}(?:, \d{4})?|\{\{ \.Year \}\}) '
            r'The Cambridge Crystallographic Data Centre \(CCDC\)'
        )
        return re.fullmatch(pattern, actual) is not None
    return actual == expected


def _known_header_prefix_end(text, offset, expected):
    actual_lines = []
    position = offset
    for line in text[offset:].splitlines(keepends=True):
        actual_lines.append((position, position + len(line), line.strip()))
        position += len(line)

    expected_lines = [line.strip() for line in expected.splitlines()]
    if len(actual_lines) < 2 or len(expected_lines) < 2:
        return offset
    if actual_lines[0][2] != expected_lines[0]:
        return offset
    if not _header_line_matches(actual_lines[1][2], expected_lines[1]):
        return offset

    header_end = actual_lines[1][1]
    expected_index = 2
    for _, line_end, actual in actual_lines[2:]:
        if actual == '':
            continue
        match_index = next(
            (index for index in range(expected_index, len(expected_lines))
             if _header_line_matches(actual, expected_lines[index])),
            None
        )
        if match_index is None:
            break
        expected_index = match_index + 1
        header_end = line_end
    return header_end


def _damaged_full_header_end(text, offset, style):
    marker = '#' if style == 'hash' else '//'
    lines = text[offset:].splitlines(keepends=True)
    if len(lines) < 2 or lines[0].strip() != marker:
        return offset
    identity_line = lines[1].strip()
    if (
        not identity_line.startswith(f'{marker} This code is ')
        or 'Crystallographic Data Centre (CCDC)' not in identity_line
    ):
        return offset

    position = offset
    line_positions = []
    for line in lines:
        line_positions.append((position, position + len(line), line.strip()))
        position += len(line)

    for index, (_, line_end, stripped) in enumerate(line_positions[2:], start=2):
        if stripped and not stripped.startswith(marker):
            break
        if stripped.startswith(marker) and stripped.endswith('law.'):
            if index + 1 < len(line_positions) and line_positions[index + 1][2] == marker:
                return line_positions[index + 1][1]
            return line_end
    return offset


def _existing_header_end(text, offset, style, expected):
    lines = text[offset:].splitlines(keepends=True)
    if lines and LEGACY_HEADER_PATTERN.match(lines[0]):
        if len(lines) > 1 and lines[1].strip() == '':
            return offset + len(lines[0]) + len(lines[1])
        return offset + len(lines[0])
    damaged_header_end = _damaged_full_header_end(text, offset, style)
    if damaged_header_end != offset:
        return damaged_header_end
    return _known_header_prefix_end(text, offset, expected)


def check_content(filename, data, year=None):
    '''Return an error message when a supported file lacks the exact header.'''
    style = _comment_style(filename)
    if style is None:
        return None
    try:
        text, _ = _decode_content(filename, data)
    except (LookupError, SyntaxError, UnicodeDecodeError):
        return 'file encoding could not be decoded'

    newline = '\r\n' if '\r\n' in text else '\n'
    offset = _header_offset(filename, text, style)
    expected = _render_header(style, newline, year)
    if text.startswith(expected, offset):
        return None
    return 'missing or non-compliant CCDC copyright and licence header'


def fix_content(filename, data, year=None):
    '''Return content with the full rendered header for supported files.'''
    style = _comment_style(filename)
    if style is None:
        return data

    text, encoding = _decode_content(filename, data)
    newline = '\r\n' if '\r\n' in text else '\n'
    offset = _header_offset(filename, text, style)
    expected = _render_header(style, newline, year)
    if text.startswith(expected, offset):
        return data

    header_end = _existing_header_end(text, offset, style, expected)
    prefix = text[:offset]
    if prefix and not prefix.endswith(('\n', '\r')):
        prefix += newline
    fixed = prefix + expected + text[header_end:]
    return fixed.encode(encoding) if encoding else fixed


def process_files(files, fix=False, year=None):
    failures = 0
    for filename in files:
        path = Path(filename)
        if path.is_symlink() or not path.is_file() or _comment_style(filename) is None:
            continue
        data = path.read_bytes()
        issue = check_content(filename, data, year)
        if issue is None:
            continue
        if fix:
            path.write_bytes(fix_content(filename, data, year))
            print(f'Updated CCDC licence header: {filename}')
        else:
            print(f'HEADER FAIL: {filename}: {issue}')
            failures += 1
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['check', 'fix'])
    parser.add_argument('files', nargs='*')
    arguments = parser.parse_args(argv)
    return process_files(arguments.files, fix=arguments.mode == 'fix')


if __name__ == '__main__':
    sys.exit(main())
