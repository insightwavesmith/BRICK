#!/usr/bin/env python3
"""Validate the U5.5 Evidence Spine (Truth Layer) structure.

GUARD-FIRST (slice-1A): this structural checker exists and FIRES before the
slice-1B disk writer. For a building whose ``evidence/evidence-manifest.json``
declares ``evidence_generation == "u5_5_live"`` it verifies the spine is an
immutable, ordered, re-derivable Truth-Layer judgment sequence. Any building
WITHOUT that tag (every pre-U5.5 building) is SKIPPED, so existing evidence is
untouched.

What it verifies for a u5_5_live building (design §2):
  * every ``events/<seq>-<type>.json`` has a paired ``.md`` AND
    ``.md == render_event_md(json-body)`` (the shared pure contract);
  * spine.json index: per-event ``content_hash == sha256(canonical_json(body))``
    (so a mutated ``.json`` => mismatch => RED = event-file write-once probe),
    ``md_hash == sha256(.md file)``, the ``prev_hash`` chain unbroken, and
    ``sequence_index`` strictly increasing AND ``run_segment`` non-decreasing
    (events written in one run share a run_segment; sequence_index is the strict
    anti-reuse counter — no dup / gap misuse / dangling);
  * spine.json / spine.jsonl / spine.md are a PURE PROJECTION re-derived from
    ``events/`` (disagreement => RED);
  * ``axis_scope`` is a non-empty subset of {Brick, Agent, Link, Support
    residue}; the ``<type>`` segment is an admitted spine event_type;
  * NO FORBIDDEN_CAPTURE_KEYS / RETURNED_FORBIDDEN_KEYS key appears in any event
    body (reusing the single-source sets — not re-listed here).

This checker is support evidence only. It is not source truth, not success
judgment, not quality judgment, and not Movement authority. It judges nothing
about the building's content; it only enforces the spine's structural integrity.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# stdlib-only path bootstrap so the canonical command
# `PYTHONPATH=brick_protocol/support/import_identity python3 ...` (no repo-root on PYTHONPATH)
# can still import the support tree when this checker is run standalone. The
# import_identity router governs only brick_protocol.*, not support.*.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from brick_protocol.support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)

# SINGLE-SOURCE the structural validation from the spine module. The convergent
# slice-1B fix made spine.spine_structural_violations the ONE shared validator that
# returns EVERY structural RED for a building's spine; both this checker and the
# disk writer's all-or-nothing preflight call it, so the writer refuses to append
# to anything this checker would RED (no drift between the two). The dependency
# direction is checker -> recording (recording never imports checkers). This
# checker is now a THIN wrapper: it gates on building_is_u5_5_live (which still
# needs _load_json for the manifest) and delegates the structural verdict to
# spine_structural_violations(..., require_index_present=True).
from brick_protocol.support.recording.spine import (
    _load_json,
    spine_structural_violations,
)


PROJECT_ROOT = "project"
BUILDINGS_SEGMENT = "buildings"
U5_5_LIVE = "u5_5_live"

PROOF_LIMIT = (
    "proof limit: this checker proves only the U5.5 spine's structural integrity "
    "(pairing, hash chain, monotonic order, index==re-derived, admitted event "
    "type + axis scope, no forbidden success/quality key) for u5_5_live "
    "buildings; it does not prove content correctness, source truth, success "
    "judgment, quality judgment, or Movement authority."
)


def building_is_u5_5_live(building_root: Path, violations: list[str]) -> bool:
    """True iff evidence-manifest.json declares evidence_generation == u5_5_live.

    Untagged / pre-U5.5 buildings (no field) => None => not live => SKIP. A
    missing/parse-broken manifest is NOT treated as live here (manifest presence
    is the lifecycle-path checker's job); this checker simply does not engage.
    """

    manifest_path = building_root / "evidence" / "evidence-manifest.json"
    if not manifest_path.is_file():
        return False
    manifest = _load_json(manifest_path, violations)
    if not isinstance(manifest, dict):
        return False
    return manifest.get("evidence_generation") == U5_5_LIVE


def _spine_is_populated(building_root: Path) -> bool:
    """True iff the building carries a NON-EMPTY spine events/ directory.

    GUARD #4 (populated-spine anchor): the u5_5_live manifest tag is the normal
    inspect gate, but capture.py can blind-overwrite the manifest and DROP the
    tag — silently freeing an ALREADY-BUILT spine from validation (false-green).
    A spine with ANY recorded artifact on disk MUST be inspected regardless of the
    tag, so inspection fails CLOSED on a populated spine. POPULATED iff the spine
    carries ANY part of its recorded set: an ``events/`` entry (``*.json`` OR its
    ``*.md`` render half) OR a ``spine.{json,jsonl,md}`` index file (P2 widening —
    counting ``*.json`` alone let a bulk file-op that left only the ``*.md`` halves
    + the index, plus a dropped tag, free a recorded spine from validation).

    The 154 pre-U5.5 buildings have NO ``evidence/spine/`` dir at all, so this is
    False for them — they stay SKIPPED exactly as today (no regression).
    """

    spine_dir = building_root / "evidence" / "spine"
    if not spine_dir.is_dir():
        return False
    events_dir = spine_dir / "events"
    if events_dir.is_dir() and (
        any(events_dir.glob("*.json")) or any(events_dir.glob("*.md"))
    ):
        return True
    return any(
        (spine_dir / name).is_file()
        for name in ("spine.json", "spine.jsonl", "spine.md")
    )


def validate_spine(building_root: Path, violations: list[str]) -> None:
    """Validate one u5_5_live building's spine. Appends RED reasons to violations.

    THIN WRAPPER over the single shared validator. ``require_index_present=True``
    because a u5_5_live building must already carry a complete spine (a missing
    spine/ or events/ dir, or a missing spine.{json,jsonl,md}, is a RED here). The
    writer's preflight calls the SAME function with ``require_index_present=False``
    (a missing index/dir it legitimately creates is not a RED), so the writer
    refuses to append to anything this checker would RED — one validation, no drift.
    """

    violations.extend(
        spine_structural_violations(building_root, require_index_present=True)
    )


def building_roots_under(repo: Path) -> list[Path]:
    """Every project/*/buildings/<id>/ directory under repo."""

    roots: list[Path] = []
    project_root = repo / PROJECT_ROOT
    if not project_root.is_dir():
        return roots
    for buildings_root in sorted(project_root.glob(f"*/{BUILDINGS_SEGMENT}")):
        if not buildings_root.is_dir():
            continue
        for building_root in sorted(buildings_root.iterdir()):
            if building_root.is_dir():
                roots.append(building_root)
    return roots


def find_violations(repo: Path) -> tuple[list[str], int]:
    """Return (violations, inspected_u5_5_live_count) over every building."""

    violations: list[str] = []
    inspected = 0
    for building_root in building_roots_under(repo):
        # GUARD #4: inspect when tagged u5_5_live OR when the spine is already
        # populated (a dropped manifest tag must NOT free a built spine). Keep
        # building_is_u5_5_live FIRST so its manifest-load violations-append
        # behavior is unchanged; the populated check only widens the gate.
        if not (
            building_is_u5_5_live(building_root, violations)
            or _spine_is_populated(building_root)
        ):
            continue
        inspected += 1
        validate_spine(building_root, violations)
    return violations, inspected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker for the U5.5 Evidence Spine (Truth Layer) "
            "structure of u5_5_live buildings. It does not prove content "
            "correctness, source truth, success, quality, or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    parser.add_argument(
        "--target",
        default=None,
        help="A single building root (or a buildings/ parent) to inspect directly.",
    )
    args = parser.parse_args(argv)

    try:
        if args.target:
            target = Path(args.target).resolve()
            if not target.is_dir():
                raise FileNotFoundError(f"target does not exist: {target}")
            violations: list[str] = []
            inspected = 0
            # Accept either a single building root or a buildings/ parent.
            roots = (
                [child for child in sorted(target.iterdir()) if child.is_dir()]
                if target.name == BUILDINGS_SEGMENT
                else [target]
            )
            for building_root in roots:
                # GUARD #4: same widened gate as find_violations — a populated
                # spine is inspected even if the manifest tag was dropped.
                if not (
                    building_is_u5_5_live(building_root, violations)
                    or _spine_is_populated(building_root)
                ):
                    continue
                inspected += 1
                validate_spine(building_root, violations)
        else:
            repo = Path(args.repo).resolve()
            if not repo.is_dir():
                raise FileNotFoundError(f"--repo must be a directory: {repo}")
            violations, inspected = find_violations(repo)
    except OSError as exc:
        print(f"evidence spine rejected: {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    if violations:
        print("evidence spine rejected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    print(
        "evidence spine passed: "
        f"{inspected} u5_5_live building spine(s) verified "
        "(pairing, hash chain, monotonic order, index re-derivation, admitted "
        "event types, no forbidden success/quality key)."
    )
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
