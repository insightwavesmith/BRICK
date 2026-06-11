#!/usr/bin/env python3
"""General invariant: every brick spec (bricks/<kind>/brick.md) is complete and resolvable.

The unified model's Builder auto-fills a node from bricks/<kind>/brick.md. Active
frontmatter separates the Brick work contract from Builder selection metadata:
``requires_brick_write_scope`` and ``performer_lane_need`` are NEED inputs,
``agent_object_hint_ref`` is an optional hint, ``link_movement_literal`` is the
declared linear Link literal, and ``required_return_template_refs`` is the return
contract source. None of these fields makes the Brick spec a writer, Agent
authority, Link authority, or source truth.

Support evidence only: proves the spec fields are present + resolve, not that the
instruction is correct, nor source truth, success, quality, or Movement authority.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path, PurePosixPath


BRICKS_DIR = Path("brick/templates/bricks")
BRICK_SPEC_FILENAME = "brick.md"
BRICK_RETURN_FILENAME = "return.yaml"
# REQUIRED = Brick identity / contract plus Builder selection metadata. The
# legacy names are RETIRED (L legacy cut, 0610): the Builder loader
# (plan_rendering._step_templates_from_bricks) now REJECTS them loudly naming
# the canonical key, and this checker flags any spec still carrying one. Active
# brick specs must use these names so the Brick file does not look like it owns
# Agent selection, write authority, or Link Movement.
REQUIRED_FRONTMATTER = (
    "brick_kind",
    "brick_word",
    "performer_word",
    "requires_brick_write_scope",
    "performer_lane_need",
    "required_return_template_refs",
    "link_movement_literal",
    "brick_contract",
)
LEGACY_FRONTMATTER_ALIASES = {
    "agent_word": "performer_word",
    "write_need": "requires_brick_write_scope",
    "role_need": "performer_lane_need",
    "return_template": "required_return_template_refs",
    "default_link": "link_movement_literal",
    "default_agent": "agent_object_hint_ref",
}


def _frontmatter(text: str):
    """Return the parsed YAML frontmatter mapping between the leading --- fences, or None."""
    import yaml  # type: ignore[import-not-found]

    if not text.startswith("---"):
        return None
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return None
    block = parts[0][len("---"):]
    data = yaml.safe_load(block)
    return data if isinstance(data, dict) else None


def _instruction_body(text: str) -> str:
    """Return the markdown body after the closing frontmatter fence ('' if none).

    The body is the agent-readable work instruction the Builder hands to the
    Agent; an empty body means the spec has no instruction to give.
    """
    if not text.startswith("---"):
        return text
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return ""
    after = parts[1]
    nl = after.find("\n")
    return after[nl + 1:] if nl != -1 else ""


def _fm_value(fm: dict, canonical_key: str, legacy_key: str):
    if canonical_key in fm:
        return fm.get(canonical_key)
    return fm.get(legacy_key)


def find_violations(repo: Path, *, run_u2: bool = True) -> tuple[list[str], int]:
    try:
        import yaml  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise ValueError("bricks spec completeness requires PyYAML") from exc

    violations: list[str] = []
    bricks_dir = repo / BRICKS_DIR
    if not bricks_dir.is_dir():
        raise ValueError(f"{BRICKS_DIR} must exist")
    specs: dict[str, dict] = {}
    for path in sorted(bricks_dir.glob("*.md")):
        rel = path.relative_to(repo).as_posix()
        violations.append(
            f"{rel}: flat brick specs are retired; use "
            f"{BRICKS_DIR.as_posix()}/{path.stem}/{BRICK_SPEC_FILENAME}"
        )
    for kind_dir in sorted(path for path in bricks_dir.iterdir() if path.is_dir()):
        kind = kind_dir.name
        if not kind or not all(part and (part.isalnum() or part == "-") for part in kind.split("-")):
            violations.append(f"{kind_dir.relative_to(repo).as_posix()}: brick kind directory must be a slug")
            continue
        path = kind_dir / BRICK_SPEC_FILENAME
        return_path = kind_dir / BRICK_RETURN_FILENAME
        if not path.is_file():
            violations.append(
                f"{kind_dir.relative_to(repo).as_posix()}: missing active {BRICK_SPEC_FILENAME}"
            )
            continue
        if not return_path.is_file():
            violations.append(
                f"{kind_dir.relative_to(repo).as_posix()}: missing primary {BRICK_RETURN_FILENAME}"
            )
        rel = path.relative_to(repo).as_posix()
        text = path.read_text(encoding="utf-8")
        fm = _frontmatter(text)
        if fm is None:
            violations.append(f"{rel}: missing or unparseable YAML frontmatter (--- fences)")
            continue
        specs[kind] = fm
        # brick_kind is the Builder's auto-fill IDENTITY: it must match the kind
        # directory, else a spec can silently claim a different kind than its path
        # (and the coverage count would look complete while a kind is duplicated/absent).
        declared_kind = fm.get("brick_kind")
        if isinstance(declared_kind, str) and declared_kind.strip() and declared_kind.strip() != kind:
            violations.append(f"{rel}: brick_kind '{declared_kind.strip()}' must match directory slug '{kind}'")
        # the markdown body after the frontmatter IS the agent-readable work
        # instruction; an empty body means the Builder has nothing to hand the Agent.
        if not _instruction_body(text).strip():
            violations.append(f"{rel}: instruction body after frontmatter is empty (no agent-readable work instruction)")
        for field in REQUIRED_FRONTMATTER:
            value = fm.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                violations.append(f"{rel}: missing/empty frontmatter field '{field}'")
        for legacy_field, canonical_field in LEGACY_FRONTMATTER_ALIASES.items():
            if legacy_field in fm:
                violations.append(
                    f"{rel}: retired legacy frontmatter field '{legacy_field}' is "
                    f"not admitted; use '{canonical_field}' (the Builder loader "
                    "rejects the legacy spelling)"
                )
        # requires_brick_write_scope must be a clear yes/no
        wn = fm.get("requires_brick_write_scope")
        if wn not in (True, False, "yes", "no"):
            violations.append(f"{rel}: requires_brick_write_scope must be yes/no (got {wn!r})")
        # required_return_template_refs is the return contract source: a single
        # ref OR a list of refs.
        # Each entry must resolve to an existing file so the Builder's auto-fill of
        # required_return_shape stays honest.
        rt = fm.get("required_return_template_refs")
        if isinstance(rt, str):
            rt_refs = [rt] if rt.strip() else []
        elif isinstance(rt, list):
            rt_refs = rt
            if not rt:
                violations.append(
                    f"{rel}: required_return_template_refs list is empty "
                    "(no return contract source)"
                )
        else:
            rt_refs = []
            if rt is not None:
                violations.append(
                    f"{rel}: required_return_template_refs must be a path or "
                    f"a list of paths (got {rt!r})"
                )
        for entry in rt_refs:
            if not isinstance(entry, str) or not entry.strip():
                violations.append(
                    f"{rel}: required_return_template_refs entry must be non-empty "
                    f"text (got {entry!r})"
                )
                continue
            stripped = entry.strip()
            pure = PurePosixPath(stripped)
            if pure.is_absolute() or ".." in pure.parts:
                violations.append(
                    f"{rel}: required_return_template_refs '{entry}' must be a repo-relative path "
                    "(no absolute path, no '..' segment)"
                )
            elif not (repo / stripped).is_file():
                violations.append(
                    f"{rel}: required_return_template_refs '{entry}' does not resolve to a file"
                )
        primary_return_ref = f"{BRICKS_DIR.as_posix()}/{kind}/{BRICK_RETURN_FILENAME}"
        if rt_refs and isinstance(rt_refs[0], str) and rt_refs[0].strip() != primary_return_ref:
            violations.append(
                f"{rel}: primary required_return_template_refs entry must be "
                f"{primary_return_ref} (got {rt_refs[0]!r})"
            )
        # agent_object_hint_ref is an OPTIONAL hint, NOT a selection authority.
        da = fm.get("agent_object_hint_ref")
        if isinstance(da, str) and da.strip():
            if not da.startswith("agent-object:"):
                violations.append(f"{rel}: agent_object_hint_ref '{da}' must be an agent-object: ref")
            else:
                slug = da.split(":", 1)[1]
                if not (repo / "agent" / "objects" / f"{slug}.yaml").is_file():
                    violations.append(
                        f"{rel}: agent_object_hint_ref '{da}' has no agent/objects/{slug}.yaml"
                    )
        # PROSE<->YAML drift: the agent-readable ## body is what the Agent actually
        # reads to know WHICH fields to return; the primary return.yaml is what the
        # Link gate REQUIRES. If a required field is added to return.yaml but never
        # named in the body, the Agent omits it and a real building HOLDS on a
        # missing required field while every existing checker stays green. Assert
        # every field in the PRIMARY required_return_shape is named in the body text.
        violations.extend(
            _prose_return_shape_drift_violations(
                repo, rel, _instruction_body(text), primary_return_ref
            )
        )

    # Coverage ("is every NEEDED step kind present?") is NOT self-checked here: a
    # brick-library-vs-itself count would be tautological. U4 retired the
    # step-templates.yaml expected-kind source and moved that responsibility to the
    # preset-references check -- a kind is NEEDED iff a preset references it, and
    # check_brick_template_catalog_restructure verifies every preset
    # step_template_ref resolves to an active step kind (now sourced from
    # bricks/<kind>/brick.md). This checker keeps each present brick spec complete +
    # resolvable.

    # U2 regression net (finding-5): the Builder's NEED<->CAPABILITY resolution
    # and required_return_shape derivation had no committed regression evidence.
    # Build the step_template registry once via the SAME path the Builder uses and
    # assert, per kind, that (a) the resolved agent_object_ref equals the spec's
    # declared agent_object_hint_ref (9/10 kinds resolve only because that hint
    # disambiguates a multi-candidate NEED -- a drift here means the match no
    # longer lands on the hinted agent), and (b) the registry's
    # required_return_shape equals the PRIMARY required_return_template_refs entry's
    # required_return_shape (refs[0] only; the 2nd transition-concern ref is
    # excluded), computed INDEPENDENTLY here by reading the template YAML so the
    # assertion is not tautological with the code under test. A registry-build
    # failure is wrapped into a clear fail-closed violation (not a traceback).
    if run_u2:
        violations.extend(_u2_resolution_regression_violations(repo, specs))

    return sorted(set(violations)), len(specs)


def _fixture_text(*, primary_ref: str | None = None) -> str:
    primary = primary_ref or "brick/templates/bricks/work/return.yaml"
    return f"""---
brick_kind: work
brick_word: work
performer_word: dev
requires_brick_write_scope: yes
performer_lane_need: maker
agent_object_hint_ref: agent-object:dev
required_return_template_refs:
  - {primary}
link_movement_literal: forward
brick_contract: Fixture work Brick for checker FIRE.
---
## Work

Do fixture work. Return `observed_evidence` and `not_proven`.
"""


def _write_fixture_repo(root: Path) -> None:
    kind_dir = root / BRICKS_DIR / "work"
    kind_dir.mkdir(parents=True, exist_ok=True)
    (kind_dir / BRICK_SPEC_FILENAME).write_text(_fixture_text(), encoding="utf-8")
    (kind_dir / BRICK_RETURN_FILENAME).write_text(
        "template_ref: brick-template:work-return\n"
        "required_return_shape:\n"
        "  - observed_evidence\n"
        "  - not_proven\n",
        encoding="utf-8",
    )
    agent_dir = root / "agent" / "objects"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "dev.yaml").write_text("object_ref: agent-object:dev\n", encoding="utf-8")


def _run_fire_fixtures() -> tuple[int, tuple[str, ...]]:
    fixtures = {
        "flat_spec_rejected": (
            lambda root: (root / BRICKS_DIR / "work.md").write_text(
                _fixture_text(),
                encoding="utf-8",
            ),
            "flat brick specs are retired",
        ),
        "missing_return_rejected": (
            lambda root: (root / BRICKS_DIR / "work" / BRICK_RETURN_FILENAME).unlink(),
            f"missing primary {BRICK_RETURN_FILENAME}",
        ),
        "primary_return_mismatch_rejected": (
            lambda root: _write_primary_mismatch_fixture(root),
            "primary required_return_template_refs entry must be",
        ),
        "prose_return_shape_drift_rejected": (
            lambda root: _write_prose_drift_fixture(root),
            "## body prose does not name PRIMARY required_return_shape",
        ),
        # L legacy cut (0610): a retired legacy frontmatter spelling on an active
        # brick spec is a violation here AND a loader rejection (see the
        # loader-level FIRE below).
        "legacy_frontmatter_key_rejected": (
            lambda root: _write_legacy_frontmatter_fixture(root),
            "retired legacy frontmatter field 'write_need' is not admitted",
        ),
    }
    results: list[str] = []
    for name, (mutate, expected_text) in fixtures.items():
        with tempfile.TemporaryDirectory(prefix="bp-bricks-spec-fire-") as tmp:
            root = Path(tmp)
            _write_fixture_repo(root)
            mutate(root)
            violations, _count = find_violations(root, run_u2=False)
            if not any(expected_text in violation for violation in violations):
                observed = "\n".join(f"- {violation}" for violation in violations) or "<none>"
                raise ValueError(
                    f"FIRE fixture {name} expected {expected_text!r}, observed:\n{observed}"
                )
            results.append(f"{name}:{expected_text}")
    return len(results), tuple(results)


def _write_primary_mismatch_fixture(root: Path) -> None:
    alternate_ref = "brick/templates/bricks/transition-concern-return.yaml"
    alternate = root / alternate_ref
    alternate.parent.mkdir(parents=True, exist_ok=True)
    alternate.write_text(
        "template_ref: brick-template:transition-concern-return\n"
        "required_return_shape:\n"
        "  - transition_concern_evidence\n"
        "  - not_proven\n",
        encoding="utf-8",
    )
    kind_dir = root / BRICKS_DIR / "work"
    (kind_dir / BRICK_SPEC_FILENAME).write_text(
        _fixture_text(primary_ref=alternate_ref),
        encoding="utf-8",
    )


def _write_prose_drift_fixture(root: Path) -> None:
    """Body names observed_evidence but DROPS not_proven (a primary-shape field)."""
    kind_dir = root / BRICKS_DIR / "work"
    body_drops_field = _fixture_text().replace(
        "Do fixture work. Return `observed_evidence` and `not_proven`.",
        "Do fixture work. Return `observed_evidence`.",
    )
    (kind_dir / BRICK_SPEC_FILENAME).write_text(body_drops_field, encoding="utf-8")


def _write_legacy_frontmatter_fixture(root: Path) -> None:
    """Spec carries the retired legacy ``write_need`` spelling (L legacy cut 0610)."""
    kind_dir = root / BRICKS_DIR / "work"
    legacy_text = _fixture_text().replace(
        "requires_brick_write_scope: yes",
        "write_need: yes",
    )
    (kind_dir / BRICK_SPEC_FILENAME).write_text(legacy_text, encoding="utf-8")


def _run_loader_legacy_key_fire() -> str:
    """LOADER-level FIRE (L legacy cut 0610): the Builder loader REJECTS legacy keys.

    Drives the REAL Builder source path
    (plan_rendering._step_templates_from_bricks) over a fixture repo whose
    work/brick.md carries the retired ``write_need`` spelling and asserts the
    loader raises a CLEAR error naming both the legacy and the canonical key.
    The rejection fires BEFORE agent/return-template resolution, so the minimal
    fixture repo is sufficient. Anti-tautology: restoring the loader's old
    alias-read behavior makes the loader NOT raise and this FIRE goes RED.
    """
    repo_root = Path(__file__).resolve().parents[2]
    import_identity = repo_root / "support" / "import_identity"
    for entry in (str(import_identity), str(repo_root)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    from brick_protocol.support.operator.plan_rendering import _step_templates_from_bricks

    with tempfile.TemporaryDirectory(prefix="bp-bricks-legacy-loader-fire-") as tmp:
        root = Path(tmp)
        _write_fixture_repo(root)
        _write_legacy_frontmatter_fixture(root)
        try:
            _step_templates_from_bricks(root)
        except ValueError as exc:
            message = str(exc)
            if (
                "retired legacy frontmatter key" in message
                and "write_need" in message
                and "requires_brick_write_scope" in message
            ):
                return "legacy_frontmatter_key_loader_reject:retired legacy frontmatter key(s) not admitted"
            raise ValueError(
                f"loader legacy-key FIRE rejected with an unexpected message: {message}"
            )
        raise ValueError(
            "loader legacy-key FIRE was NOT rejected: "
            "_step_templates_from_bricks accepted a retired legacy frontmatter key"
        )


def _primary_return_shape_from_template(repo: Path, primary_ref: str) -> str | None:
    """Independently read refs[0]'s required_return_shape list -> comma-joined text.

    Returns None (with no exception) if the ref does not resolve to a YAML mapping
    declaring a non-empty required_return_shape list; the caller turns None into a
    clear violation. Computed WITHOUT the plan_rendering derivation so this stays a
    genuine regression net rather than a tautology.
    """
    import yaml  # type: ignore[import-not-found]

    if not isinstance(primary_ref, str) or not primary_ref.strip():
        return None
    pure = PurePosixPath(primary_ref.strip())
    if pure.is_absolute() or ".." in pure.parts:
        return None
    path = repo / primary_ref.strip()
    if not path.is_file():
        return None
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        return None
    shape = doc.get("required_return_shape")
    if not isinstance(shape, list) or not shape:
        return None
    fields: list[str] = []
    for item in shape:
        if not isinstance(item, str) or not item.strip():
            return None
        fields.append(item.strip())
    return ",".join(fields)


def _prose_return_shape_drift_violations(
    repo: Path, rel: str, body: str, primary_return_ref: str
) -> list[str]:
    """Every PRIMARY required_return_shape field must be NAMED in the body prose.

    The body (markdown after the frontmatter) is the agent-readable instruction;
    the primary return.yaml declares the fields the Link gate requires. A field
    present in the YAML but absent from the body is a drift that makes the Agent
    omit a now-required field. Matching is by field-name TOKEN presence in the body
    (the prose legitimately names fields in backticks, e.g. ``observed_evidence``),
    using a word boundary so a field name is not spuriously matched as a substring
    of a longer identifier.
    """
    import re

    expected = _primary_return_shape_from_template(repo, primary_return_ref)
    if expected is None:
        # The U2 regression net already turns an unresolvable primary shape into a
        # clear violation; do not double-report it here.
        return []
    fields = [f for f in expected.split(",") if f]
    missing = [
        field
        for field in fields
        if not re.search(rf"(?<![0-9A-Za-z_]){re.escape(field)}(?![0-9A-Za-z_])", body)
    ]
    if not missing:
        return []
    return [
        f"{rel}: ## body prose does not name PRIMARY required_return_shape "
        f"field(s) {', '.join(missing)} (Agent would omit a required field that the "
        f"Link gate requires -- prose<->return.yaml drift)"
    ]


def _u2_resolution_regression_violations(repo: Path, specs: dict[str, dict]) -> list[str]:
    # Standalone bootstrap (codex U2-4 P3): allow `python3 check_bricks_spec_completeness.py`
    # from repo root WITHOUT the canonical PYTHONPATH=support/import_identity, mirroring
    # the engine-backed standalone checkers (e.g. check_building_operator_driver0).
    import_identity = repo / "support" / "import_identity"
    for entry in (str(import_identity), str(repo)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    from brick_protocol.support.operator.plan_rendering import _step_templates_from_bricks

    violations: list[str] = []
    try:
        registry = _step_templates_from_bricks(repo)
    except (OSError, ValueError) as exc:
        return [
            "U2 regression: building the step_template registry from bricks/<kind>/brick.md "
            f"failed (the Builder auto-fill source cannot be resolved): {exc}"
        ]
    for kind, fm in sorted(specs.items()):
        row = registry.get(f"building-step-template:{kind}")
        if not isinstance(row, dict):
            violations.append(
                f"U2 regression: kind '{kind}' has a brick spec but no step_template "
                "registry row (Builder auto-fill would not resolve this kind)"
            )
            continue
        # (a) resolved agent_object_ref must equal the spec's declared hint when present.
        default_agent = _fm_value(fm, "agent_object_hint_ref", "default_agent")
        default_agent = default_agent.strip() if isinstance(default_agent, str) else default_agent
        resolved_agent = row.get("agent_object_ref")
        if default_agent and resolved_agent != default_agent:
            violations.append(
                f"U2 regression: kind '{kind}' resolved agent_object_ref "
                f"'{resolved_agent}' != declared agent_object_hint_ref '{default_agent}' "
                "(NEED<->CAPABILITY match no longer lands on the declared agent)"
            )
        # (b) registry required_return_shape must equal the PRIMARY (refs[0])
        # return template required_return_shape, computed independently here.
        rt = _fm_value(fm, "required_return_template_refs", "return_template")
        if isinstance(rt, str):
            primary_ref = rt
        elif isinstance(rt, list) and rt:
            primary_ref = rt[0]
        else:
            primary_ref = None
        expected_shape = (
            _primary_return_shape_from_template(repo, primary_ref)
            if primary_ref is not None
            else None
        )
        if expected_shape is None:
            violations.append(
                f"U2 regression: kind '{kind}' PRIMARY return_template "
                f"'{primary_ref}' does not declare a resolvable required_return_shape "
                "list (cannot prove the Builder's derived shape)"
            )
        elif row.get("required_return_shape") != expected_shape:
            violations.append(
                f"U2 regression: kind '{kind}' registry required_return_shape "
                f"'{row.get('required_return_shape')}' != PRIMARY return_template "
                f"required_return_shape '{expected_shape}'"
            )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: every brick spec (bricks/<kind>/brick.md) has the "
            "required canonical frontmatter (Brick contract + Builder selection "
            "metadata), resolving required_return_template_refs "
            "(and agent_object_hint_ref if present -- a hint, not authority), "
            "a brick_kind matching the filename, and a non-empty "
            "instruction body. (Needed-kind coverage is the preset-references "
            "check's job.) Does not prove instruction correctness, source truth, "
            "success, quality, or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    try:
        fire_count, fire_results = _run_fire_fixtures()
        loader_fire_result = _run_loader_legacy_key_fire()
        fire_count += 1
        fire_results = (*fire_results, loader_fire_result)
        violations, count = find_violations(repo)
    except (OSError, ValueError) as exc:
        print(f"bricks spec completeness rejected: {exc}")
        return 1

    if violations:
        print("bricks spec completeness rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker proves only that brick specs are complete + "
            "resolve; it does not prove the instruction is correct, nor source "
            "truth, success, quality, or Movement authority."
        )
        return 1

    print(
        "bricks spec completeness passed: "
        f"{count} brick spec(s) complete + resolvable; "
        f"{fire_count} FIRE fixture(s) rejected."
    )
    print("- fixtures: " + ", ".join(fire_results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
