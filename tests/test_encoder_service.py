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
    return project_dir

@pytest.fixture
def base_config(project_structure):
    return EncoderConfig(
        directory=str(project_structure),
        ext=['.py', '.js'],
        file=['Dockerfile'],
        exclude_dirs=['dist'],
        exclude_exts=['.log'],
        exclude_files=['.DS_Store']
    )

def test_aggregation_full_initial_run(project_structure, base_config):
    """Test the first run where no hashes.json exists."""
    service = EncoderService(base_config)
    service.run()

    output_file = Path(project_structure) / '.aicodec' / 'context.json'
    hashes_file = Path(project_structure) / '.aicodec' / 'hashes.json'
    
    assert output_file.exists()
    assert hashes_file.exists()

    data = json.loads(output_file.read_text(encoding='utf-8'))
    assert len(data) == 3

    hashes_data = json.loads(hashes_file.read_text(encoding='utf-8'))
    assert len(hashes_data) == 3
    assert 'main.py' in hashes_data

def test_aggregation_no_changes(project_structure, base_config, capsys):
    """Test a second run where no files have changed."""
    # First run to establish baseline
    service1 = EncoderService(base_config)
    service1.run()

    # Second run
    service2 = EncoderService(base_config)
    service2.run()

    captured = capsys.readouterr()
    assert "No file changes detected since last run." in captured.out

def test_aggregation_with_changes(project_structure, base_config):
    """Test a run where one file has been modified."""
    # First run
    service1 = EncoderService(base_config)
    service1.run()

    # Modify a file
    (project_structure / 'main.py').write_text('print("modified main")')

    # Second run
    service2 = EncoderService(base_config)
    service2.run()

    output_file = Path(project_structure) / '.aicodec' / 'context.json'
    assert output_file.exists()
    data = json.loads(output_file.read_text(encoding='utf-8'))
    
    # Only the single changed file should be in the output
    assert len(data) == 1
    assert data[0]['filePath'] == 'main.py'
    assert data[0]['content'] == 'print("modified main")'

def test_aggregation_with_full_run_flag(project_structure, base_config):
    """Test that the --full flag forces re-aggregation of all files."""
    # First run
    service1 = EncoderService(base_config)
    service1.run()

    # Second run with --full flag, even with no changes
    service2 = EncoderService(base_config)
    service2.run(full_run=True)

    output_file = Path(project_structure) / '.aicodec' / 'context.json'
    assert output_file.exists()
    data = json.loads(output_file.read_text(encoding='utf-8'))
    
    # All files should be present in the output despite no changes
    assert len(data) == 3
