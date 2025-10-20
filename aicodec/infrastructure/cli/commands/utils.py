# aicodec/infrastructure/cli/commands/utils.py
import json
import re
import sys
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


def clean_json_string(s: str) -> str:
    """
    Cleans a string intended for JSON parsing.

    1. Replaces actual non-breaking spaces (\u00a0 or \xa0) with regular spaces.
    2. Replaces the literal text "\\u00a0" with a regular space.
    3. Removes problematic ASCII control characters (0-8, 11-12, 14-31, 127)
       while preserving tab (\t), newline (\n), and carriage return (\r).
    """

    # 1. Replace the actual non-breaking space character with a regular space
    s = re.sub(r'\xa0', ' ', s)

    # 2. Replace the literal text sequence "\\u00a0" with a regular space
    # (The first \ escapes the second \ for the regex)
    s = re.sub(r'\\u00a0', ' ', s)

    # 3. Remove other control characters, preserving \t, \n, \r
    #    (Ranges: 0-8, 11-12, 14-31, and 127)
    s = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', s)

    return s
