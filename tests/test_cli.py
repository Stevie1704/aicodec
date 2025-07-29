# tests/test_cli.py
import pytest
import sys
import json
from pathlib import Path
from aicodec import cli

@pytest.fixture(autouse=True)
def mock_side_effects(mocker):
    """Prevents tests from having side effects like opening a browser or hanging on a server loop."""
    mocker.patch('webbrowser.open_new_tab')
    mocker.patch('socketserver.TCPServer.serve_forever')
    mocker.patch('aicodec.cli.open_file_in_editor')
    mocker.patch('aicodec.cli.pyperclip')


def test_aggregate_command(mocker):
    mock_service = mocker.patch('aicodec.cli.EncoderService')
    mocker.patch.object(sys, 'argv', ['aicodec', 'aggregate', '--ext', 'py', '-d', '/tmp/project'])
    cli.main()
    mock_service.assert_called_once()
    config_arg = mock_service.call_args[0][0]
    assert config_arg.directory == '/tmp/project'

def test_apply_command(mocker):
    mock_launch_server = mocker.patch('aicodec.cli.launch_review_server')
    mocker.patch.object(sys, 'argv', ['aicodec', 'apply', '--output-dir', '.', '--changes', 'c.json'])
    cli.main()
    mock_launch_server.assert_called_once_with(Path('.'), Path('c.json'))

def test_apply_command_missing_args(mocker, capsys):
    mocker.patch.object(sys, 'argv', ['aicodec', 'apply', '--output-dir', '.'])
    mocker.patch('aicodec.cli.load_config', return_value={})
    cli.main()
    assert 'Missing required configuration' in capsys.readouterr().out

def test_prepare_command_editor(tmp_path, mocker):
    mock_open_editor = mocker.patch('aicodec.utils.open_file_in_editor')
    changes_file = tmp_path / "changes.json"
    mocker.patch.object(sys, 'argv', ['aicodec', 'prepare', '--changes', str(changes_file)])
    cli.main()
    assert changes_file.exists()
    mock_open_editor.assert_called_once_with(changes_file)

def test_prepare_command_from_clipboard(tmp_path, mocker):
    mock_pyperclip = mocker.patch('pyperclip.paste')
    valid_json = json.dumps({"summary": "from clipboard"})
    mock_pyperclip.return_value = valid_json
    changes_file = tmp_path / "changes.json"
    mocker.patch.object(sys, 'argv', ['aicodec', 'prepare', '--from-clipboard', '--changes', str(changes_file)])
    cli.main()
    assert changes_file.read_text() == valid_json

def test_prepare_command_overwrite_cancel(tmp_path, mocker, capsys):
    mock_open_editor = mocker.patch('aicodec.utils.open_file_in_editor')
    changes_file = tmp_path / "changes.json"
    changes_file.write_text("existing content")
    mocker.patch('builtins.input', return_value='n')
    mocker.patch.object(sys, 'argv', ['aicodec', 'prepare', '--changes', str(changes_file)])
    cli.main()
    assert "Operation cancelled" in capsys.readouterr().out
    mock_open_editor.assert_not_called()
