---
description: Run linting checks (same as CI)
---

# Run Linting Checks

This workflow runs the same linting checks that are executed in the GitHub Actions CI pipeline (`.github/workflows/check-lint.yml`).

## Steps

1. **Install ruff** (if not already installed)
   ```bash
   pip install ruff
   ```

2. **Check ruff version**
   ```bash
   ruff --version
   ```

// turbo
3. **Run ruff linting check**
   ```bash
   ruff check .
   ```

// turbo
4. **Run ruff format check**
   ```bash
   ruff format --check .
   ```

// turbo
5. **Check all _DBG_* flags are False**
   ```bash
   grep -rPn '_DBG_\w+ = (?!False)' --include='*.py' . && echo "ERROR: Found _DBG_* flags not set to False" || echo "✓ All _DBG_* flags are False"
   ```

## Notes

- The `// turbo` annotation allows these commands to auto-run without user approval
- These checks match exactly what runs in CI on push/PR to main or dev branches
- All checks should pass before pushing to ensure CI will pass
