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
        skip_editor=False,
        output_guide=False
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
        include_map=True,  # Explicitly include
        output_guide=False
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
        skip_editor=False,
        output_guide=False
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
        skip_editor=False,
        output_guide=False
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
        skip_editor=False,
        output_guide=False
    )

    with patch('aicodec.infrastructure.cli.commands.prompt.open_file_in_editor', return_value=True):
        prompt.run(args)

    captured = capsys.readouterr()
    assert "Warning: Repo map file not found" in captured.out
    assert "Run 'aicodec buildmap' first" in captured.out

    prompt_file = sample_project / ".aicodec" / "prompt.txt"
    content = prompt_file.read_text()
    assert "<repository_map>" not in content


class TestOutputGuide:
    """Tests for the --output-guide flag."""

    def test_output_guide_full(self, sample_project, aicodec_config_file, monkeypatch):
        """Test --output-guide outputs only the formatting rules (full version)."""
        monkeypatch.chdir(sample_project)

        args = Namespace(
            config=str(aicodec_config_file),
            task="Ignored task",
            minimal=False,
            tech_stack="Python",
            output_file=None,
            clipboard=False,
            exclude_output_instructions=False,
            is_new_project=False,
            exclude_code=False,
            include_map=None,
            skip_editor=True,
            output_guide=True
        )

        prompt.run(args)

        prompt_file = sample_project / ".aicodec" / "prompt.txt"
        assert prompt_file.exists()
        content = prompt_file.read_text()

        # Should contain output instructions
        assert "<output_instructions>" in content
        assert "JSON Schema:" in content
        # Full version includes extra guidance
        assert "<action_rules>" in content
        assert "<coding_standard>" in content
        assert "<preflight_checking>" in content
        # Should NOT contain task or context
        assert "Ignored task" not in content
        assert "<code_context>" not in content
        assert "<repository_map>" not in content
        assert "<task>" not in content

    def test_output_guide_minimal(self, sample_project, aicodec_config_file, monkeypatch):
        """Test --output-guide --minimal outputs only the basic formatting rules."""
        monkeypatch.chdir(sample_project)

        args = Namespace(
            config=str(aicodec_config_file),
            task="Ignored task",
            minimal=True,
            tech_stack="Python",
            output_file=None,
            clipboard=False,
            exclude_output_instructions=False,
            is_new_project=False,
            exclude_code=False,
            include_map=None,
            skip_editor=True,
            output_guide=True
        )

        prompt.run(args)

        prompt_file = sample_project / ".aicodec" / "prompt.txt"
        assert prompt_file.exists()
        content = prompt_file.read_text()

        # Should contain output instructions
        assert "<output_instructions>" in content
        assert "JSON Schema:" in content
        # Minimal version does NOT include extra guidance
        assert "<action_rules>" not in content
        assert "<coding_standard>" not in content
        assert "<preflight_checking>" not in content

    @patch('pyperclip.copy')
    def test_output_guide_clipboard(self, mock_copy, sample_project, aicodec_config_file, monkeypatch):
        """Test --output-guide with --clipboard copies to clipboard."""
        monkeypatch.chdir(sample_project)

        args = Namespace(
            config=str(aicodec_config_file),
            task="Ignored task",
            minimal=False,
            tech_stack="Python",
            output_file=None,
            clipboard=True,
            exclude_output_instructions=False,
            is_new_project=False,
            exclude_code=False,
            include_map=None,
            skip_editor=True,
            output_guide=True
        )

        prompt.run(args)

        mock_copy.assert_called_once()
        content = mock_copy.call_args[0][0]
        assert "<output_instructions>" in content
        assert "JSON Schema:" in content

    def test_output_guide_with_tech_stack(self, sample_project, aicodec_config_file, monkeypatch):
        """Test --output-guide includes tech stack in coding standards."""
        monkeypatch.chdir(sample_project)

        args = Namespace(
            config=str(aicodec_config_file),
            task="Ignored task",
            minimal=False,
            tech_stack="TypeScript and React",
            output_file=None,
            clipboard=False,
            exclude_output_instructions=False,
            is_new_project=False,
            exclude_code=False,
            include_map=None,
            skip_editor=True,
            output_guide=True
        )

        prompt.run(args)

        prompt_file = sample_project / ".aicodec" / "prompt.txt"
        content = prompt_file.read_text()

        assert "TypeScript and React" in content

    def test_output_guide_no_reverts_cleared(self, sample_project, aicodec_config_file, monkeypatch):
        """Test --output-guide does not clear reverts folder (it's not a new session)."""
        monkeypatch.chdir(sample_project)

        # Create a revert file
        reverts_dir = sample_project / ".aicodec" / "reverts"
        reverts_dir.mkdir(parents=True, exist_ok=True)
        revert_file = reverts_dir / "revert-001.json"
        revert_file.write_text('{}')

        args = Namespace(
            config=str(aicodec_config_file),
            task="Ignored task",
            minimal=False,
            tech_stack="Python",
            output_file=None,
            clipboard=False,
            exclude_output_instructions=False,
            is_new_project=False,
            exclude_code=False,
            include_map=None,
            skip_editor=True,
            output_guide=True
        )

        prompt.run(args)

        # Revert file should still exist
        assert revert_file.exists()
