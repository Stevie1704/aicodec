# aicodec/infrastructure/cli/commands/init.py
import json
from pathlib import Path
from typing import Any

from rich.console import Console

from .utils import get_list_from_user, get_user_confirmation


def register_subparser(subparsers: Any) -> None:
    init_parser = subparsers.add_parser(
        "init", help="Initialize a new aicodec project."
    )
    init_parser.add_argument(
        "--plugin",
        action="extend",
        nargs="+",
        default=[],
        help="Define a plugin, e.g., '.ext=command {file}'.",
    )
    init_parser.set_defaults(func=run)


def run(args: Any) -> None:
    """Handles the interactive project initialization."""
    console = Console()
    console.print("Initializing aicodec configuration...", style="bold")
    config_dir = Path(".aicodec")
    config_file = config_dir / "config.json"

    if config_file.exists():
        if not get_user_confirmation(
            f'Configuration file "{config_file}" already exists. Overwrite?',
            default_yes=False,
        ):
            console.print("Initialization cancelled.", style="bold red")
            return

    # Process plugins from CLI
    final_plugins = []
    for p_str in args.plugin:
        if "=" in p_str:
            ext, command = p_str.split("=", 1)
            final_plugins.append(f"{ext.strip()}={command.strip()}")

    config = {"aggregate": {}, "prompt": {}, "prepare": {}, "apply": {}}

    console.rule("[bold cyan]Aggregation Settings[/bold cyan]")
    config["aggregate"]["directories"] = get_list_from_user(
        "Directories to scan (relative or absolute, defaults to '.' for current directory):"
    ) or ["."]
    console.print(
        "'.git/**' and '.aicodec/**' are always excluded by default.", style="dim"
    )
    config["aggregate"]["exclude"] = []
    config["aggregate"]["include"] = []
    config["aggregate"]["plugins"] = final_plugins

    use_gitignore = get_user_confirmation(
        "Use the .gitignore file for exclusions?", default_yes=True
    )
    config["aggregate"]["use_gitignore"] = use_gitignore


    if use_gitignore:
        if get_user_confirmation(
            "Update .gitignore to exclude the '.aicodec/' directory?",
            default_yes=True,
        ):
            gitignore_path = Path(".gitignore")
            aicodec_entry = ".aicodec/"
            try:
                if gitignore_path.is_file():
                    content = gitignore_path.read_text("utf-8")
                    if aicodec_entry not in content.splitlines():
                        with gitignore_path.open("a", encoding="utf-8") as f:
                            if content and not content.endswith("\n"):
                                f.write("\n")
                            f.write(f"{aicodec_entry}\n")
                        console.print(
                            f"Added '{aicodec_entry}' to '.gitignore'.", style="green"
                        )
                    else:
                        console.print(
                            f"'.gitignore' already contains '{aicodec_entry}'. No changes made.",
                            style="dim",
                        )
                else:
                    gitignore_path.write_text(
                        f"{aicodec_entry}\n", encoding="utf-8"
                    )
                    console.print(
                        f"Created '.gitignore' and added '{aicodec_entry}'.",
                        style="green",
                    )
            except Exception as e:
                console.print(
                    f"Warning: Could not update .gitignore: {e}", style="yellow"
                )

        if get_user_confirmation(
            "Also exclude the .gitignore file itself from the context?",
            default_yes=True,
        ):
            config["aggregate"]["exclude"].append(".gitignore")

    if get_user_confirmation(
        "Configure additional inclusion/exclusion glob patterns?", default_yes=False
    ):
        config["aggregate"]["include"].extend(
            get_list_from_user("Glob patterns to always include (gitignore-style):")
        )
        config["aggregate"]["exclude"].extend(
            get_list_from_user(
                "Additional glob patterns to exclude (gitignore-style):"
            )
        )

    console.rule("[bold cyan]LLM Interaction Settings[/bold cyan]")
    config["prepare"]["changes"] = ".aicodec/changes.json"
    config["apply"]["output_dir"] = "."
    config["prompt"]["output_file"] = ".aicodec/prompt.txt"
    console.print(
        "LLM changes will be read from '.aicodec/changes.json' and applied to the current directory ('.')."
    )
    console.print("A default prompt file will be generated at '.aicodec/prompt.txt'.")

    minimal = get_user_confirmation(
        "Use a minimal prompt template to reduce context size (might influence results)?",
        default_yes=False,
    )
    config["prompt"]["minimal"] = minimal
    tech_stack = input(
        "What is your primary language or tech stack? (e.g., Python, TypeScript/React) [optional]: "
    ).strip()
    if tech_stack:
        config["prompt"]["tech_stack"] = tech_stack

    include_map = get_user_confirmation(
        "Include the repository map in the prompt by default?", default_yes=False
    )
    config["prompt"]["include_map"] = include_map

    from_clipboard = get_user_confirmation(
        "Read LLM output directly from the clipboard by default?", default_yes=False
    )
    config["prepare"]["from_clipboard"] = from_clipboard
    if from_clipboard:
        console.print(
            "Note: Using the clipboard in some environments (like devcontainers) might require extra setup.",
            style="italic dim",
        )

    include_code = get_user_confirmation(
        "Should the prompt include the code context by default?", default_yes=True
    )
    config["prompt"]["include_code"] = include_code

    prompt_clipboard = get_user_confirmation(
        "Copy generated prompt directly to the clipboard by default (instead of writing to file)?",
        default_yes=False,
    )
    config["prompt"]["clipboard"] = prompt_clipboard

    config_dir.mkdir(exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    console.print(
        f"\nSuccessfully created configuration at '[bold]{config_file}[/bold]'.",
        style="bold green",
    )
