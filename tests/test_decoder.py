# test_decoder.py

import pytest
import os
from aicodec.decoder import apply_changes


@pytest.fixture
def temp_output_dir(tmp_path):
    """A pytest fixture that provides a temporary directory for test output."""
    return tmp_path


@pytest.fixture
def changes_data():
    """A pytest fixture that provides a sample changes data structure."""
    return {
        'changes': [
            {
                'action': 'CREATE',
                'filePath': 'new_file.txt',
                'content': 'Hello World!'
            },
            {
                'action': 'REPLACE',
                'filePath': os.path.join('src', 'app.py'),
                'content': 'print("hello from app")'
            }
        ]
    }


def test_dry_run(changes_data, temp_output_dir, capsys):
    """
    Tests that --dry-run shows proposed changes but doesn't modify the filesystem.
    - `capsys` is a fixture that captures stdout/stderr.
    """
    output_dir_path = temp_output_dir
    apply_changes(changes_data, str(output_dir_path), dry_run=True)

    # capsys.readouterr() returns the captured output
    captured = capsys.readouterr()
    output = captured.out

    # Use simple `assert` statements for checks
    assert "Dry run complete. No files were changed." in output
    assert f"- CREATE: {output_dir_path / 'new_file.txt'}" in output
    assert f"- REPLACE: {output_dir_path / 'src' / 'app.py'}" in output

    # Check that no files were created using pathlib objects from tmp_path
    assert not (output_dir_path / 'new_file.txt').exists()
    assert not (output_dir_path / 'src').exists()


def test_apply_changes_auto_confirm(changes_data, temp_output_dir):
    """Tests that changes are correctly applied with auto_confirm=True."""
    output_dir_path = temp_output_dir
    apply_changes(changes_data, str(output_dir_path), auto_confirm=True)

    file1_path = output_dir_path / 'new_file.txt'
    assert file1_path.exists()
    assert file1_path.read_text(encoding='utf-8') == 'Hello World!'

    file2_path = output_dir_path / 'src' / 'app.py'
    assert file2_path.exists()
    assert file2_path.read_text(encoding='utf-8') == 'print("hello from app")'


def test_apply_changes_user_confirms_yes(changes_data, temp_output_dir, mocker):
    """
    Tests the interactive confirmation flow where the user enters 'y'.
    - `mocker` is a fixture from pytest-mock for easy mocking.
    """
    mocker.patch('builtins.input', return_value='y')
    apply_changes(changes_data, str(temp_output_dir), auto_confirm=False)

    assert (temp_output_dir / 'new_file.txt').exists()
    assert (temp_output_dir / 'src' / 'app.py').exists()


def test_apply_changes_user_confirms_no(changes_data, temp_output_dir, capsys, mocker):
    """Tests the interactive flow where the user enters 'n' to cancel."""
    mocker.patch('builtins.input', return_value='n')
    apply_changes(changes_data, str(temp_output_dir), auto_confirm=False)

    captured = capsys.readouterr()
    assert "Operation cancelled." in captured.out
    assert not (temp_output_dir / 'new_file.txt').exists()


def test_unsupported_action(temp_output_dir, capsys):
    """Tests that an unsupported action is handled gracefully."""
    unsupported_changes = {
        'changes': [{'action': 'DELETE', 'filePath': 'file.txt', 'content': ''}]
    }
    apply_changes(unsupported_changes, str(temp_output_dir), auto_confirm=True)

    captured = capsys.readouterr()
    assert "WARNING: Action 'DELETE' is not supported." in captured.out
    assert not (temp_output_dir / 'file.txt').exists()
