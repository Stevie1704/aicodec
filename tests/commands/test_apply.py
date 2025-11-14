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

    args = Namespace(config=str(aicodec_config_file), output_dir=None, changes=None, all=False, files=None)

    with patch("aicodec.infrastructure.cli.commands.apply.launch_review_server") as mock_launch:
        apply.run(args)
        mock_launch.assert_called_once()
        call_args = mock_launch.call_args
        assert call_args[1]["mode"] == "apply"  # mode


def test_apply_run_with_overrides(sample_project, aicodec_config_file, sample_changes_file, monkeypatch):
    """Test apply command with CLI overrides for paths."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file), output_dir=sample_project, changes=sample_changes_file, all=False, files=None
    )

    with patch("aicodec.infrastructure.cli.commands.apply.launch_review_server") as mock_launch:
        apply.run(args)
        mock_launch.assert_called_once()

        # Check that the service was initialized with the correct, resolved paths
        review_service = mock_launch.call_args[0][0]
        assert review_service.output_dir == sample_project.resolve()
        assert review_service.changes_file == sample_changes_file.resolve()


def test_apply_run_all_flag(sample_project, aicodec_config_file, sample_changes_file, monkeypatch, capsys):
    """Test apply command with --all flag bypasses the UI."""
    monkeypatch.chdir(sample_project)

    config_data = json.loads(aicodec_config_file.read_text())
    config_data["prepare"]["changes"] = str(sample_changes_file)
    aicodec_config_file.write_text(json.dumps(config_data))

    args = Namespace(config=str(aicodec_config_file), output_dir=None, changes=None, all=True, files=None)

    with (
        patch("aicodec.infrastructure.cli.commands.apply.launch_review_server") as mock_launch,
        patch("aicodec.infrastructure.cli.commands.apply.ReviewService") as mock_review_service_class,
    ):

        mock_service_instance = mock_review_service_class.return_value
        mock_service_instance.get_review_context.return_value = {
            "changes": [{"filePath": "a.py", "proposed_content": "test", "action": "CREATE"}]
        }
        mock_service_instance.apply_changes.return_value = [{"status": "SUCCESS"}]

        apply.run(args)

        mock_launch.assert_not_called()
        mock_service_instance.apply_changes.assert_called_once()

        captured = capsys.readouterr()
        assert "Applying all changes without review..." in captured.out
        assert "Apply complete" in captured.out


def test_apply_run_missing_config(sample_project, monkeypatch, capsys):
    """Test apply command fails gracefully if config values are missing."""
    monkeypatch.chdir(sample_project)

    # Create an empty config
    config_file = sample_project / ".aicodec" / "config.json"
    config_file.parent.mkdir()
    config_file.write_text("{}")

    args = Namespace(config=str(config_file), output_dir=None, changes=None, all=False, files=None)

    apply.run(args)
    captured = capsys.readouterr()
    assert "Error: Missing required configuration" in captured.out


def test_apply_run_with_files_single(sample_project, aicodec_config_file, sample_changes_file, monkeypatch, capsys):
    """Test apply command with --files flag for a single file."""
    monkeypatch.chdir(sample_project)

    config_data = json.loads(aicodec_config_file.read_text())
    config_data["prepare"]["changes"] = str(sample_changes_file)
    aicodec_config_file.write_text(json.dumps(config_data))

    args = Namespace(config=str(aicodec_config_file), output_dir=None, changes=None, all=False, files=["a.py"])

    with (
        patch("aicodec.infrastructure.cli.commands.apply.launch_review_server") as mock_launch,
        patch("aicodec.infrastructure.cli.commands.apply.ReviewService") as mock_review_service_class,
    ):

        mock_service_instance = mock_review_service_class.return_value
        mock_service_instance.get_review_context.return_value = {
            "changes": [
                {"filePath": "a.py", "proposed_content": "test", "action": "CREATE"},
                {"filePath": "b.py", "proposed_content": "test2", "action": "CREATE"},
            ]
        }
        mock_service_instance.apply_changes.return_value = [{"status": "SUCCESS"}]

        apply.run(args)

        mock_launch.assert_not_called()
        mock_service_instance.apply_changes.assert_called_once()

        # Verify only one file was applied
        call_args = mock_service_instance.apply_changes.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["filePath"] == "a.py"

        captured = capsys.readouterr()
        assert "Applying changes for 1 file(s)..." in captured.out
        assert "Found 1 change(s) to apply." in captured.out
        assert "Apply complete" in captured.out


def test_apply_run_with_files_multiple(sample_project, aicodec_config_file, sample_changes_file, monkeypatch, capsys):
    """Test apply command with --files flag for multiple files."""
    monkeypatch.chdir(sample_project)

    config_data = json.loads(aicodec_config_file.read_text())
    config_data["prepare"]["changes"] = str(sample_changes_file)
    aicodec_config_file.write_text(json.dumps(config_data))

    args = Namespace(config=str(aicodec_config_file), output_dir=None, changes=None, all=False, files=["a.py", "b.py"])

    with (
        patch("aicodec.infrastructure.cli.commands.apply.launch_review_server") as mock_launch,
        patch("aicodec.infrastructure.cli.commands.apply.ReviewService") as mock_review_service_class,
    ):

        mock_service_instance = mock_review_service_class.return_value
        mock_service_instance.get_review_context.return_value = {
            "changes": [
                {"filePath": "a.py", "proposed_content": "test", "action": "CREATE"},
                {"filePath": "b.py", "proposed_content": "test2", "action": "CREATE"},
                {"filePath": "c.py", "proposed_content": "test3", "action": "CREATE"},
            ]
        }
        mock_service_instance.apply_changes.return_value = [{"status": "SUCCESS"}, {"status": "SUCCESS"}]

        apply.run(args)

        mock_launch.assert_not_called()
        mock_service_instance.apply_changes.assert_called_once()

        # Verify only two files were applied
        call_args = mock_service_instance.apply_changes.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["filePath"] == "a.py"
        assert call_args[1]["filePath"] == "b.py"

        captured = capsys.readouterr()
        assert "Applying changes for 2 file(s)..." in captured.out
        assert "Found 2 change(s) to apply." in captured.out


def test_apply_run_with_files_not_found(sample_project, aicodec_config_file, sample_changes_file, monkeypatch, capsys):
    """Test apply command with --files flag when specified file is not in changes."""
    monkeypatch.chdir(sample_project)

    config_data = json.loads(aicodec_config_file.read_text())
    config_data["prepare"]["changes"] = str(sample_changes_file)
    aicodec_config_file.write_text(json.dumps(config_data))

    args = Namespace(
        config=str(aicodec_config_file), output_dir=None, changes=None, all=False, files=["nonexistent.py"]
    )

    with patch("aicodec.infrastructure.cli.commands.apply.ReviewService") as mock_review_service_class:

        mock_service_instance = mock_review_service_class.return_value
        mock_service_instance.get_review_context.return_value = {
            "changes": [{"filePath": "a.py", "proposed_content": "test", "action": "CREATE"}]
        }

        apply.run(args)

        mock_service_instance.apply_changes.assert_not_called()

        captured = capsys.readouterr()
        assert "No changes found for the specified file(s): nonexistent.py" in captured.out


def test_apply_run_with_files_partial_match(
    sample_project, aicodec_config_file, sample_changes_file, monkeypatch, capsys
):
    """Test apply command with --files flag when some files are found and some are not."""
    monkeypatch.chdir(sample_project)

    config_data = json.loads(aicodec_config_file.read_text())
    config_data["prepare"]["changes"] = str(sample_changes_file)
    aicodec_config_file.write_text(json.dumps(config_data))

    args = Namespace(
        config=str(aicodec_config_file), output_dir=None, changes=None, all=False, files=["a.py", "nonexistent.py"]
    )

    with patch("aicodec.infrastructure.cli.commands.apply.ReviewService") as mock_review_service_class:

        mock_service_instance = mock_review_service_class.return_value
        mock_service_instance.get_review_context.return_value = {
            "changes": [{"filePath": "a.py", "proposed_content": "test", "action": "CREATE"}]
        }
        mock_service_instance.apply_changes.return_value = [{"status": "SUCCESS"}]

        apply.run(args)

        # Verify only one file was applied
        call_args = mock_service_instance.apply_changes.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["filePath"] == "a.py"

        captured = capsys.readouterr()
        assert "Warning: No changes found for: nonexistent.py" in captured.out
        assert "Found 1 change(s) to apply." in captured.out
