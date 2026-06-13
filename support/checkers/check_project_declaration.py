#!/usr/bin/env python3
"""PROJECT-0 S1-B: every project vessel declares its charter and direction.

A ``project/<id>/`` directory is a project vessel (그릇): buildings accumulate
inside it. A vessel with buildings but no charter (``README.md``) or no
machine declaration (``project.json``) is a silent dogfood-era hardcoding —
nobody can tell WHY the buildings exist or WHERE the project is going. This
checker enforces, for EVERY directory under ``project/``:

  1. ``README.md`` (the human charter) exists and is non-trivial
     (>= 3 non-empty lines, MIN_CHARTER_LINES);
  2. ``project.json`` exists, parses, and passes the support loader
     (closed key set, non-empty direction, judgment keys rejected,
     human-only managers);
  3. ``charter_ref`` resolves to the project's own README.md.

Missing either => RED: a project must declare its charter and direction
before buildings accumulate.

Anti-tautology: negative probes synthesize violating project vessels in a
temp tree (buildings without charter / empty direction / unknown key /
judgment key / non-slug ids 'ABC'·'프로젝트'·'a..b' / a symlinked vessel
whose target escapes the repo) and one positive probe synthesizes a fully
declared vessel. PROJECT-0 S5-FIX adds seam-parity probes (the SAME non-slug
ids must reject at the capture ``buildings_root_for`` seam and the admission
vessel-id matcher, while 'brick-protocol' passes everywhere) and a creation
rollback probe (a non-str managers entry is refused with NO partial vessel
left on disk). A probe the validator fails to reject (or a valid vessel it
rejects) makes ``main()`` non-zero, so a validator that silently stops
rejecting drives ``--all`` RED.

Support evidence only: proves charter+declaration presence and record shape,
NOT source truth, success judgment, quality judgment, or Movement authority.
It cannot prove the charter text is truthful or current.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

MIN_CHARTER_LINES = 3

PROBE_DECLARATION = {
    "project_ref": "project:fire-probe",
    "label": "FIRE probe project",
    "direction": "synthetic probe direction",
    "done_means": "probe complete",
    "out_of_scope": "everything real",
    "managers": ["smith"],
    "declared_by": "smith",
    "declared_at": "2026-06-11T00:00:00+00:00",
    "charter_ref": "project/fire-probe/README.md",
}
PROBE_CHARTER = "# FIRE probe\n\npurpose line\ndirection line\n"


def _ensure_import_path(repo: Path) -> None:
    import_identity = repo / "support" / "import_identity"
    for entry in (str(import_identity), str(repo)):
        if entry not in sys.path:
            sys.path.insert(0, entry)


def _charter_nontrivial(charter_path: Path) -> bool:
    try:
        text = charter_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    nonempty = [line for line in text.splitlines() if line.strip()]
    return len(nonempty) >= MIN_CHARTER_LINES


def find_violations(repo: Path) -> tuple[list[str], int]:
    """Validate every project vessel under repo/project. Returns (violations, inspected)."""

    from brick_protocol.support.operator.project_declaration import (
        PROJECT_CHARTER_FILENAME,
        load_project_declaration,
    )

    violations: list[str] = []
    inspected = 0
    project_root = repo / "project"
    if not project_root.is_dir():
        return violations, inspected
    for project_dir in sorted(project_root.iterdir()):
        if not project_dir.is_dir():
            continue
        if not any(
            (project_dir / marker).exists()
            for marker in ("README.md", "project.json", "buildings")
        ):
            continue
        inspected += 1
        project_id = project_dir.name
        charter_path = project_dir / PROJECT_CHARTER_FILENAME
        if not charter_path.is_file():
            violations.append(
                f"project/{project_id}: charter {PROJECT_CHARTER_FILENAME} is missing — "
                "a project must declare its charter and direction before buildings accumulate"
            )
        elif not _charter_nontrivial(charter_path):
            violations.append(
                f"project/{project_id}: charter {PROJECT_CHARTER_FILENAME} is trivial "
                f"(fewer than {MIN_CHARTER_LINES} non-empty lines) — a charter must say why "
                "the project exists and where it is going"
            )
        try:
            load_project_declaration(repo, project_id)
        except ValueError as exc:
            violations.append(str(exc))
    return violations, inspected


def _write_probe_vessel(
    root: Path,
    *,
    charter: str | None,
    declaration: dict | None,
    with_building: bool = False,
    vessel_id: str = "fire-probe",
) -> None:
    vessel = root / "project" / vessel_id
    vessel.mkdir(parents=True)
    if with_building:
        (vessel / "buildings" / "probe-building-0").mkdir(parents=True)
    if charter is not None:
        (vessel / "README.md").write_text(charter, encoding="utf-8")
    if declaration is not None:
        (vessel / "project.json").write_text(
            json.dumps(declaration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def _probe_declaration_for(vessel_id: str) -> dict:
    """The standard probe declaration re-keyed to ``vessel_id`` (so a non-slug
    id probe REDs on the slug law alone, not on a mismatched ref)."""

    return {
        **PROBE_DECLARATION,
        "project_ref": f"project:{vessel_id}",
        "charter_ref": f"project/{vessel_id}/README.md",
    }


# PROJECT-0 S5-FIX: ids the slug law must reject at EVERY seam (loader,
# capture buildings_root_for, admission vessel-id matcher). 'ABC' (uppercase)
# and '프로젝트' (unicode) passed the old .isalnum() predicate; 'a..b' is the
# traversal-adjacent shape.
NON_SLUG_PROBE_IDS = ("ABC", "프로젝트", "a..b")


def _slug_seam_parity_failures(repo: Path) -> list[str]:
    """FIRE: the SAME ids reject at the capture seam and the admission
    vessel-id matcher, and 'brick-protocol' passes everywhere (anti-tautology
    positive control). The loader seam is probed via synthetic vessels in
    ``run_fire_probes``."""

    failures: list[str] = []
    from brick_protocol.support.recording.capture import (
        buildings_root_for,
        is_project_id_slug,
    )
    from support.checkers.check_package_path_admission import (
        is_project_root_declaration_path,
    )

    for bad_id in NON_SLUG_PROBE_IDS:
        if is_project_id_slug(bad_id):
            failures.append(f"slug law admitted non-slug id {bad_id!r} (is_project_id_slug)")
        try:
            buildings_root_for(f"project:{bad_id}")
            failures.append(f"capture seam admitted non-slug id {bad_id!r} (buildings_root_for)")
        except ValueError:
            pass
        if is_project_root_declaration_path(f"project/{bad_id}", is_dir=True):
            failures.append(
                f"admission matcher admitted non-slug vessel id {bad_id!r} "
                "(is_project_root_declaration_path)"
            )
    # Positive control: the existing vessel id passes all three seams.
    if not is_project_id_slug("brick-protocol"):
        failures.append("slug law rejected the valid id 'brick-protocol'")
    try:
        buildings_root_for("project:brick-protocol")
    except ValueError as exc:
        failures.append(f"capture seam rejected the valid id 'brick-protocol': {exc}")
    if not is_project_root_declaration_path("project/brick-protocol", is_dir=True):
        failures.append("admission matcher rejected the valid vessel id 'brick-protocol'")
    return failures


def _symlink_vessel_failure(repo: Path) -> str | None:
    """FIRE (symlink vessel escape): a symlinked project/<id> — charter and
    declaration fully valid AT THE TARGET — must be rejected loudly, naming
    the symlink. Synthetic: created with tempfile + os.symlink and removed
    with the temp tree; never touches the real project/ tree."""

    import os

    with tempfile.TemporaryDirectory(prefix="project-declaration-symlink-fire-") as tmp:
        tmp_root = Path(tmp)
        target = tmp_root / "outside-target"
        target.mkdir()
        (target / "README.md").write_text(PROBE_CHARTER, encoding="utf-8")
        (target / "project.json").write_text(
            json.dumps(_probe_declaration_for("sym-vessel"), indent=2) + "\n",
            encoding="utf-8",
        )
        (tmp_root / "project").mkdir()
        os.symlink(target, tmp_root / "project" / "sym-vessel", target_is_directory=True)
        violations, _ = find_violations(tmp_root)
        if not violations:
            return "symlinked vessel project/sym-vessel was NOT rejected (escape tautology)"
        if not any("symlink" in violation for violation in violations):
            return (
                "symlinked vessel was rejected for the WRONG reason "
                f"(rejection must name the symlink): {violations[0]}"
            )
    return None


def _creation_rollback_failure(repo: Path) -> str | None:
    """FIRE (creation rollback): a non-str managers entry must be refused
    loudly BEFORE any filesystem write — no partial vessel survives
    (operator reproduced: managers=['smith', object()] used to leave
    project/fire-typeerr on disk via an uncaught json TypeError)."""

    from brick_protocol.support.operator.project_creation import create_project

    with tempfile.TemporaryDirectory(prefix="project-creation-rollback-fire-") as tmp:
        tmp_root = Path(tmp)
        try:
            create_project(
                tmp_root,
                project_id="fire-typeerr",
                label="rollback probe",
                direction="probe direction",
                why_exists="probe",
                why_now="probe",
                done_means="probe",
                out_of_scope="probe",
                managers=["smith", object()],  # type: ignore[list-item]
                declared_by="smith",
            )
            return "create_project accepted a non-str managers entry (no TypeError)"
        except TypeError as exc:
            if "managers[1]" not in str(exc):
                return f"create_project TypeError does not name the bad slot: {exc}"
        except Exception as exc:  # noqa: BLE001 — probe reports any wrong shape
            return f"create_project failed with the WRONG exception type: {exc!r}"
        if (tmp_root / "project" / "fire-typeerr").exists():
            return "create_project left a partial vessel on disk after rejection"
    return None


def run_fire_probes(repo: Path) -> list[str]:
    """Anti-tautology probes. Returns failure messages (empty = all behaved)."""

    failures: list[str] = []

    def probe(name: str, *, expect_red: bool, **vessel_kwargs) -> None:
        with tempfile.TemporaryDirectory(prefix="project-declaration-fire-") as tmp:
            tmp_root = Path(tmp)
            _write_probe_vessel(tmp_root, **vessel_kwargs)
            violations, _ = find_violations(tmp_root)
            if expect_red and not violations:
                failures.append(f"probe {name}: violating vessel was NOT rejected (tautology)")
            if not expect_red and violations:
                failures.append(
                    f"probe {name}: fully declared vessel was rejected: {violations[0]}"
                )

    probe(
        "buildings-without-charter",
        expect_red=True,
        charter=None,
        declaration=None,
        with_building=True,
    )
    probe(
        "charter+declaration-green",
        expect_red=False,
        charter=PROBE_CHARTER,
        declaration=dict(PROBE_DECLARATION),
        with_building=True,
    )
    probe(
        "empty-direction",
        expect_red=True,
        charter=PROBE_CHARTER,
        declaration={**PROBE_DECLARATION, "direction": "   "},
    )
    probe(
        "unknown-key",
        expect_red=True,
        charter=PROBE_CHARTER,
        declaration={**PROBE_DECLARATION, "velocity_score": 11},
    )
    probe(
        "judgment-key",
        expect_red=True,
        charter=PROBE_CHARTER,
        declaration={**PROBE_DECLARATION, "success": "declared"},
    )
    # PROJECT-0 S5-FIX: the slug law at the LOADER seam — a vessel dir whose
    # id is uppercase / unicode / dotted must RED even when its charter and
    # declaration are otherwise fully valid for that id.
    for bad_id in NON_SLUG_PROBE_IDS:
        probe(
            f"non-slug-id-{bad_id}",
            expect_red=True,
            charter=PROBE_CHARTER,
            declaration=_probe_declaration_for(bad_id),
            vessel_id=bad_id,
        )
    failures.extend(_slug_seam_parity_failures(repo))
    with tempfile.TemporaryDirectory(prefix="project-declaration-status-only-") as tmp:
        tmp_root = Path(tmp)
        (tmp_root / "project" / "brick-protocol" / "status" / "inbox").mkdir(parents=True)
        violations, inspected = find_violations(tmp_root)
        if violations or inspected != 0:
            failures.append(
                "status-only project scaffold must not be treated as a declared "
                f"vessel: inspected={inspected}, violations={violations}"
            )
    symlink_failure = _symlink_vessel_failure(repo)
    if symlink_failure:
        failures.append(f"probe symlinked-vessel: {symlink_failure}")
    rollback_failure = _creation_rollback_failure(repo)
    if rollback_failure:
        failures.append(f"probe creation-rollback: {rollback_failure}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: every project/<id>/ vessel declares its "
            "charter (README.md) and machine declaration (project.json) with a "
            "non-empty direction. Does not prove source truth, success, quality, "
            "or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    _ensure_import_path(repo)

    probe_failures = run_fire_probes(repo)
    if probe_failures:
        print("project declaration rejected (anti-tautology probe failure):")
        for failure in probe_failures:
            print(f"- {failure}")
        return 1

    try:
        violations, inspected = find_violations(repo)
    except (OSError, ValueError) as exc:
        print(f"project declaration rejected: {exc}")
        return 1

    if violations:
        print("project declaration rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker proves charter+declaration presence and "
            "record shape only; it does not prove the charter text is truthful, "
            "nor source truth, success, quality, or Movement authority."
        )
        print(
            "prescription: declare the vessel via agent/skills/project-creation/"
            "SKILL.md (support.operator.project_creation.create_project) — do not "
            "hand-make project/<id>/ files."
        )
        return 1

    print(
        "project declaration passed: "
        f"{inspected} project vessel(s) carry a non-trivial charter (README.md) and a "
        "closed-key declaration (project.json) with a non-empty direction; "
        "anti-tautology probes behaved (8 violating vessels rejected incl. 3 non-slug "
        "ids + 1 symlinked vessel, 1 declared vessel accepted, status-only scaffold "
        "ignored, slug-law parity across loader/capture/admission seams, creation "
        "rollback left no partial vessel)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
