# aicodec/infrastructure/cli/commands/aggregate.py
from pathlib import Path
from typing import Any

from ....application.services import AggregationService
from ....domain.models import AggregateConfig
from ...config import load_config as load_json_config
from ...repositories.file_system_repository import FileSystemFileRepository


def register_subparser(subparsers: Any) -> None:
    agg_parser = subparsers.add_parser(
        "aggregate", help="Aggregate project files into a JSON context."
    )
    agg_parser.add_argument("-c", "--config", type=str,
                            default=".aicodec/config.json")
    agg_parser.add_argument(
        "-d", "--directory",
        type=str,
        help="The root directory to scan."
    )
    agg_parser.add_argument(
        "--include-dirs",
        action="append",
        default=[],
        help="Specific directories to include, overriding exclusions.",
    )
    agg_parser.add_argument(
        "--include-exts",
        action="append",
        default=[],
        help="File extensions to include."
    )
    agg_parser.add_argument(
        "--include-files",
        action="append",
        default=[],
        help="Specific files or glob patterns to include.",
    )
    agg_parser.add_argument("--exclude-dirs",
                            action="append",
                            default=[],
                            help="Specific directories to exclude."
                            )
    agg_parser.add_argument("--exclude-exts",
                            action="append",
                            default=[],
                            help="File extensions to exclude."
                            )
    agg_parser.add_argument("--exclude-files",
                            action="append",
                            default=[],
                            help="Specific files or glob patterns to exclude."
                            )
    agg_parser.add_argument(
        "--full",
        action="store_true",
        help="Perform a full aggregation, ignoring previous hashes.",
    )
    agg_parser.add_argument(
        "--count-tokens",
        action="store_true",
        help="Count and display the number of tokens in the aggregated output.",
    )
    gitignore_group = agg_parser.add_mutually_exclusive_group()
    gitignore_group.add_argument(
        "--use-gitignore",
        action="store_true",
        dest="use_gitignore",
        default=None,
        help="Explicitly use .gitignore for exclusions (default). Overrides config.",
    )
    gitignore_group.add_argument(
        "--no-gitignore",
        action="store_false",
        dest="use_gitignore",
        help="Do not use .gitignore for exclusions. Overrides config.",
    )
    agg_parser.set_defaults(func=run)


def run(args: Any) -> None:
    file_cfg = load_json_config(args.config).get("aggregate", {})

    use_gitignore_cfg = file_cfg.get("use_gitignore", True)
    if args.use_gitignore is not None:
        use_gitignore = args.use_gitignore
    else:
        use_gitignore = use_gitignore_cfg

    project_root = Path.cwd().resolve()
    scan_dir = project_root / \
        Path(args.directory or file_cfg.get("directory", ".")).resolve()
    exclude_dirs = args.exclude_dirs + file_cfg.get("exclude_dirs", [])
    # Always exclude .aicodec and .git directories
    exclude_dirs.extend([".aicodec", ".git"])
    config = AggregateConfig(
        directory=scan_dir,
        include_dirs=args.include_dirs or file_cfg.get("include_dirs", []),
        include_ext=[
            e if e.startswith(".") else "." + e
            for e in args.include_exts or file_cfg.get("include_exts", [])
        ],
        include_files=args.include_files or file_cfg.get("include_files", []),
        exclude_dirs=exclude_dirs,
        exclude_exts=[
            e if e.startswith(".") else "." + e
            for e in args.exclude_exts or file_cfg.get("exclude_exts", [])
        ],
        exclude_files=args.exclude_files or file_cfg.get("exclude_files", []),
        use_gitignore=use_gitignore,
        project_root=project_root,
    )

    repo = FileSystemFileRepository()
    service = AggregationService(repo, config, project_root=project_root)
    service.aggregate(full_run=args.full, count_tokens=args.count_tokens)
