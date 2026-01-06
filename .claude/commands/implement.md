# Implementation Agent

You are an implementation agent for the aicodec project - a CLI tool for applying LLM-generated code changes.

## Your Task

Implement the following feature or change: $ARGUMENTS

## Project Context

- **Architecture**: Clean Architecture (domain -> application -> infrastructure)
- **Language**: Python 3.10+
- **Key Directories**:
  - `aicodec/domain/` - Models and interfaces
  - `aicodec/application/` - Services
  - `aicodec/infrastructure/cli/commands/` - CLI commands
  - `aicodec/infrastructure/repositories/` - Data access
  - `tests/` - Test files

## Implementation Guidelines

1. **Before coding**:
   - Search the codebase to understand existing patterns
   - Check for similar implementations to follow conventions
   - Identify which layer(s) need changes

2. **Code style**:
   - Full type hints on all functions
   - Line length: 120 characters
   - Follow existing patterns (Repository, Service, Command patterns)
   - Use `|` for union types (Python 3.10+)

3. **For new CLI commands**:
   - Create file in `aicodec/infrastructure/cli/commands/`
   - Implement `register_subparser(subparsers)` function
   - Register in `command_line_interface.py`

4. **For domain changes**:
   - Add models to `aicodec/domain/models.py`
   - Add interfaces to `aicodec/domain/repositories.py`

5. **Testing**:
   - Write tests alongside implementation
   - Follow pytest conventions
   - Place tests in corresponding `tests/` subdirectory

6. **After implementation**:
   - Run `ruff check .` for linting
   - Run `mypy aicodec/` for type checking
   - Run `pytest` to verify tests pass

## Output

Provide a complete implementation with:
- All necessary code changes
- Corresponding tests
- Brief explanation of design decisions
