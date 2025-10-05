from argparse import Namespace
from unittest.mock import patch

from aicodec.infrastructure.cli.commands import prepare


def test_prepare_run_from_clipboard_pyperclip_exception(sample_project, aicodec_config_file, monkeypatch, capsys):
    """Tests that a clipboard error falls back to opening an editor."""
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        changes=None,
        from_clipboard=True
    )

    # When pyperclip.paste() raises an exception, the app should fall back
    # to calling open_file_in_editor. We must mock both.
    with patch('aicodec.infrastructure.cli.commands.prepare.pyperclip.paste') as mock_paste, \
         patch('aicodec.infrastructure.cli.commands.prepare.open_file_in_editor') as mock_open:
        
        # Dynamically get the exception type to avoid import errors if pyperclip is not installed
        class DummyExc(Exception):
            pass
        try:
            from pyperclip import PyperclipException
            exc_type = PyperclipException
        except ImportError:
            exc_type = DummyExc

        mock_paste.side_effect = exc_type("No clipboard found")
        prepare.run(args)

    captured = capsys.readouterr()
    assert "Warning: Clipboard access failed" in captured.out
    assert "Falling back to creating an empty file" in captured.out

    # Verify that the fallback to open an editor was triggered
    mock_open.assert_called_once()
