# tests/commands/test_schema.py
import json
from unittest.mock import patch, MagicMock
import pytest

from aicodec.infrastructure.cli.commands import schema


def test_schema_run_prints_json(capsys):
    """Tests that the schema command prints a valid JSON object."""
    schema.run(None)
    captured = capsys.readouterr()

    # Check that it's valid JSON
    schema_data = json.loads(captured.out)
    assert isinstance(schema_data, dict)
    assert "$schema" in schema_data
    assert "title" in schema_data


def test_schema_run_file_not_found(capsys):
    """Tests error handling when the schema file is missing."""
    with patch('aicodec.infrastructure.cli.commands.schema.files') as mock_files:
        mock_path = MagicMock()
        mock_path.read_text.side_effect = FileNotFoundError
        # This is a bit complex to mock the `files() / "assets" / "file.json"` pattern
        mock_files.return_value.__truediv__.return_value.__truediv__.return_value = mock_path

        with pytest.raises(SystemExit) as e:
            schema.run(None)

        assert e.value.code == 1
        captured = capsys.readouterr()
        assert "Error: decoder_schema.json not found" in captured.err
