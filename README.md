# design-system-archetype

The **Design System Engineer** archetype bundle for [protoAgent](https://github.com/protoLabsAI/protoAgent) —
a design-system + frontend + accessibility engineer that reads the design system
**live**, turns design direction into focused reviewed PRs, and directs builder
delegates instead of hand-coding. Humans merge.

| plugin | source | role |
|---|---|---|
| `delegates` | builtin | builder delegates — the agent directs, they author |
| `artifact` | builtin | generative UI — prototypes rendered as React artifacts |
| `agent_browser` | builtin | in-page probe — the auditing-a-site / `theme_probe_script` flows run here |
| `execute_code` | builtin | sandboxed code runs — token extraction and audit scripts (no shell) |
| `design-system` | [design-system-plugin](https://github.com/protoLabsAI/design-system-plugin) | live tokens / component inventory / rules reads, `ds_check` lint, drift watch |
| `github` | [github-plugin](https://github.com/protoLabsAI/github-plugin) | issues/PRs on the DS repo (write = PR-opening; merges stay human) |

The config defaults enforce the archetype's invariant — **direct and QA, never
hand-ship**: no shell (`run_command` disabled), PRs as the only codebase write
path, `edit_soul` history on.

## Install

```
python -m server plugin install https://github.com/protoLabsAI/design-system-archetype
```

— or pick **Design System Engineer** in the new-agent picker; it installs this bundle.

## After install (required)

1. **Bind the design system** — Settings ▸ Plugins ▸ Design System: your repo,
   ref, and the three paths (built tokens JSON, component source dir, rules doc).
   The daily drift-watch cron is on by default; blank it to disable.
2. **Bind the github plugin** to the same repo; leave `write: true` only if the
   agent should open PRs.
3. **Register a builder delegate** (Settings ▸ Delegates) and uncomment the
   `component-author` example in the manifest as a starting spec — the agent
   briefs it, QAs the output, and ships the PR.
4. **Set up onboarding** if you want `ds_audit_repo` (see below) — it only audits
   checkouts under the onboarding root or a registered project.

## Onboarding (`ds_audit_repo`)

`ds_audit_repo` will only audit a checkout that lives under the onboarding **root**
or an explicitly registered project — never an arbitrary path on the host. Configure
two keys under `config.onboarding` (commented in the manifest):

- **`allow`** — the repos the auditor may clone, e.g. `github.com/<your-org>/*`.
- **`root`** — a directory **inside the agent workspace**, e.g. `<workspace>/projects`.

```yaml
config:
  onboarding:
    allow:
      - github.com/<your-org>/*     # repos the auditor is allowed to clone
    root: <workspace>/projects       # inside the agent workspace
```

> ⚠️ **`root` must never be `~/dev` and never your home directory.** The auditor
> treats everything under `root` as disposable working copies it clones into and
> re-syncs; pointing it at `~/dev` or `$HOME` puts your real checkouts in scope.

## Two-board model (recommended)

Run the design system and its consuming app as **two peer PM boards**, not one:

- **This agent's `project_board` owns the DS repos** — the design system plus its
  plugin/library packages. It reads them live, lints, drift-watches, and opens PRs
  there.
- **A peer PM agent, `protoEngineer`, owns the consuming _app_ repo.** It is reached
  as an **a2a delegate**, so this agent never opens app-repo PRs directly — it
  delegates app-side adoption of a shipped DS change to `protoEngineer` instead.

Add `protoEngineer` next to the builder delegate (commented in the manifest):

```yaml
config:
  delegates:
    - name: protoEngineer
      type: a2a
      url: http://your-protoengineer-host:8080   # a2a endpoint of the peer PM agent
      description: >-
        Peer PM agent that owns the consuming application repo.
```

When an app change must wait on a design-system release, gate the consumer card with
`waits_for: npm:<pkg>@contains:<owner>/<repo>@<card-id>` — the consumer only unblocks
once the published package actually contains that DS card's merge.

The persona itself lives in protoAgent's `design-system` soul preset
(`config/soul-presets/design-system.md`), owned by the `protoEngineer` board — request
persona changes there, not in this bundle.

Pins move through release tags only (ADR 0049) — `scripts/check_bundle_updates.py`
proposes bumps, `.github/workflows/verify-bundle.yml` gates them.

## Pin-bump PR lifecycle (explicit-approval model, [#2645][issue-2645])

The scheduled `bump` job pushes to a single, stable branch — `bump-pins` — and keeps **at
most one** open pin-bump PR at a time. A later scheduled run that finds more bumps
force-pushes that same branch, updating the PR in place instead of piling up duplicates.
Treat `bump-pins` as bot-owned: it's rewritten wholesale every run, so hand edits to it
don't survive the next bump.

GitHub does **not** auto-start a `pull_request` workflow run for a PR opened with the
repository `GITHUB_TOKEN` — it's held `action_required` until someone with write access
clicks **Approve and run workflows** on the Actions tab (recursion-prevention; see
[GitHub's docs][gh-token-docs]). This repo has no GitHub App installation or PAT
provisioned to avoid that, so it deliberately runs the **explicit-approval model** instead:

- **Approving is a documented, one-click operator responsibility, not a bug.** Watch the
  repo's Actions tab (or PR notifications) for the pin-bump PR and approve its run so
  `verify` actually runs before merge.
- **The `bump` job makes a stall visible instead of silent.** After pushing, it polls
  (bounded wait) for the `verify` run it should have queued. If that run comes back
  `action_required` — or never shows up at all, which is worse — the job **fails**,
  comments on the PR, and adds a `needs-approval` label. An unapproved pin-bump PR then
  shows up as a red weekly schedule, not a PR quietly rotting for weeks.
- **ADR 0049's invariant still holds either way:** `verify` still has to pass before merge
  — this only makes sure someone notices it needs to be *started*.

[issue-2645]: https://github.com/protoLabsAI/protoAgent/issues/2645
[gh-token-docs]: https://docs.github.com/en/actions/concepts/security/github_token#when-github_token-triggers-workflow-runs

