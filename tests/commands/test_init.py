# tests/commands/test_init.py
import json
from unittest.mock import MagicMock, patch

from aicodec.infrastructure.cli.commands import init


def test_init_run_defaults(tmp_path, monkeypatch):
    """Test `init` with default 'yes' for most prompts and skipping advanced config."""
    monkeypatch.chdir(tmp_path)

    # Responses:
    # Overwrite? (not asked)
    # Use gitignore? (Y)
    # Update .gitignore? (Y)
    # Exclude .gitignore? (Y)
    # Configure additional? (n)
    # Use minimal prompt? (n)
    # Tech stack? (Python)
    # From clipboard default? (n)
    # Include code? (Y)
    # Prompt clipboard? (n)
    user_inputs = ['y', 'y', 'y', 'n', 'n', 'Python', 'n', 'y', 'n']

    with patch('builtins.input', side_effect=user_inputs):
        init.run(MagicMock())

    config_file = tmp_path / '.aicodec' / 'config.json'
    assert config_file.exists()
    config = json.loads(config_file.read_text())

    assert config['aggregate']['use_gitignore'] is True
    assert '.gitignore' in config['aggregate']['exclude_files']
    assert config['prompt']['minimal'] is False
    assert config['prompt']['tech_stack'] == 'Python'
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
        init.run(MagicMock())

    assert config_file.read_text() == '{"original": true}'


def test_init_run_advanced_config(tmp_path, monkeypatch):
    """Test `init` with detailed inclusion/exclusion configuration."""
    monkeypatch.chdir(tmp_path)

    user_inputs = [
        'y', 'y', 'y',  # Standard gitignore prompts
        'y',  # Configure additional?
        'src, lib',  # include_dirs
        '*.py',  # include_files
        '.ts, .tsx',  # include_ext
        'node_modules, build',  # exclude_dirs
        '*.log',  # exclude_files
        '.tmp',  # exclude_exts
        'y',  # Use minimal prompt?
        'TypeScript/React',  # Tech stack
        'y',  # from_clipboard
        'y',  # include_code
        'y',  # prompt to clipboard
    ]

    with patch('builtins.input', side_effect=user_inputs):
        init.run(MagicMock())

    config_file = tmp_path / '.aicodec' / 'config.json'
    config = json.loads(config_file.read_text())
    agg_config = config['aggregate']

    assert agg_config['include_dirs'] == ['src', 'lib']
    assert agg_config['include_files'] == ['*.py']
    assert agg_config['include_ext'] == ['.ts', '.tsx']
    assert 'node_modules' in agg_config['exclude_dirs']
    assert '*.log' in agg_config['exclude_files']
    assert agg_config['exclude_exts'] == ['.tmp']
    assert config['prompt']['minimal'] is True
    assert config['prompt']['tech_stack'] == 'TypeScript/React'
    assert config['prepare']['from_clipboard'] is True
    assert config['prompt']['clipboard'] is True
