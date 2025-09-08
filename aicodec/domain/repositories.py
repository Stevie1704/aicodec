# aicodec/domain/repositories.py
from abc import ABC, abstractmethod
from pathlib import Path

from .models import AggregateConfig, Change, ChangeSet, FileItem


class IFileRepository(ABC):
    """Interface for file discovery and content retrieval."""

    @abstractmethod
    def discover_files(self, config: AggregateConfig) -> list[FileItem]:
        """Discovers all files to be included based on the configuration."""
        pass  # pragma: no cover

    @abstractmethod
    def load_hashes(self, path: Path) -> dict[str, str]:
        """Loads previously stored file hashes."""
        pass  # pragma: no cover

    @abstractmethod
    def save_hashes(self, path: Path, hashes: dict[str, str]) -> None:
        """Saves the current file hashes."""
        pass  # pragma: no cover


class IChangeSetRepository(ABC):
    """Interface for reading and writing change sets to the filesystem."""

    @abstractmethod
    def get_change_set(self, path: Path) -> ChangeSet:
        """Loads a ChangeSet from a given path."""
        pass  # pragma: no cover

    @abstractmethod
    def save_change_set_from_dict(self, path: Path, data: dict) -> None:
        """Saves a ChangeSet from a dictionary to a given path."""
        pass  # pragma: no cover

    @abstractmethod
    def get_original_content(self, path: Path) -> str:
        """Gets the current content of a file on disk."""
        pass  # pragma: no cover

    @abstractmethod
    def apply_changes(self, changes: list[Change], output_dir: Path, mode: str, session_id: str | None) -> list[dict]:
        """Applies a list of changes to the filesystem and manages revert data."""
        pass  # pragma: no cover
