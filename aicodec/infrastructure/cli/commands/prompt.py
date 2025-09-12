# aicodec/infrastructure/cli/commands/prompt.py
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

import pyperclip

from ...config import load_config as load_json_config
from ...utils import open_file_in_editor
from .utils import load_default_prompt_template, parse_json_file


def register_subparser(subparsers: Any) -> None:
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
        "--minimal",
        action="store_true",
        help="Use minimal prompt template.",
    )
    prompt_parser.add_argument(
        "--tech-stack",
        type=str,
        default="[REPLACE THIS WITH YOUR tech-stack]",
        help="The specific tech stack for the LLM to consider.",
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
    group = prompt_parser.add_mutually_exclusive_group()
    group.add_argument(
        "--no-code",
        action="store_true",
        dest="exclude_code",
        help="Exclude code context from the prompt (overrides config).",
    )
    prompt_parser.set_defaults(func=run)


def run(args: Any) -> None:
    """Handles the generation of a prompt file."""
    config = load_json_config(args.config)
    prompt_cfg = config.get("prompt", {})

    if args.exclude_code:
        include_code_context = False
    else:
        include_code_context = prompt_cfg.get("include_code", True)

    context_file = Path(".aicodec") / "context.json"
    code_context_section = ""
    if include_code_context:
        if not context_file.is_file():
            print(
                f"Error: Context file '{context_file}' not found. Run 'aicodec aggregate' first."
            )
            sys.exit(1)

        try:
            context_content = parse_json_file(context_file)
            code_context_section = (
                "<code_context>\n"
                "The relevant codebase is provided below as a JSON array. Each object in the array contains the relative 'filePath' and the full 'content' of a file.\n\n"
                f"```json\n{context_content}\n```\n"
                "</code_context>\n"
            )
        except FileNotFoundError as e:
            print(f"Error reading required file: {e}", file=sys.stderr)
            sys.exit(1)

    schema_path = files("aicodec") / "assets" / "decoder_schema.json"
    schema_content = parse_json_file(schema_path)

    tech_stack = prompt_cfg.get("tech_stack", False) or args.tech_stack
    minimal_prompt = args.minimal or prompt_cfg.get("minimal", False)
    template = prompt_cfg.get(
        "template", load_default_prompt_template(minimal_prompt))
    # Default values for placeholders if they are not in the template
    prompt_placeholders = {
        "language_and_tech_stack": tech_stack,
        "user_task_description": args.task,
        "code_context_section": code_context_section,
        "json_schema": schema_content,
    }

    prompt = template.format(**prompt_placeholders)

    clipboard = prompt_cfg.get("clipboard", False) or args.clipboard

    if clipboard:
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
