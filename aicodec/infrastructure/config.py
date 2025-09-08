# aicodec/infrastructure/config.py
import json
from pathlib import Path
from typing import Any


def load_config(path: str) -> dict[str, Any]:
    config_path = Path(path)
    if config_path.is_file():
        with open(config_path, encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}
