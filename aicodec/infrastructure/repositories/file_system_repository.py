# aicodec/infrastructure/repositories/file_system_repository.py
import fnmatch
import json
import os
from datetime import datetime
from pathlib import Path

import pathspec

from ...domain.models import AggregateConfig, Change, ChangeAction, ChangeSet, FileItem
from ...domain.repositories import IChangeSetRepository, IFileRepository


class FileSystemFileRepository(IFileRepository):
    """Manages file discovery and hashing on the local filesystem."""

    def discover_files(self, config: AggregateConfig) -> list[FileItem]:
        discovered_paths = self._discover_paths(config)
        file_items = []
        for file_path in discovered_paths:
            try:
                # Simple binary file check to avoid reading large binary files into memory
                with open(file_path, 'rb') as f:
                    if b'\0' in f.read(1024):
                        print(f"Skipping binary file: {file_path}")
                        continue

                # Try to read with strict UTF-8, fall back to replace on error
                try:
                    with open(file_path, encoding='utf-8', errors='strict') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    relative_path_str = str(
                        file_path.relative_to(config.project_root))
                    print(
                        f"Warning: Could not decode {relative_path_str} as UTF-8. Reading with replacement characters.")
                    with open(file_path, encoding='utf-8', errors='replace') as f:
                        content = f.read()

                relative_path = str(file_path.relative_to(config.project_root))
                file_items.append(
                    FileItem(file_path=relative_path, content=content))
            except Exception as e:
                print(f"Warning: Could not read file {file_path}: {e}")
        return file_items

    def _discover_paths(self, config: AggregateConfig) -> list[Path]:
        project_root = config.project_root
        all_files = set()
        for directory in config.directories:
            all_files.update({p for p in directory.rglob('*') if p.is_file()})

        # Bug Fix: Always exclude the .aicodec directory, regardless of gitignore settings.
        # The tool should never aggregate its own internal files.
        always_exclude_spec = pathspec.PathSpec.from_lines(
            'gitwildmatch', ['**/.aicodec/*'])
        all_files = {p for p in all_files if not always_exclude_spec.match_file(
            str(p.relative_to(project_root)))}

        gitignore_spec = self._load_gitignore_spec(config)
        normalized_include_dirs = {
            os.path.normpath(d) for d in config.include_dirs}
        explicit_includes = set()
        if config.include_dirs or config.include_ext or config.include_files:
            for path in all_files:
                rel_path = path.relative_to(project_root)
                rel_path_str = str(rel_path)
                if self._file_inside_directory(rel_path, normalized_include_dirs) or \
                    any(path.name.endswith(ext) for ext in config.include_ext) or \
                    any(fnmatch.fnmatch(rel_path_str, p) for p in config.include_files):
                    explicit_includes.add(path)

        if config.use_gitignore and gitignore_spec:
            base_files = {p for p in all_files if not gitignore_spec.match_file(
                str(p.relative_to(project_root)))}
        else:
            base_files = all_files

        files_to_exclude = set()
        for path in base_files:
            rel_path_str = str(path.relative_to(project_root))
            normalized_exclude_dirs = {
                os.path.normpath(d) for d in config.exclude_dirs}
            relative_path = path.relative_to(project_root)

            # Efficiently check if any part of the path is in the exclusion set
            if self._file_inside_directory(relative_path, normalized_exclude_dirs) or \
                any(fnmatch.fnmatch(rel_path_str, p) for p in config.exclude_files) or \
                any(rel_path_str.endswith(ext) for ext in config.exclude_exts):
                files_to_exclude.add(path)

        included_by_default = base_files - files_to_exclude
        final_files_set = included_by_default | explicit_includes
        return sorted(list(final_files_set))

    def _load_gitignore_spec(self, config: AggregateConfig) -> pathspec.PathSpec | None:
        if not config.use_gitignore:
            return None
        gitignore_path = config.project_root / '.gitignore'
        lines = []
        if gitignore_path.is_file():
            with open(gitignore_path, encoding='utf-8') as f:
                lines.extend(f.read().splitlines())
        return pathspec.PathSpec.from_lines('gitwildmatch', lines)

    def load_hashes(self, path: Path) -> dict[str, str]:
        if path.is_file():
            with open(path, encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    @staticmethod
    def _file_inside_directory(file_path: Path, directories: set[Path]) -> bool:
        """Check if a file is inside any of the specified directories."""
        return any(file_path.is_relative_to(d) for d in directories)

    def save_hashes(self, path: Path, hashes: dict[str, str]) -> None:
        path.parent.mkdir(exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(hashes, f, indent=2)


class FileSystemChangeSetRepository(IChangeSetRepository):
    """Manages reading/writing ChangeSet data from/to the filesystem."""

    def get_change_set(self, path: Path) -> ChangeSet:
        if not path.is_file():
            return ChangeSet(changes=[], summary="")
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        changes = [Change.from_dict(c) for c in data.get('changes', [])]
        return ChangeSet(changes=changes, summary=data.get('summary'))

    def save_change_set_from_dict(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def get_original_content(self, path: Path) -> str:
        if path.exists():
            try:
                return path.read_text(encoding='utf-8')
            except Exception:
                return "<Cannot read binary file>"
        return ""

    def apply_changes(self, changes: list[Change], output_dir: Path, mode: str, session_id: str | None) -> list[dict]:
        results = []
        new_revert_changes = []
        output_path_abs = output_dir.resolve()

        for change in changes:
            target_path = output_path_abs.joinpath(change.file_path).resolve()
            # Security: Prevent directory traversal attacks
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
                        # For binary files, we can't revert content but can revert the action
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

    def _save_revert_data(self, new_revert_changes: list[Change], output_dir: Path, session_id: str | None) -> None:
        if not session_id:
            session_id = f"revert-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        revert_dir = output_dir / '.aicodec'
        revert_dir.mkdir(parents=True, exist_ok=True)
        revert_file_path = revert_dir / "revert.json"

        revert_changes_as_dicts = []
        for c in new_revert_changes:
            revert_changes_as_dicts.append({
                "filePath": c.file_path,
                "action": c.action.value,
                "content": c.content
            })

        revert_data = {
            "summary": f"Revert data for apply session {session_id}.",
            "changes": revert_changes_as_dicts,
            "session_id": session_id,
            "last_updated": datetime.now().isoformat()
        }

        with open(revert_file_path, 'w', encoding='utf-8') as f:
            json.dump(revert_data, f, indent=4)

        print(
            f"Revert data for {len(new_revert_changes)} change(s) saved to {revert_file_path}")
