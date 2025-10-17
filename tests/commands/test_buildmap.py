# tests/commands/test_buildmap.py
from argparse import Namespace

from aicodec.infrastructure.cli.commands import buildmap


def test_buildmap_run_respects_gitignore(sample_project, aicodec_config_file, monkeypatch):
    """Test buildmap command creates a map and respects .gitignore by default."""
    monkeypatch.chdir(sample_project)

    # Add an extra file that should be ignored by config but not by buildmap
    (sample_project / "docs").mkdir(exist_ok=True)
    (sample_project / "docs" / "extra.md").write_text("doc")

    # Modify config to exclude markdown, which buildmap should ignore
    config_path = sample_project / ".aicodec" / "config.json"
    config_path.write_text('{"aggregate": {"exclude": ["**/*.md"]}}')

    args = Namespace(config=str(config_path), use_gitignore=True)
    buildmap.run(args)

    repo_map_file = sample_project / ".aicodec" / "repo_map.md"
    assert repo_map_file.exists()

    content = repo_map_file.read_text()

    # Files from .gitignore like app.log, dist/, node_modules/ should NOT be here
    assert "app.log" not in content
    assert "dist" not in content
    assert "node_modules" not in content

    # Files not ignored by .gitignore should be here
    assert "main.py" in content
    assert "utils.py" in content
    assert "README.md" in content  # Should be included because config is ignored
    assert "extra.md" in content  # Should be included because config is ignored


def test_buildmap_run_no_gitignore(sample_project, aicodec_config_file, monkeypatch):
    """Test buildmap command with --no-gitignore includes everything."""
    monkeypatch.chdir(sample_project)

    args = Namespace(config=str(aicodec_config_file), use_gitignore=False)
    buildmap.run(args)

    repo_map_file = sample_project / ".aicodec" / "repo_map.md"
    assert repo_map_file.exists()

    content = repo_map_file.read_text()

    # Files from .gitignore should NOW be included
    assert "app.log" in content
    assert "dist" in content
    assert "bundle.js" in content
    assert "node_modules" in content
    assert "package.js" in content


def test_buildmap_creates_correct_tree_structure(sample_project, aicodec_config_file, monkeypatch):
    """Test that the generated repo map has the correct tree structure."""
    monkeypatch.chdir(sample_project)

    args = Namespace(config=str(aicodec_config_file), use_gitignore=True)
    buildmap.run(args)

    repo_map_file = sample_project / ".aicodec" / "repo_map.md"
    content = repo_map_file.read_text()

    expected_content = "\n".join([
        ".",
        "├── .gitignore",
        "├── README.md",
        "├── config.json",
        "├── ex/",
        "│   ├── dir/",
        "│   │   └── nested.py",
        "│   └── dirt.py",
        "├── main.py",
        "├── src/",
        "│   ├── module.js",
        "│   └── utils.py",
        "└── tests/",
        "    └── test_main.py",
    ])

    assert content.strip() == expected_content.strip()
