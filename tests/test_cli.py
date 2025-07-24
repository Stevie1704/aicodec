# tests/test_cli.py
import pytest
import sys
from aicodec import cli

# Test ai-encode
def test_encode_main_with_args(mocker):
    mocker.patch.object(sys, 'argv', ['ai-encode', '--ext', 'py', '-o', 'test.json'])
    mock_service = mocker.patch('aicodec.cli.EncoderService')
    cli.encode_main()
    mock_service.assert_called_once()
    # Check that the config passed to the service is correct
    config_arg = mock_service.call_args[0][0]
    assert config_arg.output == 'test.json'
    assert '.py' in config_arg.ext

def test_encode_main_no_inclusions(mocker):
    mocker.patch.object(sys, 'argv', ['ai-encode'])
    mocker.patch('aicodec.cli.load_config', return_value={})
    with pytest.raises(SystemExit):
        cli.encode_main()

# Test ai-decode
def test_decode_main_with_args(mocker):
    mocker.patch.object(sys, 'argv', ['ai-decode', '-i', 'changes.json', '--yes'])
    mock_service = mocker.patch('aicodec.cli.DecoderService')
    cli.decode_main()
    mock_service.assert_called_once()
    config_arg = mock_service.call_args[0][0]
    assert config_arg.input == 'changes.json'

def test_decode_main_from_config(mocker):
    mocker.patch.object(sys, 'argv', ['ai-decode', '--yes'])
    mocker.patch('aicodec.cli.load_config', return_value={'decoder': {'input': 'cfg_changes.json'}})
    mock_service = mocker.patch('aicodec.cli.DecoderService')
    cli.decode_main()
    mock_service.assert_called_once()
    config_arg = mock_service.call_args[0][0]
    assert config_arg.input == 'cfg_changes.json'

def test_decode_main_no_input(mocker):
    mocker.patch.object(sys, 'argv', ['ai-decode'])
    mocker.patch('aicodec.cli.load_config', return_value={})
    with pytest.raises(SystemExit):
        cli.decode_main()