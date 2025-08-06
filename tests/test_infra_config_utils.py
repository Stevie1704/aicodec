# tests/test_infra_config_utils.py
import pytest
import json
import subprocess

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
        ("darwin", "subprocess.run", [["open", "test.txt"]]),
        ("linux", "subprocess.run", [["xdg-open", "test.txt"]]),
    ])
    def test_open_file_in_editor_platforms(self, mocker, platform, mock_function, expected_call):
        mocker.patch("sys.platform", platform)
        # Fix: Add create=True to prevent AttributeError when patching a platform-specific function.
        mock_call = mocker.patch(
            f"aicodec.infrastructure.utils.{mock_function}", create=True)

        open_file_in_editor("test.txt")

        if "subprocess" in mock_function:
            mock_call.assert_called_once_with(expected_call[0], check=True)
        else:
            mock_call.assert_called_once_with(expected_call[0])

    @pytest.mark.parametrize("error_type, error_args", [
        (FileNotFoundError, ["Test error"]),
        # Fix: Provide the required 'cmd' and 'returncode' arguments for CalledProcessError.
        (subprocess.CalledProcessError, [1, "cmd", "Test error"]),
        (Exception, ["Test error"])
    ])
    def test_open_file_in_editor_exceptions(self, mocker, capsys, error_type, error_args):
        mocker.patch("sys.platform", "linux")
        mocker.patch("subprocess.run", side_effect=error_type(*error_args))

        open_file_in_editor("test.txt")

        captured = capsys.readouterr()
        assert "Could not open file" in captured.out or "An unexpected error occurred" in captured.out
        assert "Please manually open the file" in captured.out
