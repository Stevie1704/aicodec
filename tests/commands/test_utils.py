import json
from pathlib import Path

import pytest

# Import the functions to be tested
from aicodec.infrastructure.cli.commands.utils import (
    _aggressive_escape_quotes,
    _find_closing_brace,
    _fix_json_string_value,
    clean_prepare_json_string,
    fix_and_parse_ai_json,
    get_list_from_user,
    get_user_confirmation,
    parse_json_file,
)

# Import the functions to be tested

# ---- Tests for get_user_confirmation ----


@pytest.mark.parametrize(
    "user_input, default_yes, expected_return",
    [
        # Test cases where default is YES
        ("y", True, True),
        ("yes", True, True),
        (" Y ", True, True),
        ("n", True, False),
        ("no", True, False),
        ("", True, True),  # Empty input should return the default
        # Test cases where default is NO
        ("y", False, True),
        ("n", False, False),
        (" NO ", False, False),
        ("", False, False),  # Empty input should return the default
    ],
)
def test_get_user_confirmation(monkeypatch, user_input, default_yes, expected_return):
    """Tests various inputs for the user confirmation function."""
    # Arrange: Mock the built-in input() function to return our desired user_input
    monkeypatch.setattr("builtins.input", lambda _: user_input)

    # Act: Call the function
    result = get_user_confirmation("Continue?", default_yes=default_yes)

    # Assert: Check if the result is what we expect
    assert result is expected_return


def test_get_user_confirmation_invalid_then_valid(monkeypatch, capsys):
    """Tests the retry loop for invalid input."""
    # Arrange: Mock input to provide an invalid response first, then a valid one
    inputs = iter(["invalid", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    # Act: Call the function
    result = get_user_confirmation("Proceed?")

    # Assert: The final result should be True, and an error message should be printed
    assert result is True
    captured = capsys.readouterr()
    assert "Invalid input. Please enter 'y' or 'n'." in captured.out


# ---- Tests for get_list_from_user ----


@pytest.mark.parametrize(
    "user_input, expected_list",
    [
        ("apple, banana, cherry", ["apple", "banana", "cherry"]),
        # Should strip whitespace
        ("  one , two  ,three ", ["one", "two", "three"]),
        ("single_item", ["single_item"]),
        ("", []),  # Empty input should result in an empty list
        ("a,,b", ["a", "", "b"]),  # Should handle empty items between commas
    ],
)
def test_get_list_from_user(monkeypatch, user_input, expected_list):
    """Tests various comma-separated inputs from the user."""
    # Arrange: Mock the built-in input() function
    monkeypatch.setattr("builtins.input", lambda _: user_input)

    # Act: Call the function
    result = get_list_from_user("Enter items:")

    # Assert: The returned list matches the expected output
    assert result == expected_list


# ---- Tests for load_default_prompt_template ----


@pytest.fixture
def mock_prompt_files(tmp_path):
    """Fixture to create a mock file structure for prompt templates."""
    # Create a structure that mimics aicodec/assets/prompts
    prompt_dir = tmp_path / "aicodec" / "assets" / "prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "minimal.txt").write_text("Minimal prompt content.")
    (prompt_dir / "full.txt").write_text("Full prompt content.")
    # We return the path to the top-level 'aicodec' directory
    return tmp_path / "aicodec"


def test_parse_valid_json_file(tmp_path: Path):
    """
    Tests the happy path: parsing a valid, formatted JSON file.
    The function should return a compact, single-line string.
    """
    # Arrange: Create a temporary directory and a formatted JSON file inside it
    json_content = {"name": "Test User", "details": {
        "age": 30, "is_active": True}, "tags": ["pytest", "python"]}
    file_path = tmp_path / "valid.json"
    file_path.write_text(json.dumps(json_content, indent=4), encoding="utf-8")

    # Act: Call the function with the path to the valid file
    result = parse_json_file(file_path)

    # Assert: Check if the output is the expected compact string
    expected_output = '{"name":"Test User","details":{"age":30,"is_active":true},"tags":["pytest","python"]}'
    assert result == expected_output


def test_parse_file_not_found(tmp_path: Path, capsys):
    """
    Tests the error path: attempting to parse a file that does not exist.
    The function should print an error to stderr and exit.
    """
    # Arrange: Define a path to a non-existent file
    non_existent_file = tmp_path / "not_found.json"

    # Act & Assert: Check that SystemExit is raised and capture stderr
    with pytest.raises(SystemExit) as e:
        parse_json_file(non_existent_file)

    # Assert the exit code is 1
    assert e.type is SystemExit
    assert e.value.code == 1

    # Assert the correct error message was printed to stderr
    captured = capsys.readouterr()
    assert "not found" in captured.err
    assert str(non_existent_file) in captured.err


def test_parse_invalid_json_file(tmp_path: Path, capsys):
    """
    Tests the error path: attempting to parse a file with malformed JSON.
    The function should print a parsing error to stderr and exit.
    """
    # Arrange: Create a file with invalid JSON (e.g., a trailing comma)
    invalid_content = '{"key": "value",}'
    file_path = tmp_path / "invalid.json"
    file_path.write_text(invalid_content, encoding="utf-8")

    # Act & Assert: Check that SystemExit is raised for a JSONDecodeError
    with pytest.raises(SystemExit) as e:
        parse_json_file(file_path)

    # Assert the exit code is 1
    assert e.type is SystemExit
    assert e.value.code == 1

    # Assert the correct error message was printed to stderr
    captured = capsys.readouterr()
    assert "Failed to parse JSON" in captured.err
    assert str(file_path) in captured.err


def test_perfectly_valid_json():
    """Tests that already-valid JSON passes through correctly."""
    valid_json_string = """
    {
      "summary": "This is a valid summary.",
      "changes": [
        {
          "filePath": "src/main.py",
          "action": "REPLACE",
          "content": "print(\\"Hello World!\\n\\tThis is indented.\\")"
        }
      ]
    }
    """
    expected_dict = {
        "summary": "This is a valid summary.",
        "changes": [
            {"filePath": "src/main.py", "action": "REPLACE",
                "content": 'print("Hello World!\n\tThis is indented.")'}
        ],
    }
    assert json.loads(fix_and_parse_ai_json(
        valid_json_string)) == expected_dict


def test_markdown_over_escaping_global_fix():
    """Tests the global replacement of Markdown escape characters."""
    broken_json_string = r"""
    {
      "summary": "This is \_a\_ test\. With \*stars\* and \`code\`.",
      "changes": [
        {
          "filePath": "\[path]/to/file\.txt",
          "action": "REPLACE",
          "content": "# This is a \!heading\nSee \#1 and \+plus or \-minus."
        }
      ]
    }
    """
    expected_dict = {
        "summary": "This is _a_ test. With *stars* and `code`.",
        "changes": [
            {
                "filePath": "[path]/to/file.txt",
                "action": "REPLACE",
                "content": "# This is a !heading\nSee #1 and +plus or -minus.",
            }
        ],
    }
    # Note: The \n in content is fixed by the targeted replacer
    assert json.loads(fix_and_parse_ai_json(
        broken_json_string)) == expected_dict


def test_unescaped_quotes_in_summary_and_content():
    """Tests fixing unescaped double-quotes in targeted fields."""
    broken_json_string = """
    {
      "summary": "This is a "broken" summary.",
      "changes": [
        {
          "filePath": "src/main.py",
          "action": "REPLACE",
          "content": "print("Hello "World"")"
        }
      ]
    }
    """
    expected_dict = {
        "summary": 'This is a "broken" summary.',
        "changes": [{"filePath": "src/main.py", "action": "REPLACE", "content": 'print("Hello "World"")'}],
    }
    assert json.loads(fix_and_parse_ai_json(
        broken_json_string)) == expected_dict


def test_literal_newlines_and_tabs_in_content():
    """Tests fixing unescaped control characters (newlines, tabs) in content."""
    # Using triple-quotes to create literal newlines and tabs
    broken_json_string = """
    {
      "summary": "Fixing newlines.",
      "changes": [
        {
          "filePath": "src/main.py",
          "action": "REPLACE",
          "content": "def hello():
    print("Hello")
	print("\tThis is a real tab char.")"
        }
      ]
    }
    """
    expected_dict = {
        "summary": "Fixing newlines.",
        "changes": [
            {
                "filePath": "src/main.py",
                "action": "REPLACE",
                "content": 'def hello():\n    print("Hello")\n\tprint("\tThis is a real tab char.")',
            }
        ],
    }
    assert json.loads(fix_and_parse_ai_json(
        broken_json_string)) == expected_dict


def test_unescaped_backslashes_in_content():
    """Tests fixing unescaped backslashes (e.g., Windows paths)."""
    # Let's create a more realistic broken string for this test
    # The AI would send literal backslashes, which we must represent
    # in Python by escaping them (e.g., 'C:\\Users' to represent 'C:\Users').
    broken_path_string = r"""
    {
      "summary": "Fixing paths.",
      "changes": [
        {
          "filePath": "C:\\Windows\\System32",
          "action": "REPLACE",
          "content": "path = "C:\Users\test\new_folder"
print("This is a valid escape: \n")"
        }
      ]
    }
    """

    parsed = json.loads(fix_and_parse_ai_json(broken_path_string))
    assert parsed is not None
    # The parsed string "C:\\\\Users..." becomes "C:\\Users..." in Python
    assert (
        parsed["changes"][0][
            "content"] == 'path = "C:\\Users\test\new_folder"\nprint("This is a valid escape: \n")'
    )


def test_all_errors_combined_multiple_entries():
    """Tests a complex string with all error types and multiple change entries."""
    broken_json_string = r"""
    {
      "summary": "This \_summary\_ has "quotes" and a \. (dot).",
      "changes": [
        {
          "filePath": "\[file1].py",
          "action": "REPLACE",
          "content": "def func1():
    print("This is "func1"")"
        },
        {
          "filePath": "src/path\.txt",
          "action": "CREATE",
          "content": "path = "C:\Windows"
This is a \*star\*."
        }
      ]
    }
    """
    expected_dict = {
        "summary": 'This _summary_ has "quotes" and a . (dot).',
        "changes": [
            {"filePath": "[file1].py", "action": "REPLACE",
                "content": 'def func1():\n    print("This is "func1"")'},
            {"filePath": "src/path.txt", "action": "CREATE",
                "content": 'path = "C:\\Windows"\nThis is a *star*.'},
        ],
    }
    assert json.loads(fix_and_parse_ai_json(
        broken_json_string)) == expected_dict


def test_preserves_already_valid_escapes():
    """Tests that the function doesn't double-escape valid JSON."""
    valid_json_string = r"""{"summary": "This summary is \"already\" valid.","changes": [{"filePath": "src/main.py","action": "REPLACE","content": "print(\"Hello \"World\"\nThis path is C:\\Users\\test\")"}]}"""
    expected_dict = {
        "summary": 'This summary is "already" valid.',
        "changes": [
            {
                "filePath": "src/main.py",
                "action": "REPLACE",
                "content": 'print("Hello \"World\"\nThis path is C:\\Users\\test")',
            }
        ],
    }
    assert json.loads(fix_and_parse_ai_json(
        valid_json_string)) == expected_dict


def test_empty_summary_and_content():
    """Tests behavior with empty strings in targeted fields."""
    json_string = """
    {
      "summary": "",
      "changes": [
        {
          "filePath": "file.txt",
          "action": "CREATE",
          "content": ""
        }
      ]
    }
    """
    expected_dict = {"summary": "", "changes": [
        {"filePath": "file.txt", "action": "CREATE", "content": ""}]}
    assert json.loads(fix_and_parse_ai_json(json_string)) == expected_dict


def test_content_fix_at_end_of_json():
    """Tests that the 'content' regex correctly matches the last item."""
    broken_json_string = r"""
    {
      "summary": "Final test.",
      "changes": [
        {
          "filePath": "last_file.py",
          "action": "REPLACE",
          "content": "print("This is the "end"")"
        }
      ]
    }
    """
    expected_dict = {
        "summary": "Final test.",
        "changes": [{"filePath": "last_file.py", "action": "REPLACE", "content": 'print("This is the "end"")'}],
    }
    # This ensures the (?:,|\}) part of the regex works for the '}' case
    assert json.loads(fix_and_parse_ai_json(
        broken_json_string)) == expected_dict


# ---- Tests for _fix_json_string_value ----


def test_fix_json_string_value_unescaped_quotes():
    """Tests that unescaped quotes are properly escaped."""
    value = 'The "Software" is provided "AS IS"'
    fixed = _fix_json_string_value(value)
    assert fixed == 'The \\"Software\\" is provided \\"AS IS\\"'


def test_fix_json_string_value_literal_newlines():
    """Tests that literal newlines are escaped to \\n."""
    value = 'Line 1\nLine 2\nLine 3'
    fixed = _fix_json_string_value(value)
    assert fixed == 'Line 1\\nLine 2\\nLine 3'
    assert '\n' not in fixed  # No literal newlines should remain


def test_fix_json_string_value_literal_tabs():
    """Tests that literal tabs are escaped to \\t."""
    value = 'Column1\tColumn2\tColumn3'
    fixed = _fix_json_string_value(value)
    assert fixed == 'Column1\\tColumn2\\tColumn3'
    assert '\t' not in fixed  # No literal tabs should remain


def test_fix_json_string_value_already_escaped():
    """Tests that already-escaped quotes are not double-escaped."""
    value = 'Already \\"escaped\\" quotes'
    fixed = _fix_json_string_value(value)
    assert fixed == 'Already \\"escaped\\" quotes'
    # Should not become \\\\"escaped\\\\"


def test_fix_json_string_value_mixed_escapes():
    """Tests a string with both escaped and unescaped quotes."""
    value = 'Some \\"valid\\" and some "broken" quotes'
    fixed = _fix_json_string_value(value)
    assert fixed == 'Some \\"valid\\" and some \\"broken\\" quotes'


def test_fix_json_string_value_with_arrays():
    """Tests content that looks like JSON arrays."""
    value = 'requires = ["setuptools>=68", "wheel"]'
    fixed = _fix_json_string_value(value)
    assert fixed == 'requires = [\\"setuptools>=68\\", \\"wheel\\"]'


def test_fix_json_string_value_empty_string():
    """Tests that empty strings are handled correctly."""
    value = ''
    fixed = _fix_json_string_value(value)
    assert fixed == ''


# ---- Tests for _find_closing_brace ----


def test_find_closing_brace_simple():
    """Tests finding a closing brace in simple, well-formed JSON."""
    text = '{ "key": "value" },'
    result = _find_closing_brace(text, 1)
    assert result == 17  # Position of the closing }
    assert text[result] == '}'


def test_find_closing_brace_with_newline_indent():
    """Tests finding closing brace with newline and proper indentation."""
    text = '''        {
            "filePath": "test.py",
            "action": "CREATE",
            "content": "test"
        },'''
    result = _find_closing_brace(text, 1)
    assert result > 0
    assert text[result] == '}'


def test_find_closing_brace_no_newline():
    """Tests finding closing brace when it comes right after content."""
    text = '{ "content": "test" }, { "next": "obj" }'
    result = _find_closing_brace(text, 1)
    assert result == 20  # Position of first }
    assert text[result] == '}'


def test_find_closing_brace_with_braces_in_content():
    """Tests that braces inside content (like f-strings) don't confuse the finder."""
    text = '''        {
            "content": "f\\"Player {player}, enter your move\\""
        },'''
    result = _find_closing_brace(text, 1)
    assert result > 0
    assert text[result] == '}'
    # Verify it didn't stop at the } in {player}
    assert result > text.find('{player}')


def test_find_closing_brace_multiple_objects():
    """Tests finding the correct closing brace when multiple objects exist."""
    text = '''        {
            "filePath": "first.py",
            "content": "data"
        }, {
            "filePath": "second.py",
            "content": "more"
        }'''
    result = _find_closing_brace(text, 1)
    # Should find the first closing brace, not the second
    assert result > 0
    assert result < text.find('"second.py"')


# ---- Tests for _aggressive_escape_quotes ----


def test_aggressive_escape_quotes_license_content():
    """Tests escaping quotes in LICENSE-like content."""
    json_str = '''{
    "summary": "Test",
    "changes": [
        {
            "filePath": "LICENSE",
            "action": "CREATE",
            "content": "THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY"
        }
    ]
}'''
    result = _aggressive_escape_quotes(json_str)
    parsed = json.loads(result)
    assert '"AS IS"' in parsed['changes'][0]['content']
    assert 'WITHOUT WARRANTY' in parsed['changes'][0]['content']


def test_aggressive_escape_quotes_pyproject_arrays():
    """Tests escaping quotes in array literals within content."""
    json_str = '''{
    "summary": "Test",
    "changes": [
        {
            "filePath": "pyproject.toml",
            "action": "CREATE",
            "content": "requires = ["setuptools>=68", "wheel"]"
        }
    ]
}'''
    result = _aggressive_escape_quotes(json_str)
    parsed = json.loads(result)
    content = parsed['changes'][0]['content']
    assert 'setuptools>=68' in content
    assert 'wheel' in content


def test_aggressive_escape_quotes_python_fstrings():
    """Tests that Python f-strings with braces are handled correctly."""
    json_str = '''{
    "summary": "Test",
    "changes": [
        {
            "filePath": "cli.py",
            "action": "CREATE",
            "content": "input(f\\"Player {player}, enter move\\")"
        }
    ]
}'''
    result = _aggressive_escape_quotes(json_str)
    parsed = json.loads(result)
    content = parsed['changes'][0]['content']
    assert '{player}' in content
    assert 'Player' in content


def test_aggressive_escape_quotes_multiple_changes():
    """Tests processing multiple change objects."""
    json_str = '''{
    "summary": "Multiple changes",
    "changes": [
        {
            "filePath": "file1.py",
            "action": "CREATE",
            "content": "print("hello")"
        },
        {
            "filePath": "file2.py",
            "action": "CREATE",
            "content": "data = {"key": "value"}"
        }
    ]
}'''
    result = _aggressive_escape_quotes(json_str)
    parsed = json.loads(result)
    assert len(parsed['changes']) == 2
    assert 'hello' in parsed['changes'][0]['content']
    assert 'key' in parsed['changes'][1]['content']


def test_aggressive_escape_quotes_summary_with_quotes():
    """Tests that summary field quotes are also escaped."""
    json_str = '''{
    "summary": "This is a "test" summary",
    "changes": [
        {
            "filePath": "test.py",
            "action": "CREATE",
            "content": "test"
        }
    ]
}'''
    result = _aggressive_escape_quotes(json_str)
    parsed = json.loads(result)
    assert '"test"' in parsed['summary']


def test_aggressive_escape_quotes_multiline_content():
    """Tests content with literal newlines across multiple lines."""
    json_str = '''{
    "summary": "Test",
    "changes": [
        {
            "filePath": "test.py",
            "action": "CREATE",
            "content": "def func():
    print("hello")
    return True"
        }
    ]
}'''
    result = _aggressive_escape_quotes(json_str)
    parsed = json.loads(result)
    content = parsed['changes'][0]['content']
    # Literal newlines should be escaped
    assert '\\n' in result
    # But parsed content should have actual newlines
    assert '\n' in content


# ---- Integration Tests for clean_prepare_json_string ----


def test_clean_prepare_json_string_valid_json(tmp_path):
    """Tests that valid JSON passes through correctly."""
    json_str = '''{
    "summary": "Valid test",
    "changes": [
        {
            "filePath": "test.py",
            "action": "CREATE",
            "content": "print(\\"hello\\")"
        }
    ]
}'''
    result = clean_prepare_json_string(json_str)
    parsed = json.loads(result)
    assert parsed['summary'] == 'Valid test'
    assert len(parsed['changes']) == 1


def test_clean_prepare_json_string_with_unescaped_quotes(tmp_path):
    """Tests the aggressive mode kicks in for unescaped quotes."""
    json_str = '''{
    "summary": "Test with "quotes"",
    "changes": [
        {
            "filePath": "LICENSE",
            "action": "CREATE",
            "content": "THE SOFTWARE IS PROVIDED "AS IS""
        }
    ]
}'''
    result = clean_prepare_json_string(json_str)
    parsed = json.loads(result)
    assert '"quotes"' in parsed['summary']
    assert '"AS IS"' in parsed['changes'][0]['content']


def test_clean_prepare_json_string_complex_real_world(tmp_path):
    """Tests a complex real-world example similar to unvalid.json."""
    json_str = '''{
    "summary": "Scaffold a Python project with CLI and AI",
    "changes": [
        {
            "filePath": "LICENSE",
            "action": "CREATE",
            "content": "MIT License\\n\\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software"
        },
        {
            "filePath": "pyproject.toml",
            "action": "CREATE",
            "content": "[build-system]\\nrequires = ["setuptools>=68", "wheel"]\\nbuild-backend = "setuptools.build_meta""
        },
        {
            "filePath": "cli.py",
            "action": "CREATE",
            "content": "def _read_move(player: str):\\n    while True:\\n        raw = input(f\\"Player {player}, enter your move: \\").strip()"
        }
    ]
}'''
    result = clean_prepare_json_string(json_str)
    parsed = json.loads(result)

    # Verify all three files were processed
    assert len(parsed['changes']) == 3

    # Verify LICENSE content
    license_content = parsed['changes'][0]['content']
    assert '"Software"' in license_content

    # Verify pyproject.toml content
    pyproject_content = parsed['changes'][1]['content']
    assert 'setuptools>=68' in pyproject_content
    assert 'wheel' in pyproject_content

    # Verify cli.py content
    cli_content = parsed['changes'][2]['content']
    assert '{player}' in cli_content
    assert 'Player' in cli_content


def test_clean_prepare_json_string_schema_validation():
    """Tests that the result is validated against the schema."""
    # Missing required fields should raise an error
    invalid_json = '{"summary": "test"}'  # Missing "changes"

    with pytest.raises(Exception) as exc_info:
        clean_prepare_json_string(invalid_json)

    assert 'validation' in str(exc_info.value).lower() or 'required' in str(exc_info.value).lower()
