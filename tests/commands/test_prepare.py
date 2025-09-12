# tests/commands/test_prepare.py
import json
from argparse import Namespace
from unittest.mock import patch

import pytest

from aicodec.infrastructure.cli.commands import prepare


@pytest.fixture
def valid_json_content(sample_changes_json_content):
    return json.dumps(sample_changes_json_content)


def test_prepare_run_editor_mode(sample_project, aicodec_config_file, monkeypatch):
    """Test prepare command opens an editor by default."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        changes=None,
        from_clipboard=False
    )

    with patch('aicodec.infrastructure.cli.commands.prepare.open_file_in_editor') as mock_open:
        prepare.run(args)
        mock_open.assert_called_once()

    changes_file = sample_project / ".aicodec" / "changes.json"
    assert changes_file.exists()
    assert changes_file.read_text() == ""


def test_prepare_run_from_clipboard_success(sample_project, aicodec_config_file, valid_json_content, monkeypatch):
    """Test prepare with valid JSON from clipboard."""
    monkeypatch.chdir(sample_project)
    monkeypatch.setenv("AICODEC_TEST_MODE", "1")
    monkeypatch.setenv("AICODEC_TEST_CLIPBOARD", valid_json_content)

    args = Namespace(
        config=str(aicodec_config_file),
        changes=None,
        from_clipboard=True
    )

    with patch('jsonschema.validate'):  # Mock validation to avoid dependency on exact schema
        prepare.run(args)

    changes_file = sample_project / ".aicodec" / "changes.json"
    assert changes_file.read_text() == valid_json_content


def test_prepare_run_from_clipboard_invalid_json(sample_project, aicodec_config_file, monkeypatch, capsys):
    """Test prepare with invalid JSON from clipboard."""
    monkeypatch.chdir(sample_project)
    monkeypatch.setenv("AICODEC_TEST_MODE", "1")
    monkeypatch.setenv("AICODEC_TEST_CLIPBOARD", "this is not json")

    args = Namespace(
        config=str(aicodec_config_file),
        changes=None,
        from_clipboard=True
    )

    prepare.run(args)
    captured = capsys.readouterr()
    assert "Error: Clipboard content is not valid JSON" in captured.out


def test_prepare_run_from_clipboard_schema_fail(sample_project, aicodec_config_file, monkeypatch, capsys):
    """Test prepare with JSON that fails schema validation."""
    monkeypatch.chdir(sample_project)
    bad_json = json.dumps({"foo": "bar"})
    monkeypatch.setenv("AICODEC_TEST_MODE", "1")
    monkeypatch.setenv("AICODEC_TEST_CLIPBOARD", bad_json)

    args = Namespace(
        config=str(aicodec_config_file),
        changes=None,
        from_clipboard=True
    )

    prepare.run(args)
    captured = capsys.readouterr()
    assert "Error: Clipboard content does not match the expected schema" in captured.out


def test_prepare_overwrite_cancel(sample_project, aicodec_config_file, monkeypatch, capsys):
    """Test canceling overwrite of an existing changes file."""
    monkeypatch.chdir(sample_project)
    changes_file = sample_project / ".aicodec" / "changes.json"
    changes_file.parent.mkdir(exist_ok=True)
    changes_file.write_text('{"existing": true}')

    args = Namespace(
        config=str(aicodec_config_file),
        changes=None,
        from_clipboard=False
    )

    with patch('builtins.input', return_value='n'):
        prepare.run(args)

    captured = capsys.readouterr()
    assert "Operation cancelled" in captured.out
    assert changes_file.read_text() == '{"existing": true}'
