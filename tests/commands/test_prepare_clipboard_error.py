from argparse import Namespace
from unittest.mock import patch

from aicodec.infrastructure.cli.commands import prepare


def test_prepare_run_from_clipboard_pyperclip_exception(sample_project, aicodec_config_file, monkeypatch, capsys):
    monkeypatch.chdir(sample_project)

    args = Namespace(
        config=str(aicodec_config_file),
        changes=None,
        from_clipboard=True
    )

    with patch('aicodec.infrastructure.cli.commands.prepare.pyperclip.paste') as mock_paste:
        class DummyExc(Exception):
            pass
        # Use actual PyperclipException if available
        try:
            from pyperclip import PyperclipException
            exc_type = PyperclipException
        except Exception:
            exc_type = DummyExc
        mock_paste.side_effect = exc_type("No clipboard found")
        prepare.run(args)

    captured = capsys.readouterr()
    assert "Clipboard access failed" in captured.out
