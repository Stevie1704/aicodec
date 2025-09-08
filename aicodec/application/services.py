# aicodec/application/services.py
import hashlib
import json
from pathlib import Path

import tiktoken

from ..domain.models import AggregateConfig, Change
from ..domain.repositories import IChangeSetRepository, IFileRepository


class AggregationService:
    """Orchestrates the file aggregation use case."""

    def __init__(self, file_repo: IFileRepository, config: AggregateConfig, project_root: Path):
        self.file_repo = file_repo
        self.config = config
        self.project_root = project_root
        self.output_dir = self.project_root / '.aicodec'
        self.output_file = self.output_dir / 'context.json'
        self.hashes_file = self.output_dir / 'hashes.json'

    def aggregate(self, full_run: bool = False, count_tokens: bool = False) -> None:
        """Main execution method to aggregate files."""
        previous_hashes = {} if full_run else self.file_repo.load_hashes(
            self.hashes_file)
        discovered_files = self.file_repo.discover_files(self.config)

        if not discovered_files:
            print("No files found to aggregate based on the current configuration.")
            return

        current_hashes: dict[str, str] = {}
        aggregated_content: list[dict[str, str]] = []

        for file_item in discovered_files:
            relative_path = file_item.file_path
            content = file_item.content
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            current_hashes[relative_path] = file_hash

            if previous_hashes.get(relative_path) != file_hash:
                aggregated_content.append({
                    'filePath': relative_path,
                    'content': content
                })

        if not aggregated_content:
            print("No changes detected in the specified files since last run.")
            self.file_repo.save_hashes(self.hashes_file, {**previous_hashes, **current_hashes})
            return

        self.output_dir.mkdir(exist_ok=True)
        json_output = json.dumps(aggregated_content, indent=2)
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(json_output)

        self.file_repo.save_hashes(self.hashes_file, {**previous_hashes, **current_hashes})

        token_count_msg = ""
        if count_tokens:
            try:
                # Using cl100k_base encoding, used by gpt-4, gpt-3.5-turbo, text-embedding-ada-002
                encoding = tiktoken.get_encoding("cl100k_base")
                token_count = len(encoding.encode(json_output))
                token_count_msg = f" (Token count: {token_count})"
            except Exception as e:
                token_count_msg = f" (Token counting failed: {e})"
        
        print(
            f"Successfully aggregated {len(aggregated_content)} changed file(s) into '{self.output_file}'.{token_count_msg}"
        )


class ReviewService:
    """Orchestrates the review and application of changes."""

    def __init__(self, change_repo: IChangeSetRepository, output_dir: Path, changes_file: Path, mode: str):
        self.change_repo = change_repo
        self.output_dir = output_dir
        self.changes_file = changes_file
        self.mode = mode

    def get_review_context(self) -> dict:
        """Prepares the data required for the review UI."""
        change_set = self.change_repo.get_change_set(self.changes_file)
        processed_changes = []

        for change in change_set.changes:
            target_path = self.output_dir.resolve().joinpath(change.file_path)
            original_content = self.change_repo.get_original_content(
                target_path)

            # This logic prepares the diff view for the UI
            current_action, should_include = self._determine_effective_action(
                change, target_path.exists(), original_content
            )

            if should_include:
                processed_changes.append({
                    "filePath": change.file_path,
                    "original_content": original_content if current_action != 'CREATE' else "",
                    "proposed_content": change.content if current_action != 'DELETE' else "",
                    "action": current_action
                })

        return {
            'summary': change_set.summary or "No summary provided.",
            'changes': processed_changes,
            'mode': self.mode
        }

    def _determine_effective_action(self, change: Change, file_exists: bool, original_content: str) -> tuple[str | None, bool]:
        """Determines the actual operation based on file state."""
        action = change.action.value

        if file_exists:
            if action == 'CREATE':  # If file exists, it's a replace
                action = 'REPLACE'
            if action == 'REPLACE':
                # Don't include if content is identical
                hash_disk = hashlib.sha256(
                    original_content.encode('utf-8')).hexdigest()
                hash_proposed = hashlib.sha256(
                    change.content.encode('utf-8')).hexdigest()
                if hash_disk == hash_proposed:
                    return None, False
            return action, True
        else:  # File does not exist
            if action == 'DELETE':  # Can't delete non-existent file
                return None, False
            # Any action on a non-existent file is a CREATE
            return 'CREATE', True

    def apply_changes(self, changes_to_apply_data: list[dict], session_id: str | None) -> list[dict]:
        """Applies a list of changes to the filesystem."""
        changes_to_apply = [Change.from_dict(c) for c in changes_to_apply_data]
        return self.change_repo.apply_changes(changes_to_apply, self.output_dir, self.mode, session_id)

    def save_editable_changes(self, change_set_data: dict) -> None:
        """Saves changes from the UI back to the changes file."""
        self.change_repo.save_change_set_from_dict(
            self.changes_file, change_set_data)
