# aicodec/infrastructure/cli/command_line_interface.py
import argparse
import sys
from pathlib import Path

from .commands import (
    aggregate,
    apply,
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
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    # Register all commands
    init.register_subparser(subparsers)
    schema.register_subparser(subparsers)
    aggregate.register_subparser(subparsers)
    prompt.register_subparser(subparsers)
    apply.register_subparser(subparsers)
    revert.register_subparser(subparsers)
    prepare.register_subparser(subparsers)

    args = parser.parse_args()

    if args.command not in ["init", "schema"]:
        check_config_exists(args.config)

    # Call the function associated with the command
    args.func(args)


if __name__ == "__main__":
    main()
