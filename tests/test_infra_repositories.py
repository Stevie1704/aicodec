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
