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

### Merge strategy

| Merge | Method | Why |
| --- | --- | --- |
| feature → `dev` | **squash** | one commit per PR; keeps `dev` readable |
| `dev` → `main` | **merge commit — never squash** | see below |
| direct → `main` (Renovate, CI) | squash | single-purpose branches |

Squashing `dev` → `main` would put a commit on `main` that is not in `dev`, so the branches diverge
and `dev` has to be force-reset after every release. A merge commit keeps `dev` an ancestor of
`main`, so no reset is ever needed and both branches can stay fully protected.

### Branch protection

Both branches require a PR and green `lint-ok`, `test-ok` and `type-ok` checks; neither can be
force-pushed or deleted. `main` additionally requires branches to be up to date before merging.

`hass-ok` is deliberately **not** a required check: `check-hass-tests.yml` is path-filtered, so it
does not run on every PR, and requiring it would leave doc-only PRs waiting for a status that never
arrives. It also carries `continue-on-error`, so HA failures stay red and visible without blocking
a merge.

See [Prerequisites](#prerequisites-one-time-setup) for the configuration itself.

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

### 4. Sync `dev` with `main`

`main` moves ahead of `dev` whenever anything lands on it directly — the release merge commit
itself, and every Renovate or CI PR in between. Those commits do not reach `dev` on their own:

```bash
git checkout dev && git pull
git merge --ff-only main    # after a release, when dev has no commits of its own
git push origin dev
```

If `dev` already has work in flight, the fast-forward is refused; use a plain `git merge main`
instead, which makes a merge commit on `dev`. That is expected and allowed.

Mid-cycle syncing is usually unnecessary — the only cost of lagging is that feature branches run CI
against slightly older pins, and the next `dev` → `main` merge resolves it. Sync when a Renovate
change actually matters to work in progress, and after each release.

> **Note:** this step only works because `dev` → `main` uses a **merge commit** (see
> [Merge strategy](#merge-strategy)). If that merge is ever squashed, `dev` keeps commits `main`
> never received, `--ff-only` is refused permanently, and the only way back is to delete and
> recreate `dev` — which branch protection forbids.

---

## Prerequisites (one-time setup)

- **PyPI Trusted Publisher** must be registered at <https://pypi.org/manage/account/publishing/> with:
  - Repository: `zxdavb/evohome-async`
  - Workflow: `publish-release.yml`
  - Environment: `pypi`
- **GitHub environment `pypi`** must exist in repo Settings → Environments.
- **GitHub Rulesets** (Settings → Rules → Rulesets) carry all branch and tag protection. Use
  rulesets, **not** the older "branch protection rules" — the two systems stack, and where they
  disagree the most restrictive wins, which makes the effective state hard to reason about.
  Inspect what is actually in force with:

  ```bash
  gh api repos/zxdavb/evohome-async/rules/branches/main   # and .../dev
  gh api repos/zxdavb/evohome-async/rulesets
  ```

  Note the classic endpoint `repos/.../branches/main/protection` returns *"Branch not protected"*
  even when a ruleset is protecting the branch — it is blind to rulesets, and has misled an audit
  of this repo before.

  Three rulesets are expected:

  | Ruleset | Target | Rules |
  | --- | --- | --- |
  | Protect main branch | `~DEFAULT_BRANCH` | deletion, non-fast-forward, pull request (0 approvals), required status checks (`lint-ok`, `test-ok`, `type-ok`, strict) |
  | Protect dev branch | `refs/heads/dev` | as above, minus strict; plus a repository-admin bypass for emergencies |
  | Version tag protection | `refs/tags/v*` | required status checks (`lint-ok`, `test-ok`, `type-ok`) before a version tag can be pushed — in addition to the CI ancestry check in `validate-tag.yml` |

  ⚠️ **Quote branch names carefully when creating a ruleset.** A condition of `refs/heads/"dev"`
  (with literal quotes) matches no branch at all and silently protects nothing.

  **The merge strategy cannot be fully enforced.** A ruleset's `allowed_merge_methods` applies to
  every PR into the branch and cannot be conditioned on the source branch — and `main` legitimately
  needs both methods: a merge commit for `dev` → `main`, and squash for the Renovate/CI PRs that
  target it directly (Renovate automerges with `automergeStrategy: "squash"`). Restricting `main`
  to `["merge"]` would block every Renovate PR. So `main` allows `["merge", "squash"]` — `rebase`
  is dropped as unused — and "never squash `dev` → `main`" remains a discipline rule.

  `dev` is different: everything entering it is a feature PR, so it is set to `["squash"]`, which
  does enforce the rule. The one consequence is that a `main` → `dev` back-merge cannot be done as
  a PR; do that sync by direct push, as [step 4](#4-sync-dev-with-main) describes.
