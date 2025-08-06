# tests/test_application_services.py
import pytest
import json
import hashlib

from aicodec.application.services import AggregationService, ReviewService
from aicodec.domain.models import AggregateConfig, FileItem, ChangeSet, Change, ChangeAction
from aicodec.domain.repositories import IFileRepository, IChangeSetRepository


@pytest.fixture
def mock_file_repo(mocker):
    return mocker.Mock(spec=IFileRepository)


@pytest.fixture
def mock_change_repo(mocker):
    return mocker.Mock(spec=IChangeSetRepository)


@pytest.fixture
def temp_config(tmp_path):
    (tmp_path / '.aicodec').mkdir()
    return AggregateConfig(directory=tmp_path)


class TestAggregationService:

    def test_aggregate_no_files_found(self, mock_file_repo, temp_config, capsys):
        mock_file_repo.discover_files.return_value = []
        service = AggregationService(mock_file_repo, temp_config)
        service.aggregate()
        captured = capsys.readouterr()
        assert "No files found to aggregate" in captured.out

    def test_aggregate_full_run(self, mock_file_repo, temp_config):
        mock_file_repo.load_hashes.return_value = {'a.py': 'old_hash'}
        # Fix: discover_files must return an iterable, even if empty.
        mock_file_repo.discover_files.return_value = []
        service = AggregationService(mock_file_repo, temp_config)
        service.aggregate(full_run=True)
        # With full_run=True, load_hashes should not be called
        mock_file_repo.load_hashes.assert_not_called()

    def test_aggregate_no_changes_detected(self, mock_file_repo, temp_config, capsys):
        file_content = 'content'
        files = [FileItem('a.py', file_content)]
        # Fix: Use the correct hash for the content.
        correct_hash = hashlib.sha256(file_content.encode('utf-8')).hexdigest()
        hashes = {'a.py': correct_hash}

        mock_file_repo.discover_files.return_value = files
        mock_file_repo.load_hashes.return_value = hashes
        service = AggregationService(mock_file_repo, temp_config)
        service.aggregate()
        captured = capsys.readouterr()
        assert "No changes detected" in captured.out
        # Hashes should still be saved even if no content is written
        mock_file_repo.save_hashes.assert_called_once()

    def test_aggregate_with_changes(self, mock_file_repo, temp_config, capsys):
        files = [FileItem('a.py', 'new_content'), FileItem('b.py', 'content')]
        prev_hashes = {'a.py': 'old_hash'}
        mock_file_repo.discover_files.return_value = files
        mock_file_repo.load_hashes.return_value = prev_hashes

        service = AggregationService(mock_file_repo, temp_config)
        service.aggregate()

        output_file = temp_config.directory / '.aicodec' / 'context.json'
        assert output_file.exists()
        with open(output_file, 'r') as f:
            data = json.load(f)
        assert len(data) == 2  # both files are considered changes
        assert data[0]['filePath'] == 'a.py'
        assert data[1]['filePath'] == 'b.py'

        captured = capsys.readouterr()
        assert "Successfully aggregated 2 changed file(s)" in captured.out
        mock_file_repo.save_hashes.assert_called_once()


class TestReviewService:

    @pytest.fixture
    def review_service(self, mock_change_repo, tmp_path):
        return ReviewService(mock_change_repo, tmp_path, tmp_path / 'changes.json', 'apply')

    def test_get_review_context(self, review_service, mock_change_repo, tmp_path):
        change = Change(file_path='a.py',
                        action=ChangeAction.REPLACE, content='new')
        change_set = ChangeSet(changes=[change], summary='Test summary')
        mock_change_repo.get_change_set.return_value = change_set
        mock_change_repo.get_original_content.return_value = 'old'
        (tmp_path / 'a.py').write_text('old')

        context = review_service.get_review_context()

        assert context['summary'] == 'Test summary'
        assert len(context['changes']) == 1
        processed_change = context['changes'][0]
        assert processed_change['filePath'] == 'a.py'
        assert processed_change['action'] == 'REPLACE'

    @pytest.mark.parametrize("change_action, file_exists, original_content, proposed_content, expected_action, should_include", [
        (ChangeAction.CREATE, False, "", "new", 'CREATE', True),
        (ChangeAction.CREATE, True, "old", "new",
         'REPLACE', True),  # Effective action is REPLACE
        (ChangeAction.DELETE, True, "old", "", 'DELETE', True),
        # Cannot delete non-existent
        (ChangeAction.DELETE, False, "", "", None, False),
        (ChangeAction.REPLACE, False, "", "new",
         'CREATE', True),  # Effective action is CREATE
        (ChangeAction.REPLACE, True, "old", "new", 'REPLACE', True),
        (ChangeAction.REPLACE, True, "old", "old",
         None, False),  # No change in content
    ])
    def test_determine_effective_action(self, review_service, change_action, file_exists, original_content, proposed_content, expected_action, should_include):
        change = Change('a.py', change_action, proposed_content)
        action, include = review_service._determine_effective_action(
            change, file_exists, original_content)
        assert action == expected_action
        assert include == should_include

    def test_apply_changes(self, review_service, mock_change_repo, tmp_path):
        changes_data = [{'filePath': 'a.py',
                         'action': 'CREATE', 'content': 'new'}]
        session_id = 'test-session'
        review_service.apply_changes(changes_data, session_id)

        # Verify that the repository method is called with the correct Change object
        mock_change_repo.apply_changes.assert_called_once()
        call_args = mock_change_repo.apply_changes.call_args[0]
        assert len(call_args[0]) == 1
        assert isinstance(call_args[0][0], Change)
        assert call_args[0][0].file_path == 'a.py'
        assert call_args[1] == tmp_path
        assert call_args[2] == 'apply'
        assert call_args[3] == session_id

    def test_save_editable_changes(self, review_service, mock_change_repo):
        change_set_data = {'summary': 's', 'changes': []}
        review_service.save_editable_changes(change_set_data)
        mock_change_repo.save_change_set_from_dict.assert_called_once_with(
            review_service.changes_file, change_set_data
        )
