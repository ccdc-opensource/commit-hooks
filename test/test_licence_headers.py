from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'main'))
import licence_headers


def test_complete_hash_header_passes():
    header = licence_headers._render_header('hash', year=2026)
    assert licence_headers.check_content('example.py', header + 'print("ok")\n', 2026) is None


def test_literal_year_token_fails():
    header = licence_headers._render_header('hash', year=2026).replace('2026', '{{ .Year }}')
    assert licence_headers.check_content('example.py', header, 2026) is not None


def test_removed_licence_line_fails_and_is_repaired():
    header = licence_headers._render_header('hash', year=2026)
    broken = header.replace('# copied, except in accordance with a valid licence agreement with CCDC and\n', '')
    content = broken + 'print("ok")\n'
    assert licence_headers.check_content('example.py', content, 2026) is not None
    fixed = licence_headers.fix_content('example.py', content, 2026)
    assert fixed == header + 'print("ok")\n'


def test_missing_header_is_added_after_shebang():
    fixed = licence_headers.fix_content('script.py', '#!/usr/bin/env python3\nprint("ok")\n', 2026)
    assert fixed.startswith('#!/usr/bin/env python3\n#\n# This code is Copyright (C) 2026')
    assert fixed.endswith('print("ok")\n')


def test_missing_slash_header_is_added_after_shebang():
    for filename in ['cli.js', 'cli.ts']:
        source = '#!/usr/bin/env node\nconsole.log("ok");\n'
        fixed = licence_headers.fix_content(filename, source, 2026)
        assert fixed.startswith('#!/usr/bin/env node\n//\n// This code is Copyright (C) 2026')
        assert fixed.endswith('console.log("ok");\n')
        assert licence_headers.check_content(filename, fixed, 2026) is None


def test_python_encoding_declaration_is_preserved_before_header():
    fixed = licence_headers.fix_content('script.py', '# -*- coding: latin-1 -*-\nprint("ok")\n', 2026)
    assert fixed.startswith('# -*- coding: latin-1 -*-\n#\n# This code is Copyright (C) 2026')


def test_second_line_python_encoding_declaration_preserves_comment_prefix():
    source = '# generated source\n# coding=latin-1\nprint("ok")\n'
    fixed = licence_headers.fix_content('script.py', source, 2026)
    prefix = '# generated source\n# coding=latin-1\n#\n# This code is Copyright (C) 2026'
    assert fixed.startswith(prefix)
    assert licence_headers.check_content('script.py', fixed, 2026) is None


def test_encoding_declaration_after_shebang_is_preserved():
    source = '#!/usr/bin/env python3\n# -*- coding: latin-1 -*-\nprint("ok")\n'
    fixed = licence_headers.fix_content('script.py', source, 2026)
    prefix = '#!/usr/bin/env python3\n# -*- coding: latin-1 -*-\n#\n# This code is Copyright (C) 2026'
    assert fixed.startswith(prefix)
    assert licence_headers.check_content('script.py', fixed, 2026) is None


def test_non_utf8_python_file_preserves_declared_encoding():
    for enc in ['latin-1', 'iso-8859-15', 'cp1252', 'utf-8-sig']:
        source = f'# coding={enc}\nname = "café"\n'.encode(enc)
        fixed = licence_headers.fix_content('script.py', source, 2026)
        assert isinstance(fixed, bytes)
        assert f'# coding={enc}'.encode('ascii') in fixed
        assert licence_headers.check_content('script.py', fixed, 2026) is None
        # Verify decoding with original encoding roundtrips cleanly
        decoded_text, detected_enc = licence_headers._decode_content('script.py', fixed)
        assert 'This code is Copyright' in decoded_text
        assert 'café' in decoded_text


def test_empty_python_file_gets_header():
    fixed = licence_headers.fix_content('empty.py', b'', 2026)
    assert fixed.startswith(b'#\n# This code is Copyright (C) 2026')
    assert licence_headers.check_content('empty.py', fixed, 2026) is None


def test_utf8_bom_remains_at_byte_zero_for_supported_non_python_files():
    for filename in ['example.yml', 'example.js', 'example.cpp']:
        fixed = licence_headers.fix_content(filename, b'\xef\xbb\xbfvalue\n', 2026)
        assert fixed.startswith(b'\xef\xbb\xbf')
        assert fixed.count(b'\xef\xbb\xbf') == 1
        assert licence_headers.check_content(filename, fixed, 2026) is None


def test_unterminated_shebang_is_separated_from_header():
    for filename, shebang in [('script.py', b'#!/usr/bin/env python3'), ('script.sh', b'#!/bin/sh')]:
        fixed = licence_headers.fix_content(filename, shebang, 2026)
        assert fixed.startswith(shebang + b'\n#\n# This code is Copyright (C) 2026')
    for filename in ['script.js', 'script.ts']:
        shebang = b'#!/usr/bin/env node'
        fixed = licence_headers.fix_content(filename, shebang, 2026)
        assert fixed.startswith(shebang + b'\n//\n// This code is Copyright (C) 2026')


def test_unterminated_encoding_declaration_is_separated_from_header():
    declaration = b'# coding=latin-1'
    fixed = licence_headers.fix_content('script.py', declaration, 2026)
    assert fixed.startswith(declaration + b'\n#\n# This code is Copyright (C) 2026')


def test_legacy_one_line_header_is_replaced():
    old_header = '# Copyright The Cambridge Crystallographic Data Centre (CCDC) 2021, 2026\n\n'
    source_comment = '# keep this source comment\n'
    fixed = licence_headers.fix_content('example.py', old_header + source_comment + 'print("ok")\n', 2026)
    assert fixed.startswith('#\n# This code is Copyright (C) 2026')
    assert old_header not in fixed
    assert fixed.endswith(source_comment + 'print("ok")\n')


def test_truncated_full_header_is_replaced_without_losing_source_comment():
    header = licence_headers._render_header('hash', year=2026)
    old_header = licence_headers._render_header('hash', year=2025)
    truncated = old_header.split('# law.\n', 1)[0]
    source = '# keep this source comment\nprint("ok")\n'
    fixed = licence_headers.fix_content('example.py', truncated + source, 2026)
    assert fixed == header + source
    assert fixed.count('This code is Copyright (C)') == 1


def test_heavily_damaged_full_header_is_replaced_without_duplication():
    damaged = '''#
# This code is CopyrightCrystallographic Data Centre (CCDC)
# of 12 Union Road, Cambridge CB2 1EZ, UK and a proprietary work of CCDC. This
# code may not be used, reproduced,sassembled or
# copied, except in accordance with a valid licence agreement with CCDC and
# may NOT be disclosed or redistributhole or in
# part, toust contain this copyright
# notice.

# No representations, warranties, or liabilities are expressed or implied in
# the supply servants or agents, except where such
# exclusion or limitation is prohibited, void or unenforceable under governing
# law.
#

'''
    source = '# keep this source comment\nhello\n'
    header = licence_headers._render_header('hash', year=2026)
    fixed = licence_headers.fix_content('example.py', damaged + source, 2026)
    assert fixed == header + '\n' + source
    assert fixed.count('This code is Copyright') == 1


def test_damaged_copyright_identity_line_is_repaired_without_duplication():
    damaged = '''#
# This code is Cop Crystallographic Data Centre (CCDC)
# of 12 Union Road, Cambridge CB2 1EZ, UK and a proprietary work of CCDC. This
# code may not beteded, disassembled or
# copied, except in accordance with a valid licence agreement with CCDC and

# part, to any third party. All copies of this code made in accordance with a
# valid licence agreement as referred to above must contain this copyright
# notice.
#
# No representations, warranties, or liabilities are expressed or implied in
# the supply of this cod servants or agents, except where such
# exclusion or limitation is prohibited, vrceable under governing
# law.
#

'''
    source = '# keep this source comment\nhello\n'
    header = licence_headers._render_header('hash', year=2026)
    fixed = licence_headers.fix_content('example.py', damaged + source, 2026)
    assert fixed == header + '\n' + source
    assert fixed.count('This code is Copyright') == 1


def test_truncated_header_does_not_consume_source_code_before_law_comment():
    truncated = '''#
# This code is Copyright (C) 2026 The Cambridge Crystallographic Data Centre (CCDC)
# of 12 Union Road, Cambridge CB2 1EZ, UK and a proprietary work of CCDC. This
'''
    source = 'def calculate():\n    return 42\n# according to the law.\n'
    fixed = licence_headers.fix_content('example.py', truncated + source, 2026)
    expected_header = licence_headers._render_header('hash', year=2026)
    assert fixed == expected_header + source
    assert 'def calculate():' in fixed


def test_truncated_header_preserves_source_comment_matching_later_header_line():
    truncated = '''#
# This code is Copyright (C) 2026 The Cambridge Crystallographic Data Centre (CCDC)
'''
    source = '# notice.\nprint("ok")\n'
    fixed = licence_headers.fix_content('example.py', truncated + source, 2026)
    expected_header = licence_headers._render_header('hash', year=2026)
    assert fixed == expected_header + source
    assert '# notice.\n' in fixed


def test_slash_header_is_added():
    fixed = licence_headers.fix_content('example.cpp', 'int main() {}\n', 2026)
    assert fixed.startswith('//\n// This code is Copyright (C) 2026')
    assert licence_headers.check_content('example.cpp', fixed, 2026) is None


def test_ignored_and_unsupported_files_are_skipped():
    assert licence_headers.check_content('.github/workflows/check.yml', 'name: check\n', 2026) is None
    assert licence_headers.check_content('templates/check.yml', 'name: check\n', 2026) is None
    assert licence_headers.check_content('README.md', '# Read me\n', 2026) is None
    assert licence_headers.check_content('notes.txt', 'some notes\n', 2026) is None
    assert licence_headers.check_content('package.json', '{"name": "app"}\n', 2026) is None
    assert licence_headers.check_content('node_modules/pkg/index.js', 'console.log();\n', 2026) is None
    assert licence_headers.check_content('dist/bundle.js', 'console.log();\n', 2026) is None
    assert licence_headers.check_content('.venv/lib/module.py', 'print("ok")\n', 2026) is None


def test_generated_files_are_excluded():
    generated_files = [
        'Form.Designer.cs',
        'Model.g.cs',
        'bundle.min.js',
        'packages.lock',
        'service.generated.ts',
        'codegen.generated.cpp',
    ]
    for filename in generated_files:
        assert licence_headers.check_content(filename, 'var x = 1;\n', 2026) is None
        assert licence_headers.fix_content(filename, 'var x = 1;\n', 2026) == 'var x = 1;\n'


def test_crlf_line_endings_are_preserved():
    source = 'int main() {\r\n    return 0;\r\n}\r\n'
    fixed = licence_headers.fix_content('main.cpp', source, 2026)
    assert '\r\n' in fixed
    assert '\n' not in fixed.replace('\r\n', '')
    assert licence_headers.check_content('main.cpp', fixed, 2026) is None


def test_legacy_slash_header_is_replaced():
    old_header = '// Copyright The Cambridge Crystallographic Data Centre (CCDC) 2020\r\n\r\n'
    source = 'const x = 42;\r\n'
    fixed = licence_headers.fix_content('app.js', old_header + source, 2026)
    assert fixed.startswith('//\r\n// This code is Copyright (C) 2026')
    assert old_header not in fixed
    assert fixed.endswith(source)


def test_damaged_slash_header_is_repaired():
    damaged = (
        '//\n'
        '// This code is Copyright (C) 2024 The Cambridge Crystallographic Data Centre (CCDC)\n'
        '// of 12 Union Road, Cambridge CB2 1EZ, UK and a proprietary work of CCDC. This\n'
        '// broken line...\n'
        '// law.\n'
        '//\n'
    )
    source = 'const app = 1;\n'
    fixed = licence_headers.fix_content('app.ts', damaged + source, 2026)
    expected_header = licence_headers._render_header('slash', year=2026)
    assert fixed == expected_header + source


def test_process_files_avoids_write_when_already_compliant(tmp_path):
    test_file = tmp_path / 'compliant.py'
    header = licence_headers._render_header('hash', year=2026)
    content = (header + 'print("hello")\n').encode('utf-8')
    test_file.write_bytes(content)

    initial_mtime = test_file.stat().st_mtime_ns
    assert licence_headers.process_files([str(test_file)], fix=True, year=2026) == 0
    assert test_file.stat().st_mtime_ns == initial_mtime


def test_process_files_skips_symlinks(tmp_path):
    target = tmp_path / 'target.py'
    target_content = 'print("target")\n'
    target.write_text(target_content, encoding='utf-8')

    symlink = tmp_path / 'link.py'
    try:
        symlink.symlink_to(target)
    except OSError:
        import pytest
        pytest.skip('Symlinks not supported in current environment or permissions')

    # Check mode should skip symlink and report 0 failures
    assert licence_headers.process_files([str(symlink)], fix=False, year=2026) == 0
    # Fix mode should skip symlink without modifying target file
    assert licence_headers.process_files([str(symlink)], fix=True, year=2026) == 0
    assert target.read_text(encoding='utf-8') == target_content
