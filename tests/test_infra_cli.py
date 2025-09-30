# tests/test_infra_cli.py
import json
from unittest.mock import MagicMock, patch

import pytest

from aicodec.infrastructure.cli.command_line_interface import check_config_exists
from aicodec.infrastructure.cli.commands import (
    aggregate,
    apply,
    init,
    prepare,
    prompt,
    revert,
    schema,
)


@pytest.fixture
def temp_config_file(tmp_path):
    config_dir = tmp_path / '.aicodec'
    config_dir.mkdir()
    config_file = config_dir / 'config.json'
    config_data = {
        "aggregate": {"directories": ["."]},
        "prompt": {"output_file": str(config_dir / "prompt.txt")},
        "prepare": {"changes": str(config_dir / 'changes.json'), "from_clipboard": False},
        "apply": {"output_dir": "."}
    }
    config_file.write_text(json.dumps(config_data))
    return config_file


def test_init_run_interactive(tmp_path, monkeypatch):
    user_inputs = [
        'y', 'y', 'y', 'y', 'src,lib', '*.ts', '.ts,.js',
        'node_modules', '*.log', '.log', 'n', 'Python', 'n', 'y', 'n'
    ]
    with patch('builtins.input', side_effect=user_inputs):
        monkeypatch.chdir(tmp_path)
        init.run(MagicMock())

    config_file = tmp_path / '.aicodec' / 'config.json'
    assert config_file.exists()
    config = json.loads(config_file.read_text())

    assert config['aggregate']['use_gitignore'] is True
    assert '.gitignore' in config['aggregate']['exclude_files']
    assert 'src' in config['aggregate']['include_dirs']
    assert 'node_modules' in config['aggregate']['exclude_dirs']
    assert config['prompt']['minimal'] is False
    assert config['prompt']['tech_stack'] == 'Python'
    assert config['prompt']['include_code'] is True
    assert config['prompt']['clipboard'] is False

    gitignore_file = tmp_path / '.gitignore'
    assert gitignore_file.exists()
    assert '.aicodec/' in gitignore_file.read_text()


def test_init_run_interactive_skip_additional(tmp_path, monkeypatch):
    user_inputs = [
        'y', 'y', 'y', 'n', 'y', 'Python', 'n', 'y', 'n'
    ]
    with patch('builtins.input', side_effect=user_inputs):
        monkeypatch.chdir(tmp_path)
        init.run(MagicMock())

    config_file = tmp_path / '.aicodec' / 'config.json'
    assert config_file.exists()
    config = json.loads(config_file.read_text())

    assert config['aggregate']['include_dirs'] == []
    assert config['aggregate']['include_ext'] == []
    assert config['aggregate']['include_files'] == []
    assert config['aggregate']['exclude_exts'] == []
    assert config['aggregate']['exclude_files'] == ['.gitignore']
    assert config['prompt']['minimal'] is True
    assert config['prompt']['tech_stack'] == 'Python'
    assert config['prompt']['include_code'] is True
    assert config['prompt']['clipboard'] is False


def test_check_config_exists_fail(capsys):
    with pytest.raises(SystemExit) as e:
        check_config_exists('non_existent_file.json')
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "aicodec not initialised" in captured.out


def test_schema_run(capsys):
    with patch('aicodec.infrastructure.cli.commands.schema.files') as mock_files:
        mock_schema_path = MagicMock()
        mock_schema_path.read_text.return_value = '{"schema": true}'
        mock_assets = MagicMock()
        mock_assets.__truediv__.return_value = mock_schema_path
        mock_aicodec = MagicMock()
        mock_aicodec.__truediv__.return_value = mock_assets
        mock_files.return_value = mock_aicodec
        schema.run(None)
    captured = capsys.readouterr()
    assert '{"schema": true}' in captured.out


def test_schema_run_not_found(capsys):
    with patch('aicodec.infrastructure.cli.commands.schema.files') as mock_files:
        mock_schema_path = MagicMock()
        mock_schema_path.read_text.side_effect = FileNotFoundError
        mock_assets = MagicMock()
        mock_assets.__truediv__.return_value = mock_schema_path
        mock_aicodec = MagicMock()
        mock_aicodec.__truediv__.return_value = mock_assets
        mock_files.return_value = mock_aicodec
        with pytest.raises(SystemExit) as e:
            schema.run(None)
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "schema.json not found" in captured.err


def test_aggregate_run(temp_config_file):
    with patch('aicodec.infrastructure.cli.commands.aggregate.AggregationService') as mock_agg_service_class:
        mock_agg_service_instance = mock_agg_service_class.return_value

        args = MagicMock(
            config=str(temp_config_file), directories=None, include_dirs=[], include_exts=[],
            include_files=[], exclude_dirs=[], exclude_exts=[], exclude_files=[],
            full=True, use_gitignore=None, count_tokens=True
        )
        aggregate.run(args)
        mock_agg_service_class.assert_called_once()
        mock_agg_service_instance.aggregate.assert_called_once_with(
            full_run=True, count_tokens=True)


def test_prompt_run(temp_config_file):
    with patch('aicodec.infrastructure.cli.commands.prompt.open_file_in_editor'):
        with patch('aicodec.infrastructure.cli.commands.prompt.files') as mock_files:
            with patch('aicodec.infrastructure.cli.commands.prompt.load_default_prompt_template') as mock_template:
                mock_schema_path = MagicMock()
                mock_schema_path.read_text.return_value = '{"schema": true}'
                mock_assets = MagicMock()
                mock_assets.__truediv__.return_value = mock_schema_path
                mock_aicodec = MagicMock()
                mock_aicodec.__truediv__.return_value = mock_assets
                mock_files.return_value = mock_aicodec
                mock_template.return_value = 'template with {user_task_description}'

                context_file = temp_config_file.parent / 'context.json'
                context_file.write_text('[]')

                args = MagicMock(config=str(
                    temp_config_file), task='test task', output_file=None, clipboard=False)

                with patch('pathlib.Path.write_text') as mock_write:
                    prompt.run(args)

                    mock_write.assert_called_once()
                    call_args = mock_write.call_args
                    assert 'template with test task' in call_args[0][0]


def test_prompt_run_to_clipboard(temp_config_file):
    with patch('aicodec.infrastructure.cli.commands.prompt.pyperclip') as mock_pyperclip:
        with patch('pathlib.Path.is_file', return_value=True):
            with patch('pathlib.Path.read_text', return_value='[]'):
                with patch('aicodec.infrastructure.cli.commands.prompt.files'):
                    with patch('aicodec.infrastructure.cli.commands.prompt.load_default_prompt_template', return_value='template'):
                        with patch('aicodec.infrastructure.cli.commands.prompt.parse_json_file', return_value='{"schema":true}'):
                            args = MagicMock(config=str(
                                temp_config_file), task='test task', output_file=None, clipboard=True)
                            prompt.run(args)

                            mock_pyperclip.copy.assert_called_once_with(
                                'template')


def test_apply_run(temp_config_file):
    with patch('aicodec.infrastructure.cli.commands.apply.ReviewService') as mock_review_service:
        with patch('aicodec.infrastructure.cli.commands.apply.launch_review_server') as mock_launch_server:
            args = MagicMock(config=str(temp_config_file),
                             output_dir=None, changes=None)
            apply.run(args)
            mock_review_service.assert_called_once()
            mock_launch_server.assert_called_once_with(
                mock_review_service.return_value, mode='apply')


def test_revert_run(temp_config_file):
    with patch('aicodec.infrastructure.cli.commands.revert.ReviewService') as mock_review_service:
        with patch('aicodec.infrastructure.cli.commands.revert.launch_review_server') as mock_launch_server:
            with patch('pathlib.Path.is_file', return_value=True):
                args = MagicMock(config=str(temp_config_file),
                                 output_dir=str(temp_config_file.parent.parent))
                revert.run(args)

                mock_review_service.assert_called_once()
                mock_launch_server.assert_called_once_with(
                    mock_review_service.return_value, mode='revert')


def test_prepare_run_from_clipboard_success(temp_config_file):
    with patch('aicodec.infrastructure.cli.commands.prepare.pyperclip') as mock_pyperclip:
        with patch('aicodec.infrastructure.cli.commands.prepare.files') as mock_files:
            with patch('jsonschema.validate'):
                mock_schema_path = MagicMock()
                mock_schema_path.read_text.return_value = '{"schema": true}'
                mock_assets = MagicMock()
                mock_assets.__truediv__.return_value = mock_schema_path
                mock_aicodec = MagicMock()
                mock_aicodec.__truediv__.return_value = mock_assets
                mock_files.return_value = mock_aicodec
                valid_json = '{"summary": "...", "changes": [{"filePath": "a.py", "action": "CREATE", "content": ""}]}'
                mock_pyperclip.paste.return_value = valid_json

                args = MagicMock(config=str(temp_config_file),
                                 changes=None, from_clipboard=True)
                prepare.run(args)

                changes_path = temp_config_file.parent / 'changes.json'
                assert changes_path.read_text() == valid_json


def test_prepare_run_open_editor(temp_config_file):
    with patch('aicodec.infrastructure.cli.commands.prepare.open_file_in_editor') as mock_open_editor:
        args = MagicMock(config=str(temp_config_file),
                         changes=None, from_clipboard=False)
        prepare.run(args)
        mock_open_editor.assert_called_once()
