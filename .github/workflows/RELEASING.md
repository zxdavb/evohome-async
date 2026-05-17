# Release workflow

## Branch model

```
feature/my-change  →  dev  →  main  →  tag  →  PyPI
```

- All development PRs target **`dev`**.
- **`main`** only receives merges from `dev` immediately before a release.
- Tags are always created on `main`.

---

## Day-to-day development

1. Branch off `dev` (e.g. `feat/my-change`).
2. Open a PR targeting `dev`.
3. Apply a label — this determines which section of the release notes the PR appears in:

   | Label | Release notes section |
   |---|---|
   | `enhancement`, `feature` | 🚀 Features |
   | `bug`, `bugfix`, `fix` | 🐛 Bug Fixes |
   | `dependencies` | ⬆️ Dependencies |
   | `ha-integration` | 🏠 HA Integration |
   | `ci`, `internal` | 🔧 Internal / CI |
   | `skip-changelog` | (excluded from notes) |
   | *(none)* | 🔀 Other |

4. CI runs lint, type-check, and tests.
5. Merge to `dev`.
6. **Release-drafter** automatically updates the draft GitHub Release with the PR, and bumps the suggested next version based on the labels seen so far:
   - `breaking-change` → major
   - `enhancement` / `feature` → minor
   - everything else → patch

---

## Making a release

### 1. Merge `dev` → `main`

Open (or push) a PR from `dev` into `main`. This is the release boundary — only merge when ready to publish.

### 2. Create a tag on `main`

```bash
git checkout main && git pull
git tag v1.2.3
git push origin v1.2.3
```

The tag format must be `vMAJOR.MINOR.PATCH`. Pushing the tag triggers
**`validate-tag.yml`**, which:
- confirms the tag format is correct,
- confirms the tagged commit is reachable from `main`,
- runs lint, type-check, and tests.

### 3. Publish the GitHub Release

1. Go to **Releases → Drafts** on GitHub.
2. Verify the release notes and version.
3. Set the tag to `v1.2.3` (the one you just pushed).
4. Click **Publish release**.

Publishing triggers **`publish-release.yml`**, which:
- re-validates the tag (format + ancestry),
- re-runs lint, type-check, and tests,
- builds the wheel (`python -m build`),
- publishes to PyPI via OIDC Trusted Publisher (no stored tokens required).

---

## Prerequisites (one-time setup)

- **PyPI Trusted Publisher** must be registered at <https://pypi.org/manage/account/publishing/> with:
  - Repository: `zxdavb/evohome-async`
  - Workflow: `publish-release.yml`
  - Environment: `pypi`
- **GitHub environment `pypi`** must exist in repo Settings → Environments.
