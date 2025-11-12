# aicodec/infrastructure/repositories/file_system_repository.py
import json
import os
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

import pathspec

from ...domain.models import AggregateConfig, Change, ChangeAction, ChangeSet, FileItem
from ...domain.repositories import IChangeSetRepository, IFileRepository


class FileSystemFileRepository(IFileRepository):
    """Manages file discovery and hashing on the local filesystem."""

    def discover_files(self, config: AggregateConfig) -> list[FileItem]:
        discovered_paths = self._discover_paths(config)
        plugin_map = {
            ext: cmd for plugin in config.plugins for ext, cmd in plugin.items()
        }
        file_items = []

        for file_path in discovered_paths:
            relative_path = os.path.relpath(
                file_path, config.project_root).replace(os.sep, '/')
            file_ext = f".{file_path.name.split('.')[-1]}" if '.' in file_path.name else None

            try:
                content = None
                # Check if a plugin is configured for this file extension
                if file_ext and file_ext in plugin_map:
                    command_template = plugin_map[file_ext]
                    
                    try:
                        # Build the command list safely
                        cmd_list = shlex.split(command_template)
                        for i, arg in enumerate(cmd_list):
                            if "{file}" in arg:
                                cmd_list[i] = arg.replace("{file}", str(file_path))

                        result = subprocess.run(
                            cmd_list,
                            shell=False,
                            capture_output=True,
                            text=True,
                            check=True,
                            encoding='utf-8'
                        )
                        # The content is simply the raw output of the plugin
                        content = result.stdout.strip()
                    except subprocess.CalledProcessError as e:
                        print(
                            f"Warning: Plugin for {file_ext} failed on {relative_path}: {e.stderr}")
                        continue
                    except FileNotFoundError as e:
                        print(f"Warning: Command not found for plugin {file_ext}: {e}")
                        continue

                # If no plugin was run, fall back to reading as a text file
                else:
                    # Simple binary file check
                    with open(file_path, 'rb') as f:
                        if b'\0' in f.read(1024):
                            print(f"Skipping binary file: {relative_path}")
                            continue

                    try:
                        with open(file_path, encoding='utf-8', errors='strict') as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        print(
                            f"Warning: Could not decode {relative_path} as UTF-8. Reading with replacement characters.")
                        with open(file_path, encoding='utf-8', errors='replace') as f:
                            content = f.read()

                if content is not None:
                    file_items.append(
                        FileItem(file_path=relative_path, content=content))

            except Exception as e:
                print(f"Warning: Could not process file {relative_path}: {e}")

        return file_items

    def _discover_paths(self, config: AggregateConfig) -> list[Path]:
        project_root = config.project_root
        all_files = set()
        for directory in config.directories:
            all_files.update({p for p in directory.rglob('*') if p.is_file()})

        # Apply gitignore first, if enabled
        if config.use_gitignore:
            gitignore_spec = self._load_gitignore_spec(config)
            if gitignore_spec:
                base_files = {p for p in all_files if not gitignore_spec.match_file(
                    os.path.relpath(p, project_root))}
            else:
                base_files = all_files
        else:
            base_files = all_files

        # Apply explicit excludes from config, plus hardcoded ones.
        # These patterns are gitignore-style.
        exclude_patterns = config.exclude + ['.aicodec/**', '.git/**']
        exclude_spec = pathspec.PathSpec.from_lines(
            'gitwildmatch', exclude_patterns)

        files_after_exclusion = {p for p in base_files if not exclude_spec.match_file(
            os.path.relpath(p, project_root))}

        # Apply explicit includes, which can bring back excluded files.
        explicit_includes = set()
        if config.include:
            include_spec = pathspec.PathSpec.from_lines(
                'gitwildmatch', config.include)
            # We check against all_files, so includes can override all excludes.
            explicit_includes = {p for p in all_files if include_spec.match_file(
                os.path.relpath(p, project_root))}

        final_files_set = files_after_exclusion | explicit_includes
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
