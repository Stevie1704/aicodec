# aicodec/infrastructure/config.py
import json
from pathlib import Path
from typing import Dict, Any

def load_config(path: str) -> Dict[str, Any]:
    config_path = Path(path)
    if config_path.is_file():
        with open(config_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}
