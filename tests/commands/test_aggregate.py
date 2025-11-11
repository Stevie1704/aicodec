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
        include=[],
        exclude=[],
        full=False, use_gitignore=None, count_tokens=False,
        plugin=[]
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
        include=[],
        exclude=[],
        full=False, use_gitignore=False, count_tokens=False,
        plugin=[]
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
        include=["dist/**", "*.log"],
        exclude=["src/**", "README.md"],
        full=True, use_gitignore=None, count_tokens=True,
        plugin=[]
    )

    aggregate.run(args)

    context_file = sample_project / ".aicodec" / "context.json"
    data = json.loads(context_file.read_text())
    filepaths = {item['filePath'] for item in data}

    assert "dist/bundle.js" in filepaths  # Included via include glob
    assert "app.log" in filepaths        # Included via include glob
    assert "src/utils.py" not in filepaths  # Excluded via exclude glob
    assert "README.md" not in filepaths     # Excluded via exclude glob


def test_aggregate_no_changes(sample_project, aicodec_config_file, monkeypatch, capsys):
    """Test aggregate reports no changes on a second run."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file), directories=None,
        include=[],
        exclude=[],
        full=False, use_gitignore=None, count_tokens=False,
        plugin=[]
    )

    # First run
    aggregate.run(args)

    # Second run
    aggregate.run(args)
    captured = capsys.readouterr()
    assert "No changes detected" in captured.out


def test_aggregate_exclude_nested_dir(sample_project, aicodec_config_file, monkeypatch):
    """Test aggregate excludes nested directories with --exclude."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file), directories=None,
        include=[],
        exclude=["ex/dir/**"],
        full=True, use_gitignore=None, count_tokens=False,
        plugin=[]
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
    """Test aggregate includes nested directories with --include, without over-including similar-named files."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file), directories=None,
        include=["node_modules/submodule/**"],
        exclude=[],
        full=True, use_gitignore=None, count_tokens=False,
        plugin=[]
    )

    aggregate.run(args)

    context_file = sample_project / ".aicodec" / "context.json"
    data = json.loads(context_file.read_text())
    filepaths = {item['filePath'] for item in data}

    assert "node_modules/submodule/subpackage.js" in filepaths
    assert "node_modules/package.js" not in filepaths


def test_aggregate_with_plugin(sample_project, aicodec_config_file, monkeypatch):
    """Test that a configured plugin is executed for a matching file type."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        directories=None,
        include=["data.hdf"],
        exclude=[],
        full=True, use_gitignore=True, count_tokens=False,
        plugin=[]
    )

    aggregate.run(args)

    context_file = sample_project / ".aicodec" / "context.json"
    assert context_file.exists()
    data = json.loads(context_file.read_text())

    plugin_output_found = False
    for item in data:
        if item['filePath'] == 'data.hdf':
            content_data = json.loads(item['content'])
            assert content_data['status'] == 'decoded'
            assert "data.hdf" in content_data['file']
            plugin_output_found = True
            break
    assert plugin_output_found, "Plugin output for data.hdf not found in context.json"


def test_aggregate_with_cli_plugin(sample_project, aicodec_config_file, monkeypatch):
    """Test that a plugin provided via the CLI is executed."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        directories=None,
        include=["other.dat"],
        exclude=[],
        full=True, use_gitignore=True, count_tokens=False,
        plugin=[".dat=python decoders/hdf_decoder.py {file}"]
    )

    aggregate.run(args)

    context_file = sample_project / ".aicodec" / "context.json"
    data = json.loads(context_file.read_text())
    
    plugin_output_found = False
    for item in data:
        if item['filePath'] == 'other.dat':
            content_data = json.loads(item['content'])
            assert content_data['status'] == 'decoded'
            assert "other.dat" in content_data['file']
            plugin_output_found = True
            break
            
    assert plugin_output_found, "CLI plugin output for other.dat not found"


def test_aggregate_with_cli_plugin_override(sample_project, aicodec_config_file, monkeypatch):
    """Test that a CLI plugin overrides a config file plugin."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        directories=None,
        include=["data.hdf"],
        exclude=[],
        full=True, use_gitignore=True, count_tokens=False,
        plugin=[".hdf=python decoders/hdf_decoder_override.py {file}"]
    )

    aggregate.run(args)

    context_file = sample_project / ".aicodec" / "context.json"
    data = json.loads(context_file.read_text())

    plugin_output_found = False
    for item in data:
        if item['filePath'] == 'data.hdf':
            # The content should now be a Markdown string
            assert "# HDF5 File" in item['content']
            assert "- Path: " in item['content']
            assert "data.hdf" in item['content']
            plugin_output_found = True
            break
            
    assert plugin_output_found, "CLI override plugin output not found"
