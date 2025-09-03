# aicodec/infrastructure/cli/commands/aggregate.py
from pathlib import Path

from ....domain.models import AggregateConfig
from ....application.services import AggregationService
from ...repositories.file_system_repository import FileSystemFileRepository
from ...config import load_config as load_json_config


def register_subparser(subparsers):
    agg_parser = subparsers.add_parser(
        "aggregate", help="Aggregate project files into a JSON context."
    )
    agg_parser.add_argument("-c", "--config", type=str,
                            default=".aicodec/config.json")
    agg_parser.add_argument(
        "-d", "--directory", type=str, help="The root directory to scan."
    )
    agg_parser.add_argument(
        "--include-dir",
        action="append",
        default=[],
        help="Specific directories to include, overriding exclusions.",
    )
    agg_parser.add_argument(
        "--include-ext", action="append", default=[], help="File extensions to include."
    )
    agg_parser.add_argument(
        "--include-file",
        action="append",
        default=[],
        help="Specific files or glob patterns to include.",
    )
    agg_parser.add_argument("--exclude-dir", action="append", default=[])
    agg_parser.add_argument("--exclude-ext", action="append", default=[])
    agg_parser.add_argument("--exclude-file", action="append", default=[])
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


def run(args):
    file_cfg = load_json_config(args.config).get("aggregate", {})

    use_gitignore_cfg = file_cfg.get("use_gitignore", True)
    if args.use_gitignore is not None:
        use_gitignore = args.use_gitignore
    else:
        use_gitignore = use_gitignore_cfg

    project_root = Path.cwd().resolve()
    scan_dir = project_root / Path(args.directory or file_cfg.get("directory", ".")).resolve()
    config = AggregateConfig(
        directory=scan_dir,
        include_dirs=args.include_dir or file_cfg.get("include_dirs", []),
        include_ext=[
            e if e.startswith(".") else "." + e
            for e in args.include_ext or file_cfg.get("include_ext", [])
        ],
        include_files=args.include_file or file_cfg.get("include_files", []),
        exclude_dirs=args.exclude_dir or file_cfg.get("exclude_dirs", []),
        exclude_exts=[
            e if e.startswith(".") else "." + e
            for e in args.exclude_ext or file_cfg.get("exclude_exts", [])
        ],
        exclude_files=args.exclude_file or file_cfg.get("exclude_files", []),
        use_gitignore=use_gitignore,
        project_root=project_root,
    )

    if (
        not config.use_gitignore
        and not config.include_ext
        and not config.include_files
        and not config.include_dirs
    ):
        print(
            "Error: No files to aggregate. Please provide inclusions in your config or via arguments, or enable 'use_gitignore'."
        )
        return

    repo = FileSystemFileRepository()
    service = AggregationService(repo, config, project_root=project_root)
    service.aggregate(full_run=args.full, count_tokens=args.count_tokens)
