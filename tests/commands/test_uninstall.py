# tests/commands/test_uninstall.py
from argparse import Namespace
from unittest.mock import patch

import pytest

from aicodec.infrastructure.cli.commands import uninstall


class TestUninstallScript:
    """Test uninstall script creation."""

    def test_create_uninstall_script_unix_with_sudo(self, tmp_path):
        """Test creation of Unix uninstall script with sudo."""
        binary_path = tmp_path / "aicodec"
        binary_path.write_text("dummy")

        with patch("platform.system", return_value="Linux"):
            script_path = uninstall.create_uninstall_script(
                binary_path=binary_path,
                install_dir=tmp_path,
                symlink_path=None,
                needs_sudo=True,
                sudo_available=True
            )

        assert script_path.exists()
        assert script_path.name == "uninstall_helper.sh"
        content = script_path.read_text()
        assert "sudo rm -f" in content
        assert str(binary_path) in content
        assert "aicodec has been uninstalled successfully" in content

    def test_create_uninstall_script_unix_without_sudo(self, tmp_path):
        """Test creation of Unix uninstall script without sudo."""
        binary_path = tmp_path / "aicodec"
        binary_path.write_text("dummy")

        with patch("platform.system", return_value="Linux"):
            script_path = uninstall.create_uninstall_script(
                binary_path=binary_path,
                install_dir=tmp_path,
                symlink_path=None,
                needs_sudo=False,
                sudo_available=False
            )

        assert script_path.exists()
        content = script_path.read_text()
        # Should not have sudo prefix when not needed
        assert "sudo rm" not in content
        assert "rm -f" in content

    def test_create_uninstall_script_unix_with_symlink(self, tmp_path):
        """Test creation of Unix uninstall script with symlink removal."""
        binary_path = tmp_path / "opt" / "aicodec"
        binary_path.parent.mkdir(parents=True)
        binary_path.write_text("dummy")
        symlink_path = tmp_path / "bin" / "aicodec"
        symlink_path.parent.mkdir(parents=True)
        symlink_path.symlink_to(binary_path)

        with patch("platform.system", return_value="Linux"):
            script_path = uninstall.create_uninstall_script(
                binary_path=binary_path,
                install_dir=binary_path.parent,
                symlink_path=symlink_path,
                needs_sudo=False,
                sudo_available=False
            )

        assert script_path.exists()
        content = script_path.read_text()
        assert str(symlink_path) in content
        assert "Remove symlink if it exists" in content

    def test_create_uninstall_script_windows(self, tmp_path):
        """Test creation of Windows uninstall script."""
        binary_path = tmp_path / "aicodec.exe"
        binary_path.write_text("dummy")

        with patch("platform.system", return_value="Windows"):
            script_path = uninstall.create_uninstall_script(
                binary_path=binary_path,
                install_dir=tmp_path,
                symlink_path=None,
                needs_sudo=False,
                sudo_available=False
            )

        assert script_path.exists()
        assert script_path.name == "uninstall_helper.ps1"
        content = script_path.read_text()
        assert "Remove-Item" in content
        assert str(binary_path) in content


class TestPerformUninstall:
    """Test the uninstall process."""

    @patch("aicodec.infrastructure.cli.commands.uninstall.get_running_binary_path")
    def test_perform_uninstall_binary_not_found(self, mock_get_path, capsys):
        """Test uninstall when binary is not found."""
        mock_get_path.return_value = (None, None)

        result = uninstall.perform_uninstall()

        assert result is False
        captured = capsys.readouterr()
        assert "Could not find aicodec binary" in captured.err

    @patch("time.sleep")
    @patch("subprocess.Popen")
    @patch("aicodec.infrastructure.cli.commands.uninstall.create_uninstall_script")
    @patch("aicodec.infrastructure.cli.commands.uninstall.can_write_to_path")
    @patch("aicodec.infrastructure.cli.commands.uninstall.is_sudo_available")
    @patch("aicodec.infrastructure.cli.commands.uninstall.get_running_binary_path")
    @patch("platform.system")
    def test_perform_uninstall_success_linux(
        self, mock_system, mock_get_path, mock_sudo_available,
        mock_can_write, mock_create_script, mock_popen, mock_sleep, tmp_path
    ):
        """Test successful uninstall on Linux."""
        mock_system.return_value = "Linux"
        binary_path = tmp_path / "aicodec"
        binary_path.write_text("dummy")
        mock_get_path.return_value = (binary_path, None)
        mock_can_write.return_value = True
        mock_sudo_available.return_value = False
        mock_create_script.return_value = tmp_path / "uninstall_helper.sh"

        result = uninstall.perform_uninstall()

        assert result is True
        assert mock_popen.called
        assert mock_sleep.called

    @patch("aicodec.infrastructure.cli.commands.uninstall.can_write_to_path")
    @patch("aicodec.infrastructure.cli.commands.uninstall.is_sudo_available")
    @patch("aicodec.infrastructure.cli.commands.uninstall.get_running_binary_path")
    @patch("platform.system")
    def test_perform_uninstall_no_permissions(
        self, mock_system, mock_get_path, mock_sudo_available, mock_can_write, tmp_path, capsys
    ):
        """Test uninstall failure when no permissions and no sudo."""
        mock_system.return_value = "Linux"
        binary_path = tmp_path / "aicodec"
        binary_path.write_text("dummy")
        mock_get_path.return_value = (binary_path, None)
        mock_can_write.return_value = False
        mock_sudo_available.return_value = False

        result = uninstall.perform_uninstall()

        assert result is False
        captured = capsys.readouterr()
        assert "Insufficient permissions" in captured.err


class TestUninstallCommand:
    """Test the main uninstall command."""

    @patch("aicodec.infrastructure.cli.commands.uninstall.is_prebuilt_install")
    def test_run_not_prebuilt(self, mock_is_prebuilt, capsys):
        """Test error when not running from pre-built binary."""
        mock_is_prebuilt.return_value = False
        args = Namespace(force=False)

        with pytest.raises(SystemExit) as exc_info:
            uninstall.run(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "only available for pre-built binary installations" in captured.out
        assert "pip uninstall aicodec" in captured.out

    @patch("aicodec.infrastructure.cli.commands.uninstall.get_running_binary_path")
    @patch("aicodec.infrastructure.cli.commands.uninstall.is_prebuilt_install")
    def test_run_binary_not_found(self, mock_is_prebuilt, mock_get_path, capsys):
        """Test error when binary cannot be found."""
        mock_is_prebuilt.return_value = True
        mock_get_path.return_value = (None, None)
        args = Namespace(force=False)

        with pytest.raises(SystemExit) as exc_info:
            uninstall.run(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Could not find aicodec binary" in captured.err

    @patch("builtins.input")
    @patch("aicodec.infrastructure.cli.commands.uninstall.get_running_binary_path")
    @patch("aicodec.infrastructure.cli.commands.uninstall.is_prebuilt_install")
    def test_run_cancelled_by_user(self, mock_is_prebuilt, mock_get_path, mock_input, tmp_path, capsys):
        """Test when user cancels the uninstall."""
        mock_is_prebuilt.return_value = True
        binary_path = tmp_path / "aicodec"
        binary_path.write_text("dummy")
        mock_get_path.return_value = (binary_path, None)
        mock_input.return_value = "n"
        args = Namespace(force=False)

        with pytest.raises(SystemExit) as exc_info:
            uninstall.run(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Uninstall cancelled" in captured.out

    @patch("aicodec.infrastructure.cli.commands.uninstall.perform_uninstall")
    @patch("builtins.input")
    @patch("aicodec.infrastructure.cli.commands.uninstall.get_running_binary_path")
    @patch("aicodec.infrastructure.cli.commands.uninstall.is_prebuilt_install")
    def test_run_successful_uninstall(
        self, mock_is_prebuilt, mock_get_path, mock_input, mock_perform, tmp_path, capsys
    ):
        """Test successful uninstall process."""
        mock_is_prebuilt.return_value = True
        binary_path = tmp_path / "aicodec"
        binary_path.write_text("dummy")
        mock_get_path.return_value = (binary_path, None)
        mock_input.return_value = "y"
        mock_perform.return_value = True
        args = Namespace(force=False)

        with pytest.raises(SystemExit) as exc_info:
            uninstall.run(args)

        assert exc_info.value.code == 0

    @patch("aicodec.infrastructure.cli.commands.uninstall.perform_uninstall")
    @patch("aicodec.infrastructure.cli.commands.uninstall.get_running_binary_path")
    @patch("aicodec.infrastructure.cli.commands.uninstall.is_prebuilt_install")
    def test_run_force_flag_skips_confirmation(
        self, mock_is_prebuilt, mock_get_path, mock_perform, tmp_path
    ):
        """Test that --force flag skips confirmation prompt."""
        mock_is_prebuilt.return_value = True
        binary_path = tmp_path / "aicodec"
        binary_path.write_text("dummy")
        mock_get_path.return_value = (binary_path, None)
        mock_perform.return_value = True
        args = Namespace(force=True)

        # Should not ask for input with --force
        with pytest.raises(SystemExit) as exc_info:
            uninstall.run(args)

        assert exc_info.value.code == 0
        # perform_uninstall should be called without any input prompt
        assert mock_perform.called

    @patch("aicodec.infrastructure.cli.commands.uninstall.perform_uninstall")
    @patch("builtins.input")
    @patch("aicodec.infrastructure.cli.commands.uninstall.get_running_binary_path")
    @patch("aicodec.infrastructure.cli.commands.uninstall.is_prebuilt_install")
    def test_run_uninstall_failed(
        self, mock_is_prebuilt, mock_get_path, mock_input, mock_perform, tmp_path, capsys
    ):
        """Test when uninstall fails."""
        mock_is_prebuilt.return_value = True
        binary_path = tmp_path / "aicodec"
        binary_path.write_text("dummy")
        mock_get_path.return_value = (binary_path, None)
        mock_input.return_value = "y"
        mock_perform.return_value = False
        args = Namespace(force=False)

        with pytest.raises(SystemExit) as exc_info:
            uninstall.run(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Uninstall failed" in captured.err

    @patch("builtins.input")
    @patch("aicodec.infrastructure.cli.commands.uninstall.get_running_binary_path")
    @patch("aicodec.infrastructure.cli.commands.uninstall.is_prebuilt_install")
    def test_run_shows_symlink_in_removal_list(
        self, mock_is_prebuilt, mock_get_path, mock_input, tmp_path, capsys
    ):
        """Test that symlink is shown in the removal list when applicable."""
        mock_is_prebuilt.return_value = True
        binary_path = tmp_path / "real" / "aicodec"
        binary_path.parent.mkdir(parents=True)
        binary_path.write_text("dummy")
        symlink_path = tmp_path / "bin" / "aicodec"
        symlink_path.parent.mkdir(parents=True)
        symlink_path.symlink_to(binary_path)
        mock_get_path.return_value = (binary_path, symlink_path)
        mock_input.return_value = "n"  # Cancel to avoid needing more mocks
        args = Namespace(force=False)

        with pytest.raises(SystemExit):
            uninstall.run(args)

        captured = capsys.readouterr()
        assert "Symlink:" in captured.out
        assert str(symlink_path) in captured.out
