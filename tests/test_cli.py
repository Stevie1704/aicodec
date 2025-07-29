# tests/test_cli.py
import pytest
import sys
import json
from pathlib import Path
from aicodec import cli

@pytest.fixture(autouse=True)
def mock_server_effects(mocker):
    """Prevents tests from having side effects like opening a browser or hanging on a server loop."""
    mocker.patch('webbrowser.open_new_tab')
    mocker.patch('socketserver.TCPServer.serve_forever')

# Test aicodec-aggregate
def test_aggregate_main_with_args(mocker):
    mocker.patch.object(sys, 'argv', ['aicodec-aggregate', '--ext', 'py', '-d', '/tmp/project'])
    mock_service = mocker.patch('aicodec.cli.EncoderService')
    cli.aggregate_main()
    mock_service.assert_called_once()
    config_arg = mock_service.call_args[0][0]
    assert config_arg.directory == '/tmp/project'
    assert '.py' in config_arg.ext

# Test aicodec-apply
def test_review_and_apply_main_with_args(mocker):
    mock_launch_server = mocker.patch('aicodec.cli.launch_review_server')
    mocker.patch.object(sys, 'argv', [
        'aicodec-apply',
        '--output-dir', '/path/to/project',
        '--changes', '/path/to/changes.json'
    ])
    cli.review_and_apply_main()
    mock_launch_server.assert_called_once_with(
        Path('/path/to/project'),
        Path('/path/to/changes.json')
    )

def test_review_and_apply_main_missing_args(mocker):
    mocker.patch.object(
        sys, 'argv', ['aicodec-apply', '--output-dir', '/path/to/project'])
    mocker.patch('aicodec.cli.load_config', return_value={})
    with pytest.raises(SystemExit):
        cli.review_and_apply_main()

# Test aicodec-prepare
@pytest.fixture
def mock_open_editor(mocker):
    return mocker.patch('aicodec.cli.open_file_in_editor')

@pytest.fixture
def mock_pyperclip(mocker):
    return mocker.patch('aicodec.cli.pyperclip')

def test_prepare_main_creates_new_file(tmp_path, mock_open_editor):
    changes_file = tmp_path / "changes.json"
    mocker.patch.object(sys, 'argv', ['aicodec-prepare', '--changes', str(changes_file)])
    cli.prepare_main()
    assert changes_file.exists()
    assert changes_file.stat().st_size == 0
    mock_open_editor.assert_called_once_with(changes_file)

def test_prepare_main_confirms_overwrite_no(tmp_path, mocker, mock_open_editor):
    original_content = "existing content"
    changes_file = tmp_path / "changes.json"
    changes_file.write_text(original_content)
    mocker.patch.object(sys, 'argv', ['aicodec-prepare', '--changes', str(changes_file)])
    mocker.patch('builtins.input', return_value='n')
    cli.prepare_main()
    assert changes_file.read_text() == original_content
    mock_open_editor.assert_not_called()

def test_prepare_from_clipboard_success(tmp_path, mock_pyperclip, mock_open_editor, capsys):
    valid_json = json.dumps({"summary": "from clipboard"})
    mock_pyperclip.paste.return_value = valid_json
    changes_file = tmp_path / "changes.json"
    mocker.patch.object(sys, 'argv', ['aicodec-prepare', '--from-clipboard', '--changes', str(changes_file)])
    
    cli.prepare_main()

    assert changes_file.read_text() == valid_json
    mock_open_editor.assert_not_called()
    assert 'Successfully wrote content from clipboard' in capsys.readouterr().out

def test_prepare_from_clipboard_invalid_json(tmp_path, mock_pyperclip, capsys):
    mock_pyperclip.paste.return_value = "{not valid json}"
    changes_file = tmp_path / "changes.json"
    mocker.patch.object(sys, 'argv', ['aicodec-prepare', '--from-clipboard', '--changes', str(changes_file)])

    cli.prepare_main()

    assert not changes_file.exists()
    assert 'Clipboard content is not valid JSON' in capsys.readouterr().out

def test_prepare_from_clipboard_empty(tmp_path, mock_pyperclip, capsys):
    mock_pyperclip.paste.return_value = ""
    changes_file = tmp_path / "changes.json"
    mocker.patch.object(sys, 'argv', ['aicodec-prepare', '--from-clipboard', '--changes', str(changes_file)])

    cli.prepare_main()

    assert not changes_file.exists()
    assert 'Clipboard is empty' in capsys.readouterr().out
