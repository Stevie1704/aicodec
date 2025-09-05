# tests/commands/test_apply.py
import json
from argparse import Namespace
from unittest.mock import patch

from aicodec.infrastructure.cli.commands import apply


def test_apply_run_basic(sample_project, aicodec_config_file, sample_changes_file, monkeypatch):
    """Test apply command launches the review server."""
    monkeypatch.chdir(sample_project)

    # Point config to the sample changes file
    config_data = json.loads(aicodec_config_file.read_text())
    config_data["prepare"]["changes"] = str(sample_changes_file)
    aicodec_config_file.write_text(json.dumps(config_data))

    args = Namespace(
        config=str(aicodec_config_file),
        output_dir=None,
        changes=None
    )

    with patch('aicodec.infrastructure.cli.commands.apply.launch_review_server') as mock_launch:
        apply.run(args)
        mock_launch.assert_called_once()
        call_args = mock_launch.call_args
        assert call_args[1]['mode'] == "apply"  # mode


def test_apply_run_with_overrides(sample_project, aicodec_config_file, sample_changes_file, monkeypatch):
    """Test apply command with CLI overrides for paths."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        output_dir=sample_project,
        changes=sample_changes_file
    )

    with patch('aicodec.infrastructure.cli.commands.apply.launch_review_server') as mock_launch:
        apply.run(args)
        mock_launch.assert_called_once()

        # Check that the service was initialized with the correct, resolved paths
        review_service = mock_launch.call_args[0][0]
        assert review_service.output_dir == sample_project.resolve()
        assert review_service.changes_file == sample_changes_file.resolve()


def test_apply_run_missing_config(sample_project, monkeypatch, capsys):
    """Test apply command fails gracefully if config values are missing."""
    monkeypatch.chdir(sample_project)

    # Create an empty config
    config_file = sample_project / ".aicodec" / "config.json"
    config_file.parent.mkdir()
    config_file.write_text("{}")

    args = Namespace(
        config=str(config_file),
        output_dir=None,
        changes=None
    )

    apply.run(args)
    captured = capsys.readouterr()
    assert "Error: Missing required configuration" in captured.out
