# tests/commands/test_aggregate.py
import json
from argparse import Namespace

from aicodec.infrastructure.cli.commands import aggregate


def test_aggregate_run_basic(sample_project, aicodec_config_file, monkeypatch):
    """Test basic aggregate command respects .gitignore."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        directories=None,
        include_dirs=[], include_exts=[], include_files=[],
        exclude_dirs=[], exclude_exts=[], exclude_files=[],
        full=False, use_gitignore=None, count_tokens=False
    )

    aggregate.run(args)

    context_file = sample_project / ".aicodec" / "context.json"
    assert context_file.exists()
    data = json.loads(context_file.read_text())
    filepaths = {item['filePath'] for item in data}

    assert "main.py" in filepaths
    assert "src/utils.py" in filepaths
    assert "app.log" not in filepaths
    assert "node_modules/package.js" not in filepaths
    assert "dist/bundle.js" not in filepaths


def test_aggregate_run_no_gitignore(sample_project, aicodec_config_file, monkeypatch):
    """Test aggregate command with --no-gitignore flag."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file), directories=None,
        include_dirs=[], include_exts=[], include_files=[],
        exclude_dirs=[], exclude_exts=[], exclude_files=[],
        full=False, use_gitignore=False, count_tokens=False
    )

    aggregate.run(args)

    context_file = sample_project / ".aicodec" / "context.json"
    data = json.loads(context_file.read_text())
    filepaths = {item['filePath'] for item in data}

    assert "app.log" in filepaths  # Should be included now
    assert "node_modules/package.js" in filepaths
    assert "dist/bundle.js" in filepaths


def test_aggregate_run_with_overrides(sample_project, aicodec_config_file, monkeypatch):
    """Test aggregate command with include/exclude flag overrides."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file), directories=None,
        include_dirs=["dist"], include_exts=[".log"], include_files=[],
        exclude_dirs=["src"], exclude_exts=[".md"], exclude_files=[],
        full=True, use_gitignore=None, count_tokens=True
    )

    aggregate.run(args)

    context_file = sample_project / ".aicodec" / "context.json"
    data = json.loads(context_file.read_text())
    filepaths = {item['filePath'] for item in data}

    assert "dist/bundle.js" in filepaths  # Included via --include-dir
    assert "app.log" in filepaths        # Included via --include-ext
    assert "src/utils.py" not in filepaths  # Excluded via --exclude-dir
    assert "README.md" not in filepaths     # Excluded via --exclude-ext


def test_aggregate_no_changes(sample_project, aicodec_config_file, monkeypatch, capsys):
    """Test aggregate reports no changes on a second run."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file), directories=None,
        include_dirs=[], include_exts=[], include_files=[],
        exclude_dirs=[], exclude_exts=[], exclude_files=[],
        full=False, use_gitignore=None, count_tokens=False
    )

    # First run
    aggregate.run(args)

    # Second run
    aggregate.run(args)
    captured = capsys.readouterr()
    assert "No changes detected" in captured.out


def test_aggregate_exclude_nested_dir(sample_project, aicodec_config_file, monkeypatch):
    """Test aggregate excludes nested directories with --exclude-dir."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file), directories=None,
        include_dirs=[], include_exts=[], include_files=[],
        exclude_dirs=["ex/dir"], exclude_exts=[], exclude_files=[],
        full=True, use_gitignore=None, count_tokens=False
    )

    aggregate.run(args)

    context_file = sample_project / ".aicodec" / "context.json"
    data = json.loads(context_file.read_text())
    filepaths = {item['filePath'] for item in data}

    assert "ex/dir/nested.py" not in filepaths
    assert "ex/dirt.py" in filepaths  # Ensure similar-named files aren't excluded
    # Ensure .gitignore still works
    assert "app.log" not in filepaths
    assert "dist/bundle.js" not in filepaths


def test_aggregate_include_nested_dir(sample_project, aicodec_config_file, monkeypatch):
    """Test aggregate includes nested directories with --include-dir, without over-including similar-named files."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file), directories=None,
        include_dirs=["node_modules/submodule"], include_exts=[], include_files=[],
        exclude_dirs=[], exclude_exts=[], exclude_files=[],
        full=True, use_gitignore=None, count_tokens=False
    )

    aggregate.run(args)

    context_file = sample_project / ".aicodec" / "context.json"
    data = json.loads(context_file.read_text())
    filepaths = {item['filePath'] for item in data}

    assert "node_modules/submodule/subpackage.js" in filepaths
    assert "node_modules/package.js" not in filepaths
