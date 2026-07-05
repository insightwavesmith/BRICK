#!/usr/bin/env python3
"""Behavioral checker for resume/approval operator ergonomics.

Support evidence only: this checker exercises path resolution and request
preparation mechanics. It does not call providers, choose Movement, judge source
truth, success, or quality.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import os.path as _osp
import sys

_REPO_ROOT = _osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_IMPORT_IDENTITY = _osp.join(_REPO_ROOT, "support", "import_identity")
if _IMPORT_IDENTITY not in sys.path:
    sys.path.insert(0, _IMPORT_IDENTITY)


def _write_building_signature(root: Path) -> None:
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "work").mkdir(parents=True, exist_ok=True)


def _assert_building_ref_resolution(repo: Path) -> int:
    from support.operator import onboard

    with tempfile.TemporaryDirectory(prefix="bp-resume-surface-root-") as tmpdir:
        output_root = Path(tmpdir) / "goal-runs"
        output_root.mkdir()
        goal_runs_root = output_root / "same-name-building"
        repo_root = repo / "project" / "brick-protocol" / "buildings" / "same-name-building"
        _write_building_signature(goal_runs_root)
        resolved, _candidates = onboard._resolve_approval_building_root(
            "same-name-building",
            output_root=output_root,
            repo_root=repo,
        )
        if resolved != goal_runs_root.resolve():
            raise AssertionError("existing output_root Building no longer has precedence")

        repo_only_ref = "project/brick-protocol/buildings/resume-surface-repo-relative"
        repo_only_root = repo / repo_only_ref
        try:
            _write_building_signature(repo_only_root)
            resolved, _candidates = onboard._resolve_approval_building_root(
                repo_only_ref,
                output_root=None,
                repo_root=repo,
            )
            if resolved != repo_only_root.resolve():
                raise AssertionError("repo-relative Building ref did not resolve to repo root")
        finally:
            for child in (repo_only_root / "raw", repo_only_root / "work"):
                try:
                    child.rmdir()
                except OSError:
                    pass
            try:
                repo_only_root.rmdir()
            except OSError:
                pass

        missing, candidates = onboard._resolve_approval_building_root(
            "project/brick-protocol/buildings/definitely-missing-resume-surface",
            output_root=None,
            repo_root=repo,
        )
        if missing is not None or not candidates:
            raise AssertionError("missing Building ref did not produce explicit candidates")
    return 3


def _assert_adapter_cwd_auto_worktree(repo: Path) -> int:
    import brick_protocol.support.operator.worktree_sandbox as sandbox_mod
    from support.operator import onboard

    calls: list[tuple[str, Path, str]] = []

    def fake_probe(repo_root: Path) -> Any:
        calls.append(("probe", Path(repo_root), ""))
        return SimpleNamespace(ok=True, reason="git-head-resolved", base_sha="abc123")

    def fake_create(repo_root: Path, *, building_id: str, base_sha: str) -> Any:
        calls.append(("create", Path(repo_root), building_id))
        return SimpleNamespace(
            path=Path("/tmp/bp-resume-surface-worktree") / building_id,
            base_sha=base_sha,
        )

    original_probe = sandbox_mod.probe_worktree_capable
    original_create = sandbox_mod.create_worktree_sandbox
    try:
        sandbox_mod.probe_worktree_capable = fake_probe
        sandbox_mod.create_worktree_sandbox = fake_create
        path, observation = onboard._prepare_resume_adapter_cwd(
            repo_root=repo,
            building_id="resume-surface-building",
            adapter_cwd=None,
        )
    finally:
        sandbox_mod.probe_worktree_capable = original_probe
        sandbox_mod.create_worktree_sandbox = original_create
    if path != Path("/tmp/bp-resume-surface-worktree/resume-surface-building"):
        raise AssertionError(f"auto worktree path was not returned: {path}")
    if not isinstance(observation, dict) or not observation.get("adapter_cwd_auto_created"):
        raise AssertionError("auto worktree observation was not recorded")
    if [call[0] for call in calls] != ["probe", "create"]:
        raise AssertionError(f"worktree probe/create sequence drifted: {calls!r}")

    explicit = Path(tempfile.mkdtemp(prefix="bp-resume-surface-explicit-")).resolve()
    try:
        path, observation = onboard._prepare_resume_adapter_cwd(
            repo_root=repo,
            building_id="resume-surface-building",
            adapter_cwd=explicit,
        )
        if path != explicit or observation.get("adapter_cwd_auto_created") is not False:
            raise AssertionError("explicit adapter_cwd no longer has priority")
    finally:
        explicit.rmdir()
    return 2


def _assert_vessel_step_output_source_fact_fallback(repo: Path) -> int:
    from support.operator import run as run_mod

    with tempfile.TemporaryDirectory(prefix="bp-resume-surface-source-") as tmpdir:
        default_root = Path(tmpdir) / "buildings"
        building_id = "resume-surface-source-fact"
        step_ref = "resume-surface-upstream"
        source_ref = (
            "work/step-outputs/"
            "resume-surface-upstream-attempt-1/step-output.json"
        )
        step_output = default_root / building_id / source_ref
        step_output.parent.mkdir(parents=True)
        step_output.write_text(
            '{"step_ref":"%s","attempt_index":1,"returned":{"marker":"vessel"}}\n'
            % step_ref,
            encoding="utf-8",
        )
        original_default = run_mod.DEFAULT_BUILDINGS_ROOT
        try:
            run_mod.DEFAULT_BUILDINGS_ROOT = default_root
            bodies = run_mod._adapter_source_fact_bodies(
                {},
                [source_ref],
                building_id=building_id,
            )
        finally:
            run_mod.DEFAULT_BUILDINGS_ROOT = original_default
        if source_ref not in bodies or '"marker":"vessel"' not in bodies[source_ref]:
            raise AssertionError("existing vessel step-output source_fact was not loaded")

        try:
            run_mod._adapter_source_fact_bodies(
                {},
                ["work/step-outputs/missing/step-output.json"],
                building_id=building_id,
            )
        except ValueError as exc:
            if "missing step-output source_fact body/evidence" not in str(exc):
                raise
        else:
            raise AssertionError("missing step-output source_fact no longer fails closed")
    return 2


def run(repo: Path) -> int:
    inspected = 0
    inspected += _assert_building_ref_resolution(repo)
    inspected += _assert_adapter_cwd_auto_worktree(repo)
    inspected += _assert_vessel_step_output_source_fact_fallback(repo)
    return inspected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=_REPO_ROOT)
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    inspected = run(repo)
    print(f"resume_disposition_surface passed: inspected {inspected} probe(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
