import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _get_version() -> str:
    """Determine the version of aicodec.

    For pre-built binaries (frozen/compiled), reads from a VERSION file
    in the same directory as the executable.
    For pip installations, uses importlib.metadata.
    """
    # Check if we're running as a frozen binary (PyInstaller, Nuitka, etc.)
    is_frozen = getattr(sys, 'frozen', False)
    executable_name = Path(sys.executable).name.lower()
    is_compiled_binary = 'python' not in executable_name and 'aicodec' in executable_name

    if is_frozen or is_compiled_binary:
        # For frozen binaries, look for VERSION file next to the executable
        if is_frozen:
            # PyInstaller: use sys._MEIPASS or executable directory
            base_path = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
        else:
            # Nuitka or other: use executable directory
            base_path = Path(sys.executable).parent

        version_file = base_path / "VERSION"
        if version_file.exists():
            try:
                return version_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass

    # Fall back to importlib.metadata for pip installations
    try:
        return version("aicodec")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _get_version()
__all__ = ["__version__"]
