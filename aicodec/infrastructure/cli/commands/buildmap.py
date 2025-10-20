# aicodec/infrastructure/cli/commands/buildmap.py
from pathlib import Path
from typing import Any

from ....domain.models import AggregateConfig
from ...map_generator import generate_repo_map
from ...repositories.file_system_repository import FileSystemFileRepository


def register_subparser(subparsers: Any) -> None:
    """Registers the 'buildmap' subparser."""
    buildmap_parser = subparsers.add_parser(
        "buildmap",
        help="Build a map of the repository structure, respecting .gitignore.",
    )
    buildmap_parser.add_argument(
        "-c", "--config", type=str,
        default=".aicodec/config.json",
        help="Path to the config file (used for .aicodec directory location)."
    )
    gitignore_group = buildmap_parser.add_mutually_exclusive_group()
    gitignore_group.add_argument(
        "--use-gitignore",
        action="store_true",
        dest="use_gitignore",
        default=True,
        help="Explicitly use .gitignore for exclusions (default).",
    )
    gitignore_group.add_argument(
        "--no-gitignore",
        action="store_false",
        dest="use_gitignore",
        help="Do not use .gitignore for exclusions.",
    )
    buildmap_parser.set_defaults(func=run)


def run(args: Any) -> None:
    """Runs the buildmap command."""
    project_root = Path.cwd().resolve()

    # For buildmap, we ignore include/exclude from config.json, we want the whole repo structure.
    config = AggregateConfig(
        directories=[project_root],
        include=[],
        exclude=[],  # Hardcoded excludes (.git, .aicodec) are handled in the repo.
        use_gitignore=args.use_gitignore,
        project_root=project_root,
    )

    repo = FileSystemFileRepository()
    # discover_files reads content, which we don't need, but it's the simplest
    # way to reuse the complex file filtering logic.
    discovered_files = repo.discover_files(config)

    if not discovered_files:
        print("No files found to build repository map.")
        return

    file_paths = [item.file_path for item in discovered_files]
    repo_map_content = generate_repo_map(file_paths)

    output_dir = project_root / '.aicodec'
    output_dir.mkdir(exist_ok=True)
    repo_map_file = output_dir / 'repo_map.md'

    repo_map_file.write_text(repo_map_content, encoding='utf-8')
    print(f"Successfully created repository map at '{repo_map_file}'.")
