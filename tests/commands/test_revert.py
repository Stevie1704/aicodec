# tests/commands/test_revert.py
import json
from argparse import Namespace
from unittest.mock import patch

import pytest

from aicodec.infrastructure.cli.commands import revert


@pytest.fixture
def setup_revert_file(sample_project):
    reverts_dir = sample_project / ".aicodec" / "reverts"
    reverts_dir.mkdir(parents=True, exist_ok=True)
    revert_file = reverts_dir / "revert-001.json"
    revert_file.write_text(
        json.dumps({"summary": "revert data", "changes": [{"filePath": "a.py", "action": "DELETE", "content": ""}]})
    )
    return revert_file


def test_revert_run_basic(sample_project, aicodec_config_file, setup_revert_file, monkeypatch):
    """Test revert command launches review server when revert.json exists."""
    monkeypatch.chdir(sample_project)

    args = Namespace(config=str(aicodec_config_file), output_dir=None, all=False, files=None)

    with patch("aicodec.infrastructure.cli.commands.revert.launch_review_server") as mock_launch:
        revert.run(args)
        mock_launch.assert_called_once()
        call_args = mock_launch.call_args
        assert call_args.kwargs["mode"] == "revert"  # Correctly check kwargs


def test_revert_run_no_revert_file(sample_project, aicodec_config_file, monkeypatch, capsys):
    """Test revert command prints an error if revert.json is missing."""
    monkeypatch.chdir(sample_project)

    args = Namespace(config=str(aicodec_config_file), output_dir=None, all=False, files=None)

    revert.run(args)
    captured = capsys.readouterr()
    assert "Error: No revert data found" in captured.out


def test_revert_run_with_override(sample_project, aicodec_config_file, setup_revert_file, monkeypatch):
    """Test revert command with output_dir override."""
    # We change directory to parent to ensure the override is working
    monkeypatch.chdir(sample_project.parent)

    args = Namespace(
        config=str(aicodec_config_file),
        output_dir=sample_project,  # Explicitly point to the project dir
        all=False,
        files=None,
    )

    with patch("aicodec.infrastructure.cli.commands.revert.launch_review_server") as mock_launch:
        revert.run(args)
        mock_launch.assert_called_once()

        review_service = mock_launch.call_args[0][0]
        assert review_service.output_dir == sample_project.resolve()
        # Check for the new revert file location (newest revert file)
        assert review_service.changes_file == (sample_project / ".aicodec" / "reverts" / "revert-001.json").resolve()


def test_revert_run_all_flag(sample_project, aicodec_config_file, setup_revert_file, monkeypatch, capsys):
    """Test revert command with --all flag bypasses the UI."""
    monkeypatch.chdir(sample_project)

    args = Namespace(config=str(aicodec_config_file), output_dir=None, all=True, files=None)

    with (
        patch("aicodec.infrastructure.cli.commands.revert.launch_review_server") as mock_launch,
        patch("aicodec.infrastructure.cli.commands.revert.ReviewService") as mock_review_service_class,
    ):

        mock_service_instance = mock_review_service_class.return_value
        mock_service_instance.get_review_context.return_value = {
            "changes": [{"filePath": "a.py", "proposed_content": "", "action": "DELETE"}]
        }
        mock_service_instance.apply_changes.return_value = [{"status": "SUCCESS"}]

        revert.run(args)

        mock_launch.assert_not_called()
        mock_service_instance.apply_changes.assert_called_once()

        captured = capsys.readouterr()
        assert "Reverting all changes from entire session..." in captured.out
        assert "Revert complete" in captured.out


def test_revert_run_with_files_single(sample_project, aicodec_config_file, setup_revert_file, monkeypatch, capsys):
    """Test revert command with --files flag for a single file."""
    monkeypatch.chdir(sample_project)

    # Update revert file to have multiple files
    revert_data = {
        "summary": "revert data",
        "changes": [
            {"filePath": "a.py", "action": "DELETE", "content": ""},
            {"filePath": "b.py", "action": "REPLACE", "content": "old content"},
        ],
    }
    setup_revert_file.write_text(json.dumps(revert_data))

    args = Namespace(config=str(aicodec_config_file), output_dir=None, all=False, files=["a.py"])

    with (
        patch("aicodec.infrastructure.cli.commands.revert.launch_review_server") as mock_launch,
        patch("aicodec.infrastructure.cli.commands.revert.ReviewService") as mock_review_service_class,
    ):

        mock_service_instance = mock_review_service_class.return_value
        mock_service_instance.get_review_context.return_value = {
            "changes": [
                {"filePath": "a.py", "action": "DELETE", "proposed_content": ""},
                {"filePath": "b.py", "action": "REPLACE", "proposed_content": "old content"},
            ]
        }
        mock_service_instance.apply_changes.return_value = [{"status": "SUCCESS"}]

        revert.run(args)

        mock_launch.assert_not_called()
        mock_service_instance.apply_changes.assert_called_once()

        # Verify only one file was reverted
        call_args = mock_service_instance.apply_changes.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["filePath"] == "a.py"

        captured = capsys.readouterr()
        assert "Reverting changes for 1 file(s) across all sessions..." in captured.out
        assert "Reverting 1 change(s)..." in captured.out
        assert "Revert complete" in captured.out


def test_revert_run_with_files_multiple(sample_project, aicodec_config_file, setup_revert_file, monkeypatch, capsys):
    """Test revert command with --files flag for multiple files."""
    monkeypatch.chdir(sample_project)

    # Update revert file to have multiple files
    revert_data = {
        "summary": "revert data",
        "changes": [
            {"filePath": "a.py", "action": "DELETE", "content": ""},
            {"filePath": "b.py", "action": "REPLACE", "content": "old content"},
            {"filePath": "c.py", "action": "CREATE", "content": "new content"},
        ],
    }
    setup_revert_file.write_text(json.dumps(revert_data))

    args = Namespace(config=str(aicodec_config_file), output_dir=None, all=False, files=["a.py", "b.py"])

    with (
        patch("aicodec.infrastructure.cli.commands.revert.launch_review_server") as mock_launch,
        patch("aicodec.infrastructure.cli.commands.revert.ReviewService") as mock_review_service_class,
    ):

        mock_service_instance = mock_review_service_class.return_value
        mock_service_instance.get_review_context.return_value = {
            "changes": [
                {"filePath": "a.py", "action": "DELETE", "proposed_content": ""},
                {"filePath": "b.py", "action": "REPLACE", "proposed_content": "old content"},
                {"filePath": "c.py", "action": "CREATE", "proposed_content": "new content"},
            ]
        }
        mock_service_instance.apply_changes.return_value = [{"status": "SUCCESS"}, {"status": "SUCCESS"}]

        revert.run(args)

        mock_launch.assert_not_called()
        mock_service_instance.apply_changes.assert_called_once()

        # Verify only two files were reverted
        call_args = mock_service_instance.apply_changes.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["filePath"] == "a.py"
        assert call_args[1]["filePath"] == "b.py"

        captured = capsys.readouterr()
        assert "Reverting changes for 2 file(s) across all sessions..." in captured.out
        assert "Reverting 2 change(s)..." in captured.out


def test_revert_run_with_files_not_found(sample_project, aicodec_config_file, setup_revert_file, monkeypatch, capsys):
    """Test revert command with --files flag when specified file is not in revert data."""
    monkeypatch.chdir(sample_project)

    args = Namespace(config=str(aicodec_config_file), output_dir=None, all=False, files=["nonexistent.py"])

    with patch("aicodec.infrastructure.cli.commands.revert.ReviewService") as mock_review_service_class:

        mock_service_instance = mock_review_service_class.return_value
        mock_service_instance.get_review_context.return_value = {
            "changes": [{"filePath": "a.py", "action": "DELETE", "content": ""}]
        }

        revert.run(args)

        mock_service_instance.apply_changes.assert_not_called()

        captured = capsys.readouterr()
        # The new behavior says "No matching changes in revert-XXX.json"
        assert "No matching changes in revert-001.json" in captured.out


def test_revert_run_with_files_partial_match(
    sample_project, aicodec_config_file, setup_revert_file, monkeypatch, capsys
):
    """Test revert command with --files flag when some files are found and some are not."""
    monkeypatch.chdir(sample_project)

    # Update revert file to have multiple files
    revert_data = {"summary": "revert data", "changes": [{"filePath": "a.py", "action": "DELETE", "content": ""}]}
    setup_revert_file.write_text(json.dumps(revert_data))

    args = Namespace(config=str(aicodec_config_file), output_dir=None, all=False, files=["a.py", "nonexistent.py"])

    with patch("aicodec.infrastructure.cli.commands.revert.ReviewService") as mock_review_service_class:

        mock_service_instance = mock_review_service_class.return_value
        mock_service_instance.get_review_context.return_value = {
            "changes": [{"filePath": "a.py", "action": "DELETE", "proposed_content": ""}]
        }
        mock_service_instance.apply_changes.return_value = [{"status": "SUCCESS"}]

        revert.run(args)

        # Verify only one file was reverted
        call_args = mock_service_instance.apply_changes.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["filePath"] == "a.py"

        captured = capsys.readouterr()
        # The new behavior shows "Reverting 1 change(s)..." for the matched file
        assert "Reverting 1 change(s)..." in captured.out
        assert "Revert complete" in captured.out
