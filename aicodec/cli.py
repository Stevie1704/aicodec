# aicodec/cli.py
import argparse
from pathlib import Path
from aicodec.core.config import EncoderConfig, load_config
from aicodec.services.encoder_service import EncoderService
from aicodec.review_server import launch_review_server


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
    parser.add_argument('--full', action='store_true',
                        help="Perform a full aggregation, ignoring previous hashes.")
    args = parser.parse_args()

    file_cfg = load_config(args.config).get('aggregate', {})

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
    parser = argparse.ArgumentParser(
        description="AI Codec Review and Apply UI")
    parser.add_argument('-c', '--config', type=str,
                        default='.aicodec/config.json',
                        help="Path to the config file.")
    parser.add_argument('-od', '--output-dir', type=Path,
                        help="The project directory to apply changes to (overrides config).")
    parser.add_argument('--changes', type=Path,
                        help="Path to the LLM changes JSON file (overrides config).")
    args = parser.parse_args()

    file_cfg = load_config(args.config).get('apply', {})

    # Prioritize CLI arguments, then fall back to config file values
    output_dir = args.output_dir or file_cfg.get('output_dir')
    changes_file = args.changes or file_cfg.get('changes')

    # Check if all required configurations are present
    if not all([output_dir, changes_file]):
        parser.error(
            "Missing required configuration. Provide 'output_dir' and 'changes' via CLI arguments or in the 'apply' section of your config file.")

    launch_review_server(Path(output_dir), Path(changes_file))


if __name__ == "__main__":
    aggregate_main()
