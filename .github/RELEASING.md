# Release workflow

## Branch model

```text
feature/my-change  →  dev  →  main  →  tag  →  PyPI
ci/my-change            ↗
```

- Development PRs (features, fixes) target **`dev`**.
- CI, infrastructure, and Renovate PRs may target **`main`** directly.
- **`main`** only receives merges from `dev` (or direct non-development PRs) — never individual feature branches.
- Tags are always created on `main`.

---

## Day-to-day development

1. Branch off `dev` (e.g. `feat/my-change`).
2. Open a PR targeting `dev`.
3. Apply a label — this determines which section of the release notes the PR appears in:

   | Label | Release notes section |
   | --- | --- |
   | `enhancement`, `feature` | 🚀 Features |
   | `bug`, `bugfix`, `fix` | 🐛 Bug Fixes |
   | `dependencies` | ⬆️ Dependencies |
   | `ha-integration` | 🏠 HA Integration |
   | `ci`, `internal` | 🔧 Internal / CI |
   | `skip-changelog` | (excluded from notes) |
   | *(none)* | 🔀 Other |

4. CI runs lint, type-check, and tests (HA integration tests are **not** required for `dev` PRs).
5. Merge to `dev`.
6. **Release-drafter** automatically updates the draft GitHub Release with every PR merged to `main`, and bumps the suggested next version based on the labels seen so far:
   - `breaking-change` → major
   - `enhancement` / `feature` → minor
   - everything else → patch

---

## Making a release

### 1. Merge `dev` → `main`

Open (or push) a PR from `dev` into `main`. This is the release boundary — only merge when ready to publish. The full CI suite runs here, including **`check-hass-tests`**, which is not required for `dev` PRs.

### 2. Create a tag on `main`

There is no version file to edit — the version is derived automatically from the git tag by `hatch-vcs`. Simply tag the commit:

```bash
git checkout main && git pull
git tag v1.2.3
git push origin v1.2.3
```

The tag format must be `vMAJOR.MINOR.PATCH`. Pushing the tag triggers
**`validate-tag.yml`**, which:

- confirms the tag format is correct,
- confirms the tagged commit is reachable from `main`,
- runs lint, type-check, tests, and HA integration tests (against the latest HA release).

### 3. Publish the GitHub Release

1. Go to **Releases → Drafts** on GitHub.
2. Verify the release notes and version.
3. Set the tag to `v1.2.3` (the one you just pushed).
4. Click **Publish release**.

Publishing triggers **`publish-release.yml`**, which:

- re-validates the tag (format + ancestry),
- re-runs lint, type-check, and tests,
- runs HA integration tests against the latest HA release (blocking) and HA dev (non-blocking),
- builds the wheel (`python -m build`),
- publishes to PyPI via OIDC Trusted Publisher (no stored tokens required).

### 4. Reset `dev`

After the release is published, fast-forward `dev` to `main` so the next development cycle starts clean:

```bash
git checkout dev && git pull
git merge --ff-only main
git push origin dev
```

Alternatively, delete and recreate:

```bash
git push origin --delete dev
git push origin main:dev
```

---

## Prerequisites (one-time setup)

- **PyPI Trusted Publisher** must be registered at <https://pypi.org/manage/account/publishing/> with:
  - Repository: `zxdavb/evohome-async`
  - Workflow: `publish-release.yml`
  - Environment: `pypi`
- **GitHub environment `pypi`** must exist in repo Settings → Environments.
- **GitHub Ruleset "Version tag protection"** enforces that `lint-ok`, `test-ok`, and `type-ok` status checks pass before a version tag can be pushed. This is in addition to the CI ancestry check in `validate-tag.yml`.
