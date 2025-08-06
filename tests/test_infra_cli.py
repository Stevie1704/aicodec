# tests/test_infra_cli.py
import pytest
import json
from unittest.mock import patch, MagicMock

from aicodec.infrastructure.cli import command_line_interface as cli


@pytest.fixture
def mock_services(mocker):
    mocker.patch(
        'aicodec.infrastructure.cli.command_line_interface.AggregationService')
    mocker.patch(
        'aicodec.infrastructure.cli.command_line_interface.ReviewService')
    mocker.patch(
        'aicodec.infrastructure.cli.command_line_interface.launch_review_server')
    mocker.patch(
        'aicodec.infrastructure.cli.command_line_interface.open_file_in_editor')
    mocker.patch('aicodec.infrastructure.cli.command_line_interface.pyperclip')


@pytest.fixture
def temp_config_file(tmp_path):
    config_dir = tmp_path / '.aicodec'
    config_dir.mkdir()
    config_file = config_dir / 'config.json'
    config_data = {
        "aggregate": {"directory": "."},
        "prepare": {"changes": str(config_dir / 'changes.json')},
        "apply": {"output_dir": "."}
    }
    config_file.write_text(json.dumps(config_data))
    return config_file


def test_check_config_exists_fail(capsys):
    with pytest.raises(SystemExit) as e:
        cli.check_config_exists('non_existent_file.json')
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "aicodec not initialised" in captured.out


def test_handle_schema(capsys):
    cli.handle_schema(None)
    captured = capsys.readouterr()
    assert '"$schema"' in captured.out
    assert 'LLM Code Change Proposal' in captured.out


def test_handle_schema_not_found(mocker, capsys):
    mocker.patch('importlib.resources.read_text',
                 side_effect=FileNotFoundError)
    with pytest.raises(SystemExit) as e:
        cli.handle_schema(None)
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "schema.json not found" in captured.err


def test_handle_init_interactive(mocker, tmp_path, monkeypatch):
    # Simulate user input for the interactive init process
    user_inputs = [
        'y',  # Use gitignore?
        'y',  # Exclude .gitignore file?
        'y',  # Configure additional inclusions/exclusions?
        'src,lib',  # include_dirs
        '*.ts',  # include_files
        '.ts,.js',  # include_ext
        'node_modules',  # exclude_dirs
        '*.log',  # exclude_files
        '.log',  # exclude_exts
        'n',  # Use clipboard by default?
    ]
    mocker.patch('builtins.input', side_effect=user_inputs)

    # Use monkeypatch to safely change the current working directory for the test.
    monkeypatch.chdir(tmp_path)

    cli.handle_init(None)

    config_file = tmp_path / '.aicodec' / 'config.json'
    assert config_file.exists()
    with open(config_file, 'r') as f:
        config = json.load(f)

    assert config['aggregate']['use_gitignore'] is True
    assert '.gitignore' in config['aggregate']['exclude_files']
    assert 'src' in config['aggregate']['include_dirs']
    assert '*.ts' in config['aggregate']['include_files']
    assert 'node_modules' in config['aggregate']['exclude_dirs']


def test_handle_init_overwrite_cancel(mocker, tmp_path):
    config_file = tmp_path / '.aicodec' / 'config.json'
    config_file.parent.mkdir()
    config_file.touch()
    mocker.patch('builtins.input', return_value='n')  # Do not overwrite
    cli.handle_init(None)
    # Check that it didn't proceed
    assert config_file.read_text() == ""


def test_handle_aggregate(mock_services, temp_config_file):
    args = MagicMock(
        config=str(temp_config_file),
        directory=None, include_dir=[], include_ext=[], include_file=[],
        exclude_dir=[], exclude_ext=[], exclude_file=[],
        full=True, use_gitignore=None
    )
    cli.handle_aggregate(args)
    cli.AggregationService.assert_called_once()
    service_instance = cli.AggregationService.return_value
    service_instance.aggregate.assert_called_once_with(full_run=True)


def test_handle_aggregate_no_inclusions_error(tmp_path, monkeypatch, capsys):
    # Isolate the test's filesystem operations to tmp_path.
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / '.aicodec'
    config_dir.mkdir()
    config_path = config_dir / 'bad_config.json'
    # This config, combined with no include args and use_gitignore=False, should result in no files being found.
    config_path.write_text(json.dumps({'aggregate': {'use_gitignore': False}}))
    args = MagicMock(config=str(config_path), use_gitignore=False, include_ext=[], include_files=[
    ], include_dirs=[], directory=None, exclude_dir=[], exclude_ext=[], exclude_file=[], full=False)

    cli.handle_aggregate(args)
    captured = capsys.readouterr()
    # Fix: With the repository bug fixed, the service now correctly reports that no files were found.
    assert "No files found to aggregate" in captured.out


def test_handle_apply(mock_services, temp_config_file):
    args = MagicMock(config=str(temp_config_file),
                     output_dir=None, changes=None)
    cli.handle_apply(args)
    cli.ReviewService.assert_called_once()
    cli.launch_review_server.assert_called_once_with(
        cli.ReviewService.return_value, mode='apply')


def test_handle_revert(mock_services, temp_config_file):
    revert_file = temp_config_file.parent / 'revert.json'
    revert_file.touch()

    args = MagicMock(config=str(temp_config_file),
                     output_dir=str(temp_config_file.parent.parent))
    with patch('pathlib.Path.is_file', return_value=True):
        cli.handle_revert(args)
    cli.ReviewService.assert_called_once()
    cli.launch_review_server.assert_called_once_with(
        cli.ReviewService.return_value, mode='revert')


def test_handle_revert_no_revert_file(tmp_path, monkeypatch, capsys, mocker):
    # Isolate filesystem and mock server launch to prevent UI from opening.
    monkeypatch.chdir(tmp_path)
    mocker.patch(
        'aicodec.infrastructure.cli.command_line_interface.launch_review_server')

    config_dir = tmp_path / '.aicodec'
    config_dir.mkdir()
    config_file = config_dir / 'config.json'
    config_file.write_text(json.dumps({"apply": {"output_dir": "."}}))

    args = MagicMock(config=str(config_file), output_dir=None)
    cli.handle_revert(args)
    captured = capsys.readouterr()
    assert "Error: No revert data found." in captured.out
    cli.launch_review_server.assert_not_called()


def test_handle_prepare_from_clipboard_success(mock_services, temp_config_file):
    valid_json = '{"changes": [{"filePath": "a.py", "action": "CREATE", "content": ""}]}'
    cli.pyperclip.paste.return_value = valid_json
    args = MagicMock(config=str(temp_config_file),
                     changes=None, from_clipboard=True)

    cli.handle_prepare(args)

    changes_path = temp_config_file.parent / 'changes.json'
    assert changes_path.read_text() == valid_json


@pytest.mark.parametrize("paste_content, error_msg", [
    ("", "Clipboard is empty"),
    ("not json", "not valid JSON"),
    ('{"foo": "bar"}', "does not match the expected schema")
])
def test_handle_prepare_from_clipboard_failures(mock_services, temp_config_file, capsys, paste_content, error_msg):
    cli.pyperclip.paste.return_value = paste_content
    args = MagicMock(config=str(temp_config_file),
                     changes=None, from_clipboard=True)
    cli.handle_prepare(args)
    captured = capsys.readouterr()
    assert error_msg in captured.out


def test_handle_prepare_open_editor(mock_services, temp_config_file):
    # Ensure from_clipboard is False and correctly prioritized by the handler.
    args = MagicMock(config=str(temp_config_file),
                     changes=None, from_clipboard=False)
    cli.handle_prepare(args)
    cli.open_file_in_editor.assert_called_once()
