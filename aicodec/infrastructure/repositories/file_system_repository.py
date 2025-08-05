# aicodec/infrastructure/repositories/file_system_repository.py
import os
import json
import fnmatch
from pathlib import Path
from typing import List, Optional
import pathspec
from datetime import datetime

from ...domain.repositories import IFileRepository, IChangeSetRepository
from ...domain.models import AggregateConfig, FileItem, ChangeSet, Change, ChangeAction


class FileSystemFileRepository(IFileRepository):
    """Manages file discovery and hashing on the local filesystem."""

    def discover_files(self, config: AggregateConfig) -> List[FileItem]:
        discovered_paths = self._discover_paths(config)
        file_items = []
        for file_path in discovered_paths:
            try:
                with open(file_path, 'rb') as f:
                    if b'\0' in f.read(1024):
                        continue  # Skip binary files

                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                relative_path = str(file_path.relative_to(config.directory))
                file_items.append(
                    FileItem(file_path=relative_path, content=content))
            except Exception as e:
                print(f"Warning: Could not read file {file_path}: {e}")
        return file_items

    def _discover_paths(self, config: AggregateConfig) -> list[Path]:
        all_files = {p for p in config.directory.rglob('*') if p.is_file()}
        gitignore_spec = self._load_gitignore_spec(config)

        explicit_includes = set()
        if config.include_dirs or config.include_ext or config.include_files:
            for path in all_files:
                rel_path_str = str(path.relative_to(config.directory))
                if any(rel_path_str.startswith(d) for d in config.include_dirs) or \
                   any(path.name.endswith(ext) for ext in config.include_ext) or \
                   any(fnmatch.fnmatch(rel_path_str, p) for p in config.include_files):
                    explicit_includes.add(path)

        if config.use_gitignore and gitignore_spec:
            base_files = {p for p in all_files if not gitignore_spec.match_file(
                str(p.relative_to(config.directory)))}
        else:
            base_files = all_files

        files_to_exclude = set()
        for path in base_files:
            rel_path_str = str(path.relative_to(config.directory))
            normalized_exclude_dirs = {
                os.path.normpath(d) for d in config.exclude_dirs}
            path_parts = {os.path.normpath(
                p) for p in path.relative_to(config.directory).parts}
            if not normalized_exclude_dirs.isdisjoint(path_parts) or \
               any(fnmatch.fnmatch(rel_path_str, p) for p in config.exclude_files) or \
               any(rel_path_str.endswith(ext) for ext in config.exclude_exts):
                files_to_exclude.add(path)

        included_by_default = base_files - files_to_exclude
        final_files_set = included_by_default | explicit_includes
        return sorted(list(final_files_set))

    def _load_gitignore_spec(self, config: AggregateConfig) -> Optional[pathspec.PathSpec]:
        if not config.use_gitignore:
            return None
        gitignore_path = config.directory / '.gitignore'
        lines = ['.aicodec']
        if gitignore_path.is_file():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                lines.extend(f.read().splitlines())
        return pathspec.PathSpec.from_lines('gitwildmatch', lines)

    def load_hashes(self, path: Path) -> dict[str, str]:
        if path.is_file():
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_hashes(self, path: Path, hashes: dict[str, str]):
        path.parent.mkdir(exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(hashes, f, indent=2)


class FileSystemChangeSetRepository(IChangeSetRepository):
    """Manages reading/writing ChangeSet data from/to the filesystem."""

    def get_change_set(self, path: Path) -> ChangeSet:
        if not path.is_file():
            return ChangeSet(changes=[], summary="")
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        changes = [Change.from_dict(c) for c in data.get('changes', [])]
        return ChangeSet(changes=changes, summary=data.get('summary'))

    def save_change_set_from_dict(self, path: Path, data: dict):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def get_original_content(self, path: Path) -> str:
        if path.exists():
            try:
                return path.read_text(encoding='utf-8')
            except Exception:
                return "<Cannot read binary file>"
        return ""

    def apply_changes(self, changes: List[Change], output_dir: Path, mode: str, session_id: Optional[str]) -> list[dict]:
        results = []
        new_revert_changes = []
        output_path_abs = output_dir.resolve()

        for change in changes:
            target_path = output_path_abs.joinpath(change.file_path).resolve()
            if output_path_abs not in target_path.parents and target_path != output_path_abs:
                results.append({'filePath': change.file_path, 'status': 'FAILURE',
                               'reason': 'Directory traversal attempt blocked.'})
                continue

            try:
                original_content_for_revert = ""
                file_existed = target_path.exists()
                if file_existed:
                    try:
                        original_content_for_revert = target_path.read_text(
                            encoding='utf-8')
                    except Exception:
                        pass

                if change.action in [ChangeAction.CREATE, ChangeAction.REPLACE]:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(change.content, encoding='utf-8')
                    if mode == 'apply':
                        revert_action = 'REPLACE' if file_existed else 'DELETE'
                        new_revert_changes.append(Change(file_path=change.file_path, action=ChangeAction(
                            revert_action), content=original_content_for_revert))

                elif change.action == ChangeAction.DELETE:
                    if file_existed:
                        target_path.unlink()
                        if mode == 'apply':
                            new_revert_changes.append(Change(
                                file_path=change.file_path, action=ChangeAction.CREATE, content=original_content_for_revert))
                    else:
                        results.append(
                            {'filePath': change.file_path, 'status': 'SKIPPED', 'reason': 'File not found for DELETE'})
                        continue

                results.append({'filePath': change.file_path,
                               'status': 'SUCCESS', 'action': change.action.value})

            except Exception as e:
                results.append({'filePath': change.file_path,
                               'status': 'FAILURE', 'reason': str(e)})

        if mode == 'apply' and new_revert_changes:
            self._save_revert_data(
                new_revert_changes, output_path_abs, session_id)

        return results

    def _save_revert_data(self, new_revert_changes: List[Change], output_dir: Path, session_id: Optional[str]):
        revert_file_dir = output_dir / '.aicodec'
        revert_file_path = revert_file_dir / 'revert.json'
        revert_file_dir.mkdir(exist_ok=True)

        # For simplicity in this refactor, we are not merging sessions. Each 'apply' is a new revert file.
        # A more advanced implementation would merge based on session_id.
        revert_data = {
            "summary": "Revert data for the last apply operation.",
            "changes": [c.__dict__ for c in new_revert_changes],
            "session_id": session_id,
            "last_updated": datetime.now().isoformat()
        }
        with open(revert_file_path, 'w', encoding='utf-8') as f:
            json.dump(revert_data, f, indent=4)
        print(
            f"Revert data for {len(new_revert_changes)} change(s) saved to {revert_file_path}")
