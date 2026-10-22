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
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
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
TEMPLATE_DIRECTORY = Path(__file__).resolve().parent / 'headers'
PYTHON_ENCODING_PATTERN = re.compile(r'^[ \t\f]*#.*?coding[:=][ \t]*[-\w.]+')
LEGACY_HEADER_PATTERN = re.compile(
    r'^(#|//) Copyright The Cambridge Crystallographic Data Centre '
    r'\(CCDC\) \d{4}(?:, \d{4})?\r?\n?$'
)
COMMENT_MARKERS = {'hash': '#', 'slash': '//'}
YEAR_TOKEN = '{{ .Year }}'
YEAR_PATTERN = r'\d{4}(?:, \d{4})?'
IDENTITY_PREFIX = 'This code is'
IDENTITY_OWNER = 'Crystallographic Data Centre (CCDC)'
LICENCE_REGION_LABEL = re.compile(r'licen[cs]e|copyright|header', re.IGNORECASE)

# Region open/close directives per file extension. To support another
# language, add its extension with (open pattern, close pattern); the open
# pattern may capture a "label" group used to find a licence region.
REGION_SYNTAX = {
    '.cs': (
        re.compile(r'^\s*#region\b(?P<label>.*)$'),
        re.compile(r'^\s*#endregion\b'),
    ),
    '.py': (
        re.compile(r'^\s*#\s?region\b(?P<label>.*)$'),
        re.compile(r'^\s*#\s?endregion\b'),
    ),
}

# Non-comment lines that may legitimately appear before the licence header.
PREAMBLE_DIRECTIVES = {
    '.cs': (
        re.compile(r'^\s*(?:global\s+)?using\s+(?:static\s+)?[\w.]+(?:\s*=\s*[\w.<>, ]+)?\s*;\s*$'),
        re.compile(r'^\s*#\s*(?:nullable|pragma|define|undef)\b'),
    ),
    '.js': (re.compile(r'''^\s*(['"])use strict\1;?\s*$'''),),
    '.ts': (re.compile(r'''^\s*(['"])use strict\1;?\s*$'''),),
    '.cpp': (re.compile(r'^\s*#\s*pragma\s+once\b'),),
    '.cxx': (re.compile(r'^\s*#\s*pragma\s+once\b'),),
    '.cc': (re.compile(r'^\s*#\s*pragma\s+once\b'),),
    '.h': (re.compile(r'^\s*#\s*pragma\s+once\b'),),
    '.hpp': (re.compile(r'^\s*#\s*pragma\s+once\b'),),
    '.yaml': (re.compile(r'^---\s*$'),),
    '.yml': (re.compile(r'^---\s*$'),),
}

# Damaged header recovery tolerances.
ALIGNMENT_LOOKAHEAD = 3
MAX_UNMATCHED_LINES = 2


@dataclass
class _Line:
    kind: str  # blank, comment, region_open, region_close, directive, shebang, code
    text: str = ''
    label: str = ''


@dataclass
class _HeaderSpan:
    start: int
    end: int
    valid: bool


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


def _suffix(filename):
    return PurePosixPath(str(filename).replace('\\', '/')).suffix.lower()


def _read_template(style):
    return (TEMPLATE_DIRECTORY / f'ccdc_{style}.tmpl').read_text(encoding='utf-8')


def _render_header(style, newline='\n', year=None):
    rendered = _read_template(style).replace(YEAR_TOKEN, str(year or datetime.now().year))
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


def _normalise(text):
    return ' '.join(text.split())


def _comment_text(line, marker):
    '''Return the comment body of `line`, or None when it is not a comment.'''
    stripped = line.lstrip('\ufeff').strip()
    if not stripped.startswith(marker):
        return None
    return _normalise(stripped[len(marker):])


def _template_lines(style):
    '''Template body lines with comment markers removed and marker-only lines dropped.'''
    marker = COMMENT_MARKERS[style]
    texts = (_comment_text(line, marker) for line in _read_template(style).splitlines())
    return [text for text in texts if text]


def _header_pattern(style):
    '''Regex matching the normalised header text with any valid year.'''
    escaped = re.escape(' '.join(_template_lines(style)))
    return re.compile(escaped.replace(re.escape(YEAR_TOKEN), YEAR_PATTERN))


def _classify(filename, style, lines):
    '''Classify the leading preamble lines; classification stops at the first code line.'''
    marker = COMMENT_MARKERS[style]
    region_open, region_close = REGION_SYNTAX.get(_suffix(filename), (None, None))
    directives = PREAMBLE_DIRECTIVES.get(_suffix(filename), ())
    classified = []
    for index, raw in enumerate(lines):
        line = raw.lstrip('\ufeff').rstrip('\r\n')
        if not line.strip():
            classified.append(_Line('blank'))
            continue
        if index == 0 and line.startswith('#!'):
            classified.append(_Line('shebang'))
            continue
        open_match = region_open.match(line) if region_open else None
        if open_match:
            classified.append(_Line('region_open', label=open_match.group('label').strip()))
            continue
        if region_close and region_close.match(line):
            classified.append(_Line('region_close'))
            continue
        text = _comment_text(line, marker)
        if text is not None:
            classified.append(_Line('comment', text=text))
            continue
        if any(pattern.match(line) for pattern in directives):
            classified.append(_Line('directive'))
            continue
        classified.append(_Line('code'))
        break
    return classified


def _is_marker_only(line):
    return line.kind == 'comment' and not line.text


def _comment_runs(classified):
    run = []
    for index, line in enumerate(classified):
        if line.kind == 'comment':
            run.append(index)
        elif run:
            yield run
            run = []
    if run:
        yield run


def _find_valid_headers(classified, pattern):
    '''Find complete headers by matching normalised text within contiguous comment runs.'''
    spans = []
    for run in _comment_runs(classified):
        parts, starts, ends = [], {}, {}
        position = 0
        for index in run:
            text = classified[index].text
            if not text:
                continue
            if parts:
                position += 1
            starts[position] = index
            ends[position + len(text)] = index
            parts.append(text)
            position += len(text)
        for match in pattern.finditer(' '.join(parts)):
            if match.start() not in starts or match.end() not in ends:
                continue
            start, end = starts[match.start()], ends[match.end()] + 1
            if start > 0 and _is_marker_only(classified[start - 1]) and not _claimed(spans, start - 1):
                start -= 1
            if end < len(classified) and _is_marker_only(classified[end]):
                end += 1
            spans.append(_HeaderSpan(start, end, valid=True))
    return spans


def _claimed(spans, index):
    return any(span.start <= index < span.end for span in spans)


def _similar(actual, expected):
    if actual == expected:
        return True
    matcher = SequenceMatcher(None, actual, expected, autojunk=False)
    longest = matcher.find_longest_match(0, len(actual), 0, len(expected)).size
    return (longest >= 6 and longest >= len(actual) / 2) or matcher.ratio() >= 0.75


def _align(text, expected, pointer):
    '''Return the template line index `text` corresponds to, scanning forward from `pointer`.'''
    for index in range(pointer, min(pointer + ALIGNMENT_LOOKAHEAD, len(expected))):
        if _similar(text, expected[index]):
            return index
    if pointer < len(expected) and text == expected[-1]:
        return len(expected) - 1
    return None


def _damaged_span(classified, anchor, expected, claimed):
    '''Extend a damaged header from its identity line while lines still resemble the template.'''
    start = anchor
    if anchor > 0 and _is_marker_only(classified[anchor - 1]) and not _claimed(claimed, anchor - 1):
        start -= 1
    pointer, end, unmatched = 1, anchor + 1, 0
    index = anchor + 1
    while index < len(classified) and pointer < len(expected) and not _claimed(claimed, index):
        line = classified[index]
        if line.kind == 'blank' or _is_marker_only(line):
            index += 1
            continue
        if line.kind != 'comment':
            break
        aligned = _align(line.text, expected, pointer)
        if aligned is None:
            unmatched += 1
            if unmatched > MAX_UNMATCHED_LINES:
                break
        else:
            pointer, end, unmatched = aligned + 1, index + 1, 0
        index += 1
    if end < len(classified) and _is_marker_only(classified[end]) and not _claimed(claimed, end):
        end += 1
    return _HeaderSpan(start, end, valid=False)


def _find_headers(filename, style, lines):
    classified = _classify(filename, style, lines)
    spans = _find_valid_headers(classified, _header_pattern(style))
    expected = _template_lines(style)
    for index, line in enumerate(classified):
        if _claimed(spans, index):
            continue
        if LEGACY_HEADER_PATTERN.match(lines[index].lstrip('\ufeff')):
            end = index + 1
            if end < len(classified) and classified[end].kind == 'blank':
                end += 1
            spans.append(_HeaderSpan(index, end, valid=False))
        elif (
            line.kind == 'comment'
            and line.text.startswith(IDENTITY_PREFIX)
            and IDENTITY_OWNER in line.text
        ):
            spans.append(_damaged_span(classified, index, expected, spans))
    return sorted(spans, key=lambda span: span.start), classified


def _header_offset(filename, text):
    '''Character offset where a missing header is inserted at the top of the file.'''
    lines = text.splitlines(keepends=True)
    has_shebang = bool(lines and lines[0].startswith('#!'))
    if not str(filename).lower().endswith('.py'):
        return len(lines[0]) if has_shebang else 0

    candidate_indexes = [1] if has_shebang else [0]
    if (
        not has_shebang
        and len(lines) > 1
        and (
            lines[0].strip() == ''
            or lines[0].lstrip().startswith('#')
        )
    ):
        candidate_indexes.append(1)

    for index in candidate_indexes:
        if index < len(lines) and PYTHON_ENCODING_PATTERN.match(lines[index]):
            return sum(len(line) for line in lines[:index + 1])
    return len(lines[0]) if has_shebang else 0


def _insert_header(filename, text, lines, classified, expected, newline):
    for index, line in enumerate(classified):
        if line.kind == 'region_open' and LICENCE_REGION_LABEL.search(line.label):
            prefix = ''.join(lines[:index + 1])
            if not prefix.endswith(('\n', '\r')):
                prefix += newline
            return prefix + expected + ''.join(lines[index + 1:])
    offset = _header_offset(filename, text)
    prefix = text[:offset]
    if prefix and not prefix.endswith(('\n', '\r')):
        prefix += newline
    return prefix + expected + text[offset:]


def _newline(text):
    return '\r\n' if '\r\n' in text else '\n'


def check_content(filename, data, year=None):
    '''Return an error message when a supported file lacks exactly one compliant header.'''
    style = _comment_style(filename)
    if style is None:
        return None
    try:
        text, _ = _decode_content(filename, data)
    except (LookupError, SyntaxError, UnicodeDecodeError):
        return 'file encoding could not be decoded'

    spans, _ = _find_headers(filename, style, text.splitlines(keepends=True))
    if len(spans) > 1:
        return 'duplicate CCDC copyright and licence headers'
    if len(spans) == 1 and spans[0].valid:
        return None
    return 'missing or non-compliant CCDC copyright and licence header'


def fix_content(filename, data, year=None):
    '''Return content with exactly one compliant header, repairing it in place.'''
    style = _comment_style(filename)
    if style is None:
        return data

    text, encoding = _decode_content(filename, data)
    lines = text.splitlines(keepends=True)
    spans, classified = _find_headers(filename, style, lines)
    if len(spans) == 1 and spans[0].valid:
        return data

    newline = _newline(text)
    expected = _render_header(style, newline, year)
    if not spans:
        fixed = _insert_header(filename, text, lines, classified, expected, newline)
        return fixed.encode(encoding) if encoding else fixed

    keep = next((span for span in spans if span.valid), spans[0])
    output = []
    index = 0
    for span in spans:
        output.extend(lines[index:span.start])
        index = span.end
        if span is keep:
            if span.valid:
                output.extend(lines[span.start:span.end])
            else:
                output.append(expected)
        elif index < len(classified) and classified[index].kind == 'blank':
            index += 1
    output.extend(lines[index:])
    fixed = ''.join(output)
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
            fixed = fix_content(filename, data, year)
            if fixed != data:
                path.write_bytes(fixed)
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
