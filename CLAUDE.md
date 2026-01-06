# CLAUDE.md

This file provides guidance for Claude Code when working with the AI Codec codebase.

## Project Overview

AI Codec is a CLI tool that provides a structured, reviewable, and reversible workflow for applying LLM-generated code changes to projects. It acts as a safe bridge between local development environments and Large Language Models.

- **Version**: 2.12.0
- **License**: MIT
- **Python**: 3.10-3.15
- **Repository**: https://github.com/Stevie1704/aicodec

## Architecture

The project follows Clean Architecture with three layers:

```
Infrastructure (CLI, Web, Repositories)
         ↕
Application (Services)
         ↕
Domain (Models, Interfaces)
```

### Directory Structure

```
aicodec/
├── domain/                    # Business logic and interfaces
│   ├── models.py             # Data models (FileItem, Change, ChangeSet, AggregateConfig)
│   └── repositories.py       # Abstract repository interfaces (IFileRepository, IChangeSetRepository)
├── application/
│   └── services.py           # AggregationService, ReviewService
├── infrastructure/
│   ├── cli/
│   │   ├── command_line_interface.py  # Main CLI entry point
│   │   └── commands/         # Individual command implementations
│   │       ├── init.py       # Initialize project configuration
│   │       ├── aggregate.py  # Aggregate files into context.json
│   │       ├── buildmap.py   # Build repository structure map
│   │       ├── prompt.py     # Generate LLM prompt
│   │       ├── prepare.py    # Prepare changes from clipboard/editor
│   │       ├── apply.py      # Review and apply changes
│   │       ├── revert.py     # Revert applied changes
│   │       ├── schema.py     # Display JSON schema
│   │       ├── update.py     # Update aicodec tool
│   │       └── utils.py      # Shared command utilities
│   ├── repositories/
│   │   └── file_system_repository.py  # File system implementations
│   ├── web/
│   │   ├── server.py         # HTTP server for review UI
│   │   └── ui/               # Frontend (HTML/CSS/JS)
│   ├── config.py             # Configuration loading
│   ├── utils.py              # Infrastructure utilities
│   └── map_generator.py      # Repository structure generator
└── assets/
    ├── decoder_schema.json   # JSON schema for LLM output
    └── prompts/              # Jinja2 prompt templates
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `init` | Initialize project with `.aicodec/config.json` |
| `aggregate` | Gather project files into JSON context |
| `buildmap` | Generate repository structure map |
| `prompt` | Generate LLM prompt with code context |
| `prepare` | Prepare changes file from clipboard/editor |
| `apply` | Web-based review and apply changes |
| `revert` | Undo previously applied changes |
| `schema` | Display JSON schema for validation |
| `update` | Update aicodec to latest version |

## Development

### Setup

```bash
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
pytest
```

### Type Checking

```bash
mypy aicodec
```

### Linting

```bash
ruff check .
ruff format .
```

## Code Conventions

### Type Hints
- Full type hints required on all function signatures
- Strict mypy configuration enforced
- Use `|` union syntax (Python 3.10+)

### Code Style
- Line length: 120 characters
- Ruff for linting and formatting
- Black-compatible formatting

### Patterns Used
- **Repository Pattern**: Abstract interfaces in `domain/repositories.py`, concrete implementations in `infrastructure/repositories/`
- **Service Pattern**: Business logic in `application/services.py`
- **Command Pattern**: Each CLI command has a `register_subparser()` function and a handler

### Adding a New Command
1. Create a new file in `aicodec/infrastructure/cli/commands/`
2. Implement `register_subparser(subparsers)` function
3. Register in `command_line_interface.py`

### Error Handling
- Use specific exception types
- Provide user-friendly error messages
- Implement security checks (e.g., directory traversal prevention)

## Key Dependencies

- **pathspec**: Gitignore-style pattern matching
- **tiktoken**: Token counting for GPT models
- **jinja2**: Prompt template rendering
- **jsonschema**: JSON schema validation
- **pyperclip**: Clipboard integration
- **rich**: Terminal formatting

## Testing

- Framework: pytest
- Coverage: pytest-cov
- Tests located in `tests/` directory
- Run with `pytest` or `pytest --cov=aicodec`

## Configuration

Project configuration is stored in `.aicodec/config.json` with options for:
- Include/exclude patterns (glob and gitignore syntax)
- Directories to scan
- Plugin configurations
- Token counting settings

## Important Files

- `pyproject.toml`: Package configuration, dependencies, tool settings
- `.pre-commit-config.yaml`: Pre-commit hooks (ruff, bandit, yamllint)
- `mkdocs.yml`: Documentation site configuration
- `assets/decoder_schema.json`: JSON schema for LLM-generated changes
