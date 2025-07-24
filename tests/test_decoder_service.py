# tests/test_decoder_service.py
import pytest
import os
import json
from aicodec.core.config import DecoderConfig
from aicodec.services.decoder_service import DecoderService


@pytest.fixture
def temp_output_dir(tmp_path):
    return tmp_path


@pytest.fixture
def changes_file(tmp_path):
    changes_data = {
        "summary": "Test changes",
        "changes": [
            {
                "filePath": "new_file.txt",
                "action": "CREATE",
                "content": "Hello World!"
            },
            {
                "filePath": "existing_file.txt",
                "action": "REPLACE",
                "content": "New content"
            },
            {
                "filePath": "file_to_delete.txt",
                "action": "DELETE",
                "content": ""
            },
            {
                "filePath": "non_existent_to_delete.txt",
                "action": "DELETE",
                "content": ""
            }
        ]
    }
    file_path = tmp_path / "changes.json"
    file_path.write_text(json.dumps(changes_data))
    return file_path


@pytest.fixture
def setup_output_dir(temp_output_dir):
    (temp_output_dir / "existing_file.txt").write_text("Old content")
    (temp_output_dir / "file_to_delete.txt").write_text("This will be deleted")
    return temp_output_dir


def test_decoder_run(changes_file, setup_output_dir):
    config = DecoderConfig(input=str(changes_file),
                           output_dir=str(setup_output_dir))
    service = DecoderService(config)
    service.run(auto_confirm=True)
    assert (setup_output_dir / "new_file.txt").exists()
    assert (setup_output_dir / "new_file.txt").read_text() == "Hello World!"
    assert (setup_output_dir / "existing_file.txt").read_text() == "New content"
    assert not (setup_output_dir / "file_to_delete.txt").exists()


def test_decoder_dry_run(changes_file, setup_output_dir, capsys):
    config = DecoderConfig(input=str(changes_file),
                           output_dir=str(setup_output_dir))
    service = DecoderService(config)
    service.run(dry_run=True)
    captured = capsys.readouterr()
    assert "Dry run complete" in captured.out
    assert not (setup_output_dir / "new_file.txt").exists()


def test_decoder_user_cancel(changes_file, setup_output_dir, mocker):
    mocker.patch("builtins.input", return_value="n")
    config = DecoderConfig(input=str(changes_file),
                           output_dir=str(setup_output_dir))
    service = DecoderService(config)
    service.run()
    assert not (setup_output_dir / "new_file.txt").exists()


def test_decoder_file_not_found(capsys):
    config = DecoderConfig(input="non_existent_file.json")
    service = DecoderService(config)
    service.run()
    captured = capsys.readouterr()
    assert "Error: Could not find a required file" in captured.out


def test_decoder_json_decode_error(tmp_path):
    bad_json_file = tmp_path / "bad.json"
    bad_json_file.write_text("{ not valid json }")
    config = DecoderConfig(input=str(bad_json_file))
    service = DecoderService(config)

    # We expect service.run() to handle the error internally and not raise an exception
    # It should simply print an error and return.
    with pytest.raises(json.JSONDecodeError):
        service.run()
