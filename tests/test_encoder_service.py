# tests/test_encoder_service.py
import pytest
import os
import json
import builtins
from pathlib import Path
from aicodec.core.config import EncoderConfig
from aicodec.services.encoder_service import EncoderService


@pytest.fixture
def project_structure(tmp_path):
    project_dir = tmp_path / 'my_project'
    project_dir.mkdir()
    (project_dir / 'main.py').write_text('print("main")')
    (project_dir / 'Dockerfile').write_text('FROM python:3.9')
    (project_dir / 'src').mkdir()
    (project_dir / 'src' / 'utils.js').write_text('// utils')
    (project_dir / 'dist').mkdir()
    (project_dir / 'dist' / 'bundle.js').write_text('// excluded bundle')
    (project_dir / 'error.log').write_text('log message')
    (project_dir / '.DS_Store').write_text('metadata')
    (project_dir / '.gitignore').write_text('*.log\n.DS_Store')
    return project_dir


@pytest.fixture
def base_config(project_structure):
    return EncoderConfig(
        directory=str(project_structure),
        include_ext=['.py', '.js'],
        include_files=['Dockerfile'],
        exclude_dirs=['dist'],
        exclude_exts=['.log'],
        exclude_files=['.DS_Store'],
        use_gitignore=False  # Disabled for this test to be specific
    )


def test_discover_files_with_exclusions(project_structure):
    """Test basic exclusion rules without gitignore."""
    config = EncoderConfig(
        directory=str(project_structure),
        exclude_dirs=['dist'],
        exclude_exts=['.log'],
        exclude_files=['.DS_Store']
    )
    service = EncoderService(config)
    files = service._discover_files()
    relative_files = {str(p.relative_to(project_structure)) for p in files}
    expected = {'main.py', 'Dockerfile', 'src/utils.js', '.gitignore'}
    assert relative_files == expected

def test_discover_files_with_inclusions(project_structure):
    """Test that inclusion rules correctly filter the files."""
    config = EncoderConfig(
        directory=str(project_structure),
        include_ext=['.py'],
        include_files=['Dockerfile']
    )
    service = EncoderService(config)
    files = service._discover_files()
    relative_files = {str(p.relative_to(project_structure)) for p in files}
    # Since use_gitignore is True by default, .log and .DS_Store are excluded
    expected = {'main.py', 'Dockerfile'}
    assert relative_files == expected

def test_discover_files_with_gitignore(project_structure):
    """Test that .gitignore rules are respected."""
    config = EncoderConfig(
        directory=str(project_structure),
        use_gitignore=True
    )
    service = EncoderService(config)
    files = service._discover_files()
    relative_files = {str(p.relative_to(project_structure)) for p in files}
    # .DS_Store and error.log should be ignored
    expected = {'main.py', 'Dockerfile', 'src/utils.js', 'dist/bundle.js', '.gitignore'}
    assert relative_files == expected

def test_inclusion_overrides_exclusion(project_structure):
    """Test that include rules take precedence over all exclusion rules."""
    config = EncoderConfig(
        directory=str(project_structure),
        include_files=['dist/bundle.js', 'error.log'],
        exclude_dirs=['dist'],
        use_gitignore=True  # .gitignore excludes *.log
    )
    service = EncoderService(config)
    files = service._discover_files()
    relative_files = {str(p.relative_to(project_structure)) for p in files}

    # main.py, Dockerfile, src/utils.js, .gitignore are included by default
    # dist/bundle.js is included explicitly, overriding exclude_dirs
    # error.log is included explicitly, overriding .gitignore
    expected = {'main.py', 'Dockerfile', 'src/utils.js', '.gitignore', 'dist/bundle.js', 'error.log'}
    assert relative_files == expected

def test_aggregation_no_changes(project_structure, base_config, capsys):
    """Test a second run where no files have changed."""
    # First run to establish baseline
    service1 = EncoderService(base_config)
    service1.run()

    # Second run
    service2 = EncoderService(base_config)
    service2.run()

    captured = capsys.readouterr()
    assert "No changes detected in the specified files since last run" in captured.out
