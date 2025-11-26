from pathlib import Path
from typing import Any

from ....application.services import ReviewService
from ...config import load_config as load_json_config
from ...repositories.file_system_repository import FileSystemChangeSetRepository
from ...web.server import launch_review_server


def register_subparser(subparsers: Any) -> None:
    revert_parser = subparsers.add_parser("revert", help="Review and revert previously applied changes.")
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
    revert_parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Revert all changes directly without launching the review UI.",
    )
    revert_parser.add_argument(
        "-f",
        "--files",
        type=str,
        nargs="+",
        help="Revert changes only for the specified file(s). Accepts one or more file paths.",
    )
    revert_parser.set_defaults(func=run)


def run(args: Any) -> None:
    file_cfg = load_json_config(args.config)
    output_dir_cfg = file_cfg.get("apply", {}).get("output_dir")
    output_dir = args.output_dir or output_dir_cfg
    if not output_dir:
        print("Error: Missing required configuration. Provide 'output_dir' via CLI or config.")
        return

    output_dir_path = Path(output_dir).resolve()
    aicodec_root = Path(args.config).resolve().parent.parent  # .aicodec/config.json -> .aicodec -> project root
    reverts_dir = aicodec_root / ".aicodec" / "reverts"

    # Check for revert files
    if not reverts_dir.exists():
        print("Error: No revert data found. Run 'aicodec apply' first.")
        return

    revert_files = sorted(reverts_dir.glob("revert-*.json"), reverse=True)  # Newest first

    if not revert_files:
        print("Error: No revert data found. Run 'aicodec apply' first.")
        return

    print(f"Found {len(revert_files)} apply operation(s) to revert.")

    repo = FileSystemChangeSetRepository()

    if args.all or args.files:
        if args.files:
            print(f"Reverting changes for {len(args.files)} file(s) across all sessions...")
        else:
            print("Reverting all changes from entire session...")

        all_results = []
        total_changes_reverted = 0

        # Process each revert file in reverse order (newest first)
        for revert_file in revert_files:
            print(f"\nProcessing {revert_file.name}...")

            service = ReviewService(repo, output_dir_path, revert_file, aicodec_root, mode="revert")
            context = service.get_review_context()
            changes_to_revert = context.get("changes", [])

            if not changes_to_revert:
                print(f"  No changes in {revert_file.name}")
                continue

            # Filter changes if specific files were requested
            if args.files:
                target_files = {Path(f).as_posix() for f in args.files}
                changes_to_revert = [c for c in changes_to_revert if Path(c["filePath"]).as_posix() in target_files]

                if not changes_to_revert:
                    print(f"  No matching changes in {revert_file.name}")
                    continue

            print(f"  Reverting {len(changes_to_revert)} change(s)...")

            changes_payload = [
                {
                    "filePath": c["filePath"],
                    "action": c["action"],
                    "content": c["proposed_content"],
                }
                for c in changes_to_revert
            ]

            # In revert mode, session_id is None
            results = service.apply_changes(changes_payload, None)
            all_results.extend(results)
            total_changes_reverted += len([r for r in results if r["status"] == "SUCCESS"])

            # Delete the revert file after successful processing
            success_count = sum(1 for r in results if r["status"] == "SUCCESS")
            if success_count > 0:
                revert_file.unlink()
                print(f"  Deleted {revert_file.name}")

        # Summary
        total_success = sum(1 for r in all_results if r["status"] == "SUCCESS")
        total_skipped = sum(1 for r in all_results if r["status"] == "SKIPPED")
        total_failure = sum(1 for r in all_results if r["status"] == "FAILURE")

        print(f"\nRevert complete. {total_success} succeeded, {total_skipped} skipped, {total_failure} failed.")
        if total_failure > 0:
            print("Failures:")
            for r in all_results:
                if r["status"] == "FAILURE":
                    print(f"  - {r['filePath']}: {r['reason']}")

        # Check if reverts directory is empty and delete it
        if not any(reverts_dir.iterdir()):
            reverts_dir.rmdir()
            print("\nAll reverts completed. Cleared reverts directory.")
    else:
        # Use UI mode - use the newest revert file
        newest_revert = revert_files[0]
        print(f"Opening review UI for {newest_revert.name}...")
        service = ReviewService(repo, output_dir_path, newest_revert, aicodec_root, mode="revert")
        launch_review_server(service, mode="revert")
