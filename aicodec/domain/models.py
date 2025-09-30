# aicodec/domain/models.py
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ChangeAction(Enum):
    CREATE = "CREATE"
    REPLACE = "REPLACE"
    DELETE = "DELETE"


@dataclass
class FileItem:
    """Represents a file in the codebase with its content."""
    file_path: str  # Relative path
    content: str


@dataclass
class Change:
    """Represents a single file change operation."""
    file_path: str
    action: ChangeAction
    content: str

    @classmethod
    def from_dict(cls, data: dict) -> "Change":
        return cls(
            file_path=data['filePath'],
            action=ChangeAction(data['action'].upper()),
            content=data.get('content', '')
        )


@dataclass
class ChangeSet:
    """Container for a set of changes with metadata."""
    changes: list[Change]
    summary: str | None = None


@dataclass
class AggregateConfig:
    """Configuration value object for the aggregation process."""
    directories: list[Path]
    include_dirs: list[str] = field(default_factory=list)
    include_ext: list[str] = field(default_factory=list)
    include_files: list[str] = field(default_factory=list)
    exclude_dirs: list[str] = field(default_factory=list)
    exclude_exts: list[str] = field(default_factory=list)
    exclude_files: list[str] = field(default_factory=list)
    use_gitignore: bool = True
    project_root: Path = field(default_factory=Path.cwd)
