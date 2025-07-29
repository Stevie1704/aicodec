# aicodec/cli.py
import argparse
from pathlib import Path
from aicodec.core.config import EncoderConfig, load_config
from aicodec.services.encoder_service import EncoderService
from aicodec.review_server import launch_review_server

def aggregate_main():
    parser = argparse.ArgumentParser(description="AI Codec Aggregator")
    parser.add_argument('-c', '--config', type=str,
                        default='.aicodec-config.json')
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
    parser.add_argument('-od', '--output-dir', type=Path, required=True,
                        help="The project directory to apply changes to.")
    parser.add_argument('--original', type=Path, required=True,
                        help="Path to the original context JSON file. (e.g., .aicodec/context.json)")
    parser.add_argument('--changes', type=Path, required=True,
                        help="Path to the LLM changes JSON file.")
    args = parser.parse_args()

    launch_review_server(args.output_dir, args.original, args.changes)


if __name__ == "__main__":
    pass
