# aicodec/infrastructure/utils.py
import os
import subprocess
import sys
from pathlib import Path


def open_file_in_editor(path: str | Path) -> bool:
    """Tries to open the given file path and returns True on success, False on failure."""
    path_str = str(path)

    # Prioritize VS Code's 'code' command if available (common in devcontainers)
    if os.environ.get("TERM_PROGRAM") == "vscode":
        try:
            subprocess.run(["code", path_str], check=True, capture_output=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            print(
                "Tried to use the 'code' command but it failed. Falling back to system default.")

    # Fallback to system-specific commands
    try:
        if sys.platform == "win32":
            os.startfile(path_str)
            return True
        elif sys.platform == "darwin":
            subprocess.run(["open", path_str], check=True, capture_output=True)
            return True
        else:  # Assumes Linux
            subprocess.run(["xdg-open", path_str],
                           check=True, capture_output=True)
            return True
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        # OSError can be raised by xdg-open in headless environments
        # Suppress printing the error here, as the caller will handle the message.
        return False
    except Exception:
        return False
