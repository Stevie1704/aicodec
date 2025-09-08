# aicodec/infrastructure/cli/commands/schema.py
import sys
from importlib.resources import files
from typing import Any


def register_subparser(subparsers: Any) -> None:
    schema_parser = subparsers.add_parser(
        "schema", help="Print the JSON schema for LLM change proposals."
    )
    schema_parser.set_defaults(func=run)


def run(args: Any) -> None:
    """Finds and prints the decoder_schema.json file content."""
    try:
        schema_path = files("aicodec") / "assets" / "decoder_schema.json"
        schema_content = schema_path.read_text(encoding="utf-8")
        print(schema_content)
    except FileNotFoundError:
        print(
            "Error: decoder_schema.json not found. The package might be corrupted.",
            file=sys.stderr,
        )
        sys.exit(1)
