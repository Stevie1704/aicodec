# tests/test_infra_repositories.py
import json

import pytest

from aicodec.domain.models import AggregateConfig, Change, ChangeAction, ChangeSet
from aicodec.infrastructure.repositories.file_system_repository import (
    FileSystemChangeSetRepository,
    FileSystemFileRepository,
)


@pytest.fixture
def project_structure(tmp_path):
    project_dir = tmp_path / 'my_project'
    project_dir.mkdir()
    (project_dir / 'main.py').write_text('print("main")')
    (project_dir / 'Dockerfile').write_text('FROM python:3.9')
    (project_dir / 'src').mkdir()
    (project_dir / 'src' / 'utils.js').write_text('// utils')
    (project_dir / 'dist').mkdir()
    (project_dir / 'dist' / 'bundle.js').write_text('// excluded bundle')
    (project_dir / 'logs').mkdir()
    (project_dir / 'logs' / 'error.log').write_text('log message')
    (project_dir / 'binary.data').write_bytes(b'\x00\x01\x02')
    (project_dir / 'bad_encoding.txt').write_bytes('Euro sign: \xa4'.encode('latin1'))
    (project_dir / '.gitignore').write_text('*.log\n/dist/\nbinary.data')
    return project_dir


@pytest.fixture
def file_repo():
    return FileSystemFileRepository()


class TestFileSystemFileRepository:

    def test_discover_with_gitignore(self, project_structure, file_repo):
        config = AggregateConfig(
            directories=[project_structure], use_gitignore=True, project_root=project_structure)
        files = file_repo.discover_files(config)
        relative_files = {item.file_path for item in files}
        expected = {'main.py', 'Dockerfile', 'src/utils.js',
                    '.gitignore', 'bad_encoding.txt'}
        assert relative_files == expected

    def test_discover_with_exclusions(self, project_structure, file_repo):
        config = AggregateConfig(directories=[project_structure], exclude=[
            'src/**', '*.js'], use_gitignore=False, project_root=project_structure)
        files = file_repo.discover_files(config)
        relative_files = {item.file_path for item in files}
        assert 'src/utils.js' not in relative_files

    def test_discover_inclusion_overrides_exclusion(self, project_structure, file_repo):
        config = AggregateConfig(
            directories=[project_structure],
            include=['dist/bundle.js'],
            use_gitignore=True,
            project_root=project_structure
        )
        files = file_repo.discover_files(config)
        relative_files = {item.file_path for item in files}
        assert 'dist/bundle.js' in relative_files

    def test_discover_skip_binary_and_handle_bad_encoding(self, project_structure, file_repo, capsys):
        config = AggregateConfig(
            directories=[project_structure], use_gitignore=False, project_root=project_structure)
        files = file_repo.discover_files(config)
        relative_files = {item.file_path for item in files}
        assert 'binary.data' not in relative_files
        captured = capsys.readouterr()
        assert "Skipping binary file" in captured.out
        assert "Could not decode bad_encoding.txt as UTF-8" in captured.out
        bad_file_content = next(
            f.content for f in files if f.file_path == 'bad_encoding.txt')
        assert '\ufffd' in bad_file_content

    def test_load_and_save_hashes(self, tmp_path, file_repo):
        hashes_file = tmp_path / 'hashes.json'
        assert file_repo.load_hashes(hashes_file) == {}
        hashes_data = {'file.py': 'hash123'}
        file_repo.save_hashes(hashes_file, hashes_data)
        assert hashes_file.exists()
        assert file_repo.load_hashes(hashes_file) == hashes_data
        hashes_file.write_text("{")
        assert file_repo.load_hashes(hashes_file) == {}

    def test_discover_with_subdir(self, project_structure, file_repo):
        # Add *.js to gitignore to test exclusion
        gitignore = project_structure / '.gitignore'
        gitignore_text = gitignore.read_text() + '\n*.js'
        gitignore.write_text(gitignore_text)

        config = AggregateConfig(
            directories=[project_structure / 'src'],
            project_root=project_structure,
            use_gitignore=True
        )
        files = file_repo.discover_files(config)
        relative_files = {item.file_path for item in files}
        assert relative_files == set()  # utils.js excluded by gitignore

        # Test without gitignore
        config = AggregateConfig(
            directories=[project_structure / 'src'],
            project_root=project_structure,
            use_gitignore=False
        )
        files = file_repo.discover_files(config)
        relative_files = {item.file_path for item in files}
        assert relative_files == {'src/utils.js'}


class TestFileSystemChangeSetRepository:

    @pytest.fixture
    def change_repo(self):
        return FileSystemChangeSetRepository()

    @pytest.fixture
    def changes_file(self, tmp_path):
        file = tmp_path / 'changes.json'
        data = {
            "summary": "Test Changes",
            "changes": [
                {"filePath": "new_file.txt", "action": "CREATE", "content": "Hello"},
                {"filePath": "existing.txt", "action": "REPLACE",
                 "content": "New Content"},
                {"filePath": "to_delete.txt", "action": "DELETE", "content": ""}
            ]
        }
        file.write_text(json.dumps(data))
        return file

    def test_get_change_set(self, change_repo, changes_file):
        change_set = change_repo.get_change_set(changes_file)
        assert isinstance(change_set, ChangeSet)
        assert change_set.summary == "Test Changes"
        assert len(change_set.changes) == 3

    def test_get_original_content(self, change_repo, tmp_path):
        file = tmp_path / 'file.txt'
        file.write_text('Original')
        assert change_repo.get_original_content(file) == 'Original'
        assert change_repo.get_original_content(
            tmp_path / 'nonexistent.txt') == ''

    def test_apply_changes(self, change_repo, tmp_path):
        (tmp_path / 'existing.txt').write_text('Old Content')
        (tmp_path / 'to_delete.txt').write_text('Delete Me')

        changes = [
            Change(file_path='new_file.txt',
                   action=ChangeAction.CREATE, content='Hello'),
            Change(file_path='existing.txt',
                   action=ChangeAction.REPLACE, content='New Content'),
            Change(file_path='to_delete.txt',
                   action=ChangeAction.DELETE, content=''),
            Change(file_path='../traversal.txt',
                   action=ChangeAction.CREATE, content='danger'),
            Change(file_path='non_existent_delete.txt',
                   action=ChangeAction.DELETE, content='')
        ]

        results = change_repo.apply_changes(
            changes, tmp_path, 'apply', 'session-123')

        assert (tmp_path / 'new_file.txt').read_text() == 'Hello'
        assert (tmp_path / 'existing.txt').read_text() == 'New Content'
        assert not (tmp_path / 'to_delete.txt').exists()
        assert not (tmp_path / '../traversal.txt').exists()

        assert len(results) == 5
        assert results[0]['status'] == 'SUCCESS'
        assert results[3]['status'] == 'FAILURE'
        assert 'Directory traversal' in results[3]['reason']
        assert results[4]['status'] == 'SKIPPED'

        revert_file = tmp_path / '.aicodec' / 'revert.json'
        assert revert_file.exists()
        with revert_file.open('r') as f:
            revert_data = json.load(f)
        assert len(revert_data['changes']) == 3
        revert_actions = {c['filePath']: c['action']
                            for c in revert_data['changes']}
        assert revert_actions['new_file.txt'] == 'DELETE'
        assert revert_actions['existing.txt'] == 'REPLACE'
        assert revert_actions['to_delete.txt'] == 'CREATE'

    def test_apply_patch_action_success(self, change_repo, tmp_path):
        """Test successful application of a PATCH action."""
        # Create a file with original content
        test_file = tmp_path / 'test.py'
        original_content = """def hello():
    print("Hello")

def world():
    print("World")
"""
        test_file.write_text(original_content)

        # Create a unified diff patch that modifies the hello function
        patch_content = """--- a/test.py
+++ b/test.py
@@ -1,2 +1,2 @@
 def hello():
-    print("Hello")
+    print("Hello, Universe!")
"""

        changes = [
            Change(file_path='test.py', action=ChangeAction.PATCH,
                   content=patch_content)
        ]

        results = change_repo.apply_changes(
            changes, tmp_path, 'apply', 'patch-session-1')

        # Verify the patch was applied successfully
        assert len(results) == 1
        assert results[0]['status'] == 'SUCCESS'
        assert results[0]['action'] == 'PATCH'

        # Verify the file content was modified correctly
        patched_content = test_file.read_text()
        assert 'Hello, Universe!' in patched_content
        assert 'def world():' in patched_content
        assert 'print("Hello")' not in patched_content

        # Verify revert data was created with reverse patch
        revert_file = tmp_path / '.aicodec' / 'revert.json'
        assert revert_file.exists()
        with revert_file.open('r') as f:
            revert_data = json.load(f)
        assert len(revert_data['changes']) == 1
        # The action should be REPLACE for the revert (applying the original content)
        assert revert_data['changes'][0]['action'] == 'REPLACE'
        assert revert_data['changes'][0]['filePath'] == 'test.py'
        assert revert_data['changes'][0]['content'] == original_content
        # The reverse patch should exist and be non-empty
        assert len(revert_data['changes'][0]['content']) > 0

    def test_apply_patch_action_file_not_found(self, change_repo, tmp_path):
        """Test PATCH action on non-existent file returns SKIPPED."""
        patch_content = """--- a/missing.py
+++ b/missing.py
@@ -1,2 +1,2 @@
-old line
+new line
"""

        changes = [
            Change(file_path='missing.py',
                   action=ChangeAction.PATCH, content=patch_content)
        ]

        results = change_repo.apply_changes(
            changes, tmp_path, 'apply', 'session-skip')

        assert len(results) == 1
        assert results[0]['status'] == 'SKIPPED'
        assert 'File not found for PATCH action' in results[0]['reason']

    def test_apply_patch_action_invalid_patch(self, change_repo, tmp_path):
        """Test PATCH action with invalid patch format returns FAILURE."""
        test_file = tmp_path / 'test.py'
        test_file.write_text('def foo():\n    pass\n')

        # Invalid patch content (not a valid unified diff)
        invalid_patch = "this is not a valid patch format"

        changes = [
            Change(file_path='test.py', action=ChangeAction.PATCH,
                   content=invalid_patch)
        ]

        results = change_repo.apply_changes(
            changes, tmp_path, 'apply', 'session-invalid')

        assert len(results) == 1
        assert results[0]['status'] == 'FAILURE'
        assert 'Patch application error' in results[0]['reason']
        # File should remain unchanged
        assert test_file.read_text() == 'def foo():\n    pass\n'

    def test_apply_patch_action_content_mismatch(self, change_repo, tmp_path):
        """Test PATCH action when file content doesn't match patch expectations."""
        test_file = tmp_path / 'test.py'
        test_file.write_text('def bar():\n    return 42\n')

        # Patch expects different content than what's in the file
        mismatched_patch = """--- a/test.py
+++ b/test.py
@@ -1,2 +1,2 @@
 def foo():
-    pass
+    return 1
"""

        changes = [
            Change(file_path='test.py', action=ChangeAction.PATCH,
                   content=mismatched_patch)
        ]

        results = change_repo.apply_changes(
            changes, tmp_path, 'apply', 'session-mismatch')

        assert len(results) == 1
        assert results[0]['status'] == 'FAILURE'
        assert 'Patch application error' in results[0]['reason']
        # File should remain unchanged
        assert test_file.read_text() == 'def bar():\n    return 42\n'

    def test_apply_patch_multiline_changes(self, change_repo, tmp_path):
        """Test PATCH action with multiple hunks and complex changes."""
        test_file = tmp_path / 'complex.py'
        original_content = """class MyClass:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1

    def decrement(self):
        self.value -= 1

    def reset(self):
        self.value = 0
"""
        test_file.write_text(original_content)

        # Patch with multiple hunks
        patch_content = """--- a/complex.py
+++ b/complex.py
@@ -1,5 +1,6 @@
 class MyClass:
     def __init__(self):
         self.value = 0
+        self.name = "Counter"
 
     def increment(self):
@@ -9,4 +10,4 @@
         self.value -= 1
 
     def reset(self):
-        self.value = 0
+        self.value = None
"""

        changes = [
            Change(file_path='complex.py',
                   action=ChangeAction.PATCH, content=patch_content)
        ]

        results = change_repo.apply_changes(
            changes, tmp_path, 'apply', 'session-multi')

        assert len(results) == 1
        assert results[0]['status'] == 'SUCCESS'

        patched_content = test_file.read_text()
        assert 'self.name = "Counter"' in patched_content
        assert 'self.value = None' in patched_content
        assert 'self.value = 0' not in patched_content.split('\n')[-2]

    def test_get_patched_content_method(self, change_repo, tmp_path):
        """Test the get_patched_content method directly."""
        original = """line 1
line 2
line 3
"""
        patch = """--- a/file.txt
+++ b/file.txt
@@ -1,3 +1,3 @@
 line 1
-line 2
+line 2 modified
 line 3
"""

        patched = change_repo.get_patched_content(original, patch)
        assert patched == "line 1\nline 2 modified\nline 3\n"

    def test_get_patched_content_invalid_patch(self, change_repo):
        """Test get_patched_content with invalid patch raises exception."""
        original = "some content"
        invalid_patch = "not a patch"

        with pytest.raises(Exception) as exc_info:
            change_repo.get_patched_content(original, invalid_patch)
        assert "Error applying patch" in str(exc_info.value)

    def test_get_patched_content_mismatch(self, change_repo):
        """Test get_patched_content when patch doesn't match content."""
        original = "wrong content\n"
        patch = """--- a/file.txt
+++ b/file.txt
@@ -1,1 +1,1 @@
-expected content
+new content
"""

        with pytest.raises(Exception) as exc_info:
            change_repo.get_patched_content(original, patch)
        assert "Error applying patch" in str(exc_info.value)

    def test_apply_patch_in_revert_mode(self, change_repo, tmp_path):
        """Test that PATCH in revert mode does not create new revert data."""
        test_file = tmp_path / 'revert_test.py'
        test_file.write_text('def old():\n    pass\n')

        patch_content = """--- a/revert_test.py
+++ b/revert_test.py
@@ -1,2 +1,2 @@
-def old():
+def new():
     pass
"""

        changes = [
            Change(file_path='revert_test.py',
                   action=ChangeAction.PATCH, content=patch_content)
        ]

        results = change_repo.apply_changes(changes, tmp_path, 'revert', None)

        assert len(results) == 1
        assert results[0]['status'] == 'SUCCESS'
        # Verify no revert file was created in revert mode
        revert_file = tmp_path / '.aicodec' / 'revert.json'
        assert not revert_file.exists()

    def test_apply_mixed_actions_with_patch(self, change_repo, tmp_path):
        """Test applying a mix of CREATE, PATCH, REPLACE, and DELETE actions."""
        # Setup files
        (tmp_path / 'to_patch.py').write_text('version = 1\n')
        (tmp_path / 'to_replace.py').write_text('old content')
        (tmp_path / 'to_delete.py').write_text('delete me')

        patch_content = """--- a/to_patch.py
+++ b/to_patch.py
@@ -1,1 +1,1 @@
-version = 1
+version = 2
"""

        changes = [
            Change(file_path='new.py', action=ChangeAction.CREATE,
                   content='print("new")'),
            Change(file_path='to_patch.py',
                   action=ChangeAction.PATCH, content=patch_content),
            Change(file_path='to_replace.py',
                   action=ChangeAction.REPLACE, content='new content'),
            Change(file_path='to_delete.py',
                   action=ChangeAction.DELETE, content=''),
        ]

        results = change_repo.apply_changes(
            changes, tmp_path, 'apply', 'mixed-session')

        assert len(results) == 4
        assert all(r['status'] == 'SUCCESS' for r in results)
        assert (tmp_path / 'new.py').read_text() == 'print("new")'
        assert (tmp_path / 'to_patch.py').read_text() == 'version = 2\n'
        assert (tmp_path / 'to_replace.py').read_text() == 'new content'
        assert not (tmp_path / 'to_delete.py').exists()

        # Verify revert data
        revert_file = tmp_path / '.aicodec' / 'revert.json'
        with revert_file.open('r') as f:
            revert_data = json.load(f)
        assert len(revert_data['changes']) == 4
        actions = {c['filePath']: c['action'] for c in revert_data['changes']}
        assert actions['new.py'] == 'DELETE'
        assert actions['to_patch.py'] == 'REPLACE'
        assert actions['to_replace.py'] == 'REPLACE'
        assert actions['to_delete.py'] == 'CREATE'
