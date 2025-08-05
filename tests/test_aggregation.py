# tests/test_aggregation.py
import pytest
from pathlib import Path

from aicodec.domain.models import AggregateConfig
from aicodec.application.services import AggregationService
from aicodec.infrastructure.repositories.file_system_repository import FileSystemFileRepository


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
    (project_dir / 'logs').mkdir()
    (project_dir / 'logs' / 'error.log').write_text('log message')
    (project_dir / '.DS_Store').write_text('metadata')
    (project_dir / '.gitignore').write_text('*.log\n.DS_Store\n/dist/\nlogs/')
    return project_dir


@pytest.fixture
def file_repo():
    return FileSystemFileRepository()


def test_discover_files_with_exclusions(project_structure, file_repo):
    """Test basic exclusion rules without gitignore."""
    config = AggregateConfig(
        directory=project_structure,
        exclude_dirs=['dist', 'logs'],
        exclude_exts=['.log'],
        exclude_files=['.DS_Store'],
        use_gitignore=False
    )
    files = file_repo.discover_files(config)
    relative_files = {item.file_path for item in files}
    expected = {'main.py', 'Dockerfile', 'src/utils.js', '.gitignore'}
    assert relative_files == expected


def test_discover_files_with_inclusions(project_structure, file_repo):
    """Test that inclusion rules correctly filter the files."""
    config = AggregateConfig(
        directory=project_structure,
        include_ext=['.py'],
        include_files=['Dockerfile'],
        use_gitignore=True
    )
    files = file_repo.discover_files(config)
    relative_files = {item.file_path for item in files}
    expected = {'main.py', 'Dockerfile'}
    assert relative_files == expected


def test_discover_files_with_gitignore(project_structure, file_repo):
    """Test that .gitignore rules are respected."""
    config = AggregateConfig(
        directory=project_structure,
        use_gitignore=True
    )
    files = file_repo.discover_files(config)
    relative_files = {item.file_path for item in files}
    expected = {'main.py', 'Dockerfile', 'src/utils.js', '.gitignore'}
    assert relative_files == expected


def test_inclusion_overrides_exclusion(project_structure, file_repo):
    """Test that include rules take precedence over all exclusion rules."""
    config = AggregateConfig(
        directory=project_structure,
        include_dirs=['logs'],
        include_files=['dist/bundle.js'],
        exclude_dirs=['dist'],
        use_gitignore=True
    )
    files = file_repo.discover_files(config)
    relative_files = {item.file_path for item in files}
    expected = {'main.py', 'Dockerfile', 'src/utils.js',
                '.gitignore', 'dist/bundle.js', 'logs/error.log'}
    assert relative_files == expected


def test_aggregation_no_changes(project_structure, file_repo, capsys):
    """Test a second run where no files have changed."""
    config = AggregateConfig(directory=project_structure, use_gitignore=True)

    # First run to establish baseline
    service1 = AggregationService(file_repo, config)
    service1.aggregate()

    # Second run
    service2 = AggregationService(file_repo, config)
    service2.aggregate()

    captured = capsys.readouterr()
    assert "No changes detected in the specified files since last run" in captured.out
