---
description: Run linting and type checks (same as CI)
---

# Run Linting and Type Checks

This workflow runs the same linting and type checks that are executed in the GitHub Actions CI pipelines (`.github/workflows/check-lint.yml` and `.github/workflows/check-type.yml`).

## Steps

### Initialization

1. **Install uv** (if not already installed)
   ```bash
   pip install uv
   ```

2. **Install dependencies**
   ```bash
   uv pip install --system ruff mypy -r requirements_dev.txt
   uv pip install --system -e .
   ```

### Linting (ruff)

3. **Check ruff version**
   ```bash
   ruff --version
   ```

// turbo
4. **Run ruff linting check**
   ```bash
   ruff check .
   ```

// turbo
5. **Run ruff format check**
   ```bash
   ruff format --check .
   ```

### Typing (mypy)

6. **Check mypy version**
   ```bash
   mypy --version
   ```

// turbo
7. **Run mypy type check**
   ```bash
   mypy
   ```

### Code Quality (Debug Flags)

// turbo
8. **Check all _DBG_* flags are False**
   ```bash
   grep -Prn '_DBG_\w+ = (?!False)' --include='*.py' . && echo "ERROR: Found _DBG_* flags not set to False" || echo "✓ All _DBG_* flags are False"
   ```

## Notes

- The `// turbo` annotation allows these commands to auto-run without user approval
- These checks match exactly what runs in CI (ruff and mypy)
- All checks should pass before pushing to ensure CI will pass
