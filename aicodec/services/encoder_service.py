# aicodec/services/encoder_service.py
import os
import json
from aicodec.core.config import EncoderConfig
from aicodec.core.models import FileItem


class EncoderService:
    def __init__(self, config: EncoderConfig):
        self.config = config

    def run(self):
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
                            aggregated_data.append(
                                FileItem(file_path=relative_path, content=content))
                    except Exception as e:
                        print(f"Error reading file {full_path}: {e}")

        try:
            output_data = [{'filePath': item.file_path,
                            'content': item.content} for item in aggregated_data]
            with open(self.config.output, 'w', encoding='utf-8') as outfile:
                json.dump(output_data, outfile, indent=2)
            print(
                f"Successfully aggregated {len(aggregated_data)} files into {self.config.output}")
        except IOError as e:
            print(f"Error writing to output file {self.config.output}: {e}")
