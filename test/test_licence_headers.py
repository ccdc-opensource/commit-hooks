from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'main'))
import licence_headers


def test_complete_hash_header_passes():
    header = licence_headers._render_header('hash', year=2026)
    assert licence_headers.check_content('example.py', header + 'print("ok")\n', 2026) is None


def test_existing_file_with_earlier_year_passes_and_is_not_modified():
    # An existing file with 2020 should pass and NOT be bumped to 2026
    header_2020 = licence_headers._render_header('hash', year=2020)
    source = header_2020 + 'print("ok")\n'
    assert licence_headers.check_content('example.py', source, year=2026) is None
    fixed = licence_headers.fix_content('example.py', source, year=2026)
    assert fixed == source
    assert 'Copyright (C) 2020' in fixed


def test_header_inside_leading_region_wrapper_passes_without_duplication():
    header = licence_headers._render_header('hash', year=2026)
    content = '#region Licence\n' + header + '#endregion\nprint("ok")\n'
    assert licence_headers.check_content('example.py', content, 2026) is None
    fixed = licence_headers.fix_content('example.py', content, 2026)
    assert fixed == content


def test_bom_before_leading_region_wrapper_is_ignored():
    header = licence_headers._render_header('slash', year=2026)
    content = '\ufeff#region Licence\n' + header + '#endregion\nprint("ok")\n'
    assert licence_headers.check_content('example.cs', content, 2026) is None
    fixed = licence_headers.fix_content('example.cs', content, 2026)
    assert fixed == content


def test_regional_keyword_is_not_treated_as_region_directive():
    header = licence_headers._render_header('hash', year=2026)
    content = '#regional\n' + header + 'print("ok")\n'
    assert licence_headers.check_content('example.py', content, 2026) is None
    assert licence_headers.fix_content('example.py', content, 2026) == content
    missing = '#regional licence\nprint("ok")\n'
    assert licence_headers.fix_content('example.py', missing, 2026) == header + missing


def test_wrapped_header_is_repaired_in_place_without_double_insert():
    header = licence_headers._render_header('hash', year=2026)
    broken = header.replace('# copied, except in accordance with a valid licence agreement with CCDC and\n', '')
    content = '#region Licence\n' + broken + '#endregion\nprint("ok")\n'
    fixed = licence_headers.fix_content('example.py', content, 2026)
    assert fixed == '#region Licence\n' + header + '#endregion\nprint("ok")\n'
    assert licence_headers.check_content('example.py', fixed, 2026) is None


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


def test_second_line_encoding_after_code_is_not_treated_as_prefix():
    source = 'print("x")\n# coding=utf-8\n'
    fixed = licence_headers.fix_content('script.py', source, 2026)
    header = licence_headers._render_header('hash', year=2026)
    assert fixed.startswith(header)
    assert fixed.endswith(source)


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


def test_unpadded_header_without_leading_and_trailing_marker_is_repaired():
    unpadded = '''# This code is Copyright (C) 2026 The Cambridge Crystallographic Data Centre (CCDC)
# of 12 Union Road, Cambridge CB2 1EZ, UK and a proprietary work of CCDC. This
# code may not be used, reproduced, translated, modified, disassembled or
# copied, except in accordance with a valid licence agreement with CCDC and
# may NOT be disclosed or redistributed in any form, either in whole or in
# part, to any third party. All copies of this code made in accordance with a
# valid licence agreement as referred to above must contain this copyright
# notice.

# No representations, warranties, or liabilities are expressed or implied in
# the supply of this code by CCDC, its servants or agents, except where such
# exclusion or limitation is prohibited, void or unenforceable under governing
# law.
'''
    source = 'print("hello world")\n'
    fixed = licence_headers.fix_content('example.py', unpadded + '\n' + source, 2026)
    expected_header = licence_headers._render_header('hash', year=2026)
    assert fixed == expected_header + '\n' + source
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


SLASH_HEADER = licence_headers._render_header('slash', year=2024)
SLASH_UNPADDED = ''.join(line for line in SLASH_HEADER.splitlines(keepends=True) if line.strip() != '//')
CS_BODY = 'namespace Ccdc.Example\n{\n    public class Foo { }\n}\n'


def _assert_stable(filename, content):
    fixed = licence_headers.fix_content(filename, content, 2026)
    assert licence_headers.check_content(filename, fixed, 2026) is None
    assert licence_headers.fix_content(filename, fixed, 2026) == fixed
    assert fixed.count('This code is Copyright') == 1
    return fixed


def test_cs_header_in_region_with_surrounding_blank_lines_passes():
    content = '#region Licence\n\n' + SLASH_HEADER + '\n#endregion\n\n' + CS_BODY
    assert licence_headers.check_content('Foo.cs', content, 2026) is None
    assert licence_headers.fix_content('Foo.cs', content, 2026) == content


def test_cs_header_after_usings_and_directives_passes():
    content = (
        '// <auto-generated-ish note>\n#nullable enable\nusing System;\nusing IO = System.IO;\n\n'
        '  #region Copyright\n' + SLASH_HEADER + '  #endregion\n' + CS_BODY
    )
    assert licence_headers.check_content('Foo.cs', content, 2026) is None
    assert licence_headers.fix_content('Foo.cs', content, 2026) == content


def test_header_without_marker_padding_lines_passes():
    for content in [SLASH_UNPADDED + CS_BODY, '#region Licence\n' + SLASH_UNPADDED + '#endregion\n' + CS_BODY]:
        assert licence_headers.check_content('Foo.cs', content, 2026) is None
        assert licence_headers.fix_content('Foo.cs', content, 2026) == content


def test_crlf_header_in_region_passes():
    content = ('#region Licence\n' + SLASH_HEADER + '#endregion\n' + CS_BODY).replace('\n', '\r\n')
    assert licence_headers.check_content('Foo.cs', content, 2026) is None
    assert licence_headers.fix_content('Foo.cs', content, 2026) == content


def test_damaged_header_in_region_after_preamble_is_repaired_in_place():
    damaged = SLASH_HEADER.replace('// may NOT be disclosed or redistributed in any form, either in whole or in\n', '')
    content = 'using System;\n\n#region Licence\n\n' + damaged + '\n#endregion\n' + CS_BODY
    fixed = _assert_stable('Foo.cs', content)
    expected_header = licence_headers._render_header('slash', year=2026)
    assert fixed == 'using System;\n\n#region Licence\n\n' + expected_header + '\n#endregion\n' + CS_BODY


def test_stacked_duplicate_headers_fail_and_collapse_to_one():
    region = '#region Licence\n' + SLASH_HEADER + '#endregion\n'
    for content in [
        SLASH_HEADER + region + CS_BODY,
        SLASH_HEADER + '\n' + SLASH_HEADER + '\n' + SLASH_UNPADDED + CS_BODY,
    ]:
        assert 'duplicate' in licence_headers.check_content('Foo.cs', content, 2026)
        fixed = _assert_stable('Foo.cs', content)
        assert fixed.endswith(CS_BODY)
        assert 'Copyright (C) 2024' in fixed


def test_damaged_duplicate_is_removed_and_valid_header_kept():
    damaged = '// This code is Copyright (C) 2020 The Cambridge Crystallographic Data Centre (CCDC)\n// of 12 Union\n'
    content = damaged + '#region Licence\n' + SLASH_HEADER + '#endregion\n' + CS_BODY
    fixed = _assert_stable('Foo.cs', content)
    assert fixed == '#region Licence\n' + SLASH_HEADER + '#endregion\n' + CS_BODY


def test_missing_header_is_inserted_into_empty_licence_region():
    content = 'using System;\n#region License\n#endregion\n' + CS_BODY
    fixed = _assert_stable('Foo.cs', content)
    expected_header = licence_headers._render_header('slash', year=2026)
    assert fixed == 'using System;\n#region License\n' + expected_header + '#endregion\n' + CS_BODY


def test_missing_header_ignores_unrelated_region():
    content = '#region Imports\nusing System;\n#endregion\n' + CS_BODY
    fixed = _assert_stable('Foo.cs', content)
    assert fixed == licence_headers._render_header('slash', year=2026) + content


def test_header_after_code_is_not_accepted():
    content = CS_BODY + SLASH_HEADER
    assert licence_headers.check_content('Foo.cs', content, 2026) is not None
    fixed = licence_headers.fix_content('Foo.cs', content, 2026)
    assert fixed.startswith(licence_headers._render_header('slash', year=2026) + CS_BODY)


def test_repeated_fix_never_adds_headers():
    samples = [
        '#region Licence\n\n' + SLASH_HEADER + '#endregion\n' + CS_BODY,
        '\ufeffusing System;\n\n#region Licence\n' + SLASH_UNPADDED + '\n#endregion\n' + CS_BODY,
        '#region Licence\n#endregion\n' + CS_BODY,
        CS_BODY,
    ]
    for content in samples:
        fixed = content
        for _ in range(3):
            fixed = licence_headers.fix_content('Foo.cs', fixed, 2026)
        assert fixed.count('This code is Copyright') == 1
        assert licence_headers.check_content('Foo.cs', fixed, 2026) is None


def _drop_template_lines(header, start, count):
    lines = header.splitlines(keepends=True)
    return ''.join(lines[:start] + lines[start + count:])


def test_large_missing_section_after_address_line_is_fully_replaced():
    header = licence_headers._render_header('hash', year=2026)
    source = '# keep this source comment\nprint("ok")\n'
    for count in range(3, 7):
        broken = _drop_template_lines(header, 3, count)
        content = broken + source
        assert licence_headers.check_content('example.py', content, 2026) is not None
        fixed = _assert_stable('example.py', content)
        assert fixed == header + source


def test_large_missing_section_anywhere_in_header_is_fully_replaced():
    header = licence_headers._render_header('slash', year=2026)
    body_lines = len(header.splitlines()) - 1
    for start in range(2, body_lines - 3):
        broken = _drop_template_lines(header, start, 4)
        content = '#region Licence\n' + broken + '#endregion\n// keep me\n' + CS_BODY
        fixed = _assert_stable('Foo.cs', content)
        assert fixed == '#region Licence\n' + header + '#endregion\n// keep me\n' + CS_BODY, start


def test_section_recovery_preserves_source_comments_resembling_header_lines():
    header = licence_headers._render_header('hash', year=2026)
    truncated = ''.join(header.splitlines(keepends=True)[:3])
    for source in [
        '# notice.\nprint("ok")\n',
        '# notice.\n# keep this source comment\nprint("ok")\n',
        '# valid licence agreement as referred to above must contain this copyright\nprint("ok")\n',
        '# notice.\nprint("ok")\n# exclusion or limitation is prohibited, void or unenforceable under governing\n# law.\n',
    ]:
        fixed = _assert_stable('example.py', truncated + source)
        assert fixed == header + source


def test_orphaned_licence_tail_after_header_fails_and_is_removed():
    header = licence_headers._render_header('hash', year=2026)
    orphan = ''.join(header.splitlines(keepends=True)[7:])
    source = '# keep this source comment\nprint("ok")\n'
    content = header + orphan + source
    assert licence_headers.check_content('example.py', content, 2026) is not None
    fixed = _assert_stable('example.py', content)
    assert fixed == header + source


def test_insertion_into_python_licence_region_keeps_encoding_declaration_in_place():
    header = licence_headers._render_header('hash', year=2026)
    for prefix in [
        '#region Licence\n# coding: latin-1\n',
        '# coding: latin-1\n#region Licence\n',
        '#region Licence\n# coding: latin-1',
    ]:
        body = '\n#endregion\nname = "café"\n' if not prefix.endswith('\n') else '#endregion\nname = "café"\n'
        source = (prefix + body).encode('latin-1')
        fixed = licence_headers.fix_content('script.py', source, 2026)
        assert isinstance(fixed, bytes)
        text = fixed.decode('latin-1')
        assert text.startswith(prefix.rstrip('\n') + '\n' + header)
        assert licence_headers.check_content('script.py', fixed, 2026) is None
        assert licence_headers.fix_content('script.py', fixed, 2026) == fixed
        compile(fixed, 'script.py', 'exec')


def test_header_replacement_keeps_python_encoding_declaration_effective():
    header = licence_headers._render_header('hash', year=2026)
    legacy = '# Copyright The Cambridge Crystallographic Data Centre (CCDC) 2021\n'
    identity = '# This code is Copyright (C) 2020 The Cambridge Crystallographic Data Centre (CCDC)\n'
    address = '# of 12 Union Road, Cambridge CB2 1EZ, UK and a proprietary work of CCDC. This\n'
    declaration = '# coding: latin-1\n'
    body = 'name = "café"\n'
    cases = [
        (legacy + declaration + body, declaration + header + body),
        (legacy + declaration + '\n' + body, declaration + header + '\n' + body),
        (identity + declaration + address + body, declaration + header + body),
        ('#!/usr/bin/env python3\n' + declaration + legacy + body,
         '#!/usr/bin/env python3\n' + declaration + header + body),
        (legacy + declaration + header + body, declaration + header + body),
        ((legacy + declaration + body).replace('\n', '\r\n'), (declaration + header + body).replace('\n', '\r\n')),
    ]
    for source, expected in cases:
        fixed = licence_headers.fix_content('script.py', source.encode('latin-1'), 2026)
        assert fixed.decode('latin-1') == expected
        assert licence_headers.check_content('script.py', fixed, 2026) is None
        assert licence_headers.fix_content('script.py', fixed, 2026) == fixed
        compile(fixed, 'script.py', 'exec')


def test_directives_with_trailing_comments_are_preamble():
    header = licence_headers._render_header('slash', year=2026)
    region = '#region Licence\n' + header + '#endregion\n'
    cases = [
        ('Foo.cs', 'using System; // imports\n' + region + CS_BODY),
        ('Foo.cs', 'global using static System.Math;   // maths\nusing IO = System.IO; /* alias */\n' + region + CS_BODY),
        ('app.js', "'use strict'; // strict mode\n" + header + 'const x = 1;\n'),
        ('app.ts', '"use strict" /* strict */\n' + header + 'const x = 1;\n'),
    ]
    for filename, content in cases:
        assert licence_headers.check_content(filename, content, 2026) is None
        assert licence_headers.fix_content(filename, content, 2026) == content


def test_using_with_trailing_code_is_not_preamble():
    header = licence_headers._render_header('slash', year=2026)
    content = 'using System; class A { }\n' + header
    assert licence_headers.check_content('Foo.cs', content, 2026) is not None
    content = 'using System; /* note */ class A { }\n' + header
    assert licence_headers.check_content('Foo.cs', content, 2026) is not None


def test_process_files_reports_undecodable_file_in_fix_mode(tmp_path, capsys):
    target = tmp_path / 'broken.py'
    target.write_bytes(b'name = "\xe9"\n')
    assert licence_headers.process_files([str(target)], fix=True, year=2026) == 1
    assert 'file encoding could not be decoded' in capsys.readouterr().out
    assert target.read_bytes() == b'name = "\xe9"\n'
