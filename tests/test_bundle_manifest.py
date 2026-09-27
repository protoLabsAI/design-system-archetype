#!/usr/bin/env python3
"""Guard the Design System Engineer bundle's declared invariants (ADR 0040/0049).

These are pure manifest/docs assertions — they don't need a protoAgent checkout
(that's what scripts/verify_bundle.py + the verify-bundle workflow do). They lock in
the pin set, the builtin roster, the execute_code sandbox defaults, verified_against,
the onboarding + two-board documentation, and — critically — that the tag-pinned
member lines stay in the ONE-LINE form check_bundle_updates.py rewrites in place.

Run with pytest, or standalone: `python tests/test_bundle_manifest.py`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "protoagent.bundle.yaml"
README = REPO / "README.md"


def _load_bundle() -> dict:
    return yaml.safe_load(BUNDLE.read_text())


def _member_regex():
    """Reuse the exact regex the pin-bump script matches member lines with."""
    spec = importlib.util.spec_from_file_location(
        "check_bundle_updates", REPO / "scripts" / "check_bundle_updates.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _plugin(bundle: dict, pid: str) -> dict | None:
    for p in bundle["plugins"]:
        if p.get("id") == pid:
            return p
    return None


# ── r1: design-system pinned at v0.9.0, single line, still bump-script-matchable ──
def test_design_system_pinned_at_v0_9_0():
    ds = _plugin(_load_bundle(), "design-system")
    assert ds is not None, "design-system member missing"
    assert ds["ref"] == "v0.9.0", f"expected ref v0.9.0, got {ds.get('ref')!r}"


def test_member_lines_are_single_line_and_rewritable():
    """check_bundle_updates.py rewrites `ref:` in place; the line must match its regex."""
    cbu = _member_regex()
    text = BUNDLE.read_text()
    matched = {}
    for line in text.splitlines():
        m = cbu._MEMBER.match(line)
        if m:
            matched[m["id"]] = m["ref"]
    assert matched.get("design-system") == "v0.9.0"
    # github stays as-is; still a matchable single-line member.
    assert matched.get("github") == "v0.7.0"


def test_v0_9_0_is_a_floor_not_an_exact_pin():
    """0.x caret = minor boundary: v0.9.0 adopts v0.9.9 but never v0.10.0."""
    cbu = _member_regex()
    assert cbu.is_compatible("v0.9.0", "v0.9.9") is True
    assert cbu.is_compatible("v0.9.0", "v0.10.0") is False


# ── r2: agent_browser + execute_code are builtins, enabled, with sandbox config ──
def test_new_builtins_declared_and_enabled():
    bundle = _load_bundle()
    for pid in ("agent_browser", "execute_code"):
        p = _plugin(bundle, pid)
        assert p is not None, f"{pid} not declared under plugins"
        assert p.get("builtin") is True, f"{pid} must be builtin: true"
        assert pid in bundle["enabled"], f"{pid} missing from enabled"
    # Existing members are preserved (additive change).
    for pid in ("delegates", "artifact", "design-system", "github"):
        assert pid in bundle["enabled"], f"{pid} dropped from enabled"


def test_execute_code_sandbox_defaults():
    cfg = _load_bundle()["config"]["execute_code"]
    assert cfg["output_truncate"] == 20000
    assert cfg["timeout"] == 90


# ── r5: verified_against bumped to the current protoAgent release ──
def test_verified_against_is_current_release():
    assert str(_load_bundle()["verified_against"]) == "0.184.1"


# ── r3: onboarding allow + root documented (root inside workspace, never ~/dev/home) ──
def test_onboarding_documented_in_bundle_and_readme():
    bundle_text = BUNDLE.read_text()
    readme_text = README.read_text()
    for text in (bundle_text, readme_text):
        assert "onboarding" in text
        assert "allow" in text
        assert "root" in text
        assert "<workspace>/projects" in text
        # Explicit "never ~/dev / home" warning.
        assert "~/dev" in text and "home" in text.lower()


# ── r4: two-board model + protoEngineer a2a delegate + waits_for gating documented ──
def test_two_board_model_documented_in_bundle_and_readme():
    bundle_text = BUNDLE.read_text()
    readme_text = README.read_text()
    for text in (bundle_text, readme_text):
        assert "protoEngineer" in text
        assert "a2a" in text
        assert "waits_for: npm:<pkg>@contains:<owner>/<repo>@<card-id>" in text
    # component-author builder example is preserved (additive).
    assert "component-author" in bundle_text


# ── r6: the forbidden model family is not mentioned anywhere in the repo ──
def test_forbidden_model_family_absent():
    # Built from fragments so this guard's own source can't trip it.
    needle = "fa" + "ble"
    offenders = []
    for path in REPO.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            body = path.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        if needle in body.lower():
            offenders.append(str(path.relative_to(REPO)))
    assert not offenders, f"forbidden term found in: {offenders}"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL {name}: {e}")
    sys.exit(1 if failures else 0)
