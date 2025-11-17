# tests/commands/test_prompt.py
import json
from argparse import Namespace
from unittest.mock import patch

from aicodec.infrastructure.cli.commands import prompt


def test_prompt_run_basic(sample_project, aicodec_config_file, monkeypatch):
    """Test basic prompt command generates a file with context but no map."""
    monkeypatch.chdir(sample_project)
    (sample_project / ".aicodec" / "context.json").write_text('[]')

    args = Namespace(
        config=str(aicodec_config_file),
        task="A test task",
        minimal=False, tech_stack=None, output_file=None, clipboard=False,
        exclude_output_instructions=False, is_new_project=False, exclude_code=False,
        include_map=None,  # Use default from config (False)
        skip_editor=False
    )

    with patch('aicodec.infrastructure.cli.commands.prompt.open_file_in_editor', return_value=True):
        prompt.run(args)

    prompt_file = sample_project / ".aicodec" / "prompt.txt"
    assert prompt_file.exists()
    content = prompt_file.read_text()

    assert "A test task" in content
    assert "<code_context>" in content
    assert "<repository_map>" not in content


@patch('pyperclip.copy')
def test_prompt_run_include_map_flag(mock_copy, sample_project, aicodec_config_file, monkeypatch):
    """Test prompt command with --include-map includes a pre-existing repo map."""
    monkeypatch.chdir(sample_project)
    map_content = ".\n└── main.py"
    (sample_project / ".aicodec" / "repo_map.md").write_text(map_content)

    args = Namespace(
        config=str(aicodec_config_file),
        task="A map task",
        minimal=False, tech_stack=None, output_file=None, clipboard=True,
        exclude_output_instructions=False, is_new_project=False, exclude_code=True,
        include_map=True  # Explicitly include
    )

    prompt.run(args)

    mock_copy.assert_called_once()
    content = mock_copy.call_args[0][0]

    assert "A map task" in content
    assert "<code_context>" not in content
    assert "<repository_map>" in content
    assert map_content in content


def test_prompt_run_exclude_map_flag(sample_project, aicodec_config_file, monkeypatch):
    """Test prompt command with --exclude-map overrides a config default of true."""
    monkeypatch.chdir(sample_project)
    (sample_project / ".aicodec" / "repo_map.md").write_text(".")

    # Set config to include map by default
    config_data = json.loads(aicodec_config_file.read_text())
    config_data['prompt']['include_map'] = True
    aicodec_config_file.write_text(json.dumps(config_data))

    args = Namespace(
        config=str(aicodec_config_file),
        task="A test task",
        minimal=False, tech_stack=None, output_file=None, clipboard=False,
        exclude_output_instructions=False, is_new_project=False, exclude_code=True,
        include_map=False,  # Explicitly exclude via --exclude-map
        skip_editor=False
    )

    with patch('aicodec.infrastructure.cli.commands.prompt.open_file_in_editor', return_value=True):
        prompt.run(args)

    prompt_file = sample_project / ".aicodec" / "prompt.txt"
    content = prompt_file.read_text()
    assert "<repository_map>" not in content


def test_prompt_run_from_config(sample_project, aicodec_config_file, monkeypatch):
    """Test prompt command respects include_map=True from config."""
    monkeypatch.chdir(sample_project)
    (sample_project / ".aicodec" / "repo_map.md").write_text(".")

    # Set config to include map by default
    config_data = json.loads(aicodec_config_file.read_text())
    config_data['prompt']['include_map'] = True
    aicodec_config_file.write_text(json.dumps(config_data))

    args = Namespace(
        config=str(aicodec_config_file),
        task="A test task",
        minimal=False, tech_stack=None, output_file=None, clipboard=False,
        exclude_output_instructions=False, is_new_project=False, exclude_code=True,
        include_map=None,  # Use config
        skip_editor=False
    )

    with patch('aicodec.infrastructure.cli.commands.prompt.open_file_in_editor', return_value=True):
        prompt.run(args)

    prompt_file = sample_project / ".aicodec" / "prompt.txt"
    content = prompt_file.read_text()
    assert "<repository_map>" in content

def test_prompt_warns_if_map_missing(sample_project, aicodec_config_file, monkeypatch, capsys):
    """Test prompt command warns the user if the repo map file is requested but not found."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        task="A test task",
        minimal=False, tech_stack=None, output_file=None, clipboard=False,
        exclude_output_instructions=False, is_new_project=False, exclude_code=True,
        include_map=True,  # Request map that doesn't exist
        skip_editor=False
    )

    with patch('aicodec.infrastructure.cli.commands.prompt.open_file_in_editor', return_value=True):
        prompt.run(args)

    captured = capsys.readouterr()
    assert "Warning: Repo map file not found" in captured.out
    assert "Run 'aicodec buildmap' first" in captured.out

    prompt_file = sample_project / ".aicodec" / "prompt.txt"
    content = prompt_file.read_text()
    assert "<repository_map>" not in content
