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
        "-d", "--directories",
        nargs="+",
        type=str,
        help="One or more root directories to scan, overriding config."
    )
    agg_parser.add_argument(
        "-i", "--include",
        action="extend",
        nargs="+",
        default=[],
        help="Specific files or glob patterns to include (gitignore-style).",
    )
    agg_parser.add_argument(
        "-e", "--exclude",
        action="extend",
        nargs="+",
        default=[],
        help="Specific files or glob patterns to exclude (gitignore-style)."
    )
    agg_parser.add_argument(
        "-f", "--full",
        action="store_true",
        help="Perform a full aggregation, ignoring previous hashes.",
    )
    agg_parser.add_argument(
        "--plugin",
        action="extend",
        nargs="+",
        default=[],
        help="Define a plugin on the fly, e.g., '.ext=command {file}'. Overrides config plugins.",
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

    # Handle both "directories" (new) and "directory" (old) for backward compatibility
    if "directories" in file_cfg:
        config_dirs = file_cfg["directories"]
    elif "directory" in file_cfg:
        config_dirs = [file_cfg["directory"]]
    else:
        config_dirs = ["."]

    scan_dirs_str = args.directories or config_dirs
    scan_dirs = []
    for d in scan_dirs_str:
        path = Path(d)
        if path.is_absolute():
            scan_dirs.append(path.resolve())
        else:
            scan_dirs.append((project_root / path).resolve())

    # Process and merge plugins
    config_plugins = {}
    for p_str in file_cfg.get("plugins", []):
        if "=" in p_str:
            ext, command = p_str.split("=", 1)
            config_plugins[ext.strip()] = command.strip()

    cli_plugins = {}
    for p_str in args.plugin:
        if "=" in p_str:
            ext, command = p_str.split("=", 1)
            cli_plugins[ext.strip()] = command.strip()
    
    # CLI plugins override config plugins
    merged_plugins_map = {**config_plugins, **cli_plugins}
    final_plugins = [{ext: cmd} for ext, cmd in merged_plugins_map.items()]

    config = AggregateConfig(
        directories=scan_dirs,
        include=args.include or file_cfg.get("include", []),
        exclude=args.exclude + file_cfg.get("exclude", []),
        plugins=final_plugins,
        use_gitignore=use_gitignore,
        project_root=project_root,
    )

    repo = FileSystemFileRepository()
    service = AggregationService(repo, config, project_root=project_root)
    service.aggregate(full_run=args.full, count_tokens=args.count_tokens)
