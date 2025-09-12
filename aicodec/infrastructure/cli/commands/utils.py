# aicodec/infrastructure/cli/commands/utils.py
import json
import sys
from importlib.resources import files
from pathlib import Path


def get_user_confirmation(prompt: str, default_yes: bool = True) -> bool:
    """Generic function to get a yes/no confirmation from the user."""
    options = "[Y/n]" if default_yes else "[y/N]"
    while True:
        response = input(f"{prompt} {options} ").lower().strip()
        if not response:
            return default_yes
        if response in ["y", "yes"]:
            return True
        if response in ["n", "no"]:
            return False
        print("Invalid input. Please enter 'y' or 'n'.")


def get_list_from_user(prompt: str) -> list[str]:
    """Gets a comma-separated list of items from the user."""
    response = input(
        f"{prompt} (comma-separated, press Enter to skip): ").strip()
    if not response:
        return []
    return [item.strip() for item in response.split(",")]


def load_default_prompt_template(minimal: bool) -> str:
    """Loads the default prompt template from the package data."""
    try:
        prompt_dir = files("aicodec") / "assets" / "prompts"
        if minimal:
            prompt_template = prompt_dir / "minimal.txt"
        else:
            prompt_template = prompt_dir / "full.txt"
        return prompt_template.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(
            "Error: prompt template not found. The package might be corrupted.",
            file=sys.stderr,
        )
        sys.exit(1)


def parse_json_file(file_path: Path) -> str:
    """Reads and returns the content of a JSON file as a formatted string."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return json.dumps(json.loads(content), separators=(',', ':'))
    except FileNotFoundError:
        print(f"Error: JSON file '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(
            f"Error: Failed to parse JSON file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)
