import json
import os
from importlib.resources import files
from pathlib import Path
from typing import Any

import pyperclip
from jsonschema import ValidationError, validate

from ...config import load_config as load_json_config
from ...utils import open_file_in_editor
from .utils import get_user_confirmation


def register_subparser(subparsers: Any) -> None:
    prep_parser = subparsers.add_parser(
        "prepare",
        help="Prepare the changes file, either by opening an editor or from clipboard.",
    )
    prep_parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=".aicodec/config.json",
        help="Path to the config file.",
    )
    prep_parser.add_argument(
        "--changes",
        type=Path,
        help="Path to the LLM changes JSON file (overrides config).",
    )
    prep_parser.add_argument(
        "--from-clipboard",
        action="store_true",
        help="Paste content directly from the system clipboard.",
    )
    prep_parser.set_defaults(func=run)


def run(args: Any) -> None:
    file_cfg = load_json_config(args.config).get("prepare", {})
    changes_path_str = args.changes or file_cfg.get(
        "changes", ".aicodec/changes.json")
    changes_path = Path(changes_path_str)

    # Prioritize CLI flag, then config file, then default to False
    if args.from_clipboard:
        from_clipboard = True
    else:
        from_clipboard = file_cfg.get("from_clipboard", False)

    if changes_path.exists() and changes_path.stat().st_size > 0:
        if not get_user_confirmation(
            f'The file "{changes_path}" already has content. Overwrite?',
            default_yes=False,
        ):
            print("Operation cancelled.")
            return

    changes_path.parent.mkdir(parents=True, exist_ok=True)

    if from_clipboard:
        try:
            if os.environ.get('AICODEC_TEST_MODE'):
                clipboard_content = os.environ.get('AICODEC_TEST_CLIPBOARD', '')
            else:
                clipboard_content = pyperclip.paste()
        except pyperclip.PyperclipException as e:
            print(f"Error: Clipboard access failed: {e}")
            return

        if not clipboard_content:
            print("Error: Clipboard is empty.")
            return
        try:
            schema_path = files("aicodec") / "assets" / "decoder_schema.json"
            schema_content = schema_path.read_text(encoding="utf-8")
            schema = json.loads(schema_content)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: Could not load the internal JSON schema. {e}")
            return

        try:
            json_content = json.loads(clipboard_content)
            validate(instance=json_content, schema=schema)
        except json.JSONDecodeError:
            print(
                "Error: Clipboard content is not valid JSON. Please copy the correct output."
            )
            return
        except ValidationError as e:
            print(
                f"Error: Clipboard content does not match the expected schema. {e.message}"
            )
            return
        changes_path.write_text(clipboard_content, encoding="utf-8")
        print(
            f'Successfully wrote content from clipboard to "{changes_path}".')
    else:
        changes_path.touch()
        print(
            f'Successfully created empty file at "{changes_path}". Opening in default editor...'
        )
        open_file_in_editor(changes_path)
