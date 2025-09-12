# tests/commands/test_prompt.py
import json
from argparse import Namespace
from unittest.mock import patch

import pytest

from aicodec.infrastructure.cli.commands import prompt


@pytest.fixture
def setup_context_file(sample_project):
    context_dir = sample_project / ".aicodec"
    context_dir.mkdir(exist_ok=True)
    context_file = context_dir / "context.json"
    context_file.write_text(json.dumps(
        [{"filePath": "main.py", "content": "print"}]))
    return context_file


def test_prompt_run_basic(sample_project, aicodec_config_file, setup_context_file, monkeypatch):
    """Test basic prompt generation to a file."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        task="My test task",
        minimal=False,
        tech_stack=None,
        output_file=None,
        clipboard=False,
        exclude_code=False
    )

    with patch('aicodec.infrastructure.cli.commands.prompt.open_file_in_editor') as mock_open:
        prompt.run(args)
        mock_open.assert_called_once()

    prompt_file = sample_project / ".aicodec" / "prompt.txt"
    assert prompt_file.exists()
    content = prompt_file.read_text()
    assert "My test task" in content
    assert "<code_context>" in content  # Code is included by default
    assert "<coding_standard>" in content  # full context is included


def test_prompt_run_to_clipboard(sample_project, aicodec_config_file, setup_context_file, monkeypatch):
    """Test prompt generation to the clipboard."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        task="Clipboard task",
        minimal=True,
        tech_stack="Python",
        output_file=None,
        clipboard=True,
        exclude_code=False
    )

    with patch('aicodec.infrastructure.cli.commands.prompt.pyperclip.copy') as mock_copy:
        prompt.run(args)
        mock_copy.assert_called_once()
        call_content = mock_copy.call_args[0][0]
        assert "Clipboard task" in call_content
        assert "Python" in call_content
        assert "<coding_standard>" not in call_content  # full context is not included


def test_prompt_run_no_code(sample_project, aicodec_config_file, setup_context_file, monkeypatch):
    """Test prompt generation with the --no-code flag."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        task="No code task",
        minimal=False,
        tech_stack=None,
        output_file=None,
        clipboard=False,
        exclude_code=True
    )

    with patch('aicodec.infrastructure.cli.commands.prompt.open_file_in_editor'):
        prompt.run(args)

    prompt_file = sample_project / ".aicodec" / "prompt.txt"
    content = prompt_file.read_text()
    assert "No code task" in content
    assert "<code_context>" not in content
    assert "<coding_standard>" in content


def test_prompt_run_missing_context(sample_project, aicodec_config_file, monkeypatch, capsys):
    """Test that prompt command exits if context.json is missing."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        task="Will fail",
        tech_stack=None,
        output_file=None,
        clipboard=False,
        exclude_code=False
    )

    with pytest.raises(SystemExit) as e:
        prompt.run(args)

    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "context.json' not found" in captured.out
