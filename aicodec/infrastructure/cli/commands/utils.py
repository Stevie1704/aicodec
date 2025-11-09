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


def fix_and_parse_ai_json(text: str) -> str | None:
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
    return text


def fix_and_parse_ai_json_new(text: str) -> dict | None:
    """
    Fixes common AI-generated JSON errors for a specific schema.

    Handles:
    - Markdown code block wrappers (```json ... ```)
    - Markdown over-escaping (e.g., \_, \*, \.)
    - Missing JSON escapes (unescaped quotes, backslashes, newlines)
    """

    # Step 1: Remove markdown code block wrappers if present
    text = text.strip()
    if text.startswith('```'):
        # Remove opening ```json or ```
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        # Remove closing ```
        text = re.sub(r'\n?```\s*$', '', text)
        text = text.strip()

    # Step 2: Fix markdown over-escaping ONLY for non-JSON-special characters
    # We do this carefully to avoid breaking legitimate JSON escapes
    markdown_escapes = {
        r'\_': '_',
        r'\*': '*',
        r'\#': '#',
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
        r'\-': '-',  # Careful with this one
        r'\.': '.',  # And this one
    }

    for escaped, unescaped in markdown_escapes.items():
        text = text.replace(escaped, unescaped)

    # Step 3: Find and fix string values in specific fields
    def fix_string_content(content: str) -> str:
        """
        Properly escape a string value for JSON.
        This processes the raw content between quotes.
        """
        result = []
        i = 0

        while i < len(content):
            char = content[i]

            # Check if this is already an escaped character
            if char == '\\' and i + 1 < len(content):
                next_char = content[i + 1]

                # Valid JSON escape sequences
                if next_char in '"\\\/bfnrtu':
                    # Keep valid escapes as-is
                    result.append(char)
                    result.append(next_char)
                    i += 2
                    continue
                else:
                    # Invalid escape - escape the backslash itself
                    result.append('\\\\')
                    i += 1
                    continue

            # Escape special characters
            if char == '"':
                result.append('\\"')
            elif char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            elif char == '\b':
                result.append('\\b')
            elif char == '\f':
                result.append('\\f')
            elif char == '\\':
                result.append('\\\\')
            else:
                result.append(char)

            i += 1

        return ''.join(result)

    # Step 4: Process summary field
    def fix_summary(match):
        prefix = match.group(1)
        content = match.group(2)
        suffix = match.group(3)
        fixed = fix_string_content(content)
        return f'{prefix}{fixed}{suffix}'

    # Match "summary": "..." where ... can contain anything including literal newlines
    summary_pattern = r'("summary"\s*:\s*")((?:[^"\\]|\\.)*)(")'
    text = re.sub(summary_pattern, fix_summary, text, flags=re.DOTALL)

    # Step 5: Process content fields
    # We need a more sophisticated approach for content fields
    # because they can be large and contain complex nested structures

    def find_and_fix_content_fields(json_text: str) -> str:
        """
        Find all "content": "..." fields and fix their content.
        Uses a character-by-character parser to handle nesting properly.
        """
        result = []
        i = 0

        while i < len(json_text):
            # Look for "content"
            if json_text[i:i+9] == '"content"':
                # Copy up to and including "content"
                result.append('"content"')
                i += 9

                # Skip whitespace and colon
                while i < len(json_text) and json_text[i] in ' \t\n\r':
                    result.append(json_text[i])
                    i += 1

                if i < len(json_text) and json_text[i] == ':':
                    result.append(':')
                    i += 1

                    # Skip whitespace after colon
                    while i < len(json_text) and json_text[i] in ' \t\n\r':
                        result.append(json_text[i])
                        i += 1

                    # Now we should be at the opening quote
                    if i < len(json_text) and json_text[i] == '"':
                        result.append('"')
                        i += 1

                        # Extract the content until the closing quote
                        content_chars = []
                        while i < len(json_text):
                            if json_text[i] == '"':
                                # Check if it's escaped
                                # Count preceding backslashes
                                num_backslashes = 0
                                j = len(content_chars) - 1
                                while j >= 0 and content_chars[j] == '\\':
                                    num_backslashes += 1
                                    j -= 1

                                # If even number of backslashes (including 0), quote is not escaped
                                if num_backslashes % 2 == 0:
                                    # This is the closing quote
                                    break

                            content_chars.append(json_text[i])
                            i += 1

                        # Fix the content
                        raw_content = ''.join(content_chars)
                        fixed_content = fix_string_content(raw_content)
                        result.append(fixed_content)

                        # Add closing quote if we found it
                        if i < len(json_text) and json_text[i] == '"':
                            result.append('"')
                            i += 1
            else:
                result.append(json_text[i])
                i += 1

        return ''.join(result)

    text = find_and_fix_content_fields(text)

    # Step 6: Try to parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print("\n--- FAILED TO PARSE JSON ---")
        print(f"Error: {e}")
        print(f"Position: Line {e.lineno}, Column {e.colno}")
        print("\n--- Context around error: ---")
        lines = text.split('\n')
        start = max(0, e.lineno - 3)
        end = min(len(lines), e.lineno + 2)
        for i in range(start, end):
            marker = ">>> " if i == e.lineno - 1 else "    "
            print(f"{marker}{i+1}: {lines[i]}")
        print("---------------------------------")
        return None


# Test with your example
if __name__ == "__main__":
    broken_json_string = """
    {
      "summary": "This is a "test" summary with an \_underscore.",
      "changes": [
        {
          "filePath": "aicodec/test_file.py",
          "action": "REPLACE",
          "content": "# This is code
    print("Hello "World"")
    path = "C:\\Users\\Test"
    f.write("\n")
    "
        },
        {
          "filePath": "another/file\\.txt",
          "action": "CREATE",
          "content": "Just a "simple" \.dot file
    with a tab:	here."
        }
      ]
    }
    """

    print("--- Fixing and Parsing AI JSON ---")
    fixed_data = fix_and_parse_ai_json(broken_json_string)

    if fixed_data:
        print("\n--- ✅ Successfully Parsed Data: ---")
        print(json.dumps(fixed_data, indent=2))
    else:
        print("\n--- ❌ Failed to parse ---")
