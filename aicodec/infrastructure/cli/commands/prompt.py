# aicodec/infrastructure/cli/commands/prompt.py
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

import jinja2
import pyperclip

from ...config import load_config as load_json_config
from ...utils import open_file_in_editor
from .utils import parse_json_file


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
    prompt_parser.add_argument(
        "-noi",
        "--no-output-instruction",
        action="store_true",
        dest="exclude_output_instructions",
        help="Exclude output instructions from the prompt.",
    )
    prompt_parser.add_argument(
        "-np",
        "--new-project",
        action="store_true",
        dest="is_new_project",
        help="Optimize the prompt for a new project with no existing code context.",
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

    if args.exclude_code or args.is_new_project:
        include_code_context = False
    else:
        include_code_context = prompt_cfg.get("include_code", True)

    code_context = None
    if include_code_context:
        context_file = Path(".aicodec") / "context.json"
        if not context_file.is_file():
            print(
                f"Error: Context file '{context_file}' not found. Run 'aicodec aggregate' first."
            )
            sys.exit(1)

        try:
            code_context = parse_json_file(context_file)
        except FileNotFoundError as e:
            print(f"Error reading required file: {e}", file=sys.stderr)
            sys.exit(1)

    schema_path = files("aicodec") / "assets" / "decoder_schema.json"
    schema_content = parse_json_file(schema_path)

    tech_stack = prompt_cfg.get("tech_stack", False) or args.tech_stack

    prompt_templates_path = files("aicodec") / "assets" / "prompts"
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(prompt_templates_path)),
        # B701:autoescape is False. This is safe as we are generating plain text files, not HTML.
        autoescape=False,  # nosec B701
    )

    custom_template_str = prompt_cfg.get("template")

    if custom_template_str:
        template = env.from_string(custom_template_str)
    else:
        minimal_prompt = args.minimal or prompt_cfg.get("minimal", False)
        template_name = "minimal.j2" if minimal_prompt else "full.j2"
        template = env.get_template(template_name)

    prompt_context = {
        "language_and_tech_stack": tech_stack,
        "user_task_description": args.task,
        "code_context": code_context,
        "json_schema": schema_content,
        "include_output_instructions": not args.exclude_output_instructions,
        "is_new_project": args.is_new_project,
    }

    prompt = template.render(**prompt_context)

    clipboard = prompt_cfg.get("clipboard", False) or args.clipboard
    output_file = args.output_file or prompt_cfg.get(
        "output_file", ".aicodec/prompt.txt"
    )

    if clipboard:
        try:
            pyperclip.copy(prompt)
            print("Prompt successfully copied to clipboard.")
        # FileNotFoundError can occur on Linux if no clipboard mechanism is found
        except (pyperclip.PyperclipException, FileNotFoundError):
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(prompt, encoding="utf-8")
            print(
                f"Clipboard not available. Prompt has been saved to '{output_path}' instead."
            )
            if not open_file_in_editor(output_path):
                print("Could not open an editor automatically.")
                print(
                    f"Please open the file and copy its contents to your LLM: {output_path}"
                )
    else:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(prompt, encoding="utf-8")
        print(f'Successfully generated prompt at "{output_path}".')
        if not open_file_in_editor(output_path):
            print("Could not open an editor automatically.")
            print(
                f"Please open the file and copy its contents to your LLM: {output_path}"
            )
