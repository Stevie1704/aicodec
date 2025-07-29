# aicodec/core/config.py
import json
from dataclasses import dataclass, field
from typing import List

@dataclass
class EncoderConfig:
    directory: str = '.'
    ext: List[str] = field(default_factory=list)
    file: List[str] = field(default_factory=list)
    exclude_dirs: List[str] = field(default_factory=list)
    exclude_exts: List[str] = field(default_factory=list)
    exclude_files: List[str] = field(default_factory=list)

@dataclass
class ReviewConfig:
    output_dir: str
    original: str
    changes: str


def load_config(path: str) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print(f"Warning: Could not parse config file at {path}")
        return {}
