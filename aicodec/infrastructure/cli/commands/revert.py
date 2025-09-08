# aicodec/infrastructure/cli/commands/revert.py
from pathlib import Path
from typing import Any

from ....application.services import ReviewService
from ...config import load_config as load_json_config
from ...repositories.file_system_repository import FileSystemChangeSetRepository
from ...web.server import launch_review_server


def register_subparser(subparsers: Any) -> None:
    revert_parser = subparsers.add_parser(
        "revert", help="Review and revert previously applied changes."
    )
    revert_parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=".aicodec/config.json",
        help="Path to the config file.",
    )
    revert_parser.add_argument(
        "-od",
        "--output-dir",
        type=Path,
        help="The project directory to revert changes in (overrides config).",
    )
    revert_parser.set_defaults(func=run)


def run(args: Any) -> None:
    file_cfg = load_json_config(args.config)
    output_dir_cfg = file_cfg.get("apply", {}).get("output_dir")
    output_dir = args.output_dir or output_dir_cfg
    if not output_dir:
        print(
            "Error: Missing required configuration. Provide 'output_dir' via CLI or config."
        )
        return

    output_dir_path = Path(output_dir).resolve()
    revert_file = output_dir_path / ".aicodec" / "revert.json"

    if not revert_file.is_file():
        print("Error: No revert data found. Run 'aicodec apply' first.")
        return

    repo = FileSystemChangeSetRepository()
    service = ReviewService(repo, output_dir_path, revert_file, mode="revert")
    launch_review_server(service, mode="revert")
