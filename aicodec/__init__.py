from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aicodec")
except PackageNotFoundError:
    __version__ = "0"

__all__ = ["__version__"]
