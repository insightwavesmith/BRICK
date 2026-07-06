"""Mutation-RED manifest coverage checker.

Support checker mechanics only: verifies that the A+ W2 manifest rows point to
existing checker/probe literals and that manifest drift goes RED. It authors no
axis facts, chooses no Movement, and judges no success or quality.
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    load_yaml_subset_file,
    require_mapping,
    require_string,
)


MANIFEST_REL = "support/checkers/mutation_red_manifest.yaml"
EXPECTED_SCHEMA = "mutation-red-manifest/v1"
EXPECTED_SURFACES = frozenset(
    {
        "declared_plan_revision",
        "plan_expansion",
        "route_materialization",
        "step_output",
        "gate_sequence_decision",
        "gate_policy_action_single_source",
        "positive_int_bool_boundary",
        "write_scope_commit_gate",
        "write_scope_segment_matcher",
        "hold_lifecycle",
        "graphdecl_proposal_path",
        "graphdecl_model_inheritance",
        "build_unify_casting_convergence",
        "build_unify_launch_repo_root_line",
        "build_unify_model_alias_loud",
    }
)
MIN_AUDIT_MUTANTS = 5


def run_mutation_red_manifest(repo: Path) -> KernelResult:
    manifest_path = repo / MANIFEST_REL
    manifest = load_yaml_subset_file(repo, MANIFEST_REL)
    inspected = _validate_manifest(repo, manifest, manifest_rel=MANIFEST_REL)
    probe_outputs = _run_manifest_mutation_probes(repo, manifest)
    return KernelResult(
        check_id="mutation_red_manifest",
        inspected=inspected,
        output=(
            "mutation_red_manifest passed: "
            f"{len(EXPECTED_SURFACES)} surface row(s) and at least "
            f"{MIN_AUDIT_MUTANTS} S11 mutant row(s) point at existing RED literals in "
            f"{manifest_path.relative_to(repo).as_posix()}. "
            + " ".join(probe_outputs)
        ),
    )


def _validate_manifest(repo: Path, manifest: Mapping[str, Any], *, manifest_rel: str) -> int:
    if manifest.get("schema") != EXPECTED_SCHEMA:
        raise ProfileError(
            f"{manifest_rel}: schema must be {EXPECTED_SCHEMA!r}, observed {manifest.get('schema')!r}"
        )
    surfaces = _require_mapping_list(manifest.get("surfaces"), f"{manifest_rel}: surfaces")
    observed = [require_string(row.get("surface"), f"{manifest_rel}: surfaces[].surface") for row in surfaces]
    if set(observed) != EXPECTED_SURFACES or len(observed) != len(EXPECTED_SURFACES):
        raise ProfileError(
            f"{manifest_rel}: surfaces must be exactly {sorted(EXPECTED_SURFACES)}, observed {observed}"
        )
    inspected = 0
    for row in surfaces:
        _validate_manifest_row(repo, row, manifest_rel=manifest_rel, row_kind="surface")
        inspected += 1

    mutants = _require_mapping_list(manifest.get("audit_mutants"), f"{manifest_rel}: audit_mutants")
    if len(mutants) < MIN_AUDIT_MUTANTS:
        raise ProfileError(
            f"{manifest_rel}: audit_mutants must include at least {MIN_AUDIT_MUTANTS} row(s)"
        )
    for row in mutants:
        mutant_id = require_string(row.get("mutant_id"), f"{manifest_rel}: audit_mutants[].mutant_id")
        surface = require_string(row.get("surface"), f"{manifest_rel}: audit_mutants[{mutant_id}].surface")
        if surface not in EXPECTED_SURFACES:
            raise ProfileError(f"{manifest_rel}: audit mutant {mutant_id} names unknown surface {surface!r}")
        _validate_manifest_row(repo, row, manifest_rel=manifest_rel, row_kind=f"audit_mutant {mutant_id}")
        require_string(row.get("audit_anchor"), f"{manifest_rel}: audit_mutants[{mutant_id}].audit_anchor")
        inspected += 1
    return inspected


def _require_mapping_list(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ProfileError(f"{label} must be a list of mappings")
    return [require_mapping(item, label) for item in value]


def _validate_manifest_row(
    repo: Path,
    row: Mapping[str, Any],
    *,
    manifest_rel: str,
    row_kind: str,
) -> None:
    fixture_rel = require_string(row.get("fixture_path"), f"{manifest_rel}: {row_kind}.fixture_path")
    fixture_path = _repo_file(repo, fixture_rel, f"{manifest_rel}: {row_kind}.fixture_path")
    identifier = require_string(
        row.get("fixture_identifier"),
        f"{manifest_rel}: {row_kind}.fixture_identifier",
    )
    if identifier not in fixture_path.read_text(encoding="utf-8"):
        raise ProfileError(
            f"{manifest_rel}: {row_kind} fixture_identifier {identifier!r} not found in {fixture_rel}"
        )
    if row_kind == "surface":
        require_string(row.get("incident_anchor"), f"{manifest_rel}: {row_kind}.incident_anchor")


def _repo_file(repo: Path, relative: str, label: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ProfileError(f"{label} escapes repo: {relative!r}")
    path = repo / candidate
    if not path.is_file():
        raise ProfileError(f"{label} does not point to an existing file: {relative!r}")
    return path


def _run_manifest_mutation_probes(repo: Path, manifest: Mapping[str, Any]) -> tuple[str, ...]:
    outputs = [
        _expect_reject(
            "row deletion",
            lambda: _validate_manifest(
                repo,
                _without_first_surface(manifest),
                manifest_rel="<mutation-red-manifest-row-deletion>",
            ),
        ),
        _expect_reject(
            "bogus fixture identifier",
            lambda: _validate_manifest(
                repo,
                _with_first_identifier(manifest, "missing-fixture-identifier-for-mutation-red"),
                manifest_rel="<mutation-red-manifest-bogus-identifier>",
            ),
        ),
    ]
    outputs.append(_fixture_rename_probe(repo, manifest))
    return tuple(outputs)


def _without_first_surface(manifest: Mapping[str, Any]) -> dict[str, Any]:
    mutated = _copy_manifest(manifest)
    mutated["surfaces"] = list(mutated.get("surfaces") or [])[1:]
    return mutated


def _with_first_identifier(manifest: Mapping[str, Any], identifier: str) -> dict[str, Any]:
    mutated = _copy_manifest(manifest)
    rows = list(mutated.get("surfaces") or [])
    first = dict(rows[0])
    first["fixture_identifier"] = identifier
    rows[0] = first
    mutated["surfaces"] = rows
    return mutated


def _fixture_rename_probe(repo: Path, manifest: Mapping[str, Any]) -> str:
    with tempfile.TemporaryDirectory(prefix="brick-mut-red-manifest-") as raw:
        temp_repo = Path(raw)
        rows = list(manifest.get("surfaces") or [])
        first = require_mapping(rows[0], "fixture rename probe first surface")
        fixture_rel = require_string(first.get("fixture_path"), "fixture rename probe fixture_path")
        source = _repo_file(repo, fixture_rel, "fixture rename probe source")
        target = temp_repo / fixture_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        renamed = target.with_name(target.name + ".renamed")
        try:
            target.rename(renamed)
            _validate_manifest(
                temp_repo,
                manifest,
                manifest_rel="<mutation-red-manifest-fixture-rename>",
            )
        except ProfileError:
            return "mutation RED observed: fixture file rename was rejected."
        finally:
            if renamed.exists() and not target.exists():
                renamed.rename(target)
    raise ProfileError("mutation RED failed: fixture file rename was accepted")


def _copy_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    copied: dict[str, Any] = dict(manifest)
    copied["surfaces"] = [dict(row) for row in manifest.get("surfaces") or []]
    copied["audit_mutants"] = [dict(row) for row in manifest.get("audit_mutants") or []]
    return copied


def _expect_reject(label: str, fn: Any) -> str:
    try:
        fn()
    except ProfileError:
        return f"mutation RED observed: manifest {label} was rejected."
    raise ProfileError(f"mutation RED failed: manifest {label} was accepted")
