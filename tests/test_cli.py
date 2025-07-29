# tests/test_cli.py
import pytest
import sys
from pathlib import Path
from aicodec import cli

# Test aicodec-aggregate


def test_aggregate_main_with_args(mocker):
    mocker.patch.object(
        sys, 'argv', ['aicodec-aggregate', '--ext', 'py', '-d', '/tmp/project'])
    mock_service = mocker.patch('aicodec.cli.EncoderService')
    cli.aggregate_main()
    mock_service.assert_called_once()
    # Check that the config passed to the service is correct
    config_arg = mock_service.call_args[0][0]
    assert config_arg.directory == '/tmp/project'
    assert '.py' in config_arg.ext


def test_aggregate_main_no_inclusions(mocker):
    mocker.patch.object(sys, 'argv', ['aicodec-aggregate'])
    mocker.patch('aicodec.cli.load_config', return_value={})
    with pytest.raises(SystemExit):
        cli.aggregate_main()

# Test aicodec-apply (now review_and_apply_main)


def test_review_and_apply_main_with_args(mocker):
    """Verify that the main review function calls the server launcher with correct args."""
    # Mock the function that launches the web server
    mock_launch_server = mocker.patch('aicodec.cli.launch_review_server')

    # Mock command-line arguments
    mocker.patch.object(sys, 'argv', [
        'aicodec-apply',
        '--output-dir', '/path/to/project',
        '--original', '/path/to/context.json',
        '--changes', '/path/to/changes.json'
    ])

    # Run the main function
    cli.review_and_apply_main()

    # Assert that the server launcher was called with the correctly parsed Path objects
    mock_launch_server.assert_called_once_with(
        Path('/path/to/project'),
        Path('/path/to/context.json'),
        Path('/path/to/changes.json')
    )
