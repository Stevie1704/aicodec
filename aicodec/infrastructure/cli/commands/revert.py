# aicodec/infrastructure/cli/commands/revert.py
from pathlib import Path
import os
import json

from ....domain.models import Change, ChangeAction
from ...repositories.file_system_repository import FileSystemChangeSetRepository


def register_subparser(subparsers):
    parser = subparsers.add_parser("revert", help="Revert previous changes from a saved revert file.")
    parser.add_argument("-s", "--session", type=str, default=None, help="Session ID of the revert file. If not provided, uses the latest.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the revert without applying changes.")
    parser.set_defaults(func=run)


def run(args):
    project_root = Path.cwd().resolve()
    revert_dir = project_root / ".aicodec" / "reverts"
    if not revert_dir.exists():
        print("No reverts found.")
        return
    revert_files = sorted(revert_dir.glob("*.revert.json"), key=os.path.getmtime, reverse=True)
    if not revert_files:
        print("No revert files found.")
        return
    if args.session:
        session_id = args.session
        revert_file_path = revert_dir / f"{session_id}.revert.json"
        if not revert_file_path.exists():
            print(f"Revert file for session {session_id} not found.")
            return
    else:
        revert_file_path = revert_files[0]
        session_id = revert_file_path.stem
    with open(revert_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    changes = [Change.from_dict(c) for c in data.get("changes", [])]
    repo = FileSystemChangeSetRepository()
    mode = "dry-run" if args.dry_run else "revert"
    results = repo.apply_changes(changes=changes, output_dir=project_root, mode=mode, session_id=None)
    for result in results:
        status = result["status"]
        file_path = result["filePath"]
        reason = result.get("reason", "")
        action = result.get("action", "")
        print(f"{file_path}: {status} {action} {reason}".strip())
    if not args.dry_run:
        print(f"Successfully reverted session {session_id}.")
