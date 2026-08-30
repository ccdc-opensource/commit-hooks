from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'main'))
import license_headers


def test_complete_hash_header_passes():
    header = license_headers._render_header('hash', year=2026)
    assert license_headers.check_content('example.py', header + 'print("ok")\n', 2026) is None


def test_literal_year_token_fails():
    header = license_headers._render_header('hash', year=2026).replace('2026', '{{ .Year }}')
    assert license_headers.check_content('example.py', header, 2026) is not None


def test_removed_licence_line_fails_and_is_repaired():
    header = license_headers._render_header('hash', year=2026)
    broken = header.replace('# copied, except in accordance with a valid licence agreement with CCDC and\n', '')
    content = broken + 'print("ok")\n'
    assert license_headers.check_content('example.py', content, 2026) is not None
    fixed = license_headers.fix_content('example.py', content, 2026)
    assert fixed == header + 'print("ok")\n'


def test_missing_header_is_added_after_shebang():
    fixed = license_headers.fix_content('script.py', '#!/usr/bin/env python3\nprint("ok")\n', 2026)
    assert fixed.startswith('#!/usr/bin/env python3\n#\n# This code is Copyright (C) 2026')
    assert fixed.endswith('print("ok")\n')


def test_python_encoding_declaration_is_preserved_before_header():
    fixed = license_headers.fix_content('script.py', '# -*- coding: latin-1 -*-\nprint("ok")\n', 2026)
    assert fixed.startswith('# -*- coding: latin-1 -*-\n#\n# This code is Copyright (C) 2026')


def test_second_line_python_encoding_declaration_preserves_comment_prefix():
    source = '# generated source\n# coding=latin-1\nprint("ok")\n'
    fixed = license_headers.fix_content('script.py', source, 2026)
    prefix = '# generated source\n# coding=latin-1\n#\n# This code is Copyright (C) 2026'
    assert fixed.startswith(prefix)
    assert license_headers.check_content('script.py', fixed, 2026) is None


def test_encoding_declaration_after_shebang_is_preserved():
    source = '#!/usr/bin/env python3\n# -*- coding: latin-1 -*-\nprint("ok")\n'
    fixed = license_headers.fix_content('script.py', source, 2026)
    prefix = '#!/usr/bin/env python3\n# -*- coding: latin-1 -*-\n#\n# This code is Copyright (C) 2026'
    assert fixed.startswith(prefix)
    assert license_headers.check_content('script.py', fixed, 2026) is None


def test_non_utf8_python_file_preserves_declared_encoding():
    source = '# generated\n# coding=latin-1\nname = "caf\xe9"\n'.encode('latin-1')
    fixed = license_headers.fix_content('script.py', source, 2026)
    assert isinstance(fixed, bytes)
    assert b'# coding=latin-1\n#\n# This code is Copyright (C) 2026' in fixed
    assert b'caf\xe9' in fixed
    assert license_headers.check_content('script.py', fixed, 2026) is None


def test_empty_python_file_gets_header():
    fixed = license_headers.fix_content('empty.py', b'', 2026)
    assert fixed.startswith(b'#\n# This code is Copyright (C) 2026')
    assert license_headers.check_content('empty.py', fixed, 2026) is None


def test_copywrite_one_line_header_is_replaced():
    old_header = '# Copyright The Cambridge Crystallographic Data Centre (CCDC) 2021, 2026\n\n'
    source_comment = '# keep this source comment\n'
    fixed = license_headers.fix_content('example.py', old_header + source_comment + 'print("ok")\n', 2026)
    assert fixed.startswith('#\n# This code is Copyright (C) 2026')
    assert old_header not in fixed
    assert fixed.endswith(source_comment + 'print("ok")\n')


def test_slash_header_is_added():
    fixed = license_headers.fix_content('example.cpp', 'int main() {}\n', 2026)
    assert fixed.startswith('//\n// This code is Copyright (C) 2026')
    assert license_headers.check_content('example.cpp', fixed, 2026) is None


def test_ignored_and_unsupported_files_are_skipped():
    assert license_headers.check_content('.github/workflows/check.yml', 'name: check\n', 2026) is None
    assert license_headers.check_content('templates/check.yml', 'name: check\n', 2026) is None
    assert license_headers.check_content('README.md', '# Read me\n', 2026) is None