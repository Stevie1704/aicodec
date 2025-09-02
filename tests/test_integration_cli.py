# tests/test_integration_cli.py
import pytest
import json
import subprocess
import sys
import os
import pyperclip
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def sample_project(tmp_path):
 	"""Create a sample project structure for testing."""
 	project_dir = tmp_path / "test_project"
 	project_dir.mkdir()

 	# Create various file types
 	(project_dir / "main.py").write_text('print("Hello World")')
 	(project_dir / "config.json").write_text('{"key": "value"}')
 	(project_dir / "README.md").write_text("# Test Project\n\nThis is a test.")

 	# Create subdirectories
 	src_dir = project_dir / "src"
 	src_dir.mkdir()
 	(src_dir / "utils.py").write_text("def helper(): pass")
 	(src_dir / "module.js").write_text("console.log('test');")

 	tests_dir = project_dir / "tests"
 	tests_dir.mkdir()
 	(tests_dir / "test_main.py").write_text("def test_example(): assert True")

 	# Create files to exclude
 	node_modules = project_dir / "node_modules"
 	node_modules.mkdir()
 	(node_modules / "package.js").write_text("// node module")

 	dist_dir = project_dir / "dist"
 	dist_dir.mkdir()
 	(dist_dir / "bundle.js").write_text("// compiled bundle")

 	# Create log files
 	(project_dir / "app.log").write_text("log entry")
 	(project_dir / "error.log").write_text("error entry")

 	# Create .gitignore
 	gitignore_content = """
node_modules/
dist/
*.log
*.tmp
"""
 	(project_dir / ".gitignore").write_text(gitignore_content.strip())

 	return project_dir


@pytest.fixture
def aicodec_config(sample_project):
 	"""Create a basic aicodec configuration."""
 	config_dir = sample_project / ".aicodec"
 	config_dir.mkdir()

 	config_data = {
 	 	"aggregate": {
 	 	 	"directory": ".",
 	 	 	"use_gitignore": True,
 	 	 	"exclude_dirs": [".git", ".aicodec"]
 	 	},
 	 	"prompt": {
 	 	 	"output_file": ".aicodec/prompt.txt",
 	 	 	"template": "Test template: {user_task_description}\n{code_context_json}"
 	 	},
 	 	"prepare": {
 	 	 	"changes": ".aicodec/changes.json",
 	 	 	"from_clipboard": False
 	 	},
 	 	"apply": {
 	 	 	"output_dir": "."
 	 	}
 	}

 	config_file = config_dir / "config.json"
 	config_file.write_text(json.dumps(config_data, indent=2))

 	return config_file


@pytest.fixture
def sample_changes_file(tmp_path):
 	"""Create a sample changes file for testing."""
 	changes_data = {
 	 	"summary": "Test changes for integration testing",
 	 	"changes": [
 	 	 	{
 	 	 	 	"filePath": "new_file.py",
 	 	 	 	"action": "CREATE",
 	 	 	 	"content": "# New file\nprint('Hello from new file')"
 	 	 	},
 	 	 	{
 	 	 	 	"filePath": "main.py",
 	 	 	 	"action": "REPLACE",
 	 	 	 	"content": "# Modified main file\nprint('Hello Modified World')"
 	 	 	},
 	 	 	{
 	 	 	 	"filePath": "old_file.py",
 	 	 	 	"action": "DELETE",
 	 	 	 	"content": ""
 	 	 	}
 	 	]
 	}

 	changes_file = tmp_path / "changes.json"
 	changes_file.write_text(json.dumps(changes_data, indent=2))
 	return changes_file


def run_aicodec_command(args, cwd=None, input_text=None, env_extra=None):
 	"""Helper function to run aicodec commands."""
 	cmd = [sys.executable, "-m",
 	 	 "aicodec.infrastructure.cli.command_line_interface"] + args

 	try:
 	 	env = os.environ.copy()
 	 	env['AICODEC_NO_EDITOR'] = '1'
 	 	env['AICODEC_TEST_MODE'] = '1'
 	 	if env_extra:
 	 	 	env.update(env_extra)
 	 	result = subprocess.run(
 	 	 	cmd,
 	 	 	cwd=cwd,
 	 	 	capture_output=True,
 	 	 	text=True,
 	 	 	input=input_text,
 	 	 	timeout=30,
 	 	 	env=env
 	 	)
 	 	return result
 	except subprocess.TimeoutExpired:
 	 	pytest.fail("Command timed out")


# INIT COMMAND TESTS

def test_init_command_basic(tmp_path, monkeypatch):
 	"""Test basic init command with default options."""
 	monkeypatch.chdir(tmp_path)

 	inputs = 'y\ny\ny\nn\n\nn\ny\n'
 	with patch('aicodec.infrastructure.cli.commands.utils.load_default_prompt_template', return_value="template"):
 	 	result = run_aicodec_command(["init"], cwd=tmp_path, input_text=inputs)

 	assert result.returncode == 0
 	assert "Successfully created configuration" in result.stdout

 	config_file = tmp_path / ".aicodec" / "config.json"
 	assert config_file.exists()

 	config = json.loads(config_file.read_text())
 	assert config["aggregate"]["use_gitignore"] is True
 	assert ".gitignore" in config["aggregate"]["exclude_files"]

 	gitignore_file = tmp_path / '.gitignore'
 	assert gitignore_file.exists()
 	assert ".aicodec/" in gitignore_file.read_text()


def test_init_command_overwrite_existing(tmp_path, monkeypatch):
 	"""Test init command with existing config file."""
 	monkeypatch.chdir(tmp_path)

 	# Create existing config
 	config_dir = tmp_path / ".aicodec"
 	config_dir.mkdir()
 	existing_config = config_dir / "config.json"
 	existing_config.write_text('{"existing": "config"}')

 	# Test cancellation
 	result = run_aicodec_command(["init"], cwd=tmp_path, input_text='n\n')

 	assert result.returncode == 0
 	assert "Initialization cancelled" in result.stdout

 	# Verify original config is unchanged
 	config = json.loads(existing_config.read_text())
 	assert config == {"existing": "config"}


def test_init_command_with_additional_options(tmp_path, monkeypatch):
 	"""Test init command with additional inclusions/exclusions."""
 	monkeypatch.chdir(tmp_path)

 	inputs = 'y\ny\ny\ny\nsrc,lib\n*.py,*.js\n.py,.js,.json\nbuild,temp\n*.tmp,*.bak\n.log,.tmp\nPython\ny\ny\n'
 	with patch('aicodec.infrastructure.cli.commands.utils.load_default_prompt_template', return_value="template"):
 	 	result = run_aicodec_command(["init"], cwd=tmp_path, input_text=inputs)

 	assert result.returncode == 0

 	config_file = tmp_path / ".aicodec" / "config.json"
 	config = json.loads(config_file.read_text())

 	assert "src" in config["aggregate"]["include_dirs"]
 	assert "lib" in config["aggregate"]["include_dirs"]
 	assert "*.py" in config["aggregate"]["include_files"]
 	assert ".py" in config["aggregate"]["include_ext"]
 	assert "build" in config["aggregate"]["exclude_dirs"]
 	assert "*.tmp" in config["aggregate"]["exclude_files"]
 	assert ".log" in config["aggregate"]["exclude_exts"]
 	assert config["prepare"]["from_clipboard"] is True
 	assert config["prompt"]["tech-stack"] == "Python"
 	assert config["prompt"]["include_code"] is True

 	gitignore_file = tmp_path / '.gitignore'
 	assert gitignore_file.exists()
 	assert ".aicodec/" in gitignore_file.read_text()


# SCHEMA COMMAND TESTS

def test_schema_command(tmp_path):
 	"""Test schema command output."""
 	result = run_aicodec_command(["schema"], cwd=tmp_path)

 	assert result.returncode == 0
 	json.loads(result.stdout)


# AGGREGATE COMMAND TESTS

def test_aggregate_command_basic(sample_project, aicodec_config, monkeypatch):
 	"""Test basic aggregate command."""
 	monkeypatch.chdir(sample_project)

 	result = run_aicodec_command(["aggregate", "-c", str(aicodec_config)])

 	assert result.returncode == 0
 	assert "Successfully aggregated" in result.stdout

 	context_file = sample_project / ".aicodec" / "context.json"
 	assert context_file.exists()

 	context_data = json.loads(context_file.read_text())
 	assert isinstance(context_data, list)
 	assert len(context_data) > 0

 	# Verify expected files are included
 	file_paths = {item["filePath"] for item in context_data}
 	assert "main.py" in file_paths
 	assert "src/utils.py" in file_paths

 	# Verify excluded files are not included (due to .gitignore)
 	assert "app.log" not in file_paths
 	assert "node_modules/package.js" not in file_paths


def test_aggregate_command_with_directory_override(sample_project, aicodec_config, monkeypatch):
 	"""Test aggregate command with directory override."""
 	monkeypatch.chdir(sample_project.parent)

 	result = run_aicodec_command([
 	 	"aggregate", "-c", str(aicodec_config),
 	 	"-d", str(sample_project)
 	])

 	assert result.returncode == 0
 	context_file = sample_project / ".aicodec" / "context.json"
 	assert context_file.exists()


def test_aggregate_command_with_inclusions(sample_project, aicodec_config, monkeypatch):
 	"""Test aggregate command with inclusion overrides."""
 	monkeypatch.chdir(sample_project)

 	result = run_aicodec_command([
 	 	"aggregate", "-c", str(aicodec_config),
 	 	"--include-dir", "node_modules",
 	 	"--include-ext", ".log",
 	 	"--include-file", "dist/bundle.js"
 	])

 	assert result.returncode == 0

 	context_file = sample_project / ".aicodec" / "context.json"
 	context_data = json.loads(context_file.read_text())
 	file_paths = {item["filePath"] for item in context_data}

 	# These should be included despite .gitignore
 	assert "node_modules/package.js" in file_paths
 	assert "app.log" in file_paths
 	assert "dist/bundle.js" in file_paths


def test_aggregate_command_with_exclusions(sample_project, aicodec_config, monkeypatch):
 	"""Test aggregate command with exclusion overrides."""
 	monkeypatch.chdir(sample_project)

 	result = run_aicodec_command([
 	 	"aggregate", "-c", str(aicodec_config),
 	 	"--exclude-dir", "src",
 	 	"--exclude-ext", ".py",
 	 	"--exclude-file", "README.md"
 	])

 	assert result.returncode == 0

 	context_file = sample_project / ".aicodec" / "context.json"
 	context_data = json.loads(context_file.read_text())
 	file_paths = {item["filePath"] for item in context_data}

 	# These should be excluded
 	assert "src/utils.py" not in file_paths
 	assert "main.py" not in file_paths
 	assert "README.md" not in file_paths


def test_aggregate_command_full_run(sample_project, aicodec_config, monkeypatch):
 	"""Test aggregate command with full run option."""
 	monkeypatch.chdir(sample_project)

 	# First run to create hashes
 	result1 = run_aicodec_command(["aggregate", "-c", str(aicodec_config)])
 	assert result1.returncode == 0

 	# Second run should detect no changes
 	result2 = run_aicodec_command(["aggregate", "-c", str(aicodec_config)])
 	assert result2.returncode == 0
 	assert "No changes detected" in result2.stdout

 	# Full run should aggregate all files regardless of hashes
 	result3 = run_aicodec_command(
 	 	["aggregate", "-c", str(aicodec_config), "--full"])
 	assert result3.returncode == 0
 	assert "Successfully aggregated" in result3.stdout


def test_aggregate_command_count_tokens(sample_project, aicodec_config, monkeypatch):
 	"""Test aggregate command with token counting."""
 	monkeypatch.chdir(sample_project)

 	result = run_aicodec_command([
 	 	"aggregate", "-c", str(aicodec_config), "--count-tokens"
 	])

 	assert result.returncode == 0
 	assert "Token count:" in result.stdout or "Token counting failed" in result.stdout


def test_aggregate_command_gitignore_options(sample_project, aicodec_config, monkeypatch):
 	"""Test aggregate command with gitignore options."""
 	monkeypatch.chdir(sample_project)

 	# Test with --no-gitignore
 	result1 = run_aicodec_command([
 	 	"aggregate", "-c", str(aicodec_config), "--no-gitignore"
 	])

 	assert result1.returncode == 0
 	context_file = sample_project / ".aicodec" / "context.json"
 	context_data = json.loads(context_file.read_text())
 	file_paths = {item["filePath"] for item in context_data}

 	# With --no-gitignore, log files should be included
 	assert "app.log" in file_paths

 	# Test with explicit --use-gitignore
 	result2 = run_aicodec_command([
 	 	"aggregate", "-c", str(aicodec_config), "--use-gitignore"
 	])

 	assert result2.returncode == 0


# PROMPT COMMAND TESTS

def test_prompt_command_basic(sample_project, aicodec_config, monkeypatch):
 	"""Test basic prompt command."""
 	monkeypatch.chdir(sample_project)

 	# First create context
 	run_aicodec_command(["aggregate", "-c", str(aicodec_config)])

 	result = run_aicodec_command([
 	 	"prompt", "-c", str(aicodec_config),
 	 	"--task", "Fix all bugs"
 	])

 	assert result.returncode == 0
 	assert "Successfully generated prompt" in result.stdout

 	prompt_file = sample_project / ".aicodec" / "prompt.txt"
 	assert prompt_file.exists()

 	prompt_content = prompt_file.read_text()
 	assert "Fix all bugs" in prompt_content
 	assert "Test template:" in prompt_content


def test_prompt_command_to_clipboard(sample_project, aicodec_config, monkeypatch):
 	"""Test prompt command with clipboard output."""
 	monkeypatch.chdir(sample_project)

 	# First create context
 	run_aicodec_command(["aggregate", "-c", str(aicodec_config)])

 	result = run_aicodec_command([
 	 	"prompt", "-c", str(aicodec_config),
 	 	"--task", "Refactor code",
 	 	"--clipboard"
 	])

 	assert result.returncode == 0
 	assert "successfully copied to test clipboard" in result.stdout


def test_prompt_command_custom_output_file(sample_project, aicodec_config, monkeypatch):
 	"""Test prompt command with custom output file."""
 	monkeypatch.chdir(sample_project)

 	# First create context
 	run_aicodec_command(["aggregate", "-c", str(aicodec_config)])

 	custom_output = sample_project / "custom_prompt.txt"

 	result = run_aicodec_command([
 	 	"prompt", "-c", str(aicodec_config),
 	 	"--output-file", str(custom_output)
 	])

 	assert result.returncode == 0
 	assert custom_output.exists()


def test_prompt_command_missing_context(sample_project, aicodec_config, monkeypatch):
 	"""Test prompt command when context file is missing."""
 	monkeypatch.chdir(sample_project)

 	result = run_aicodec_command(["prompt", "-c", str(aicodec_config)])

 	assert result.returncode == 1
 	assert "Context file" in (
 	 	result.stdout + result.stderr) and "not found" in (result.stdout + result.stderr)


# PREPARE COMMAND TESTS

def test_prepare_command_editor_mode(sample_project, aicodec_config, monkeypatch):
 	"""Test prepare command in editor mode."""
 	monkeypatch.chdir(sample_project)

 	result = run_aicodec_command(["prepare", "-c", str(aicodec_config)])

 	assert result.returncode == 0
 	assert "Opening in default editor" in result.stdout

 	changes_file = sample_project / ".aicodec" / "changes.json"
 	assert changes_file.exists()


def test_prepare_command_clipboard_mode(sample_project, aicodec_config, monkeypatch):
 	"""Test prepare command with clipboard input."""
 	monkeypatch.chdir(sample_project)

 	valid_json = json.dumps({
 	 	"summary": "Test summary",
 	 	"changes": [{
 	 	 	"filePath": "test.py",
 	 	 	"action": "CREATE",
 	 	 	"content": "print('test')"
 	 	}]
 	})

 	result = run_aicodec_command([
 	 	"prepare", "-c", str(aicodec_config), "--from-clipboard"
 	], env_extra={'AICODEC_TEST_CLIPBOARD': valid_json})

 	assert result.returncode == 0
 	assert "Successfully wrote content from clipboard" in result.stdout

 	changes_file = sample_project / ".aicodec" / "changes.json"
 	assert changes_file.exists()
 	assert json.loads(changes_file.read_text()) == json.loads(valid_json)


def test_prepare_command_clipboard_invalid_json(sample_project, aicodec_config, monkeypatch):
 	"""Test prepare command with invalid JSON in clipboard."""
 	monkeypatch.chdir(sample_project)

 	result = run_aicodec_command([
 	 	"prepare", "-c", str(aicodec_config), "--from-clipboard"
 	], env_extra={'AICODEC_TEST_CLIPBOARD': 'invalid json'})

 	assert result.returncode == 0
 	assert "Clipboard content is not valid JSON" in result.stdout


def test_prepare_command_overwrite_existing(sample_project, aicodec_config, monkeypatch):
 	"""Test prepare command with existing changes file."""
 	monkeypatch.chdir(sample_project)

 	# Create existing changes file
 	changes_file = sample_project / ".aicodec" / "changes.json"
 	changes_file.parent.mkdir(exist_ok=True)
 	changes_file.write_text('{"existing": "data"}')

 	# Test cancellation
 	result = run_aicodec_command(
 	 	["prepare", "-c", str(aicodec_config)], input_text='n\n')

 	assert result.returncode == 0
 	assert "Operation cancelled" in result.stdout

 	# Verify original content is unchanged
 	assert json.loads(changes_file.read_text()) == {"existing": "data"}


def test_prepare_command_custom_changes_file(sample_project, aicodec_config, monkeypatch):
 	"""Test prepare command with custom changes file path."""
 	monkeypatch.chdir(sample_project)

 	custom_changes = sample_project / "my_changes.json"

 	result = run_aicodec_command([
 	 	"prepare", "-c", str(aicodec_config),
 	 	"--changes", str(custom_changes)
 	])

 	assert result.returncode == 0
 	assert custom_changes.exists()


# APPLY AND REVERT COMMAND TESTS

def test_apply_command_basic(sample_project, aicodec_config, sample_changes_file, monkeypatch):
 	"""Test basic apply command (mocked server launch)."""
 	monkeypatch.chdir(sample_project)

 	# Update config to point to our sample changes file
 	config = json.loads(aicodec_config.read_text())
 	config["prepare"]["changes"] = str(sample_changes_file)
 	aicodec_config.write_text(json.dumps(config, indent=2))

 	result = run_aicodec_command([
 	 	"apply", "-c", str(aicodec_config)
 	])

 	assert result.returncode == 0
 	assert "Test mode: skipping server launch" in result.stdout


def test_apply_command_with_overrides(sample_project, sample_changes_file, monkeypatch):
 	"""Test apply command with CLI parameter overrides."""
 	monkeypatch.chdir(sample_project)

 	# Create minimal config without apply section
 	config_dir = sample_project / ".aicodec"
 	config_dir.mkdir(exist_ok=True)
 	config_file = config_dir / "config.json"
 	config_file.write_text('{}')

 	result = run_aicodec_command([
 	 	"apply", "-c", str(config_file),
 	 	"--output-dir", str(sample_project),
 	 	"--changes", str(sample_changes_file)
 	])

 	assert result.returncode == 0
 	assert "Test mode: skipping server launch" in result.stdout


def test_apply_command_missing_config(sample_project, monkeypatch):
 	"""Test apply command with missing required configuration."""
 	monkeypatch.chdir(sample_project)

 	# Create config without required fields
 	config_dir = sample_project / ".aicodec"
 	config_dir.mkdir(exist_ok=True)
 	config_file = config_dir / "config.json"
 	config_file.write_text('{}')

 	result = run_aicodec_command(["apply", "-c", str(config_file)])

 	assert result.returncode == 0
 	assert "Missing required configuration" in result.stdout


def test_revert_command_basic(sample_project, aicodec_config, monkeypatch):
 	"""Test basic revert command."""
 	monkeypatch.chdir(sample_project)

 	# Create mock revert file
 	revert_dir = sample_project / ".aicodec"
 	revert_dir.mkdir(exist_ok=True)
 	revert_file = revert_dir / "revert.json"
 	revert_data = {
 	 	"changes": [{
 	 	 	"filePath": "test.py",
 	 	 	"action": "DELETE",
 	 	 	"content": ""
 	 	}]
 	}
 	revert_file.write_text(json.dumps(revert_data))

 	result = run_aicodec_command([
 	 	"revert", "-c", str(aicodec_config)
 	])

 	assert result.returncode == 0
 	assert "Test mode: skipping server launch" in result.stdout


def test_revert_command_no_revert_data(sample_project, aicodec_config, monkeypatch):
 	"""Test revert command when no revert data exists."""
 	monkeypatch.chdir(sample_project)

 	result = run_aicodec_command([
 	 	"revert", "-c", str(aicodec_config)
 	])

 	assert result.returncode == 0
 	assert "No revert data found" in result.stdout


def test_revert_command_with_output_dir_override(sample_project, monkeypatch):
 	"""Test revert command with output directory override."""
 	monkeypatch.chdir(sample_project)

 	# Create minimal config
 	config_dir = sample_project / ".aicodec"
 	config_dir.mkdir(exist_ok=True)
 	config_file = config_dir / "config.json"
 	config_file.write_text('{}')

 	# Create revert file
 	revert_file = sample_project / ".aicodec" / "revert.json"
 	revert_file.write_text('{"changes": []}')

 	result = run_aicodec_command([
 	 	"revert", "-c", str(config_file),
 	 	"--output-dir", str(sample_project)
 	])

 	assert result.returncode == 0
 	assert "Test mode: skipping server launch" in result.stdout


# ERROR HANDLING AND EDGE CASES

def test_missing_config_file(tmp_path, monkeypatch):
 	"""Test commands that require config file when it doesn't exist."""
 	monkeypatch.chdir(tmp_path)

 	result = run_aicodec_command(["aggregate"])

 	assert result.returncode == 1
 	assert "aicodec not initialised" in result.stdout


def test_aggregate_no_files_to_aggregate(sample_project, monkeypatch):
 	"""Test aggregate command when no files match criteria."""
 	monkeypatch.chdir(sample_project)

 	# Create config that excludes everything
 	config_dir = sample_project / ".aicodec"
 	config_dir.mkdir(exist_ok=True)
 	config_data = {
 	 	"aggregate": {
 	 	 	"directory": ".",
 	 	 	"use_gitignore": True,
 	 	 	"exclude_dirs": ["src", "tests"],
 	 	 	"exclude_exts": [".py", ".js", ".json", ".md", ".log"],
 	 	 	"exclude_files": ["*"]
 	 	}
 	}
 	config_file = config_dir / "config.json"
 	config_file.write_text(json.dumps(config_data))

 	result = run_aicodec_command(["aggregate", "-c", str(config_file)])

 	assert result.returncode == 0
 	assert "No files found to aggregate" in result.stdout


def test_command_with_nonexistent_directory(tmp_path):
 	"""Test aggregate command with non-existent directory."""
 	config_dir = tmp_path / ".aicodec"
 	config_dir.mkdir()
 	config_data = {
 	 	"aggregate": {
 	 	 	"directory": ".",
 	 	 	"use_gitignore": True
 	 	}
 	}
 	config_file = config_dir / "config.json"
 	config_file.write_text(json.dumps(config_data))

 	result = run_aicodec_command([
 	 	"aggregate", "-c", str(config_file),
 	 	"-d", "/nonexistent/path"
 	])

 	# The command should handle this gracefully
 	assert result.returncode == 0
 	assert "No files found to aggregate" in result.stdout
