# aicodec/core/config.py
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EncoderConfig:
    directory: str | Path
    include_dirs: list[str] = field(default_factory=list)
    include_ext: list[str] = field(default_factory=list)
    include_files: list[str] = field(default_factory=list)
    exclude_dirs: list[str] = field(default_factory=list)
    exclude_exts: list[str] = field(default_factory=list)
    exclude_files: list[str] = field(default_factory=list)
    use_gitignore: bool = True


def load_config(path: str) -> dict:
    config_path = Path(path)
    if config_path.is_file():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}
