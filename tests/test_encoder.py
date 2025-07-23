# test_encoder.py

import pytest
import os
import json
from aicodec.encoder import aggregate_files_to_json, load_config


@pytest.fixture
def project_structure(tmp_path):
    """
    A pytest fixture that creates a temporary directory with a file structure
    to test various inclusion/exclusion scenarios.
    """
    project_dir = tmp_path / 'my_project'
    project_dir.mkdir()

    # Create files and dirs using the modern pathlib API
    (project_dir / 'main.py').write_text('print("main")')
    (project_dir / 'Dockerfile').write_text('FROM python:3.9')
    (project_dir / 'src').mkdir()
    (project_dir / 'src' / 'utils.js').write_text('// utils')

    # Files and dirs that should be excluded
    (project_dir / 'dist').mkdir()
    (project_dir / 'dist' / 'bundle.js').write_text('// excluded bundle')
    (project_dir / 'error.log').write_text('log message')
    (project_dir / '.DS_Store').write_text('metadata')

    return project_dir


def test_aggregation_include_ext_and_file(project_structure):
    """
    Tests aggregation based on a mix of file extensions and specific filenames.
    Also tests directory, file, and extension exclusion.
    """
    output_file = project_structure.parent / 'output.json'
    config = {
        'dir': str(project_structure),
        'output': str(output_file),
        'ext': ['.py', '.js'],
        'file': ['Dockerfile'],
        'exclude_dirs': ['dist'],
        'exclude_exts': ['.log'],
        'exclude_files': ['.DS_Store']
    }

    aggregate_files_to_json(config)

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

    dockerfile_data = next(
        item for item in data if item['filePath'].endswith('Dockerfile'))
    assert dockerfile_data['content'] == 'FROM python:3.9'


def test_exclusion_priority(project_structure):
    """
    Tests that an excluded file is not included, even if its extension is
    in the inclusion list.
    """
    output_file = project_structure.parent / 'output.json'
    config = {
        'dir': str(project_structure),
        'output': str(output_file),
        'ext': ['.js'],
        'file': [],
        'exclude_dirs': [],
        'exclude_exts': [],
        # Exclude a file that would normally be included
        'exclude_files': ['utils.js']
    }
    aggregate_files_to_json(config)

    data = json.loads(output_file.read_text(encoding='utf-8'))
    assert len(data) == 1


def test_load_config_file(tmp_path):
    """
    Tests the load_config function with an existing and non-existing file.
    """
    config_path = tmp_path / 'test.config.json'
    config_data = {"ext": [".py"], "output": "test_output.json"}
    config_path.write_text(json.dumps(config_data), encoding='utf-8')

    # Test loading an existing config file
    loaded_config = load_config(str(config_path))
    assert loaded_config == config_data

    # Test loading a non-existent config file
    config_path.unlink()
    loaded_config = load_config(str(config_path))
    assert loaded_config == {}
