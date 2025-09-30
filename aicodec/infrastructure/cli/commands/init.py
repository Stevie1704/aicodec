# aicodec/infrastructure/cli/commands/init.py
import json
from pathlib import Path
from typing import Any

from .utils import get_list_from_user, get_user_confirmation


def register_subparser(subparsers: Any) -> None:
    init_parser = subparsers.add_parser(
        "init", help="Initialize a new aicodec project configuration."
    )
    init_parser.set_defaults(func=run)


def run(args: Any) -> None:
    """Handles the interactive project initialization."""
    print("Initializing aicodec configuration...\n")
    config_dir = Path(".aicodec")
    config_file = config_dir / "config.json"

    if config_file.exists():
        if not get_user_confirmation(
            f'Configuration file "{config_file}" already exists. Overwrite?',
            default_yes=False,
        ):
            print("Initialization cancelled.")
            return

    config = {"aggregate": {}, "prompt": {}, "prepare": {}, "apply": {}}

    print("--- Aggregation Settings ---")
    config["aggregate"]["directories"] = ["."]
    print("The '.git' and '.aicodec', are always excluded by default.")
    config["aggregate"]["exclude_dirs"] = [".git", ".aicodec"]
    config["aggregate"]["include_dirs"] = []
    config["aggregate"]["include_ext"] = []
    config["aggregate"]["include_files"] = []
    config["aggregate"]["exclude_exts"] = []
    config["aggregate"]["exclude_files"] = []

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
                        print(f"Added '{aicodec_entry}' to '.gitignore'.")
                    else:
                        print(
                            f"'.gitignore' already contains '{aicodec_entry}'. No changes made.")
                else:
                    gitignore_path.write_text(
                        f"{aicodec_entry}\n", encoding="utf-8")
                    print(f"Created '.gitignore' and added '{aicodec_entry}'.")
            except Exception as e:
                print(f"Warning: Could not update .gitignore: {e}")

        if get_user_confirmation(
            "Also exclude the .gitignore file itself from the context?",
            default_yes=True,
        ):
            config["aggregate"]["exclude_files"].append(".gitignore")

    if get_user_confirmation(
        "Configure additional inclusions/exclusions?", default_yes=False
    ):
        config["aggregate"]["include_dirs"].extend(
            get_list_from_user("Directories to always include:")
        )
        config["aggregate"]["include_files"].extend(
            get_list_from_user("Files/glob patterns to always include:")
        )
        config["aggregate"]["include_ext"].extend(
            get_list_from_user(
                "File extensions to always include (e.g., .py, .ts):")
        )
        config["aggregate"]["exclude_dirs"].extend(
            get_list_from_user("Additional directories to exclude:")
        )
        config["aggregate"]["exclude_files"].extend(
            get_list_from_user("Additional files/glob patterns to exclude:")
        )
        config["aggregate"]["exclude_exts"].extend(
            get_list_from_user("File extensions to always exclude:")
        )

    print("\n--- LLM Interaction Settings ---")
    config["prepare"]["changes"] = ".aicodec/changes.json"
    config["apply"]["output_dir"] = "."
    config["prompt"]["output_file"] = ".aicodec/prompt.txt"
    print(
        "LLM changes will be read from '.aicodec/changes.json' and applied to the current directory ('.')."
    )
    print("A default prompt file will be generated at '.aicodec/prompt.txt'.")

    minimal = get_user_confirmation(
        "Use a minimal prompt template to reduce context size (might influence results)?", default_yes=False
    )
    config["prompt"]["minimal"] = minimal
    tech_stack = input(
        "What is your primary language or tech stack? (e.g., Python, TypeScript/React) [optional]: ").strip()
    if tech_stack:
        config["prompt"]["tech_stack"] = tech_stack

    from_clipboard = get_user_confirmation(
        "Read LLM output directly from the clipboard by default?", default_yes=False
    )
    config["prepare"]["from_clipboard"] = from_clipboard
    if from_clipboard:
        print(
            "Note: Using the clipboard in some environments (like devcontainers) might require extra setup."
        )

    include_code = get_user_confirmation(
        "Should the prompt include the code context by default?", default_yes=True
    )
    config["prompt"]["include_code"] = include_code

    prompt_clipboard = get_user_confirmation(
        "Copy generated prompt directly to the clipboard by default (instead of writing to file)?", default_yes=False
    )
    config["prompt"]["clipboard"] = prompt_clipboard

    config_dir.mkdir(exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    print(f'\nSuccessfully created configuration at "{config_file}".')
