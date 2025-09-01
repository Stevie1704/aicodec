# aicodec/infrastructure/cli/commands/prompt.py
import sys
import os
from pathlib import Path
from importlib.resources import files
import pyperclip

from ...config import load_config as load_json_config
from ...utils import open_file_in_editor
from .utils import load_default_prompt_template


def register_subparser(subparsers):
    prompt_parser = subparsers.add_parser(
        "prompt", help="Generate a prompt file with the aggregated context and schema."
    )
    prompt_parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=".aicodec/config.json",
        help="Path to the config file.",
    )
    prompt_parser.add_argument(
        "--task",
        type=str,
        default="[REPLACE THIS WITH YOUR CODING TASK]",
        help="The specific task for the LLM to perform.",
    )
    prompt_parser.add_argument(
        "--output-file",
        type=Path,
        help="Path to save the generated prompt file (overrides config).",
    )
    prompt_parser.add_argument(
        "--clipboard",
        action="store_true",
        help="Copy the generated prompt to the clipboard instead of opening a file.",
    )
    prompt_parser.set_defaults(func=run)


def run(args):
    """Handles the generation of a prompt file."""
    config = load_json_config(args.config)
    prompt_cfg = config.get("prompt", {})

    context_file = Path(".aicodec") / "context.json"
    if not context_file.is_file():
        print(
            f"Error: Context file '{context_file}' not found. Run 'aicodec aggregate' first."
        )
        sys.exit(1)

    try:
        context_content = context_file.read_text(encoding="utf-8")
        schema_path = files("aicodec") / "assets" / "decoder_schema.json"
        schema_content = schema_path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        print(f"Error reading required file: {e}", file=sys.stderr)
        sys.exit(1)

    template = prompt_cfg.get("template", load_default_prompt_template())
    # Default values for placeholders if they are not in the template
    prompt_placeholders = {
        "language_and_tech_stack": "Python, Flask, Docker",
        "user_task_description": args.task,
        "code_context_json": context_content,
        "json_schema": schema_content,
    }

    prompt = template.format(**prompt_placeholders)

    clipboard = prompt_cfg.get("clipboard", False) or args.clipboard

    if clipboard:
        if os.environ.get('AICODEC_TEST_MODE'):
            os.environ['AICODEC_TEST_CLIPBOARD'] = prompt
            print("Prompt successfully copied to test clipboard.")
        else:
            pyperclip.copy(prompt)
            print("Prompt successfully copied to clipboard.")
    else:
        output_file = args.output_file or prompt_cfg.get(
            "output_file", ".aicodec/prompt.txt"
        )
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(prompt, encoding="utf-8")
        print(
            f'Successfully generated prompt at "{output_path}". Opening in default editor...'
        )
        open_file_in_editor(output_path)
