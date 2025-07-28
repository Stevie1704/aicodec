# aicodec/services/encoder_service.py
import os
import json
import hashlib
from pathlib import Path
from aicodec.core.config import EncoderConfig
from aicodec.core.models import FileItem


class EncoderService:
    def __init__(self, config: EncoderConfig):
        self.config = config
        self.aicodec_dir = Path(self.config.directory) / '.aicodec'
        self.output_path = self.aicodec_dir / 'context.json'
        self.hashes_path = self.aicodec_dir / 'hashes.json'

    def _load_previous_hashes(self):
        if self.hashes_path.exists():
            try:
                with open(self.hashes_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def run(self, full_run=False):
        previous_hashes = {} if full_run else self._load_previous_hashes()
        current_hashes = {}
        aggregated_data = []

        for dirpath, dirnames, filenames in os.walk(self.config.directory, topdown=True):
            dirnames[:] = [
                d for d in dirnames if d not in self.config.exclude_dirs]

            for filename in filenames:
                is_excluded_file = filename in self.config.exclude_files
                is_excluded_ext = any(filename.endswith(ext)
                                      for ext in self.config.exclude_exts)

                if is_excluded_file or is_excluded_ext:
                    continue

                should_include_by_name = filename in self.config.file
                should_include_by_ext = any(
                    filename.endswith(ext) for ext in self.config.ext)

                if should_include_by_name or should_include_by_ext:
                    full_path = os.path.join(dirpath, filename)
                    relative_path = os.path.relpath(
                        full_path, self.config.directory)
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='replace') as infile:
                            content = infile.read()
                            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                            current_hashes[relative_path] = content_hash

                            if previous_hashes.get(relative_path) != content_hash:
                                aggregated_data.append(
                                    FileItem(file_path=relative_path, content=content))

                    except Exception as e:
                        print(f"Error reading file {full_path}: {e}")

        try:
            self.aicodec_dir.mkdir(exist_ok=True)

            output_data = [{'filePath': item.file_path,
                            'content': item.content} for item in aggregated_data]
            
            if not aggregated_data:
                print("No file changes detected since last run.")
            else:
                with open(self.output_path, 'w', encoding='utf-8') as outfile:
                    json.dump(output_data, outfile, indent=2)
                print(
                    f"Successfully aggregated {len(aggregated_data)} changed files into {self.output_path}")

            # Always save the new, complete set of hashes
            with open(self.hashes_path, 'w', encoding='utf-8') as f:
                json.dump(current_hashes, f, indent=2)

        except IOError as e:
            print(f"Error writing to output file: {e}")
