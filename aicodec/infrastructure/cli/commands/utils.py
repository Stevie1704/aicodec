# aicodec/infrastructure/cli/commands/utils.py
import json
import sys
from importlib.resources import files
from pathlib import Path

from json_repair import repair_json
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
        return json.dumps(json.loads(content), separators=(',', ':'))
    except FileNotFoundError:
        print(f"Error: JSON file '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)


def clean_prepare_json_string(llm_json: str) -> str:
    """
    Cleans, validates, and formats a JSON string from an LLM using json-repair.

    This function takes a potentially malformed JSON string, attempts to repair it,
    validates it against the project's decoder schema, and returns it as a
    well-formatted JSON string.

    Args:
        llm_json: The raw JSON string received from the language model.

    Returns:
        A cleaned, validated, and pretty-printed JSON string.

    Raises:
        JsonPreparationError: If the JSON string cannot be repaired or if it
                              fails validation against the schema.
    """
    try:
        # 1. Load the validation schema
        schema_path = files("aicodec") / "assets" / "decoder_schema.json"
        schema_content = schema_path.read_text(encoding="utf-8")
        schema = json.loads(schema_content)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # This is a critical internal error, so we raise an exception
        raise JsonPreparationError(f"Fatal: Could not load the internal JSON schema. {e}") from e

    try:
        # 2. Repair the JSON string
        repaired_json_str = repair_json(llm_json)
        cleaned_json = json.loads(repaired_json_str)
    except Exception as e:
        # The exception from repair_json or json.loads is not specific,
        # so we catch a broad exception.
        raise JsonPreparationError(
            f"Error: Failed to parse or repair the JSON from the LLM. {e}"
        ) from e

    try:
        # 3. Validate the repaired JSON against the schema
        validate(instance=cleaned_json, schema=schema)
    except ValidationError as e:
        # Provide a clear error message if validation fails
        raise JsonPreparationError(f"Error: Repaired JSON failed validation. {e.message}") from e

    # 4. Return the validated JSON, pretty-printed
    return json.dumps(cleaned_json, indent=4)