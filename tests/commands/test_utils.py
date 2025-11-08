import json
from pathlib import Path

import pytest

# Import the function to be tested
from aicodec.infrastructure.cli.commands.utils import (
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
    json_content = {"name": "Test User", "details": {"age": 30, "is_active": True}, "tags": ["pytest", "python"]}
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
            {"filePath": "src/main.py", "action": "REPLACE", "content": 'print("Hello World!\\n\\tThis is indented.")'}
        ],
    }
    assert fix_and_parse_ai_json(valid_json_string) == expected_dict


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
                "content": "# This is a !heading\\nSee #1 and +plus or -minus.",
            }
        ],
    }
    # Note: The \n in content is fixed by the targeted replacer
    assert fix_and_parse_ai_json(broken_json_string) == expected_dict


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
    assert fix_and_parse_ai_json(broken_json_string) == expected_dict


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
                "content": 'def hello():\\n    print("Hello")\\n\\tprint("\\tThis is a real tab char.")',
            }
        ],
    }
    assert fix_and_parse_ai_json(broken_json_string) == expected_dict


def test_unescaped_backslashes_in_content():
    """Tests fixing unescaped backslashes (e.g., Windows paths)."""
    # Let's create a more realistic broken string for this test
    # The AI would send literal backslashes, which we must represent
    # in Python by escaping them (e.g., 'C:\\Users' to represent 'C:\Users').
    broken_path_string = """
    {
      "summary": "Fixing paths.",
      "changes": [
        {
          "filePath": "C:\\\\Windows\\\\System32",
          "action": "REPLACE",
          "content": "path = "C:\\Users\\test\\new_folder"
print("This is a valid escape: \\n")"
        }
      ]
    }
    """

    parsed = fix_and_parse_ai_json(broken_path_string)
    assert parsed is not None
    # The parsed string "C:\\\\Users..." becomes "C:\\Users..." in Python
    assert (
        parsed["changes"][0]["content"] == 'path = "C:\\Users\\test\\new_folder"\\nprint("This is a valid escape: \\n")'
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
            {"filePath": "[file1].py", "action": "REPLACE", "content": 'def func1():\\n    print("This is "func1"")'},
            {"filePath": "src/path.txt", "action": "CREATE", "content": 'path = "C:\\\\Windows"\\nThis is a *star*.'},
        ],
    }
    assert fix_and_parse_ai_json(broken_json_string) == expected_dict


def test_preserves_already_valid_escapes():
    """Tests that the function doesn't double-escape valid JSON."""
    valid_json_string = r"""
    {
      "summary": "This summary is \"already\" valid.",
      "changes": [
        {
          "filePath": "src/main.py",
          "action": "REPLACE",
          "content": "print(\"Hello \\"World\\"\\nThis path is C:\\\\Users\\\\test\")"
        }
      ]
    }
    """
    expected_dict = {
        "summary": 'This summary is "already" valid.',
        "changes": [
            {
                "filePath": "src/main.py",
                "action": "REPLACE",
                "content": 'print("Hello \\"World\\"\\nThis path is C:\\\\Users\\\\test")',
            }
        ],
    }
    assert fix_and_parse_ai_json(valid_json_string) == expected_dict


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
    expected_dict = {"summary": "", "changes": [{"filePath": "file.txt", "action": "CREATE", "content": ""}]}
    assert fix_and_parse_ai_json(json_string) == expected_dict


def test_returns_none_for_structurally_invalid_json():
    """Tests that None is returned if the JSON is broken *outside* the fixes."""
    # This JSON has a missing comma after "filePath"
    invalid_json_string = """
    {
      "summary": "This summary is fine.",
      "changes": [
        {
          "filePath": "file.txt"
          "action": "CREATE",
          "content": "This content is fine."
        }
      ]
    }
    """
    assert fix_and_parse_ai_json(invalid_json_string) is None


def test_returns_none_if_regex_no_match_and_json_is_broken():
    """Tests that None is returned if the regex doesn't match and JSON is still broken."""
    # The key is "summmmary" (misspelled), so the fix won't run on it.
    # The unescaped "quotes" will cause the final json.loads() to fail.
    invalid_json_string = """
    {
      "summmmary": "This "summary" is broken.",
      "changes": [
        {
          "filePath": "file.txt",
          "action": "CREATE",
          "content": "This content is fine."
        }
      ]
    }
    """
    assert fix_and_parse_ai_json(invalid_json_string) is None


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
    assert fix_and_parse_ai_json(broken_json_string) == expected_dict
