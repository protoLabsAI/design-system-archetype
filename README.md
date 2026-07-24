# design-system-stack

The **Design System Engineer** archetype bundle for [protoAgent](https://github.com/protoLabsAI/protoAgent) —
a design-system + frontend + accessibility engineer that reads the design system
**live**, turns design direction into focused reviewed PRs, and directs builder
delegates instead of hand-coding. Humans merge.

| plugin | source | role |
|---|---|---|
| `delegates` | builtin | builder delegates — the agent directs, they author |
| `artifact` | builtin | generative UI — prototypes rendered as React artifacts |
| `design-system` | [design-system-plugin](https://github.com/protoLabsAI/design-system-plugin) | live tokens / component inventory / rules reads, `ds_check` lint, drift watch |
| `github` | [github-plugin](https://github.com/protoLabsAI/github-plugin) | issues/PRs on the DS repo (write = PR-opening; merges stay human) |

The config defaults enforce the archetype's invariant — **direct and QA, never
hand-ship**: no shell (`run_command` disabled), PRs as the only codebase write
path, `edit_soul` history on.

## Install

```
python -m server plugin install https://github.com/protoLabsAI/design-system-stack
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

Pins move through release tags only (ADR 0049) — `scripts/check_bundle_updates.py`
proposes bumps, `.github/workflows/verify-bundle.yml` gates them.
