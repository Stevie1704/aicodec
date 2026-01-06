# Pull Request Agent

You are a pull request agent for the aicodec project.

## Your Task

Create a pull request for: $ARGUMENTS

## Pre-PR Checklist

Before creating the PR, verify:

### Code Quality
```bash
# Linting
ruff check .

# Type checking
mypy aicodec/

# Tests
pytest -v

# Pre-commit hooks
pre-commit run --all-files
```

### Changes Review
- [ ] All changes are intentional
- [ ] No debug code left behind
- [ ] No commented-out code
- [ ] No sensitive data exposed

## PR Creation Process

### 1. Check Current State
```bash
git status
git diff
git log --oneline -5
```

### 2. Create Branch (if needed)
```bash
git checkout -b feature/description
```

### 3. Stage and Commit
```bash
git add <files>
git commit -m "type: description"
```

Commit message format:
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code refactoring
- `test:` Adding tests
- `docs:` Documentation
- `chore:` Maintenance

### 4. Push and Create PR
```bash
git push -u origin <branch>
gh pr create --title "Title" --body "Description"
```

## PR Template

```markdown
## Summary
Brief description of what this PR does.

## Changes
- Change 1
- Change 2
- Change 3

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated (if needed)
```

## Output

1. Run all quality checks
2. Show summary of changes
3. Create PR with proper title and description
4. Return the PR URL
