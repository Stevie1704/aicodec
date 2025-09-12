# tests/commands/test_revert.py
import json
from argparse import Namespace
from unittest.mock import patch

import pytest

from aicodec.infrastructure.cli.commands import revert


@pytest.fixture
def setup_revert_file(sample_project):
    revert_dir = sample_project / ".aicodec"
    revert_dir.mkdir(exist_ok=True)
    revert_file = revert_dir / "revert.json"
    revert_file.write_text(json.dumps({"summary": "revert data", "changes": []}))
    return revert_file


def test_revert_run_basic(sample_project, aicodec_config_file, setup_revert_file, monkeypatch):
    """Test revert command launches review server when revert.json exists."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        output_dir=None
    )

    with patch('aicodec.infrastructure.cli.commands.revert.launch_review_server') as mock_launch:
        revert.run(args)
        mock_launch.assert_called_once()
        call_args = mock_launch.call_args
        assert call_args.kwargs['mode'] == "revert"  # Correctly check kwargs


def test_revert_run_no_revert_file(sample_project, aicodec_config_file, monkeypatch, capsys):
    """Test revert command prints an error if revert.json is missing."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        output_dir=None
    )

    revert.run(args)
    captured = capsys.readouterr()
    assert "Error: No revert data found" in captured.out


def test_revert_run_with_override(sample_project, aicodec_config_file, setup_revert_file, monkeypatch):
    """Test revert command with output_dir override."""
    # We change directory to parent to ensure the override is working
    monkeypatch.chdir(sample_project.parent)

    args = Namespace(
        config=str(aicodec_config_file),
        output_dir=sample_project  # Explicitly point to the project dir
    )

    with patch('aicodec.infrastructure.cli.commands.revert.launch_review_server') as mock_launch:
        revert.run(args)
        mock_launch.assert_called_once()

        review_service = mock_launch.call_args[0][0]
        assert review_service.output_dir == sample_project.resolve()
        assert review_service.changes_file == (sample_project / ".aicodec" / "revert.json").resolve()
