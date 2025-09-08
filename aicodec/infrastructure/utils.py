# aicodec/infrastructure/utils.py
import os
import subprocess
import sys
from pathlib import Path


def open_file_in_editor(path: str | Path) -> None:
    """Opens the given file path in the system's default application."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=True)
        else:  # Assumes Linux
            subprocess.run(["xdg-open", path], check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Could not open file editor: {e}")
        print(f"Please manually open the file at: {path}")
    except Exception as e:
        print(
            f"An unexpected error occurred while trying to open the editor: {e}")
        print(f"Please manually open the file at: {path}")
