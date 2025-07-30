# aicodec/services/encoder_service.py
import os
from pathlib import Path
import hashlib
import json
import fnmatch
from typing import Optional
import pathspec
from aicodec.core.config import EncoderConfig


class EncoderService:
    def __init__(self, config: EncoderConfig):
        self.config = EncoderConfig(
            **{**config.__dict__, 'directory': Path(config.directory).resolve()}
        )
        self.output_dir = self.config.directory / '.aicodec'
        self.output_file = self.output_dir / 'context.json'
        self.hashes_file = self.output_dir / 'hashes.json'
        self.gitignore_spec = self._load_gitignore_spec()

    def _load_gitignore_spec(self) -> Optional[pathspec.PathSpec]:
        """Loads .gitignore from the project root and returns a PathSpec object."""
        if not self.config.use_gitignore:
            return None

        gitignore_path = self.config.directory / '.gitignore'
        lines = ['.aicodec']  # Always ignore the .aicodec directory
        if gitignore_path.is_file():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                lines.extend(f.read().splitlines())

        return pathspec.PathSpec.from_lines('gitwildmatch', lines)

    def _load_hashes(self) -> dict[str, str]:
        """Loads previously stored file hashes."""
        if self.hashes_file.is_file():
            with open(self.hashes_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def _save_hashes(self, hashes: dict[str, str]):
        """Saves the current file hashes."""
        self.output_dir.mkdir(exist_ok=True)
        with open(self.hashes_file, 'w', encoding='utf-8') as f:
            json.dump(hashes, f, indent=2)

    def _discover_files(self) -> list[Path]:
        """Discovers all files to be included based on the configuration."""

        files_to_consider = set()

        for root, dirs, files in os.walk(self.config.directory, topdown=True):
            root_path = Path(root)

            # Prune directories based on config and .gitignore
            dirs[:] = [d for d in dirs if d not in self.config.exclude_dirs]
            if self.gitignore_spec:
                rel_dir_paths = [
                    str((root_path / d).relative_to(self.config.directory)) for d in dirs]
                ignored_dirs = self.gitignore_spec.match_files(rel_dir_paths)
                dirs[:] = [d for d_rel, d in zip(
                    rel_dir_paths, dirs) if d_rel not in ignored_dirs]

            for file in files:
                files_to_consider.add(root_path / file)

        if self.config.use_gitignore and self.gitignore_spec:
            files_to_consider = {
                p for p in files_to_consider
                if not self.gitignore_spec.match_file(str(p.relative_to(self.config.directory)))
            }

        if self.config.ext or self.config.files:
            included_by_rules = set()
            if self.config.ext:
                for path in files_to_consider:
                    if any(path.name.endswith(ext) for ext in self.config.ext):
                        included_by_rules.add(path)
            if self.config.files:
                for pattern in self.config.files:
                    for path in files_to_consider:
                        if fnmatch.fnmatch(str(path.relative_to(self.config.directory)), pattern):
                            included_by_rules.add(path)
            files_to_consider = files_to_consider | included_by_rules

        final_files = []
        for path in sorted(list(files_to_consider)):
            rel_path_str = str(path.relative_to(self.config.directory))

            if any(fnmatch.fnmatch(rel_path_str, p) for p in self.config.exclude_files):
                continue
            if any(rel_path_str.endswith(ext) for ext in self.config.exclude_exts):
                continue
            if any(part in self.config.exclude_dirs for part in path.parts):
                continue

            final_files.append(path)

        return final_files

    def run(self, full_run: bool = False):
        """Main execution method to aggregate files."""
        previous_hashes = {} if full_run else self._load_hashes()
        discovered_files = self._discover_files()

        if not discovered_files:
            print("No files found to aggregate based on the current configuration.")
            return

        current_hashes: dict[str, str] = {}
        aggregated_content: list[dict[str, str]] = []

        for file_path in discovered_files:
            try:
                with open(file_path, 'rb') as f:
                    if b'\0' in f.read(1024):
                        continue

                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                relative_path = str(
                    file_path.relative_to(self.config.directory))
                current_hashes[relative_path] = file_hash

                if previous_hashes.get(relative_path) != file_hash:
                    aggregated_content.append({
                        'filePath': relative_path,
                        'content': content
                    })
            except Exception as e:
                print(f"Warning: Could not read or hash file {file_path}: {e}")

        if not aggregated_content:
            print("No changes detected in the specified files since last run.")
            self._save_hashes(current_hashes)
            return

        self.output_dir.mkdir(exist_ok=True)
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(aggregated_content, f, indent=2)

        self._save_hashes(current_hashes)
        print(
            f"Successfully aggregated {len(aggregated_content)} changed file(s) into '{self.output_file}'."
        )
