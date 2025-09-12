# tests/test_infra_config_utils.py
import json
import subprocess
from unittest.mock import patch

import pytest

from aicodec.infrastructure.config import load_config
from aicodec.infrastructure.utils import open_file_in_editor


class TestConfigLoader:

    def test_load_config_success(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_data = {"key": "value"}
        config_file.write_text(json.dumps(config_data))

        config = load_config(str(config_file))
        assert config == config_data

    def test_load_config_not_found(self):
        config = load_config("non_existent_file.json")
        assert config == {}

    def test_load_config_malformed_json(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("not a json string")

        config = load_config(str(config_file))
        assert config == {}


class TestUtils:

    @pytest.mark.parametrize("platform, mock_function, expected_call", [
        ("win32", "os.startfile", ["test.txt"]),
        ("darwin", "subprocess.run", ["open", "test.txt"]),
        ("linux", "subprocess.run", ["xdg-open", "test.txt"]),
    ])
    def test_open_file_in_editor_platforms(self, platform, mock_function, expected_call):
        with patch("sys.platform", platform):
            with patch(f"aicodec.infrastructure.utils.{mock_function}", create=True) as mock_call:
                open_file_in_editor("test.txt")

                if "subprocess" in mock_function:
                    mock_call.assert_called_once_with(expected_call, check=True)
                else:
                    mock_call.assert_called_once_with(*expected_call)

    @pytest.mark.parametrize("error_type, error_args", [
        (FileNotFoundError, ["Test error"]),
        (subprocess.CalledProcessError, [1, "cmd", "Test error"]),
        (Exception, ["Test error"])
    ])
    def test_open_file_in_editor_exceptions(self, capsys, error_type, error_args):
        with patch("sys.platform", "linux"):
            with patch("subprocess.run", side_effect=error_type(*error_args)):
                open_file_in_editor("test.txt")

                captured = capsys.readouterr()
                assert "Could not open file" in captured.out or "An unexpected error occurred" in captured.out
                assert "Please manually open the file" in captured.out
