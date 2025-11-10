import uuid
from pathlib import Path
from typing import Any

from ....application.services import ReviewService
from ...config import load_config as load_json_config
from ...repositories.file_system_repository import FileSystemChangeSetRepository
from ...web.server import launch_review_server
from .utils import clean_prepare_json_string


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
    apply_parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Apply all changes directly without launching the review UI.",
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
    if not Path(changes_file).exists():
        print(f"Error: Changes file '{changes_file}' not found.")
        return

    # logic doubled, if someone directly copies json from llm to changes file
    changes_json_str = clean_prepare_json_string(
        Path(changes_file).read_text(encoding="utf-8"))
    Path(changes_file).write_text(changes_json_str, encoding="utf-8")

    repo = FileSystemChangeSetRepository()
    service = ReviewService(
        repo, Path(output_dir).resolve(), Path(changes_file).resolve(), mode="apply"
    )

    if args.all:
        session_id = str(uuid.uuid4())
        print(f"Starting new apply session: {session_id}")
        print("Applying all changes without review...")
        context = service.get_review_context()
        changes_to_apply = context.get("changes", [])

        if not changes_to_apply:
            print("No changes to apply.")
            return

        changes_payload = [
            {
                "filePath": c["filePath"],
                "action": c["action"],
                "content": c["proposed_content"],
            }
            for c in changes_to_apply
        ]

        results = service.apply_changes(changes_payload, session_id)

        success_count = sum(1 for r in results if r["status"] == "SUCCESS")
        skipped_count = sum(1 for r in results if r["status"] == "SKIPPED")
        failure_count = sum(1 for r in results if r["status"] == "FAILURE")

        print(
            f"Apply complete. {success_count} succeeded, {skipped_count} skipped, {failure_count} failed."
        )
        if failure_count > 0:
            print("Failures:")
            for r in results:
                if r["status"] == "FAILURE":
                    print(f"  - {r['filePath']}: {r['reason']}")
    else:
        launch_review_server(service, mode="apply")
