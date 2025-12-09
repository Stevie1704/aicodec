# tests/commands/test_update.py
import json
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from aicodec.infrastructure.cli.commands import update


class TestVersionComparison:
    """Test version comparison logic."""

    def test_compare_versions_older(self):
        assert update.compare_versions("2.9.0", "2.10.0") == -1
        assert update.compare_versions("1.5.3", "2.0.0") == -1
        assert update.compare_versions("2.9.9", "2.10.0") == -1

    def test_compare_versions_equal(self):
        assert update.compare_versions("2.10.0", "2.10.0") == 0
        assert update.compare_versions("1.0.0", "1.0.0") == 0

    def test_compare_versions_newer(self):
        assert update.compare_versions("2.11.0", "2.10.0") == 1
        assert update.compare_versions("3.0.0", "2.10.0") == 1
        assert update.compare_versions("2.10.1", "2.10.0") == 1

    def test_compare_versions_invalid(self, capsys):
        """Test handling of invalid version strings."""
        result = update.compare_versions("invalid", "2.10.0")
        assert result == 0
        captured = capsys.readouterr()
        assert "Could not parse version strings" in captured.err


class TestPrebuiltDetection:
    """Test detection of pre-built installations."""

    @patch("platform.system")
    @patch("pathlib.Path.exists")
    def test_is_prebuilt_install_true_linux(self, mock_exists, mock_system):
        """Test detection when pre-built binary exists on Linux."""
        mock_system.return_value = "Linux"
        mock_exists.return_value = True
        assert update.is_prebuilt_install() is True

    @patch("platform.system")
    @patch("pathlib.Path.exists")
    def test_is_prebuilt_install_true_windows(self, mock_exists, mock_system):
        """Test detection when pre-built binary exists on Windows."""
        mock_system.return_value = "Windows"
        mock_exists.return_value = True
        assert update.is_prebuilt_install() is True

    @patch("platform.system")
    @patch("pathlib.Path.exists")
    def test_is_prebuilt_install_false(self, mock_exists, mock_system):
        """Test detection when pre-built binary doesn't exist."""
        mock_system.return_value = "Linux"
        mock_exists.return_value = False
        assert update.is_prebuilt_install() is False


class TestDownloadUrlGeneration:
    """Test download URL generation for different platforms."""

    @patch("platform.system")
    @patch("platform.machine")
    def test_get_download_url_linux_amd64(self, mock_machine, mock_system):
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"
        url = update.get_download_url()
        assert url == "https://github.com/Stevie1704/aicodec/releases/latest/download/aicodec-linux-amd64.zip"

    @patch("platform.system")
    @patch("platform.machine")
    def test_get_download_url_darwin_arm64(self, mock_machine, mock_system):
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"
        url = update.get_download_url()
        assert url == "https://github.com/Stevie1704/aicodec/releases/latest/download/aicodec-darwin-arm64.zip"

    @patch("platform.system")
    @patch("platform.machine")
    def test_get_download_url_linux_arm64(self, mock_machine, mock_system):
        mock_system.return_value = "Linux"
        mock_machine.return_value = "aarch64"
        url = update.get_download_url()
        assert url == "https://github.com/Stevie1704/aicodec/releases/latest/download/aicodec-linux-arm64.zip"

    @patch("platform.system")
    @patch("platform.machine")
    def test_get_download_url_windows_amd64(self, mock_machine, mock_system):
        mock_system.return_value = "Windows"
        mock_machine.return_value = "x86_64"
        url = update.get_download_url()
        assert url == "https://github.com/Stevie1704/aicodec/releases/latest/download/aicodec-windows-amd64.zip"

    @patch("platform.system")
    @patch("platform.machine")
    def test_get_download_url_unsupported_os(self, mock_machine, mock_system, capsys):
        mock_system.return_value = "FreeBSD"
        mock_machine.return_value = "x86_64"
        url = update.get_download_url()
        assert url is None
        captured = capsys.readouterr()
        assert "Unsupported OS" in captured.err

    @patch("platform.system")
    @patch("platform.machine")
    def test_get_download_url_unsupported_arch(self, mock_machine, mock_system, capsys):
        mock_system.return_value = "Linux"
        mock_machine.return_value = "i386"
        url = update.get_download_url()
        assert url is None
        captured = capsys.readouterr()
        assert "Unsupported architecture" in captured.err


class TestGetLatestVersion:
    """Test fetching latest version from GitHub."""

    @patch("urllib.request.urlopen")
    def test_get_latest_version_success(self, mock_urlopen):
        """Test successful fetch of latest version."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"tag_name": "v2.10.0"}).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        version = update.get_latest_version()
        assert version == "2.10.0"

    @patch("urllib.request.urlopen")
    def test_get_latest_version_without_v_prefix(self, mock_urlopen):
        """Test version without 'v' prefix."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"tag_name": "2.10.0"}).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        version = update.get_latest_version()
        assert version == "2.10.0"

    @patch("urllib.request.urlopen")
    def test_get_latest_version_network_error(self, mock_urlopen, capsys):
        """Test handling of network errors."""
        mock_urlopen.side_effect = Exception("Network error")

        version = update.get_latest_version()
        assert version is None
        captured = capsys.readouterr()
        assert "Error fetching latest version" in captured.err

    @patch("urllib.request.urlopen")
    def test_get_latest_version_invalid_json(self, mock_urlopen, capsys):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"invalid json"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        version = update.get_latest_version()
        assert version is None
        captured = capsys.readouterr()
        assert "Error fetching latest version" in captured.err


class TestUpdateBinary:
    """Test the actual update process."""

    @patch("aicodec.infrastructure.cli.commands.update.get_download_url")
    def test_update_binary_no_url(self, mock_get_url):
        """Test handling when download URL cannot be determined."""
        mock_get_url.return_value = None
        result = update.update_binary()
        assert result is False

    @patch("time.sleep")
    @patch("subprocess.Popen")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("zipfile.ZipFile")
    @patch("urllib.request.urlretrieve")
    @patch("aicodec.infrastructure.cli.commands.update.get_download_url")
    @patch("aicodec.infrastructure.cli.commands.update.is_sudo_available")
    @patch("aicodec.infrastructure.cli.commands.update.can_write_to_path")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.write_text")
    @patch("os.chmod")
    def test_update_binary_success(
        self, mock_chmod, mock_write_text, mock_unlink, mock_exists, mock_can_write,
        mock_sudo_available, mock_get_url, mock_retrieve, mock_zipfile, mock_open,
        mock_popen, mock_sleep
    ):
        """Test successful update process with helper script."""
        mock_get_url.return_value = "https://example.com/aicodec.zip"
        mock_exists.return_value = True  # Simulate that the new binary was extracted
        mock_sudo_available.return_value = True  # Sudo is available
        mock_can_write.return_value = False  # Need sudo for write

        # Mock the zip file extraction
        mock_zip = MagicMock()
        mock_zip.namelist.return_value = ["aicodec"]
        mock_zip.open.return_value.__enter__.return_value.read.return_value = b"binary_content"
        mock_zipfile.return_value.__enter__.return_value = mock_zip

        # Mock file open for writing binary
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        mock_popen.return_value = MagicMock()

        result = update.update_binary()
        assert result is True

        # Verify Popen was called to launch the helper script
        assert mock_popen.called
        # Verify sleep was called (waiting before exit)
        assert mock_sleep.called

    @patch("time.sleep")
    @patch("subprocess.Popen")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("zipfile.ZipFile")
    @patch("urllib.request.urlretrieve")
    @patch("aicodec.infrastructure.cli.commands.update.get_download_url")
    @patch("aicodec.infrastructure.cli.commands.update.is_sudo_available")
    @patch("aicodec.infrastructure.cli.commands.update.can_write_to_path")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.write_text")
    @patch("os.chmod")
    def test_update_binary_no_sudo_but_has_write_permission(
        self, mock_chmod, mock_write_text, mock_unlink, mock_exists, mock_can_write,
        mock_sudo_available, mock_get_url, mock_retrieve, mock_zipfile, mock_open,
        mock_popen, mock_sleep
    ):
        """Test successful update in devcontainer (no sudo but has write permissions)."""
        mock_get_url.return_value = "https://example.com/aicodec.zip"
        mock_exists.return_value = True
        mock_sudo_available.return_value = False  # No sudo available (devcontainer)
        mock_can_write.return_value = True  # But has write permissions

        # Mock the zip file extraction
        mock_zip = MagicMock()
        mock_zip.namelist.return_value = ["aicodec"]
        mock_zip.open.return_value.__enter__.return_value.read.return_value = b"binary_content"
        mock_zipfile.return_value.__enter__.return_value = mock_zip

        # Mock file open for writing binary
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        mock_popen.return_value = MagicMock()

        result = update.update_binary()
        assert result is True

        # Verify update succeeded without sudo
        assert mock_popen.called

    @patch("aicodec.infrastructure.cli.commands.update.get_download_url")
    @patch("aicodec.infrastructure.cli.commands.update.is_sudo_available")
    @patch("aicodec.infrastructure.cli.commands.update.can_write_to_path")
    def test_update_binary_no_sudo_no_write_permission(
        self, mock_can_write, mock_sudo_available, mock_get_url, capsys
    ):
        """Test update failure when no sudo and no write permissions."""
        mock_get_url.return_value = "https://example.com/aicodec.zip"
        mock_sudo_available.return_value = False  # No sudo
        mock_can_write.return_value = False  # No write permissions

        result = update.update_binary()
        assert result is False

        captured = capsys.readouterr()
        assert "Insufficient permissions" in captured.err
        assert "sudo is not available" in captured.err


class TestUpdateCommand:
    """Test the main update command."""

    @patch("aicodec.infrastructure.cli.commands.update.is_prebuilt_install")
    def test_run_not_prebuilt(self, mock_is_prebuilt, capsys):
        """Test error when not running from pre-built binary (without --check)."""
        mock_is_prebuilt.return_value = False
        args = Namespace(check=False)

        with pytest.raises(SystemExit) as exc_info:
            update.run(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "only available for pre-built binary installations" in captured.out
        assert "pip install --upgrade aicodec" in captured.out

    @patch("aicodec.infrastructure.cli.commands.update.get_latest_version")
    @patch("aicodec.infrastructure.cli.commands.update.is_prebuilt_install")
    def test_run_check_with_pip_installation(self, mock_is_prebuilt, mock_get_latest, capsys):
        """Test --check flag works with pip installations."""
        mock_is_prebuilt.return_value = False  # Pip installation
        mock_get_latest.return_value = "2.12.0"
        args = Namespace(check=True)

        with pytest.raises(SystemExit) as exc_info:
            update.run(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "A new version is available" in captured.out
        assert "pip install --upgrade aicodec" in captured.out
        assert "aicodec update" not in captured.out  # Should not suggest binary update for pip

    @patch("aicodec.infrastructure.cli.commands.update.get_latest_version")
    @patch("aicodec.infrastructure.cli.commands.update.is_prebuilt_install")
    def test_run_already_latest(self, mock_is_prebuilt, mock_get_latest, capsys):
        """Test when already running latest version."""
        mock_is_prebuilt.return_value = True
        mock_get_latest.return_value = "2.11.4"  # Same as pyproject.toml
        args = Namespace(check=False)

        with pytest.raises(SystemExit) as exc_info:
            update.run(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "already running the latest version" in captured.out

    @patch("aicodec.infrastructure.cli.commands.update.get_latest_version")
    @patch("aicodec.infrastructure.cli.commands.update.is_prebuilt_install")
    def test_run_check_only(self, mock_is_prebuilt, mock_get_latest, capsys):
        """Test --check flag (no installation)."""
        mock_is_prebuilt.return_value = True
        mock_get_latest.return_value = "2.12.0"
        args = Namespace(check=True)

        with pytest.raises(SystemExit) as exc_info:
            update.run(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "A new version is available" in captured.out
        assert "Run 'aicodec update' to install" in captured.out

    @patch("builtins.input")
    @patch("aicodec.infrastructure.cli.commands.update.get_latest_version")
    @patch("aicodec.infrastructure.cli.commands.update.is_prebuilt_install")
    def test_run_cancelled_by_user(self, mock_is_prebuilt, mock_get_latest, mock_input, capsys):
        """Test when user cancels the update."""
        mock_is_prebuilt.return_value = True
        mock_get_latest.return_value = "2.12.0"
        mock_input.return_value = "n"
        args = Namespace(check=False)

        with pytest.raises(SystemExit) as exc_info:
            update.run(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Update cancelled" in captured.out

    @patch("aicodec.infrastructure.cli.commands.update.update_binary")
    @patch("builtins.input")
    @patch("aicodec.infrastructure.cli.commands.update.get_latest_version")
    @patch("aicodec.infrastructure.cli.commands.update.is_prebuilt_install")
    def test_run_successful_update(self, mock_is_prebuilt, mock_get_latest, mock_input, mock_update_binary, capsys):
        """Test successful update process."""
        mock_is_prebuilt.return_value = True
        mock_get_latest.return_value = "2.12.0"
        mock_input.return_value = "y"
        mock_update_binary.return_value = True
        args = Namespace(check=False)

        # Successful update exits so helper script can replace binary
        with pytest.raises(SystemExit) as exc_info:
            update.run(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "A new version is available" in captured.out

    @patch("aicodec.infrastructure.cli.commands.update.update_binary")
    @patch("builtins.input")
    @patch("aicodec.infrastructure.cli.commands.update.get_latest_version")
    @patch("aicodec.infrastructure.cli.commands.update.is_prebuilt_install")
    def test_run_update_failed(self, mock_is_prebuilt, mock_get_latest, mock_input, mock_update_binary, capsys):
        """Test when update fails."""
        mock_is_prebuilt.return_value = True
        mock_get_latest.return_value = "2.12.0"
        mock_input.return_value = "y"
        mock_update_binary.return_value = False
        args = Namespace(check=False)

        with pytest.raises(SystemExit) as exc_info:
            update.run(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Update failed" in captured.out

    @patch("aicodec.infrastructure.cli.commands.update.get_latest_version")
    @patch("aicodec.infrastructure.cli.commands.update.is_prebuilt_install")
    def test_run_cannot_check_updates(self, mock_is_prebuilt, mock_get_latest, capsys):
        """Test when unable to fetch latest version."""
        mock_is_prebuilt.return_value = True
        mock_get_latest.return_value = None
        args = Namespace(check=False)

        with pytest.raises(SystemExit) as exc_info:
            update.run(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Could not check for updates" in captured.out
