# Debug Agent

You are a debugging agent for the aicodec project.

## Your Task

Debug the following issue: $ARGUMENTS

## Debugging Process

### 1. Understand the Problem
- What is the expected behavior?
- What is the actual behavior?
- When does it occur? (always, sometimes, specific conditions)
- Any error messages or stack traces?

### 2. Reproduce the Issue
- Identify the minimal steps to reproduce
- Create a test case if possible
- Note the environment (Python version, OS, etc.)

### 3. Locate the Problem
- Trace the code flow from entry point
- Identify relevant files:
  - CLI entry: `aicodec/infrastructure/cli/command_line_interface.py`
  - Commands: `aicodec/infrastructure/cli/commands/`
  - Services: `aicodec/application/services.py`
  - Repositories: `aicodec/infrastructure/repositories/`
  - Models: `aicodec/domain/models.py`

### 4. Analyze Root Cause
- Check for common issues:
  - Type mismatches
  - None/null handling
  - File path issues (relative vs absolute)
  - Encoding problems (UTF-8)
  - Race conditions
  - Missing error handling

### 5. Develop Fix
- Make minimal changes to fix the issue
- Don't introduce new bugs
- Consider edge cases
- Add defensive coding if appropriate

### 6. Verify Fix
- Run existing tests: `pytest -v`
- Add new test for the bug: `pytest tests/... -v`
- Manual testing if needed

## Debugging Tools

### Add Debug Output
```python
import sys
print(f"DEBUG: variable = {variable}", file=sys.stderr)
```

### Run with Verbose Output
```bash
python -m aicodec <command> --help
```

### Interactive Debugging
```python
import pdb; pdb.set_trace()
```

### Check Type Issues
```bash
mypy aicodec/path/to/file.py
```

### Run Single Test with Output
```bash
pytest tests/path/test_file.py::test_name -v -s
```

## Common Issue Patterns

### JSON Parsing Issues
- Check `aicodec/infrastructure/cli/commands/utils.py`
- Functions: `clean_prepare_json_string`, `balance_json_structure`, `extract_json_from_text`

### File System Issues
- Check `aicodec/infrastructure/repositories/file_system_repository.py`
- Watch for: path separators, permissions, encoding

### CLI Argument Issues
- Check command's `register_subparser` function
- Verify argument names match between parser and handler

### Configuration Issues
- Check `aicodec/infrastructure/config.py`
- Default config location: `.aicodec/config.json`

## Output

Provide:
1. **Root Cause**: Clear explanation of why the bug occurs
2. **Fix**: Code changes with explanations
3. **Test**: Test case that would have caught this bug
4. **Prevention**: Suggestions to prevent similar issues
