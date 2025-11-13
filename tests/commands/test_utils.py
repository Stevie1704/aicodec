import json
from pathlib import Path

import pytest

# Import the function to be tested
from aicodec.infrastructure.cli.commands.utils import (
    JsonPreparationError,
    clean_prepare_json_string,
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


# --- Tests for clean_prepare_json_string ---

# A valid JSON structure that conforms to the schema
VALID_PAYLOAD = {
    "summary": "This is a valid summary.",
    "changes": [
        {
            "filePath": "src/main.py",
            "action": "REPLACE",
            "content": "print('Hello, World!')",
        }
    ],
}

# A dictionary that will be converted to a pretty-printed JSON string
VALID_JSON_STRING = json.dumps(VALID_PAYLOAD, indent=4)


def test_clean_prepare_json_with_valid_json():
    """Tests that a perfectly valid JSON string passes through correctly."""
    llm_output = json.dumps(VALID_PAYLOAD)  # Compact JSON
    result = clean_prepare_json_string(llm_output)
    assert json.loads(result) == VALID_PAYLOAD
    assert result == VALID_JSON_STRING  # Ensure it's pretty-printed


def test_clean_prepare_json_with_trailing_comma():
    """Tests repair of a JSON string with a trailing comma."""
    broken_json = """
    {
      "summary": "A summary.",
      "changes": [
        {
          "filePath": "file.txt",
          "action": "CREATE",
          "content": "Hello"
        },
      ]
    }
    """
    result = clean_prepare_json_string(broken_json)
    # The repaired JSON should not have the trailing comma in the list
    expected_payload = {
        "summary": "A summary.",
        "changes": [
            {"filePath": "file.txt", "action": "CREATE", "content": "Hello"}
        ],
    }
    assert json.loads(result) == expected_payload


def test_clean_prepare_json_with_missing_quotes():
    """Tests repair of a JSON string with missing quotes around keys."""
    broken_json = """
    {
      summary: "A summary.",
      changes: [
        {
          filePath: "file.txt",
          action: "CREATE",
          content: "Hello"
        }
      ]
    }
    """
    result = clean_prepare_json_string(broken_json)
    expected_payload = {
        "summary": "A summary.",
        "changes": [
            {"filePath": "file.txt", "action": "CREATE", "content": "Hello"}
        ],
    }
    assert json.loads(result) == expected_payload


def test_clean_prepare_json_with_single_quotes():
    """Tests repair of a JSON string that uses single quotes."""
    broken_json = """
    {
      'summary': 'A summary.',
      'changes': [
        {
          'filePath': 'file.txt',
          'action': 'CREATE',
          'content': 'Hello'
        }
      ]
    }
    """
    result = clean_prepare_json_string(broken_json)
    expected_payload = {
        "summary": "A summary.",
        "changes": [
            {"filePath": "file.txt", "action": "CREATE", "content": "Hello"}
        ],
    }
    assert json.loads(result) == expected_payload


def test_validation_error_missing_field():
    """Tests that a validation error is raised for a missing required field."""
    # Missing the 'summary' field
    invalid_payload = {
        "changes": [
            {"filePath": "file.txt", "action": "CREATE", "content": "Hello"}
        ]
    }
    invalid_json = json.dumps(invalid_payload)

    with pytest.raises(JsonPreparationError) as excinfo:
        clean_prepare_json_string(invalid_json)

    assert "Repaired JSON failed validation" in str(excinfo.value)
    assert "'summary' is a required property" in str(excinfo.value)


def test_validation_error_wrong_data_type():
    """Tests that a validation error is raised for an incorrect data type."""
    # 'changes' should be a list, not a string
    invalid_payload = {
        "summary": "A summary.",
        "changes": "this should be a list of objects",
    }
    invalid_json = json.dumps(invalid_payload)

    with pytest.raises(JsonPreparationError) as excinfo:
        clean_prepare_json_string(invalid_json)

    assert "Repaired JSON failed validation" in str(excinfo.value)
    assert "'this should be a list of objects' is not of type 'array'" in str(
        excinfo.value
    )


def test_unrepairable_json():
    """Tests that an error is raised for completely un-repairable JSON."""
    unrepairable_json = "this is not json at all"

    with pytest.raises(JsonPreparationError) as excinfo:
        clean_prepare_json_string(unrepairable_json)

    assert "Failed to parse or repair the JSON" in str(excinfo.value)


def test_schema_loading_error(monkeypatch):
    """
    Tests that a fatal error is raised if the JSON schema cannot be loaded.
    """
    # Mock the `files()` object from importlib.resources to raise a FileNotFoundError
    def mock_files(package):
        class MockPath:
            def __truediv__(self, other):
                return self

            def read_text(self, encoding):
                raise FileNotFoundError("Mocked: Schema file not found.")
        return MockPath()

    monkeypatch.setattr(
        "aicodec.infrastructure.cli.commands.utils.files", mock_files)

    with pytest.raises(JsonPreparationError) as excinfo:
        clean_prepare_json_string(VALID_JSON_STRING)

    assert "Fatal: Could not load the internal JSON schema" in str(
        excinfo.value)
