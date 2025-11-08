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


def fix_and_parse_ai_json(text: str) -> dict | None:
    """
    Fixes common AI-generated JSON errors for a specific schema.

    1. Fixes Markdown "over-escaping" (e.g., \_) globally.
    2. Fixes JSON "under-escaping" (e.g., unescaped ", \, newlines)
       only within the "summary" and "content" string values.
    """

    # 1. Fix all Markdown "over-escaping" globally.
    markdown_escapes = {
        r'\_': '_',
        r'\*': '*',
        r'\.': '.',
        r'\#': '#',
        r'\-': '-',
        r'\+': '+',
        r'\!': '!',
        r'\`': '`',
        r'\[': '[',
        r'\]': ']',
        r'\(': '(',
        r'\)': ')',
        r'\{': '{',
        r'\}': '}',
        r'\>': '>',
        r'\|': '|',
    }

    for escaped, unescaped in markdown_escapes.items():
        text = text.replace(escaped, unescaped)

    # 2. Define a replacer function for targeted fields.
    def fix_string_value_replacer(match):
        """
        Takes a regex match and fixes the 'content' group (group 2).
        """
        pre = match.group(1)
        content = match.group(2)
        post = match.group(3)

        # --- Start Fixes ---

        # NEW STEP (A): Escape control characters.
        # This MUST run before fixing backslashes.
        # Order matters: \r\n must become \\r\\n (or just do \r then \n)
        fixed_content = content.replace('\r', '\\r')
        fixed_content = fixed_content.replace('\n', '\\n')
        fixed_content = fixed_content.replace('\t', '\\t')

        # STEP (B): Fix unescaped backslashes.
        # Replace any \ that is NOT followed by a valid JSON escape char.
        # This now correctly ignores the \\n, \\r, \\t we just created.
        fixed_content = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', fixed_content)

        # STEP (C): Fix unescaped double-quotes.
        # Replace any " that is NOT preceded by a \
        fixed_content = re.sub(r'(?<!\\)"', r'\"', fixed_content)

        # --- End Fixes ---

        return f"{pre}{fixed_content}{post}"

    # 3. Define regex patterns for the fields that need fixing.
    try:
        # Pattern for "summary"
        summary_regex = re.compile(
            r'("summary":\s*")(.*?)("\s*,\s*"changes")',
            re.DOTALL
        )

        # Pattern for "content"
        # This regex is now more "greedy" to capture the end correctly
        content_regex = re.compile(
            r'("content":\s*")(.*?)("\s*(?:,|\}))',
            re.DOTALL
        )

        # 4. Run the targeted replacements
        text = summary_regex.sub(fix_string_value_replacer, text)
        text = content_regex.sub(fix_string_value_replacer, text)

    except Exception as e:
        print(f"Error during regex replacement: {e}")
        return None

    # 5. Parse the fully corrected string
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print("\n--- FAILED TO PARSE JSON ---")
        print(f"Error: {e}")
        return None
