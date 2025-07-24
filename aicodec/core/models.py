# aicodec/core/models.py
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class ChangeAction(Enum):
    CREATE = "CREATE"
    REPLACE = "REPLACE"
    DELETE = "DELETE"


@dataclass
class FileItem:
    """Represents a file in the codebase with its metadata."""
    file_path: str
    content: str


@dataclass
class Change:
    """Represents a single file change."""
    file_path: str
    action: ChangeAction
    content: str


@dataclass
class ChangeSet:
    """Container for a set of changes with metadata."""
    changes: List[Change]
    summary: Optional[str] = None
