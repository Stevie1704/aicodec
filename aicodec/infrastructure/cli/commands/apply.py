# aicodec/infrastructure/cli/commands/apply.py
from pathlib import Path
from typing import Any

from ....application.services import ReviewService
from ...config import load_config as load_json_config
from ...repositories.file_system_repository import FileSystemChangeSetRepository
from ...web.server import launch_review_server


def register_subparser(subparsers: Any) -> None:
    apply_parser = subparsers.add_parser(
        "apply", help="Review and apply changes from an LLM."
    )
    apply_parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=".aicodec/config.json",
        help="Path to the config file.",
    )
    apply_parser.add_argument(
        "-od",
        "--output-dir",
        type=Path,
        help="The project directory to apply changes to (overrides config).",
    )
    apply_parser.add_argument(
        "--changes",
        type=Path,
        help="Path to the LLM changes JSON file (overrides config).",
    )
    apply_parser.set_defaults(func=run)


def run(args: Any) -> None:
    file_cfg = load_json_config(args.config)
    output_dir_cfg = file_cfg.get("apply", {}).get("output_dir")
    changes_file_cfg = file_cfg.get("prepare", {}).get("changes")
    output_dir = args.output_dir or output_dir_cfg
    changes_file = args.changes or changes_file_cfg
    if not all([output_dir, changes_file]):
        print(
            "Error: Missing required configuration. Provide 'output_dir' and 'changes' via CLI or config."
        )
        return

    repo = FileSystemChangeSetRepository()
    service = ReviewService(
        repo, Path(output_dir).resolve(), Path(changes_file).resolve(), mode="apply"
    )
    launch_review_server(service, mode="apply")
