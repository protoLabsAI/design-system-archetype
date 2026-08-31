#!/usr/bin/env python3
"""Pin-bump checker for a bundle manifest (ADR 0049, as amended 2026-08-31).

A member pin is a bounded FLOOR, not an exact pin: protoAgent's installer already
ls-remotes each release-tag-pinned member and adopts the newest COMPATIBLE release
(caret semantics — the boundary is the leftmost non-zero component, so for the 0.x
versions this fleet uses, the MINOR).

So this script deliberately does NOT chase compatible releases any more. Rewriting
`ref: v0.7.0` to `v0.7.1` produced a PR, an approval click and a merge to write down
a value the installer computes on its own — churn with no effect on what installs.

It now reports only what actually needs a human: a member whose newest release is
OUTSIDE the compatible range. Adopting that is a real decision (it may be breaking),
so the ref is rewritten and the verify job gates the result.

    python3 scripts/check_bundle_updates.py protoagent.bundle.yaml

Prints `bump: <id> <old> -> <new>` per out-of-range member (workflow turns the dirty
tree into a PR), and `compatible: <id> …` for releases the installer picks up by
itself. Raw-SHA pins and `builtin:` members are left alone by design.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_MEMBER = re.compile(r"^\s*-\s*\{\s*id:\s*(?P<id>[\w-]+)\s*,\s*url:\s*(?P<url>\S+?)\s*,\s*ref:\s*(?P<ref>\S+?)\s*\}")
_SEMVER_TAG = re.compile(r"^v?\d+\.\d+\.\d+$")


def _semver_key(tag: str) -> tuple[int, ...]:
    return tuple(int(x) for x in tag.lstrip("v").split("."))


def latest_tag(url: str) -> str | None:
    """Newest semver tag at ``url`` (peeled lines preferred-equivalent: tag NAMES only)."""
    out = subprocess.run(
        ["git", "ls-remote", "--tags", url],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    tags = set()
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        name = parts[1].removeprefix("refs/tags/").removesuffix("^{}")
        if _SEMVER_TAG.match(name):
            tags.add(name)
    return max(tags, key=_semver_key) if tags else None


def is_compatible(pinned: str, candidate: str) -> bool:
    """Caret semantics — mirrors ``graph.plugins.installer.is_compatible_upgrade``.

    The boundary is the leftmost NON-ZERO component. That distinction is the whole point
    for this fleet: every plugin is 0.x, where a minor bump is where breaking changes land,
    so bounding on the major alone would be no bound at all.
    """
    a, b = _semver_key(pinned), _semver_key(candidate)
    if b < a:
        return False
    if a[0] != 0:
        return a[0] == b[0]
    if a[1] != 0:
        return b[0] == 0 and a[1] == b[1]
    return b[0] == 0 and b[1] == 0


def main(manifest_path: str) -> int:
    path = Path(manifest_path)
    lines = path.read_text().splitlines(keepends=True)
    changed = False
    for i, line in enumerate(lines):
        m = _MEMBER.match(line)
        if not m or not _SEMVER_TAG.match(m["ref"]):
            continue  # builtin, raw-SHA pin, or not a member line — leave alone
        newest = latest_tag(m["url"])
        if not newest or _semver_key(newest) <= _semver_key(m["ref"]):
            continue
        if is_compatible(m["ref"], newest):
            # The installer adopts this by itself — bumping the manifest changes nothing.
            print(f"compatible: {m['id']} {m['ref']} -> {newest} (adopted at install; no bump needed)")
            continue
        lines[i] = line.replace(f"ref: {m['ref']}", f"ref: {newest}")
        print(f"bump: {m['id']} {m['ref']} -> {newest}  [OUT OF RANGE — review before merging]")
        changed = True
    if changed:
        path.write_text("".join(lines))
    else:
        print("no out-of-range member releases — nothing to decide")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "protoagent.bundle.yaml"))
