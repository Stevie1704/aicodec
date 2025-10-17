# aicodec/infrastructure/cli/command_line_interface.py
import argparse
import sys
from pathlib import Path

from aicodec import __version__

from .commands import (
    aggregate,
    apply,
    buildmap,
    init,
    prepare,
    prompt,
    revert,
    schema,
)


def check_config_exists(config_path_str: str) -> None:
    """Checks if the config file exists and exits if it doesn't."""
    config_path = Path(config_path_str)
    if not config_path.is_file():
        print(
            "aicodec not initialised for this folder. Please run aicodec init before or change the directory."
        )
        sys.exit(1)


def main() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="A lightweight communication layer for developers to interact with LLMs."
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )

    # Register all commands
    init.register_subparser(subparsers)
    schema.register_subparser(subparsers)
    aggregate.register_subparser(subparsers)
    buildmap.register_subparser(subparsers)
    prompt.register_subparser(subparsers)
    apply.register_subparser(subparsers)
    revert.register_subparser(subparsers)
    prepare.register_subparser(subparsers)

    args = parser.parse_args()

    # If --version was not used and no command was given, show help and exit.
    if not args.command:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.command not in ["init", "schema"]:
        check_config_exists(args.config)

    # Call the function associated with the command
    args.func(args)


if __name__ == "__main__":
    main()
