# aicodec/cli.py
import argparse
import os
from aicodec.core.config import EncoderConfig, DecoderConfig, load_config
from aicodec.services.encoder_service import EncoderService
from aicodec.services.decoder_service import DecoderService


def encode_main():
    parser = argparse.ArgumentParser(description="AI Codec Encoder")
    parser.add_argument('-c', '--config', type=str,
                        default='.aicodec-config.json')
    parser.add_argument('-d', '--dir', type=str)
    parser.add_argument('-o', '--output', type=str)
    parser.add_argument('-e', '--ext', action='append', default=[])
    parser.add_argument('-f', '--file', action='append', default=[])
    parser.add_argument('--exclude-dir', action='append', default=[])
    parser.add_argument('--exclude-ext', action='append', default=[])
    parser.add_argument('--exclude-file', action='append', default=[])
    args = parser.parse_args()

    file_cfg = load_config(args.config).get('encoder', {})

    config = EncoderConfig(
        directory=args.dir or file_cfg.get('dir', '.'),
        output=args.output or file_cfg.get(
            'output', 'aggregated_content.json'),
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
    service.run()


def decode_main():
    parser = argparse.ArgumentParser(description="AI Codec Decoder")
    parser.add_argument('-c', '--config', type=str,
                        default='.aicodec-config.json')
    parser.add_argument('-i', '--input', type=str)
    parser.add_argument('-od', '--output-dir', type=str)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('-y', '--yes', action='store_true')
    args = parser.parse_args()

    file_cfg = load_config(args.config).get('decoder', {})

    input_file = args.input or file_cfg.get('input')
    if not input_file:
        parser.error(
            "No input file specified. Provide it via --input or in the config file.")

    output_dir = args.output_dir or file_cfg.get('output_dir')
    if not output_dir:
        output_dir = os.path.dirname(os.path.abspath(input_file))

    config = DecoderConfig(input=input_file, output_dir=output_dir)
    service = DecoderService(config)
    service.run(dry_run=args.dry_run, auto_confirm=args.yes)
