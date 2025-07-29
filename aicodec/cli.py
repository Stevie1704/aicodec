# aicodec/cli.py
import argparse
import json
import pyperclip
from pathlib import Path
from aicodec.core.config import EncoderConfig, load_config
from aicodec.services.encoder_service import EncoderService
from aicodec.review_server import launch_review_server
from aicodec.utils import open_file_in_editor

def aggregate_main():
    parser = argparse.ArgumentParser(description="AI Codec Aggregator")
    parser.add_argument('-c', '--config', type=str,
                        default='.aicodec/config.json')
    parser.add_argument('-d', '--dir', type=str)
    parser.add_argument('-e', '--ext', action='append', default=[])
    parser.add_argument('-f', '--file', action='append', default=[])
    parser.add_argument('--exclude-dir', action='append', default=[])
    parser.add_argument('--exclude-ext', action='append', default=[])
    parser.add_argument('--exclude-file', action='append', default=[])
    parser.add_argument('--full', action='store_true', help="Perform a full aggregation, ignoring previous hashes.")
    args = parser.parse_args()

    file_cfg = load_config(args.config).get('encoder', {})

    config = EncoderConfig(
        directory=args.dir or file_cfg.get('dir', '.'),
        ext=[e if e.startswith('.') else '.' +
             e for e in args.ext or file_cfg.get('ext', [])],
        file=args.file or file_cfg.get('file', []),
        exclude_dirs=args.exclude_dir or file_cfg.get('exclude_dirs', []),
        exclude_exts=[e if e.startswith(
            '.') else '.' + e for e in args.exclude_ext or file_cfg.get('exclude_exts', [])],
        exclude_files=args.exclude_file or file_cfg.get('exclude_files', [])
    )

    if not config.ext and not config.file:
        parser.error(
            "No files to aggregate. Please provide inclusions in your config or via arguments.")

    service = EncoderService(config)
    service.run(full_run=args.full)

def review_and_apply_main():
    parser = argparse.ArgumentParser(description="AI Codec Review and Apply UI")
    parser.add_argument('-c', '--config', type=str,
                        default='.aicodec/config.json',
                        help="Path to the config file.")
    parser.add_argument('-od', '--output-dir', type=Path,
                        help="The project directory to apply changes to (overrides config).")
    parser.add_argument('--changes', type=Path,
                        help="Path to the LLM changes JSON file (overrides config).")
    args = parser.parse_args()

    file_cfg = load_config(args.config).get('review', {})

    # Prioritize CLI arguments, then fall back to config file values
    output_dir = args.output_dir or file_cfg.get('output_dir')
    changes_file = args.changes or file_cfg.get('changes')

    # Check if all required configurations are present
    if not all([output_dir, changes_file]):
        parser.error(
            "Missing required configuration. Provide 'output_dir', and 'changes' via CLI arguments or in the 'review' section of your config file.")

    launch_review_server(Path(output_dir), Path(changes_file))

def prepare_main():
    parser = argparse.ArgumentParser(description="Prepares the changes file for LLM output.")
    parser.add_argument('-c', '--config', type=str, default='.aicodec/config.json', help="Path to the config file.")
    parser.add_argument('--changes', type=Path, help="Path to the LLM changes JSON file (overrides config).")
    parser.add_argument('--from-clipboard', action='store_true', help="Paste content directly from the system clipboard.")
    args = parser.parse_args()

    file_cfg = load_config(args.config).get('review', {})
    changes_path_str = args.changes or file_cfg.get('changes', '.aicodec/changes.json')
    changes_path = Path(changes_path_str)

    if changes_path.exists() and changes_path.stat().st_size > 0:
        choice = input(f'"{changes_path}" already exists with content. Overwrite? [y/N] ').lower()
        if choice != 'y':
            print("Operation cancelled.")
            return
    
    changes_path.parent.mkdir(parents=True, exist_ok=True)

    if args.from_clipboard:
        clipboard_content = pyperclip.paste()
        if not clipboard_content:
            print("Error: Clipboard is empty.")
            return
        try:
            # Validate that the content is valid JSON before writing
            json.loads(clipboard_content)
        except json.JSONDecodeError:
            print("Error: Clipboard content is not valid JSON. Please copy the correct output.")
            return
        
        changes_path.write_text(clipboard_content, encoding='utf-8')
        print(f'Successfully wrote content from clipboard to "{changes_path}".')
    else:
        # Creates or truncates the file to be empty
        with open(changes_path, 'w') as f:
            pass
        print(f'Successfully created empty file at "{changes_path}". Opening in default editor...')
        open_file_in_editor(changes_path)

if __name__ == "__main__":
    pass
