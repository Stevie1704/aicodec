# tests/commands/test_init.py
import json
from argparse import Namespace
from unittest.mock import patch

from aicodec.infrastructure.cli.commands import init


def test_init_run_defaults(tmp_path, monkeypatch):
    """Test `init` with default 'yes' for most prompts and skipping advanced config."""
    monkeypatch.chdir(tmp_path)

    user_inputs = [
        '',  # Directories to scan
        'y',  # Standard gitignore prompts
        'y',
        'y',
        'n',  # Configure additional?
        'n',  # Use minimal prompt?
        'Python',  # Tech stack
        'y',  # Include repository map?
        'n',  # from_clipboard
        'y',  # include_code
        'y',  # prompt to clipboard
    ]

    with patch('builtins.input', side_effect=user_inputs):
        init.run(Namespace(plugin=[]))

    config_file = tmp_path / '.aicodec' / 'config.json'
    assert config_file.exists()
    config = json.loads(config_file.read_text())

    assert config['aggregate']['use_gitignore'] is True
    assert '.gitignore' in config['aggregate']['exclude']
    assert config['aggregate']['plugins'] == []
    assert config['prompt']['minimal'] is False
    assert config['prompt']['tech_stack'] == 'Python'
    assert config['prompt']['include_map'] is True
    assert config['prepare']['from_clipboard'] is False
    assert config['prompt']['include_code'] is True

    gitignore_file = tmp_path / '.gitignore'
    assert gitignore_file.exists()
    assert '.aicodec/' in gitignore_file.read_text()


def test_init_run_overwrite_cancel(tmp_path, monkeypatch):
    """Test `init` cancels if user chooses not to overwrite existing config."""
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / '.aicodec'
    config_dir.mkdir()
    config_file = config_dir / 'config.json'
    config_file.write_text('{"original": true}')

    with patch('builtins.input', return_value='n'):
        init.run(Namespace(plugin=[]))

    assert config_file.read_text() == '{"original": true}'


def test_init_run_advanced_config(tmp_path, monkeypatch):
    """Test `init` with detailed inclusion/exclusion configuration."""
    monkeypatch.chdir(tmp_path)

    user_inputs = [
        '',  # Directories to scan
        'y',  # Standard gitignore prompts
        'y',
        'y',
        'y',  # Configure additional?
        'src/**, lib/**',  # include
        'node_modules/, **/*.log',  # exclude
        'y',  # Use minimal prompt?
        'TypeScript/React',  # Tech stack
        'n',  # Include repository map?
        'y',  # from_clipboard
        'y',  # include_code
        'y',  # prompt to clipboard
    ]

    with patch('builtins.input', side_effect=user_inputs):
        init.run(Namespace(plugin=[]))

    config_file = tmp_path / '.aicodec' / 'config.json'
    config = json.loads(config_file.read_text())
    agg_config = config['aggregate']

    assert agg_config['include'] == ['src/**', 'lib/**']
    assert 'node_modules/' in agg_config['exclude']
    assert '**/*.log' in agg_config['exclude']
    assert config['prompt']['minimal'] is True
    assert config['prompt']['tech_stack'] == 'TypeScript/React'
    assert config['prompt']['include_map'] is False
    assert config['prepare']['from_clipboard'] is True
    assert config['prompt']['clipboard'] is True


def test_init_with_plugins(tmp_path, monkeypatch):
    """Test `init` with plugins provided via CLI."""
    monkeypatch.chdir(tmp_path)

    user_inputs = [
        '',  # Directories to scan
        'y',  # Standard gitignore prompts
        'y',
        'y',
        'n',  # Configure additional?
        'n',  # Use minimal prompt?
        'Python',  # Tech stack
        'y',  # Include repository map?
        'n',  # from_clipboard
        'y',  # include_code
        'y',  # prompt to clipboard
    ]
    
    plugins_to_add = [
        ".zip=unzip -l {file}",
        ".tar.gz=tar -ztvf {file}"
    ]

    with patch('builtins.input', side_effect=user_inputs):
        init.run(Namespace(plugin=plugins_to_add))

    config_file = tmp_path / '.aicodec' / 'config.json'
    assert config_file.exists()
    config = json.loads(config_file.read_text())

    expected_plugins = [
        ".zip=unzip -l {file}",
        ".tar.gz=tar -ztvf {file}"
    ]
    assert config['aggregate']['plugins'] == expected_plugins
