# aicodec/cli.py
import argparse
import json
import os
from jsonschema import validate, ValidationError
import pyperclip
from pathlib import Path
from aicodec.core.config import EncoderConfig, load_config
from aicodec.services.encoder_service import EncoderService
from aicodec.review_server import launch_review_server
from aicodec.utils import open_file_in_editor


def main():
    parser = argparse.ArgumentParser(
        description="A lightweight communication layer for developers to interact with LLMs."
    )
    subparsers = parser.add_subparsers(
        dest='command', required=True, help='Available commands')

    # --- Init Command ---
    init_parser = subparsers.add_parser(
        'init', help='Initialize a new aicodec project configuration.')

    # --- Aggregate Command ---
    agg_parser = subparsers.add_parser(
        'aggregate', help='Aggregate project files into a JSON context.')
    agg_parser.add_argument('-c', '--config', type=str,
                            default='.aicodec/config.json')
    agg_parser.add_argument('-d', '--directory', type=str, help="The root directory to scan.")
    agg_parser.add_argument('--include-dir', action='append', default=[], help="Specific directories to include, overriding exclusions.")
    agg_parser.add_argument('--include-ext', action='append', default=[], help="File extensions to include.")
    agg_parser.add_argument('--include-file', action='append', default=[], help="Specific files or glob patterns to include.")
    agg_parser.add_argument('--exclude-dir', action='append', default=[])
    agg_parser.add_argument('--exclude-ext', action='append', default=[])
    agg_parser.add_argument('--exclude-file', action='append', default=[])
    agg_parser.add_argument('--full', action='store_true',
                            help="Perform a full aggregation, ignoring previous hashes.")
    gitignore_group = agg_parser.add_mutually_exclusive_group()
    gitignore_group.add_argument('--use-gitignore', action='store_true', dest='use_gitignore', default=None,
                                 help="Explicitly use .gitignore for exclusions (default). Overrides config.")
    gitignore_group.add_argument('--no-gitignore', action='store_false', dest='use_gitignore',
                                 help="Do not use .gitignore for exclusions. Overrides config.")

    # --- Apply Command ---
    apply_parser = subparsers.add_parser(
        'apply', help='Review and apply changes from an LLM.')
    apply_parser.add_argument('-c', '--config', type=str,
                              default='.aicodec/config.json', help="Path to the config file.")
    apply_parser.add_argument('-od', '--output-dir', type=Path,
                              help="The project directory to apply changes to (overrides config).")
    apply_parser.add_argument(
        '--changes', type=Path, help="Path to the LLM changes JSON file (overrides config).")

    # --- Revert Command ---
    revert_parser = subparsers.add_parser(
        'revert', help='Review and revert previously applied changes.')
    revert_parser.add_argument('-c', '--config', type=str,
                               default='.aicodec/config.json', help="Path to the config file.")
    revert_parser.add_argument('-od', '--output-dir', type=Path,
                               help="The project directory to revert changes in (overrides config).")

    # --- Prepare Command ---
    prep_parser = subparsers.add_parser(
        'prepare', help='Prepare the changes file, either by opening an editor or from clipboard.')
    prep_parser.add_argument('-c', '--config', type=str,
                             default='.aicodec/config.json', help="Path to the config file.")
    prep_parser.add_argument(
        '--changes', type=Path, help="Path to the LLM changes JSON file (overrides config).")
    prep_parser.add_argument('--from-clipboard', action='store_true',
                             help="Paste content directly from the system clipboard.")

    args = parser.parse_args()

    if args.command == 'init':
        handle_init(args)
    elif args.command == 'aggregate':
        handle_aggregate(args)
    elif args.command == 'apply':
        handle_apply(args)
    elif args.command == 'revert':
        handle_revert(args)
    elif args.command == 'prepare':
        handle_prepare(args)


def get_user_confirmation(prompt: str, default_yes: bool = True) -> bool:
    """Generic function to get a yes/no confirmation from the user."""
    options = "[Y/n]" if default_yes else "[y/N]"
    while True:
        response = input(f"{prompt} {options} ").lower().strip()
        if not response:
            return default_yes
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Invalid input. Please enter 'y' or 'n'.")


def get_list_from_user(prompt: str) -> list[str]:
    """Gets a comma-separated list of items from the user."""
    response = input(f"{prompt} (comma-separated, press Enter to skip): ").strip()
    if not response:
        return []
    return [item.strip() for item in response.split(',')]


def handle_init(args):
    """Handles the interactive project initialization."""
    print("Initializing aicodec configuration...\n")
    config_dir = Path('.aicodec')
    config_file = config_dir / 'config.json'

    if config_file.exists():
        if not get_user_confirmation(f'Configuration file "{config_file}" already exists. Overwrite?', default_yes=False):
            print("Initialization cancelled.")
            return

    config = {
        "aggregate": {},
        "prepare": {},
        "apply": {}
    }

    # --- Aggregation Config ---
    print("--- Aggregation Settings ---")
    config['aggregate']['directory'] = '.'
    print("The '.git' directory is always excluded by default.")
    config['aggregate']['exclude_dirs'] = ['.git']

    use_gitignore = get_user_confirmation("Use the .gitignore file for exclusions?", default_yes=True)
    config['aggregate']['use_gitignore'] = use_gitignore

    if use_gitignore:
        if get_user_confirmation("Also exclude the .gitignore file itself from the context?", default_yes=True):
            config['aggregate'].setdefault('exclude_files', []).append('.gitignore')

    if get_user_confirmation("Configure additional inclusions/exclusions?", default_yes=False):
        config['aggregate'].setdefault('include_dirs', []).extend(get_list_from_user("Directories to always include:"))
        config['aggregate'].setdefault('include_files', []).extend(get_list_from_user("Files/glob patterns to always include:"))
        config['aggregate'].setdefault('include_ext', []).extend(get_list_from_user("File extensions to always include (e.g., .py, .ts):"))
        config['aggregate'].setdefault('exclude_dirs', []).extend(get_list_from_user("Additional directories to exclude:"))
        config['aggregate'].setdefault('exclude_files', []).extend(get_list_from_user("Additional files/glob patterns to exclude:"))
        config['aggregate'].setdefault('exclude_exts', []).extend(get_list_from_user("File extensions to always exclude:"))

    # --- Prepare & Apply Config ---
    print("\n--- LLM Interaction Settings ---")
    config['prepare']['changes'] = '.aicodec/changes.json'
    config['apply']['output_dir'] = '.'
    print("LLM changes will be read from '.aicodec/changes.json' and applied to the current directory ('.').")
    print("This can be changed in the config file later if needed.")

    from_clipboard = get_user_confirmation("Read LLM output directly from the clipboard by default?", default_yes=False)
    config['prepare']['from_clipboard'] = from_clipboard
    if from_clipboard:
        print("Note: Using the clipboard in some environments (like devcontainers) might require extra setup.")

    # --- Save Config ---
    config_dir.mkdir(exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

    print(f'\nSuccessfully created configuration at "{config_file}".')

def handle_aggregate(args):
    file_cfg = load_config(args.config).get('aggregate', {})

    use_gitignore_cfg = file_cfg.get('use_gitignore', True)
    if args.use_gitignore is not None:
        use_gitignore = args.use_gitignore
    else:
        use_gitignore = use_gitignore_cfg

    config = EncoderConfig(
        directory=args.directory or file_cfg.get('directory', '.'),
        include_dirs=args.include_dir or file_cfg.get('include_dirs', []),
        include_ext=[e if e.startswith('.') else '.' +
             e for e in args.include_ext or file_cfg.get('include_ext', [])],
        include_files=args.include_file or file_cfg.get('include_files', []),
        exclude_dirs=args.exclude_dir or file_cfg.get('exclude_dirs', []),
        exclude_exts=[e if e.startswith(
            '.') else '.' + e for e in args.exclude_ext or file_cfg.get('exclude_exts', [])],
        exclude_files=args.exclude_file or file_cfg.get('exclude_files', []),
        use_gitignore=use_gitignore
    )

    # If not using gitignore, we must have some inclusion rules.
    if not config.use_gitignore and not config.include_ext and not config.include_files and not config.include_dirs:
        print("Error: No files to aggregate. Please provide inclusions in your config or via arguments, or enable 'use_gitignore'.")
        return

    service = EncoderService(config)
    service.run(full_run=args.full)


def handle_apply(args):
    file_cfg = load_config(args.config)
    output_dir_cfg = file_cfg.get('apply', {}).get('output_dir')
    changes_file_cfg = file_cfg.get('prepare', {}).get('changes')
    output_dir = args.output_dir or output_dir_cfg
    changes_file = args.changes or changes_file_cfg
    if not all([output_dir, changes_file]):
        print("Error: Missing required configuration. Provide 'output_dir' and 'changes' via CLI or config.")
        return
    launch_review_server(Path(output_dir), Path(changes_file), mode='apply')


def handle_revert(args):
    file_cfg = load_config(args.config)
    output_dir_cfg = file_cfg.get('apply', {}).get('output_dir')
    output_dir = args.output_dir or output_dir_cfg
    if not output_dir:
        print("Error: Missing required configuration. Provide 'output_dir' via CLI or config.")
        return
    
    output_dir_path = Path(output_dir)
    revert_file = output_dir_path / '.aicodec' / 'revert.json'

    if not revert_file.is_file():
        print(f"Error: Revert file not found at '{revert_file}'. Run 'aicodec apply' first.")
        return

    launch_review_server(output_dir_path, revert_file, mode='revert')


def handle_prepare(args):
    file_cfg = load_config(args.config).get('prepare', {})
    changes_path_str = args.changes or file_cfg.get(
        'changes', '.aicodec/changes.json')
    changes_path = Path(changes_path_str)
    from_clipboard = args.from_clipboard or file_cfg.get(
        'from-clipboard', False)
    if changes_path.exists() and changes_path.stat().st_size > 0:
        choice = input(
            f'\"{changes_path}\" already exists with content. Overwrite? [y/N] ').lower()
        if choice != 'y':
            print("Operation cancelled.")
            return

    changes_path.parent.mkdir(parents=True, exist_ok=True)

    if from_clipboard:
        clipboard_content = pyperclip.paste()
        if not clipboard_content:
            print("Error: Clipboard is empty.")
            return
        script_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(script_dir, 'decoder_schema.json')
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
        except FileNotFoundError as e:
            print(f"Error: Could not find a required file. {e}")
            return

        try:
            json_content = json.loads(clipboard_content)
            validate(instance=json_content, schema=schema)
        except json.JSONDecodeError:
            print(
                "Error: Clipboard content is not valid JSON. Please copy the correct output.")
            return
        except ValidationError as e:
            print(
                f"Error: Clipboard content does not match the expected schema. {e.message}")
            return
        changes_path.write_text(clipboard_content, encoding='utf-8')
        print(
            f'Successfully wrote content from clipboard to \"{changes_path}\".')
    else:
        with open(changes_path, 'w') as f:
            pass
        print(
            f'Successfully created empty file at \"{changes_path}\". Opening in default editor...')
        open_file_in_editor(changes_path)


if __name__ == "__main__":
    main()
