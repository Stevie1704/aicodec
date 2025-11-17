# aicodec/infrastructure/cli/commands/utils.py
import json
import re
import sys
from importlib.resources import files
from pathlib import Path

from jsonschema import ValidationError, validate


class JsonPreparationError(Exception):
    pass


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
    response = input(f"{prompt} (comma-separated, press Enter to skip): ").strip()
    if not response:
        return []
    return [item.strip() for item in response.split(",")]


def parse_json_file(file_path: Path) -> str:
    """Reads and returns the content of a JSON file as a formatted string."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return json.dumps(json.loads(content), separators=(",", ":"))
    except FileNotFoundError:
        print(f"Error: JSON file '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)


def _schema_aware_json_fix(text: str) -> str:
    """
    Schema-aware JSON fixing for the decoder_schema.json structure.

    Expected structure:
    {
        "summary": "...",
        "changes": [
            {"filePath": "...", "action": "...", "content": "..."},
            ...
        ]
    }

    This function handles unescaped quotes in summary and content fields by:
    1. Parsing the JSON structure character by character
    2. Identifying field boundaries using JSON structural characters
    3. Escaping quotes within string values
    """
    import re

    # First apply basic cleaning
    text = clean_json_string(text)

    # State machine to track where we are in the JSON structure
    result = []
    i = 0

    def skip_whitespace(pos):
        """Skip whitespace and return next non-whitespace position"""
        while pos < len(text) and text[pos] in ' \t\n\r':
            result.append(text[pos])
            pos += 1
        return pos

    def read_and_fix_string_value(pos, field_name=None):
        """
        Read a JSON string value starting at pos (after opening ").
        Escape any unescaped quotes within it.

        Args:
            pos: Position after the opening quote
            field_name: Optional field name for context (e.g., "content", "summary")

        Returns (fixed_value, position_at_closing_quote, found_closing_quote)
        """
        value_chars = []
        escaped = False

        while pos < len(text):
            char = text[pos]

            if escaped:
                # This character is escaped, keep it as-is
                value_chars.append(char)
                escaped = False
                pos += 1
                continue

            if char == '\\':
                # Check if this is a valid escape sequence
                if pos + 1 < len(text) and text[pos + 1] in '"\\/:bfnrtu':
                    # Valid escape sequence, keep it
                    value_chars.append(char)
                    escaped = True
                else:
                    # Invalid/stray backslash, escape it
                    value_chars.append('\\\\')
                pos += 1
                continue

            if char == '"':
                # This is an unescaped quote - could be the end or needs escaping
                # Check if this looks like the end of the string value
                # by looking at what comes after
                lookahead_start = pos + 1
                lookahead_end = min(len(text), pos + 50)
                lookahead = text[lookahead_start:lookahead_end]

                # For the "content" field, be more conservative since it can contain
                # any text including TOML/Python code with brackets
                # Only accept } as a definite end (end of change object)
                if field_name == "content":
                    # For content field, only end on } or next field marker
                    if re.match(r'^}', lookahead) or re.match(r'^\s+}', lookahead):
                        return ''.join(value_chars), pos, True
                    if re.match(r'^,\s*"filePath"', lookahead):
                        return ''.join(value_chars), pos, True
                else:
                    # For other fields, we can be less strict
                    # Check for definite end patterns
                    if re.match(r'^[}\]]', lookahead) or re.match(r'^\s+[}\]]', lookahead):
                        # Definitely the end (closing object or array)
                        return ''.join(value_chars), pos, True

                    # Check for likely end: comma followed by whitespace and a known field name
                    if re.match(r'^,\s*"(summary|changes|filePath|action|content)"', lookahead):
                        # Very likely the end (next JSON field)
                        return ''.join(value_chars), pos, True

                # Otherwise, this is an unescaped quote inside the value - escape it
                value_chars.append('\\"')
                pos += 1
                continue

            # Control characters need to be escaped
            if char == '\n':
                value_chars.append('\\n')
            elif char == '\r':
                value_chars.append('\\r')
            elif char == '\t':
                value_chars.append('\\t')
            else:
                # Regular character
                value_chars.append(char)

            pos += 1

        # Reached end without finding closing quote - return what we have
        return ''.join(value_chars), pos, False

    def read_field_name(pos):
        """Read a field name (expects to be at opening quote)"""
        if pos >= len(text) or text[pos] != '"':
            return None, pos

        result.append(text[pos])  # opening "
        pos += 1

        # Read until closing quote (field names shouldn't have escaped chars typically)
        while pos < len(text):
            char = text[pos]
            result.append(char)
            if char == '"':
                return text[pos], pos + 1
            pos += 1

        return None, pos

    # Expect opening {
    i = skip_whitespace(i)
    if i >= len(text) or text[i] != '{':
        raise JsonPreparationError("Expected opening { at start")
    result.append('{')
    i += 1

    # Read summary field
    i = skip_whitespace(i)
    field_name, i = read_field_name(i)

    i = skip_whitespace(i)
    if i < len(text) and text[i] == ':':
        result.append(':')
        i += 1

    i = skip_whitespace(i)
    if i < len(text) and text[i] == '"':
        result.append('"')
        i += 1
        # Read and fix the summary value
        fixed_value, i, found_quote = read_and_fix_string_value(i)
        result.append(fixed_value)
        if found_quote and i < len(text) and text[i] == '"':
            result.append('"')
            i += 1
        elif not found_quote:
            # Add missing closing quote
            result.append('"')

    # Expect comma after summary
    i = skip_whitespace(i)
    if i < len(text) and text[i] == ',':
        result.append(',')
        i += 1

    # Read changes field name
    i = skip_whitespace(i)
    field_name, i = read_field_name(i)

    i = skip_whitespace(i)
    if i < len(text) and text[i] == ':':
        result.append(':')
        i += 1

    # Expect opening [
    i = skip_whitespace(i)
    if i < len(text) and text[i] == '[':
        result.append('[')
        i += 1

    # Process each change object
    first_change = True
    while i < len(text):
        i = skip_whitespace(i)

        # Check if array ends
        if i < len(text) and text[i] == ']':
            result.append(']')
            i += 1
            break

        # Add comma between objects
        if not first_change:
            if i < len(text) and text[i] == ',':
                result.append(',')
                i += 1
            i = skip_whitespace(i)
        first_change = False

        # Expect opening {
        if i >= len(text) or text[i] != '{':
            break
        result.append('{')
        i += 1

        # Read the three fields: filePath, action, content
        for field_idx in range(3):
            i = skip_whitespace(i)

            # Add comma between fields
            if field_idx > 0:
                if i < len(text) and text[i] == ',':
                    result.append(',')
                    i += 1
                i = skip_whitespace(i)

            # Read field name
            current_field_name, i = read_field_name(i)

            # Expect colon
            i = skip_whitespace(i)
            if i < len(text) and text[i] == ':':
                result.append(':')
                i += 1

            # Read field value (always a string in our schema)
            i = skip_whitespace(i)
            if i < len(text) and text[i] == '"':
                result.append('"')
                i += 1
                # Read and fix the value, passing field context
                # Determine if this is the content field (field_idx == 2, or check the name)
                ctx_field = "content" if field_idx == 2 else None
                fixed_value, i, found_quote = read_and_fix_string_value(i, ctx_field)
                result.append(fixed_value)
                if found_quote and i < len(text) and text[i] == '"':
                    result.append('"')
                    i += 1
                elif not found_quote:
                    # Add missing closing quote
                    result.append('"')

        # Expect closing }
        i = skip_whitespace(i)
        if i < len(text) and text[i] == '}':
            result.append('}')
            i += 1

    # Expect closing }
    i = skip_whitespace(i)
    if i < len(text) and text[i] == '}':
        result.append('}')
        i += 1

    # Append any remaining content
    result.append(text[i:])

    return ''.join(result)


def clean_prepare_json_string(llm_json: str) -> dict:
    """
    Cleans and validates a JSON string generated by an LLM for the prepare command.
    Returns the cleaned JSON string if valid, otherwise raises an exception.
    """
    try:
        schema_path = files("aicodec") / "assets" / "decoder_schema.json"
        schema_content = schema_path.read_text(encoding="utf-8")
        schema = json.loads(schema_content)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: Could not load the internal JSON schema. {e}")
        return

    # First, apply basic cleaning
    cleaned_str = clean_json_string(llm_json)

    # Try to parse directly
    try:
        cleaned_json = json.loads(cleaned_str)
    except json.JSONDecodeError:
        print("Given JSON is invalid after cleaning. Trying to fix it with markdown to json conversion")
        # Try the standard fix first
        cleaned_str = fix_and_parse_ai_json(cleaned_str)
        try:
            cleaned_json = json.loads(cleaned_str)
        except json.JSONDecodeError as e:
            # If still failing, try a more aggressive fix for unescaped quotes
            print(f"Standard fix failed ({e}). Applying aggressive quote escaping...")
            cleaned_str = _aggressive_escape_quotes(llm_json)
            try:
                cleaned_json = json.loads(cleaned_str)
            except json.JSONDecodeError as e2:
                # Final attempt: schema-aware fixing
                print(f"Aggressive escaping failed ({e2}). Applying schema-aware JSON fix...")
                try:
                    cleaned_str = _schema_aware_json_fix(llm_json)
                    cleaned_json = json.loads(cleaned_str)
                except (json.JSONDecodeError, JsonPreparationError) as e3:
                    raise JsonPreparationError(f"Error: Failed to parse JSON after all fixing attempts. {e3}") from e3

    try:
        validate(instance=cleaned_json, schema=schema)
    except ValidationError as e:
        raise JsonPreparationError(f"Error: JSON validation failed. {e}") from e
    return json.dumps(cleaned_json, indent=4)


def _find_closing_brace(text: str, start_pos: int) -> int:
    """
    Find the position of the closing brace that matches the structure at start_pos.
    This is used to find where a change object ends.

    For malformed JSON with unescaped quotes, we use a schema-aware approach:
    look for the pattern that indicates end of a change object.

    Args:
        text: The full JSON text
        start_pos: Position to start searching from (should be after an opening brace)

    Returns:
        Position of the matching closing brace, or -1 if not found
    """
    import re

    # For change objects, we know the structure ends with: content value, closing quote, whitespace, }
    # Look for the pattern: } followed by comma or ] at the correct indentation level
    # Change objects in the changes array are indented with 8 spaces before the }

    # Strategy 1: look for \n followed by spaces, then }, then comma or ]
    # This avoids matching } inside string content
    pattern1 = re.compile(r"\n\s{8}}\s*[,\]]")
    match = pattern1.search(text, start_pos)
    if match:
        # Return the position of the } (after the newline and spaces)
        matched_text = match.group(0)
        brace_offset = matched_text.index("}")
        return match.start() + brace_offset

    # Strategy 2: For objects without newline before }, look for: "\s*}\s*[,\]]
    # This pattern (quote, optional space, brace, comma/bracket) marks end of content field
    pattern2 = re.compile(r'"\s*}\s*[,\]]')
    match = pattern2.search(text, start_pos)
    if match:
        # Return the position of the }
        matched_text = match.group(0)
        brace_offset = matched_text.index("}")
        return match.start() + brace_offset

    # Fallback: try the traditional approach for well-formed JSON
    depth = 0
    in_string = False
    escape_next = False

    for i in range(start_pos, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if not in_string:
            if char == "{":
                depth += 1
            elif char == "}":
                if depth == 0:
                    return i
                depth -= 1

    return -1


def _aggressive_escape_quotes(text: str) -> str:
    """
    Schema-aware JSON fixing that handles unescaped quotes in content/summary fields.

    Uses knowledge of the decoder_schema.json structure:
    - Root level: "summary" field followed by "changes" array
    - Change objects: "filePath", "action", "content" fields (content is last)
    """
    import re

    # First, clean control characters
    text = clean_json_string(text)

    result = []
    pos = 0

    # Process summary field (root level)
    summary_match = re.search(r'"summary"\s*:\s*"', text)
    if summary_match:
        # Add everything up to and including the opening quote
        result.append(text[pos : summary_match.end()])
        pos = summary_match.end()

        # Find where summary ends: look for ", "changes"
        # Scan for the pattern that ends summary
        end_pattern = re.search(r'",\s*"changes"', text[pos:])
        if end_pattern:
            summary_value = text[pos : pos + end_pattern.start()]
            # Fix the summary value
            fixed_summary = _fix_json_string_value(summary_value)
            result.append(fixed_summary)
            result.append('",')
            pos = pos + end_pattern.start() + 2  # Skip past ",
        else:
            # Couldn't find end, append rest as-is
            result.append(text[pos:])
            return "".join(result)

    # Add everything up to "changes" array
    changes_match = re.search(r'"changes"\s*:\s*\[', text[pos:])
    if changes_match:
        result.append(text[pos : pos + changes_match.end()])
        pos = pos + changes_match.end()
    else:
        # No changes array found, return what we have
        result.append(text[pos:])
        return "".join(result)

    # Process each change object in the changes array
    # Find all change objects using a more robust method
    changes_pattern = re.compile(r'\{\s*"filePath"', re.DOTALL)
    search_start = pos

    while search_start < len(text):
        # Find the next change object
        match = changes_pattern.search(text, search_start)
        if not match:
            # No more objects, append rest
            result.append(text[pos:])
            break

        obj_start = match.start()  # Position of the {

        # Add everything from last position up to this object's opening brace
        result.append(text[pos:obj_start])

        # Find where this object ends
        obj_end = _find_closing_brace(text, obj_start + 1)
        if obj_end == -1:
            # Couldn't find end, append rest and break
            result.append(text[obj_start:])
            break

        # Add the opening brace
        result.append("{")

        # Extract the object content (everything between { and })
        obj_text = text[obj_start + 1 : obj_end]

        # Find the "content" field within THIS object only
        content_match = re.search(r'"content"\s*:\s*"', obj_text)

        if not content_match:
            # No content field in this object, just copy it as-is
            result.append(obj_text)
            result.append("}")
            pos = obj_end + 1
            search_start = obj_end + 1
            continue

        # Add everything before the content value (filePath, action, etc.)
        result.append(obj_text[: content_match.end()])

        # Extract the content value (everything from after opening quote to before closing quote)
        content_value_start = content_match.end()
        remaining_in_obj = obj_text[content_value_start:]

        # Find the closing quote (work backwards from end of object)
        remaining_stripped = remaining_in_obj.rstrip()
        if remaining_stripped.endswith('"'):
            content_value = remaining_stripped[:-1]
            after_content = remaining_in_obj[len(remaining_stripped) - 1 :]  # Include the closing quote and whitespace
        else:
            # No closing quote, use everything
            content_value = remaining_in_obj
            after_content = '"'  # Add the missing quote

        # Fix the content value
        fixed_content = _fix_json_string_value(content_value)
        result.append(fixed_content)
        result.append(after_content)

        # Add the closing brace of the object
        result.append("}")

        # Move position past this entire object
        pos = obj_end + 1
        search_start = obj_end + 1

    return "".join(result)


def _fix_json_string_value(value: str) -> str:
    """
    Fix a JSON string value by escaping unescaped quotes and control characters.

    Args:
        value: The raw string value (without the surrounding quotes)

    Returns:
        Fixed string value with proper escaping
    """
    import re

    # Step 1: Escape literal control characters
    fixed = value.replace("\r", "\\r")
    fixed = fixed.replace("\n", "\\n")
    fixed = fixed.replace("\t", "\\t")

    # Step 2: Escape unescaped quotes
    # This regex finds quotes that are NOT preceded by a backslash
    fixed = re.sub(r'(?<!\\)"', r'\\"', fixed)

    # Step 3: Fix stray backslashes (handle cases like \U that aren't valid escapes)
    fixed = _fix_stray_backslashes(fixed)

    return fixed


def clean_json_string(s: str) -> str:
    """
    Cleans a string intended for JSON parsing.

    1. Replaces actual non-breaking spaces (\u00a0 or \xa0) with regular spaces.
    2. Replaces the literal text "\\u00a0" with a regular space.
    3. Removes problematic ASCII control characters (0-8, 11-12, 14-31, 127)
       while preserving tab (\t), newline (\n), and carriage return (\r).
    """

    # 1. Replace the actual non-breaking space character with a regular space
    s = re.sub(r"\xa0", " ", s)

    # 2. Replace the literal text sequence "\\u00a0" with a regular space
    # (The first \ escapes the second \ for the regex)
    s = re.sub(r"\\u00a0", " ", s)

    # 3. Remove other control characters, preserving \t, \n, \r
    #    (Ranges: 0-8, 11-12, 14-31, and 127)
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", s)

    return s


## Helpers for Robust AI-Generated JSON Fixing ##
# --- 1. Pre-compiled Regex Constants for Efficiency ---
# Fixes stray backslashes: finds 1+ slashes followed by a "non-escape" char
JSON_STRAY_BACKSLASH_PATTERN = re.compile(r'(\\+)(?:([^"\\/bfnrtu])|$)')

# Finds "summary" or "content" string values in the JSON.
# This is more robust: it captures ("key": ")(...content...)(" , or })
# It correctly captures the start/end quotes as groups 1 and 3.
TARGET_FIELD_PATTERN_TEMPLATE = r'("{field_name}":\s*")(.*?)("\s*(?:,|}}))'

JSON_SUMMARY_PATTERN = re.compile(TARGET_FIELD_PATTERN_TEMPLATE.format(field_name="summary"), re.DOTALL)
JSON_CONTENT_PATTERN = re.compile(TARGET_FIELD_PATTERN_TEMPLATE.format(field_name="content"), re.DOTALL)

# --- 2. Markdown Escape Map ---
MARKDOWN_ESCAPES = {
    r"\_": "_",
    r"\*": "*",
    r"\.": ".",
    r"\#": "#",
    r"\-": "-",
    r"\+": "+",
    r"\!": "!",
    r"\`": "`",
    r"\[": "[",
    r"\]": "]",
    r"\(": "(",
    r"\)": ")",
    r"\{": "{",
    r"\}": "}",
    r"\>": ">",
    r"\|": "|",
}

# --- 3. Helper Functions for Clean Code ---


def _fix_global_markdown_escapes(text: str) -> str:
    """Fixes all Markdown "over-escaping" (e.g., \_ -> _) globally."""
    for escaped, unescaped in MARKDOWN_ESCAPES.items():
        text = text.replace(escaped, unescaped)
    return text


def _backslash_replacer(match: re.Match) -> str:
    """
    Replacer function for JSON_STRAY_BACKSLASH_PATTERN.
    Escapes a stray backslash only if it's part of an ODD-numbered
    sequence of backslashes.
    """
    slashes = match.group(1)
    # char is group 2, or empty string if end-of-line
    char = match.group(2) or ""

    if len(slashes) % 2 == 1:
        # Odd number of slashes: \U -> \\U or \\\U -> \\\\U
        # This is a stray slash that needs escaping.
        slashes += "\\"

    # Even number of slashes (e.g., \\U) is already escaped.
    # Return the (potentially fixed) slashes and the character.
    return slashes + char


def _fix_stray_backslashes(s: str) -> str:
    """Robustly fixes stray backslashes in a string."""
    return JSON_STRAY_BACKSLASH_PATTERN.sub(_backslash_replacer, s)


def _fix_json_string_content(content: str) -> str:
    """
    Applies all required JSON string-value fixes in the correct order.
    """
    # STEP (A): Escape control characters.
    # This MUST run before fixing backslashes.
    fixed_content = content.replace("\r", "\\r")
    fixed_content = fixed_content.replace("\n", "\\n")
    fixed_content = fixed_content.replace("\t", "\\t")

    # STEP (B): Fix unescaped backslashes (ROBUSTLY).
    # This correctly handles \\U vs \U and ignores the \\n, \\r, \\t
    # we just created.
    fixed_content = _fix_stray_backslashes(fixed_content)

    # STEP (C): Fix unescaped double-quotes.
    # This logic is correct, as it only escapes a " if it's
    # NOT already preceded by a (single) backslash.
    fixed_content = re.sub(r'(?<!\\)"', r"\"", fixed_content)

    return fixed_content


def _json_string_value_replacer(match: re.Match) -> str:
    """
    The main re.sub replacer function for summary_regex and content_regex.
    It extracts the content, fixes it, and reassembles the string.
    """
    pre = match.group(1)  # ("summary": "
    content = match.group(2)  # ... the broken content ...
    post = match.group(3)  # ",

    fixed_content = _fix_json_string_content(content)

    return f"{pre}{fixed_content}{post}"


# --- 4. Main Public Function ---


def _simple_escape_quotes_in_json_strings(text: str) -> str:
    """
    Simple approach: Escape all unescaped quotes within JSON string values.

    This uses a character-by-character scan to identify string boundaries
    and escape quotes within them.

    Args:
        text: The potentially malformed JSON string

    Returns:
        JSON string with quotes properly escaped within string values
    """
    import re

    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(text):
        char = text[i]

        if escape_next:
            # Already escaped, keep it
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == "\\":
            result.append(char)
            escape_next = True
            i += 1
            continue

        if char == '"':
            # Check if this is a field name or value by looking at context
            # Look back to see if we have : before this quote (field value start)
            # or if we have , or { before (field name start)
            if not in_string:
                # Check if this starts a string value
                # Look backwards for the context
                lookback = "".join(result[-20:]) if len(result) >= 20 else "".join(result)
                # If we see : followed by whitespace and then ", it's a value start
                if re.search(r":\s*$", lookback):
                    in_string = True
                    result.append(char)
                # If we see , or { or [ followed by whitespace and ", it might be a key start
                elif re.search(r"[,\{\[]\s*$", lookback):
                    # This is likely a field name, not a value
                    result.append(char)
                else:
                    # Structural quote, keep it
                    result.append(char)
            else:
                # We're in a string, this might be the end
                # Check if the next chars are : (then this was a field name, not a value)
                lookahead = text[i + 1 : i + 10]
                if re.match(r"\s*:", lookahead):
                    # This was a field name, not a value string
                    in_string = False
                    result.append(char)
                else:
                    # This should be the string end - but we need to check if it's escaped
                    # If it's not preceded by \, it's the end
                    # We already handled escape_next above, so this is unescaped
                    in_string = False
                    result.append(char)
            i += 1
            continue

        # Regular character
        result.append(char)
        i += 1

    return "".join(result)


def _escape_quotes_in_string_fields(text: str) -> str:
    """
    Targeted approach: Find specific fields (summary, content) and escape quotes within them.
    Uses the schema structure: summary is at root, content is in change objects.

    This handles multi-line string values where the content spans multiple lines in the file.
    """
    import re

    # Strategy: Find "fieldname": " and scan forward to find the closing
    # Then escape quotes and control characters within that range

    result = []
    pos = 0

    # Find all occurrences of summary or content fields
    pattern = re.compile(r'("(summary|content)":\s*")', re.DOTALL)

    for match in pattern.finditer(text):
        field_name = match.group(2)  # Extract the field name (summary or content)
        value_start = match.end()

        # Add everything before this field
        result.append(text[pos:value_start])

        # Now find the end of this string value
        # Scan forward, tracking escapes and looking for the closing quote
        i = value_start
        escaped = False
        found_end = False

        # Different end patterns for different fields
        if field_name == "summary":
            end_pattern = r"\s*,"  # summary is followed by comma
        else:  # content
            end_pattern = r"\s*}"  # content is last field, followed by closing brace

        while i < len(text):
            char = text[i]

            if escaped:
                escaped = False
                i += 1
                continue

            if char == "\\":
                # Check if this is a valid escape sequence or a stray backslash
                if i + 1 < len(text) and text[i + 1] in '"\\/:bfnrtu':
                    escaped = True
                i += 1
                continue

            if char == '"':
                # Found a potential closing quote
                # Check what follows to see if this is really the end
                lookahead = text[i + 1 : i + 10]
                # Use the appropriate end pattern for this field type
                if re.match(end_pattern, lookahead):
                    # This is the closing quote
                    value_end = i
                    found_end = True
                    break

            i += 1

        if found_end:
            # Extract the value between value_start and value_end
            value = text[value_start:value_end]

            # Fix the value: escape unescaped quotes and control characters
            # 1. Escape literal control characters (newlines, tabs, etc.)
            fixed_value = value.replace("\r", "\\r")
            fixed_value = fixed_value.replace("\n", "\\n")
            fixed_value = fixed_value.replace("\t", "\\t")

            # 2. Escape unescaped quotes
            fixed_value = re.sub(r'(?<!\\)"', r'\\"', fixed_value)

            # 3. Fix stray backslashes (but not the ones we just added)
            fixed_value = _fix_stray_backslashes(fixed_value)

            result.append(fixed_value)
            result.append('"')  # Add the closing quote
            pos = value_end + 1  # Move past the closing quote
        else:
            # Couldn't find the end, keep original
            result.append(text[value_start:])
            break

    # Add any remaining text
    result.append(text[pos:])

    return "".join(result)


def fix_and_parse_ai_json(text: str) -> str | None:
    """
    Fixes common AI-generated JSON errors for a specific schema.

    1. Fixes Markdown "over-escaping" (e.g., \_) globally.
    2. Fixes JSON "under-escaping" (e.g., unescaped ", \, newlines)
       only within the "summary" and "content" string values.
    3. Handles unescaped quotes within content fields using schema knowledge.
    """
    try:
        # 1. Fix all Markdown "over-escaping" globally.
        text = _fix_global_markdown_escapes(text)

        # 2. Try the regex-based approach first (simpler and faster)
        text_with_regex = text
        text_with_regex = JSON_SUMMARY_PATTERN.sub(_json_string_value_replacer, text_with_regex)
        text_with_regex = JSON_CONTENT_PATTERN.sub(_json_string_value_replacer, text_with_regex)

        # Test if the regex approach worked by trying to parse
        import json

        try:
            json.loads(text_with_regex)
            # If successful, use the regex-fixed version
            return text_with_regex
        except json.JSONDecodeError:
            # Regex approach failed, try the line-based approach
            pass

        # 3. Line-based approach: escape quotes in summary and content fields
        text = _escape_quotes_in_string_fields(text)

    except Exception as e:
        # Log the error if you have a logger
        print(f"Error during regex replacement: {e}")
        return None

    return text
