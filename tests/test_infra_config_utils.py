# tests/test_infra_config_utils.py
import json
import os
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

    def test_open_file_in_editor_vscode(self, monkeypatch):
        """Tests that the 'code' command is used when TERM_PROGRAM is vscode."""
        monkeypatch.setenv("TERM_PROGRAM", "vscode")
        with patch("subprocess.run") as mock_run:
            result = open_file_in_editor("test.txt")
            assert result is True
            mock_run.assert_called_once_with(
                ["code", "test.txt"], check=True, capture_output=True)

    @pytest.mark.parametrize("platform, mock_function, expected_call", [
        ("win32", "os.startfile", ["test.txt"]),
        ("darwin", "subprocess.run", ["open", "test.txt"]),
        ("linux", "subprocess.run", ["xdg-open", "test.txt"]),
    ])
    def test_open_file_in_editor_platforms(self, platform, mock_function, expected_call):
        """Tests the correct command is called for each platform."""
        # Ensure we don't hit the vscode path by clearing the env var
        with patch.dict(os.environ, {}, clear=True):
            with patch("sys.platform", platform):
                with patch(f"aicodec.infrastructure.utils.{mock_function}", create=True) as mock_call:
                    open_file_in_editor("test.txt")
                    if "subprocess" in mock_function:
                        mock_call.assert_called_once_with(
                            expected_call, check=True, capture_output=True)
                    else:
                        mock_call.assert_called_once_with(*expected_call)

    @pytest.mark.parametrize("error_type", [
        FileNotFoundError,
        subprocess.CalledProcessError,
        OSError,
        Exception,
    ])
    def test_open_file_in_editor_exceptions(self, capsys, error_type):
        """Tests that the function returns False and does not print on any exception."""
        # Prepare a side effect, instantiating exceptions that require arguments
        side_effect = error_type
        if error_type is subprocess.CalledProcessError:
            side_effect = error_type(1, 'cmd')
        with patch("sys.platform", "linux"):
            with patch("subprocess.run", side_effect=side_effect):
                result = open_file_in_editor("test.txt")
                # Assert the function signals failure and remains silent
                assert result is False
                captured = capsys.readouterr()
                assert captured.out == ""
                assert captured.err == ""
