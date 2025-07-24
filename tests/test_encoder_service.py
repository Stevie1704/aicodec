# tests/test_encoder_service.py
import pytest
import os
import json
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

def test_aggregation_full(project_structure):
    output_file = project_structure.parent / 'output.json'
    config = EncoderConfig(
        directory=str(project_structure),
        output=str(output_file),
        ext=['.py', '.js'],
        file=['Dockerfile'],
        exclude_dirs=['dist'],
        exclude_exts=['.log'],
        exclude_files=['.DS_Store']
    )
    service = EncoderService(config)
    service.run()

    assert output_file.exists()
    data = json.loads(output_file.read_text(encoding='utf-8'))
    assert len(data) == 3
    result_paths = sorted([item['filePath'] for item in data])
    expected_paths = sorted([
        os.path.join('my_project', 'main.py'),
        os.path.join('my_project', 'src', 'utils.js'),
        os.path.join('my_project', 'Dockerfile')
    ])
    assert result_paths == expected_paths

def test_encoder_io_error(project_structure, mocker):
    """Test that an IOError during file writing is handled."""
    mocker.patch("builtins.open", side_effect=IOError("Disk full"))
    mock_print = mocker.patch("builtins.print")
    config = EncoderConfig(directory=str(project_structure), ext=['.py'])
    service = EncoderService(config)
    service.run()
    mock_print.assert_any_call(f"Error writing to output file {config.output}: Disk full")