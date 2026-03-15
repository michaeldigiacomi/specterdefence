# Contributing to SpecterDefence

Thank you for your interest in contributing to SpecterDefence! This document outlines our development process and coding standards.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Quality Standards](#code-quality-standards)
- [Linting Rules](#linting-rules)
- [Type Checking](#type-checking)
- [Submitting Changes](#submitting-changes)
- [Pre-commit Hooks](#pre-commit-hooks)

---

## Development Setup

### Prerequisites

- Python 3.11 or 3.12
- Git

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/bluedigiacomi/specterdefence.git
cd specterdefence

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

---

## Code Quality Standards

### Zero Tolerance Policy

**We have a ZERO TOLERANCE policy for linting errors.** All code must pass strict linting checks before being merged.

The CI pipeline will **FAIL** if ANY of the following checks fail:

- Ruff linting
- Black formatting
- MyPy type checking
- Import sorting

---

## Linting Rules

### Ruff (Python Linter)

We use Ruff with a comprehensive set of rules enabled. The following rule categories are active:

| Category | Code | Description |
|----------|------|-------------|
| **Pyflakes** | `F` | Basic Python errors (undefined names, unused imports) |
| **pycodestyle** | `E`, `W` | PEP 8 style conventions |
| **isort** | `I` | Import sorting and organization |
| **pep8-naming** | `N` | Naming conventions (snake_case, PascalCase) |
| **pyupgrade** | `UP` | Modern Python syntax upgrades |
| **bugbear** | `B` | Common bugs and design problems |
| **comprehensions** | `C4` | List/dict/set comprehension best practices |
| **simplify** | `SIM` | Code simplification suggestions |
| **security** | `S` | Security vulnerability detection (bandit) |
| **complexity** | `C90` | McCabe cyclomatic complexity limits |
| **pylint** | `PL` | Additional code quality checks |
| **annotations** | `ANN` | Type annotation requirements |
| **quotes** | `Q` | Quote consistency |
| **debugger** | `T10` | Debugger statement detection |
| **print** | `T20` | Print statement detection |

#### Complexity Limits

- **Maximum cyclomatic complexity: 10**
- Functions exceeding this limit must be refactored

#### Running Ruff

```bash
# Check all files
ruff check .

# Check with auto-fix
ruff check . --fix

# Check specific rules
ruff check . --select B,S
```

---

## Type Checking

### MyPy Configuration

We use **strict** MyPy configuration with the following requirements:

| Option | Setting | Description |
|--------|---------|-------------|
| `disallow_untyped_defs` | `true` | All functions must have type annotations |
| `disallow_incomplete_defs` | `true` | All parameters and returns must be typed |
| `disallow_any_generics` | `true` | Generic types must specify type parameters |
| `no_implicit_optional` | `true` | Optional types must be explicit |
| `warn_return_any` | `true` | Warn when returning `Any` |
| `warn_unused_configs` | `true` | Warn about unused mypy config |
| `strict_equality` | `true` | Strict equality checks |

### Type Annotation Requirements

All functions must have complete type annotations:

```python
# ✅ GOOD - Fully typed
def get_user(user_id: int) -> User:
    return User.query.get(user_id)

# ❌ BAD - Missing types
def get_user(user_id):
    return User.query.get(user_id)

# ✅ GOOD - Complex types
def process_items(
    items: list[dict[str, Any]],
    options: dict[str, bool] | None = None
) -> tuple[list[Item], int]:
    ...
```

### Running MyPy

```bash
# Check src directory
mypy src/

# Check with strict mode (CI does this)
mypy src/ tests/ --strict
```

---

## Code Formatting

### Black Configuration

- **Line length: 100 characters**
- **Target Python versions: 3.11, 3.12**

### Running Black

```bash
# Check formatting (CI does this)
black --check .

# Auto-format all files
black .

# Format specific file
black src/myfile.py
```

---

## Import Sorting

Imports must be organized in the following order:

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# ✅ GOOD
import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from src.models import User
from src.services import UserService
```

---

## Pre-commit Hooks

### Installation

Pre-commit hooks are automatically installed when you run `pre-commit install`. These hooks run on every commit to ensure code quality.

### Manual Run

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black
pre-commit run ruff
pre-commit run mypy
```

### Bypassing Hooks (Emergency Only)

In rare emergencies, you can bypass hooks:

```bash
git commit --no-verify
```

**Note:** Bypassing hooks is strongly discouraged. CI will still fail if code doesn't meet standards.

---

## Submitting Changes

### Branch Naming

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Messages

Follow conventional commits format:

```
type(scope): description

[optional body]

[optional footer]
```

Examples:

```
feat(auth): add OAuth2 integration

fix(api): handle null response from MS Graph

docs(readme): update installation instructions
```

### Pull Request Process

1. **Ensure all checks pass locally:**
   ```bash
   ruff check .
   black --check .
   mypy src/ tests/
   pytest
   ```

2. **Update documentation** if needed

3. **Add tests** for new functionality

4. **Ensure CI passes** - All checks must be green

5. **Request review** from maintainers

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test
pytest tests/unit/test_specific.py

# Run with markers
pytest -m unit
pytest -m integration
```

### Coverage Requirements

- **Minimum coverage: 75%**
- New code should maintain or improve coverage

---

## Security

### Bandit Security Scanner

All code is scanned for security issues:

```bash
bandit -r src/
```

Common checks include:
- Hardcoded passwords/tokens
- SQL injection risks
- Unsafe eval/exec usage
- Weak cryptography

---

## CI/CD Pipeline

Our CI pipeline enforces all quality checks:

1. **Lint Job** - Ruff, Black, MyPy, Bandit (must all pass)
2. **Test Job** - Unit tests with coverage (must pass, 75% min)
3. **Integration Tests** - Integration test suite
4. **Docker Build** - Container build verification
5. **Pre-commit Validation** - All hooks must pass

**No PR will be merged if any check fails.**

---

## Getting Help

If you encounter issues with linting or type checking:

1. Check this document for configuration details
2. Run tools with `--help` for available options
3. Open an issue with the `question` label

---

## Quick Reference

```bash
# Full local validation (run before pushing)
ruff check . && black --check . && mypy src/ tests/ && pytest

# Auto-fix what can be fixed
ruff check . --fix && black .

# Check specific areas
ruff check src/ --select S    # Security only
ruff check . --select B       # Bugbear only
mypy src/core/                # Specific module
```

---

Thank you for contributing to SpecterDefence! 🚀
