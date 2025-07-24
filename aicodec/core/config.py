# aicodec/core/config.py
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json


@dataclass
class EncoderConfig:
    """Configuration for the encoder."""
    directory: str = '.'
    output: str = 'aggregated_content.json'
    ext: List[str] = field(default_factory=list)
    file: List[str] = field(default_factory=list)
    exclude_dirs: List[str] = field(default_factory=lambda: [
                                    '.git', 'node_modules', '__pycache__', '.venv', 'dist', 'build'])
    exclude_exts: List[str] = field(
        default_factory=lambda: ['.log', '.tmp', '.bak'])
    exclude_files: List[str] = field(default_factory=lambda: ['.DS_Store'])


@dataclass
class DecoderConfig:
    """Configuration for the decoder."""
    input: Optional[str] = None
    output_dir: str = '.'


def load_config(config_path: str) -> Dict[str, Any]:
    """Loads configuration from a JSON file if it exists."""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}
