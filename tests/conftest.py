# tests/conftest.py
import json

import pytest


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
    node_modules = project_dir / "node_modules" / "submodule"
    node_modules.mkdir(parents=True, exist_ok=True)
    (node_modules / "subpackage.js").write_text("// node module")
    (project_dir / "node_modules" / "package.js").write_text("// package file")

    dist_dir = project_dir / "dist"
    dist_dir.mkdir()
    (dist_dir / "bundle.js").write_text("// compiled bundle")

    # Create log files
    (project_dir / "app.log").write_text("log entry")
    (project_dir / "error.log").write_text("error entry")

    # Create nested directories for testing
    ex_dir = project_dir / "ex" / "dir"
    ex_dir.mkdir(parents=True, exist_ok=True)
    (ex_dir / "nested.py").write_text("def nested(): pass")
    (project_dir / "ex" / "dirt.py").write_text("def dirt(): pass")

    # Create .gitignore
    gitignore_content = """
node_modules/
dist/
*.log
*.tmp
decoders/
"""
    (project_dir / ".gitignore").write_text(gitignore_content.strip())

    # Create files for plugin testing
    (project_dir / "data.hdf").write_text("dummy hdf content")
    (project_dir / "other.dat").write_text("dummy dat content")
    decoder_dir = project_dir / "decoders"
    decoder_dir.mkdir()
    (decoder_dir / "__init__.py").write_text("")
    (decoder_dir / "hdf_decoder.py").write_text(
        """
import sys
import json
if __name__ == "__main__":
    file_path = sys.argv[1]
    print(json.dumps({"status": "decoded", "file": file_path}))
"""
    )
    (decoder_dir / "hdf_decoder_override.py").write_text(
        """
import sys
if __name__ == "__main__":
    file_path = sys.argv[1]
    print(f"# HDF5 File\\n\\n- Path: {file_path}")
"""
    )

    return project_dir


@pytest.fixture
def aicodec_config_file(sample_project):
    """Create a basic aicodec configuration file in the sample project."""
    config_dir = sample_project / ".aicodec"
    config_dir.mkdir()

    config_data = {
        "aggregate": {
            "directories": ["."],
            "use_gitignore": True,
            "plugins": [
                ".hdf=python decoders/hdf_decoder.py {file}"
            ]
        },
        "prompt": {
            "output_file": ".aicodec/prompt.txt",
            "tech_stack": "Python"
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
def sample_changes_json_content():
    """Returns the content for a sample changes file as a dictionary."""
    return {
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
                "filePath": "README.md",
                "action": "DELETE",
                "content": ""
            }
        ]
    }


@pytest.fixture
def sample_changes_file(tmp_path, sample_changes_json_content):
    """Create a sample changes file for testing."""
    changes_file = tmp_path / "changes.json"
    changes_file.write_text(json.dumps(sample_changes_json_content, indent=2))
    return changes_file
