# tests/test_domain_models.py
from pathlib import Path

import pytest

from aicodec.domain.models import AggregateConfig, Change, ChangeAction, ChangeSet, FileItem


def test_change_from_dict_full():
    """Tests creating a Change object from a standard dictionary."""
    data = {
        'filePath': 'src/main.py',
        'action': 'REPLACE',
        'content': 'print("hello")'
    }
    change = Change.from_dict(data)
    assert isinstance(change, Change)
    assert change.file_path == 'src/main.py'
    assert change.action == ChangeAction.REPLACE
    assert change.content == 'print("hello")'

def test_change_from_dict_delete_action():
    """Tests creating a Change object for a DELETE action where content can be empty."""
    data = {
        'filePath': 'src/old.py',
        'action': 'DELETE',
        'content': ''
    }
    change = Change.from_dict(data)
    assert change.file_path == 'src/old.py'
    assert change.action == ChangeAction.DELETE
    assert change.content == ''

def test_change_from_dict_missing_content_key():
    """Tests that content defaults to an empty string if the key is missing."""
    data = {
        'filePath': 'src/another.py',
        'action': 'CREATE'
    }
    change = Change.from_dict(data)
    assert change.file_path == 'src/another.py'
    assert change.action == ChangeAction.CREATE
    assert change.content == ''

def test_change_from_dict_case_insensitivity():
    """Tests that the action value is correctly parsed regardless of case."""
    data = {
        'filePath': 'src/main.py',
        'action': 'replace',
        'content': 'print("hello")'
    }
    change = Change.from_dict(data)
    assert change.action == ChangeAction.REPLACE

def test_change_from_dict_invalid_action():
    """Tests that an invalid action string raises a ValueError."""
    data = {
        'filePath': 'src/main.py',
        'action': 'INVALID_ACTION',
        'content': 'print("hello")'
    }
    with pytest.raises(ValueError):
        Change.from_dict(data)

def test_dataclass_instantiation():
    """Ensures all domain models can be instantiated correctly."""
    file_item = FileItem(file_path="a/b.py", content="test")
    assert file_item.file_path == "a/b.py"

    change = Change(file_path="a/b.py", action=ChangeAction.CREATE, content="new")
    assert change.action == ChangeAction.CREATE

    change_set = ChangeSet(changes=[change], summary="A test summary")
    assert change_set.summary == "A test summary"
    assert len(change_set.changes) == 1

    agg_config = AggregateConfig(directories=[Path(".")])
    assert agg_config.directories == [Path(".")]
    assert agg_config.use_gitignore is True
