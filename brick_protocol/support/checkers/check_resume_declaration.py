#!/usr/bin/env python3
"""Behavioral checker for the JSON resume declaration support surface.

Support evidence only. The probes exercise declaration loading, hold preflight,
explicit adapter_cwd selection, CLI admission pins, and lowering into the
existing onboard resume seam. They do not call providers, choose Movement,
judge source truth, success, or quality.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import sys

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from brick_protocol.support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _assert_loader_and_shape(repo: Path) -> int:
    from brick_protocol.support.operator import resume_declaration as mod

    del repo
    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-loader-") as tmpdir:
        root = Path(tmpdir)
        building = root / "building"
        building.mkdir()
        valid = root / "valid.json"
        _write_json(
            valid,
            {
                "building_ref": str(building),
                "chain": "until-terminal",
                "dispositions": [
                    {"on": "human_or_coo_gate_pause", "action": "forward"},
                    {"on": "target_node_budget_exhausted", "action": "raise", "budget_increment": 1},
                ],
            },
        )
        normalized = mod.validate_resume_declaration(mod.load_resume_declaration(valid))
        if normalized["chain"] != "until-terminal":
            raise AssertionError("chain was not normalized from the declaration")
        if normalized["author_ref"] != "coo:resume-decl":
            raise AssertionError("default author_ref drifted")

        bad = root / "bad.json"
        _write_json(
            bad,
            {
                "building_ref": str(building),
                "dispositions": [{"on": "human_or_coo_gate_pause", "action": "reroute"}],
            },
        )
        try:
            mod.validate_resume_declaration(mod.load_resume_declaration(bad))
        except ValueError as exc:
            if "one of raise, forward, stop" not in str(exc):
                raise
        else:
            raise AssertionError("reroute action was accepted by the narrow decl grammar")

        forward_budget = root / "forward-budget.json"
        _write_json(
            forward_budget,
            {
                "building_ref": str(building),
                "dispositions": [
                    {"on": "human_or_coo_gate_pause", "action": "forward", "budget_increment": 1}
                ],
            },
        )
        try:
            mod.validate_resume_declaration(mod.load_resume_declaration(forward_budget))
        except ValueError as exc:
            if "budget_increment is admitted only for action=raise" not in str(exc):
                raise
        else:
            raise AssertionError("forward+budget_increment was accepted")
    return 6


def _assert_preflight_class_action_reject(repo: Path) -> int:
    from brick_protocol.support.operator import resume_declaration as mod

    building = repo / "project" / "brick-protocol" / "buildings" / "resume-decl-checker-preflight"
    hold = {
        "hold_reason": "adapter_error_frontier",
        "source_step_ref": "resume-check-step",
        "pending_target_ref": "brick-resume-check-target",
    }
    original_observe = mod.observe_building_frontier
    original_read = mod._read_written_dynamic_plan
    try:
        mod.observe_building_frontier = lambda _root, repo_root: {
            "frontier_kind": "link_paused",
            "frontier_reason": "adapter_error_frontier",
        }
        mod._read_written_dynamic_plan = lambda _root: (
            {},
            {"walker_mode": "dynamic", "hold": hold},
        )
        normalized = {
            "building_ref": str(building),
            "chain": "single",
            "author_ref": "coo:resume-decl",
            "adapter_timeout_seconds": 120,
            "dispositions": [{"on": "adapter_error_frontier", "action": "forward"}],
        }
        try:
            mod.preflight_resume_declaration(normalized, repo_root=repo)
        except ValueError as exc:
            if "not admitted for hold_reason='adapter_error_frontier'" not in str(exc):
                raise
        else:
            raise AssertionError("class/action mismatch did not fail loudly")
    finally:
        mod.observe_building_frontier = original_observe
        mod._read_written_dynamic_plan = original_read
    return 1


def _assert_class_action_prevalidation_mutation_red(repo: Path) -> int:
    from brick_protocol.support.operator import resume_declaration as mod

    building = repo / "project" / "brick-protocol" / "buildings" / "resume-decl-checker-prevalidation-red"
    hold = {
        "hold_reason": "adapter_error_frontier",
        "source_step_ref": "resume-check-step",
        "pending_target_ref": "brick-resume-check-target",
    }
    original_observe = mod.observe_building_frontier
    original_read = mod._read_written_dynamic_plan
    original_run = mod._run_approve_entry
    original_cwd = mod.resolve_dispo_adapter_cwd
    try:
        mod.observe_building_frontier = lambda _root, repo_root: {
            "frontier_kind": "link_paused",
            "frontier_reason": "adapter_error_frontier",
        }
        mod._read_written_dynamic_plan = lambda _root: (
            {},
            {"walker_mode": "dynamic", "hold": hold},
        )
        mod.resolve_dispo_adapter_cwd = lambda repo_root, building_id: Path("/tmp") / "bp-resume-red"
        mod._run_approve_entry = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("class/action prevalidation removal caused misjudgment acceptance")
        )
        try:
            mod.run_resume_declaration(
                {
                    "building_ref": str(building),
                    "chain": "single",
                    "dispositions": [{"on": "adapter_error_frontier", "action": "forward"}],
                },
                repo_root=repo,
            )
        except ValueError as exc:
            if "not admitted for hold_reason='adapter_error_frontier'" not in str(exc):
                raise
        else:
            raise AssertionError(
                "class-action prevalidation removal mutation-RED did not reject misjudgment acceptance"
            )
    finally:
        mod.observe_building_frontier = original_observe
        mod._read_written_dynamic_plan = original_read
        mod._run_approve_entry = original_run
        mod.resolve_dispo_adapter_cwd = original_cwd
    return 1


def _assert_adapter_cwd_choice(repo: Path) -> int:
    from brick_protocol.support.operator import resume_declaration as mod

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-home-") as tmpdir:
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir
        residue = Path(tmpdir) / ".brick" / "worktrees" / "resume-decl-pure-residue"
        residue.mkdir(parents=True)
        try:
            choice = mod._dispo_adapter_cwd_choice(
                repo_root=repo,
                building_id="resume-decl-pure-residue",
            )
            if choice.get("choice_kind") != "residue":
                raise AssertionError("_dispo_adapter_cwd_choice did not expose residue policy")
            if Path(str(choice.get("adapter_cwd"))).resolve() != residue.resolve():
                raise AssertionError("_dispo_adapter_cwd_choice returned the wrong residue path")
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-home-") as tmpdir:
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir
        original_probe = mod.probe_worktree_capable
        try:
            mod.probe_worktree_capable = lambda _repo: type(
                "Probe",
                (),
                {"ok": False, "base_sha": ""},
            )()
            choice = mod._dispo_adapter_cwd_choice(
                repo_root=repo,
                building_id=f"resume-decl-pure-fallback-{Path(tmpdir).name}",
            )
            if choice.get("choice_kind") != "fallback_probe_unavailable":
                raise AssertionError("_dispo_adapter_cwd_choice did not expose probe fallback")
            if "fallback" not in str(choice.get("fallback_warning") or ""):
                raise AssertionError("_dispo_adapter_cwd_choice did not report fallback warning")
        finally:
            mod.probe_worktree_capable = original_probe
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-home-") as tmpdir:
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir
        original_probe = mod.probe_worktree_capable
        try:
            mod.probe_worktree_capable = lambda _repo: type(
                "Probe",
                (),
                {"ok": True, "base_sha": "abc123"},
            )()
            choice = mod._dispo_adapter_cwd_choice(
                repo_root=repo,
                building_id=f"resume-decl-pure-git-{Path(tmpdir).name}",
            )
            if choice.get("choice_kind") != "git_worktree_add":
                raise AssertionError("_dispo_adapter_cwd_choice did not expose git add policy")
            if choice.get("base_sha") != "abc123":
                raise AssertionError("_dispo_adapter_cwd_choice did not carry base sha")
        finally:
            mod.probe_worktree_capable = original_probe
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-home-") as tmpdir:
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir
        residue = Path(tmpdir) / ".brick" / "worktrees" / "resume-decl-residue"
        residue.mkdir(parents=True)
        try:
            chosen = mod.resolve_dispo_adapter_cwd(
                repo_root=repo,
                building_id="resume-decl-residue",
            )
            if chosen != residue.resolve():
                raise AssertionError("existing ~/.brick/worktrees residue was not reused")
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-home-") as tmpdir:
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir
        original_probe = mod.probe_worktree_capable
        building_id = "resume-decl-fallback-no-git"
        fallback = Path("/tmp") / f"brick-coo-dispo-{building_id}"
        try:
            mod.probe_worktree_capable = lambda _repo: type(
                "Probe",
                (),
                {"ok": False, "base_sha": ""},
            )()
            chosen = mod.resolve_dispo_adapter_cwd(
                repo_root=repo,
                building_id=building_id,
            )
            if chosen != fallback.resolve() or not fallback.is_dir():
                raise AssertionError("non-git adapter_cwd fallback did not create /tmp path")
        finally:
            mod.probe_worktree_capable = original_probe
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-home-") as tmpdir:
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir
        original_probe = mod.probe_worktree_capable
        original_run = mod.subprocess.run
        building_id = "resume-decl-fallback-git-fail"
        fallback = Path("/tmp") / f"brick-coo-dispo-{building_id}"
        try:
            mod.probe_worktree_capable = lambda _repo: type(
                "Probe",
                (),
                {"ok": True, "base_sha": "abc123"},
            )()
            mod.subprocess.run = lambda *args, **kwargs: type(
                "Completed",
                (),
                {"returncode": 1, "stdout": "", "stderr": "fixture failure"},
            )()
            chosen = mod.resolve_dispo_adapter_cwd(
                repo_root=repo,
                building_id=building_id,
            )
            if chosen != fallback.resolve() or not fallback.is_dir():
                raise AssertionError("git-worktree failure fallback did not create /tmp path")
        finally:
            mod.probe_worktree_capable = original_probe
            mod.subprocess.run = original_run
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home
    return 6


def _assert_dead_end_guidance_mutation_red(repo: Path) -> int:
    from brick_protocol.support.operator import resume_declaration as mod

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-dead-end-") as tmpdir:
        building = Path(tmpdir) / "building"
        building.mkdir()
        original_observe = mod.observe_building_frontier
        try:
            mod.observe_building_frontier = lambda _root, repo_root: {
                "frontier_kind": "evidence_incomplete",
                "frontier_reason": "missing-ledger-tail",
            }
            packet = mod.run_resume_declaration(
                {
                    "building_ref": str(building),
                    "chain": "single",
                    "dispositions": [{"on": "missing-ledger-tail", "action": "forward"}],
                },
                repo_root=repo,
            )
        finally:
            mod.observe_building_frontier = original_observe
        if packet.get("error_kind") != "resume_declaration_dead_end":
            raise AssertionError(f"dead-end preflight did not return declared error: {packet!r}")
        if "COO_GATE_HARVEST_SHA=<anchor>" not in str(packet.get("next_command") or ""):
            raise AssertionError("dead-end orphan-harvest guidance pin was removed")
    return 1


def _assert_runtime_not_approval_hold_dead_end(repo: Path) -> int:
    from brick_protocol.support.operator import resume_declaration as mod

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-runtime-dead-") as tmpdir:
        building = Path(tmpdir) / "building"
        building.mkdir()
        hold = {
            "hold_reason": "human_or_coo_gate_pause",
            "source_step_ref": "step-a",
            "pending_target_ref": "brick-b",
        }
        original_observe = mod.observe_building_frontier
        original_read = mod._read_written_dynamic_plan
        original_run = mod._run_approve_entry
        original_cwd = mod.resolve_dispo_adapter_cwd
        try:
            mod.observe_building_frontier = lambda _root, repo_root: {
                "frontier_kind": "link_paused",
                "frontier_reason": "human_or_coo_gate_pause",
            }
            mod._read_written_dynamic_plan = lambda _root: (
                {},
                {"walker_mode": "dynamic", "hold": hold},
            )
            mod.resolve_dispo_adapter_cwd = lambda repo_root, building_id: Path(tmpdir) / "adapter"
            mod._run_approve_entry = lambda *args, **kwargs: {
                "ok": False,
                "error_kind": "not_approval_hold",
                "frontier_kind": "evidence_incomplete",
            }
            packet = mod.run_resume_declaration(
                {
                    "building_ref": str(building),
                    "chain": "single",
                    "dispositions": [{"on": "human_or_coo_gate_pause", "action": "forward"}],
                },
                repo_root=repo,
            )
        finally:
            mod.observe_building_frontier = original_observe
            mod._read_written_dynamic_plan = original_read
            mod._run_approve_entry = original_run
            mod.resolve_dispo_adapter_cwd = original_cwd
        if packet.get("error_kind") != "resume_declaration_dead_end":
            raise AssertionError(f"runtime not_approval_hold did not map to dead-end: {packet!r}")
        if packet.get("runtime_error_kind") != "not_approval_hold":
            raise AssertionError("runtime dead-end did not preserve runtime_error_kind")
        if "COO_GATE_HARVEST_SHA=<anchor>" not in str(packet.get("next_command") or ""):
            raise AssertionError("runtime dead-end did not print orphan-harvest next command")
    return 1


def _assert_terminal_guards(repo: Path) -> int:
    from brick_protocol.support.operator import resume_declaration as mod

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-no-match-") as tmpdir:
        building = Path(tmpdir) / "building"
        building.mkdir()
        holds = [
            {
                "hold_reason": "human_or_coo_gate_pause",
                "source_step_ref": "step-a",
                "pending_target_ref": "brick-b",
            },
            {
                "hold_reason": "target_node_budget_exhausted",
                "source_step_ref": "step-b",
                "pending_target_ref": "brick-c",
            },
        ]
        index = {"value": 0}

        def fake_observe(_root: Path, repo_root: Path) -> Mapping[str, Any]:
            del repo_root
            hold = holds[index["value"]]
            return {"frontier_kind": "link_paused", "frontier_reason": hold["hold_reason"]}

        def fake_read(_root: Path) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
            return {}, {"walker_mode": "dynamic", "hold": holds[index["value"]]}

        def fake_run(*args: Any, **kwargs: Any) -> dict[str, Any]:
            del args, kwargs
            index["value"] = 1
            return {"ok": True, "frontier_kind": "link_paused"}

        original_observe = mod.observe_building_frontier
        original_read = mod._read_written_dynamic_plan
        original_run = mod._run_approve_entry
        original_cwd = mod.resolve_dispo_adapter_cwd
        try:
            mod.observe_building_frontier = fake_observe
            mod._read_written_dynamic_plan = fake_read
            mod._run_approve_entry = fake_run
            mod.resolve_dispo_adapter_cwd = lambda repo_root, building_id: Path(tmpdir) / "adapter"
            packet = mod.run_resume_declaration(
                {
                    "building_ref": str(building),
                    "chain": "until-terminal",
                    "dispositions": [{"on": "human_or_coo_gate_pause", "action": "forward"}],
                },
                repo_root=repo,
            )
        finally:
            mod.observe_building_frontier = original_observe
            mod._read_written_dynamic_plan = original_read
            mod._run_approve_entry = original_run
            mod.resolve_dispo_adapter_cwd = original_cwd
        if packet.get("error_kind") != "resume_declaration_no_match":
            raise AssertionError(f"next-hold no-match was not terminal: {packet!r}")

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-no-progress-") as tmpdir:
        building = Path(tmpdir) / "building"
        building.mkdir()
        hold = {
            "hold_reason": "human_or_coo_gate_pause",
            "source_step_ref": "step-a",
            "pending_target_ref": "brick-b",
            "paused_at_ref": "pause-a",
        }
        original_observe = mod.observe_building_frontier
        original_read = mod._read_written_dynamic_plan
        original_run = mod._run_approve_entry
        original_cwd = mod.resolve_dispo_adapter_cwd
        try:
            mod.observe_building_frontier = lambda _root, repo_root: {
                "frontier_kind": "link_paused",
                "frontier_reason": "human_or_coo_gate_pause",
            }
            mod._read_written_dynamic_plan = lambda _root: (
                {},
                {"walker_mode": "dynamic", "hold": hold},
            )
            mod._run_approve_entry = lambda *args, **kwargs: {
                "ok": True,
                "frontier_kind": "link_paused",
            }
            mod.resolve_dispo_adapter_cwd = lambda repo_root, building_id: Path(tmpdir) / "adapter"
            packet = mod.run_resume_declaration(
                {
                    "building_ref": str(building),
                    "chain": "until-terminal",
                    "dispositions": [{"on": "human_or_coo_gate_pause", "action": "forward"}],
                },
                repo_root=repo,
            )
        finally:
            mod.observe_building_frontier = original_observe
            mod._read_written_dynamic_plan = original_read
            mod._run_approve_entry = original_run
            mod.resolve_dispo_adapter_cwd = original_cwd
        if packet.get("error_kind") != "resume_declaration_no_progress":
            raise AssertionError(f"repeated frontier did not stop as no-progress: {packet!r}")

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-round-cap-") as tmpdir:
        building = Path(tmpdir) / "building"
        building.mkdir()
        counter = {"value": 0}

        def fake_observe_cap(_root: Path, repo_root: Path) -> Mapping[str, Any]:
            del repo_root
            return {"frontier_kind": "link_paused", "frontier_reason": "human_or_coo_gate_pause"}

        def fake_read_cap(_root: Path) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
            counter["value"] += 1
            return (
                {},
                {
                    "walker_mode": "dynamic",
                    "hold": {
                        "hold_reason": "human_or_coo_gate_pause",
                        "source_step_ref": f"step-{counter['value']}",
                        "pending_target_ref": "brick-b",
                        "paused_at_ref": f"pause-{counter['value']}",
                    },
                },
            )

        original_observe = mod.observe_building_frontier
        original_read = mod._read_written_dynamic_plan
        original_run = mod._run_approve_entry
        original_cwd = mod.resolve_dispo_adapter_cwd
        original_cap = mod._MAX_CHAIN_ROUNDS
        try:
            mod.observe_building_frontier = fake_observe_cap
            mod._read_written_dynamic_plan = fake_read_cap
            mod._run_approve_entry = lambda *args, **kwargs: {
                "ok": True,
                "frontier_kind": "link_paused",
            }
            mod.resolve_dispo_adapter_cwd = lambda repo_root, building_id: Path(tmpdir) / "adapter"
            mod._MAX_CHAIN_ROUNDS = 2
            packet = mod.run_resume_declaration(
                {
                    "building_ref": str(building),
                    "chain": "until-terminal",
                    "dispositions": [{"on": "human_or_coo_gate_pause", "action": "forward"}],
                },
                repo_root=repo,
            )
        finally:
            mod.observe_building_frontier = original_observe
            mod._read_written_dynamic_plan = original_read
            mod._run_approve_entry = original_run
            mod.resolve_dispo_adapter_cwd = original_cwd
            mod._MAX_CHAIN_ROUNDS = original_cap
        if packet.get("error_kind") != "resume_declaration_round_cap":
            raise AssertionError(f"round cap was not terminal: {packet!r}")
    return 3


def _assert_already_complete_noop(repo: Path) -> int:
    from brick_protocol.support.operator import resume_declaration as mod

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-complete-") as tmpdir:
        building = Path(tmpdir) / "building"
        building.mkdir()
        original_observe = mod.observe_building_frontier
        original_cwd = mod.resolve_dispo_adapter_cwd
        original_run = mod._run_approve_entry
        try:
            mod.observe_building_frontier = lambda _root, repo_root: {
                "frontier_kind": "complete",
                "frontier_reason": "",
            }
            mod.resolve_dispo_adapter_cwd = lambda repo_root, building_id: (_ for _ in ()).throw(
                AssertionError("adapter_cwd resolved for already-complete preflight")
            )
            mod._run_approve_entry = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("run_approve_entry called for already-complete preflight")
            )
            packet = mod.run_resume_declaration(
                {
                    "building_ref": str(building),
                    "chain": "single",
                    "dispositions": [{"on": "human_or_coo_gate_pause", "action": "forward"}],
                },
                repo_root=repo,
            )
        finally:
            mod.observe_building_frontier = original_observe
            mod.resolve_dispo_adapter_cwd = original_cwd
            mod._run_approve_entry = original_run
        if not packet.get("ok") or not packet.get("preflight", {}).get("already_complete"):
            raise AssertionError(f"already-complete preflight was not a clean OK: {packet!r}")
        if packet.get("rounds"):
            raise AssertionError("already-complete preflight recorded disposition rounds")
    return 1


def _assert_chain_lowering(repo: Path) -> int:
    from brick_protocol.support.operator import resume_declaration as mod

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-chain-") as tmpdir:
        building = Path(tmpdir) / "building"
        building.mkdir()
        calls: list[Mapping[str, Any]] = []
        states = iter(
            [
                {
                    "frontier_kind": "link_paused",
                    "frontier_reason": "human_or_coo_gate_pause",
                    "hold_reason": "human_or_coo_gate_pause",
                    "source_step_ref": "step-a",
                    "pending_target_ref": "brick-b",
                },
                {
                    "frontier_kind": "link_paused",
                    "frontier_reason": "target_node_budget_exhausted",
                    "hold_reason": "target_node_budget_exhausted",
                    "source_step_ref": "step-b",
                    "pending_target_ref": "brick-c",
                },
            ]
        )
        current: dict[str, Any] = {}

        def fake_observe(_root: Path, repo_root: Path) -> Mapping[str, Any]:
            del repo_root
            if not current:
                current.update(next(states))
            return {
                "frontier_kind": current["frontier_kind"],
                "frontier_reason": current["frontier_reason"],
            }

        def fake_read(_root: Path) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
            return {}, {"walker_mode": "dynamic", "hold": dict(current)}

        def fake_run(
            building_root: Path,
            row: Mapping[str, Any],
            *,
            author_ref: str,
            repo_root: Path,
            adapter_cwd: Path,
            adapter_timeout_seconds: int,
        ) -> dict[str, Any]:
            calls.append(
                {
                    "building_root": str(building_root),
                    "row": dict(row),
                    "author_ref": author_ref,
                    "adapter_cwd": str(adapter_cwd),
                    "adapter_timeout_seconds": adapter_timeout_seconds,
                }
            )
            if len(calls) == 1:
                current.clear()
                current.update(next(states))
                return {"ok": True, "frontier_kind": "link_paused"}
            return {"ok": True, "frontier_kind": "complete"}

        original_observe = mod.observe_building_frontier
        original_read = mod._read_written_dynamic_plan
        original_run = mod._run_approve_entry
        original_cwd = mod.resolve_dispo_adapter_cwd
        try:
            mod.observe_building_frontier = fake_observe
            mod._read_written_dynamic_plan = fake_read
            mod._run_approve_entry = fake_run
            mod.resolve_dispo_adapter_cwd = lambda repo_root, building_id: Path(tmpdir) / "adapter"
            packet = mod.run_resume_declaration(
                {
                    "building_ref": str(building),
                    "chain": "until-terminal",
                    "author_ref": "coo:resume-decl-checker",
                    "dispositions": [
                        {"on": "human_or_coo_gate_pause", "action": "forward"},
                        {"on": "target_node_budget_exhausted", "action": "raise", "budget_increment": 2},
                    ],
                },
                repo_root=repo,
            )
        finally:
            mod.observe_building_frontier = original_observe
            mod._read_written_dynamic_plan = original_read
            mod._run_approve_entry = original_run
            mod.resolve_dispo_adapter_cwd = original_cwd
        if not packet.get("ok") or len(packet.get("rounds") or []) != 2:
            raise AssertionError(f"until-terminal chain did not run two rounds: {packet!r}")
        if calls[0]["row"]["action"] != "forward" or calls[1]["row"]["action"] != "raise":
            raise AssertionError(f"disposition order drifted: {calls!r}")
        if calls[1]["row"].get("budget_increment") != 2:
            raise AssertionError("raise budget_increment was not lowered")
    return 2


def _assert_mid_chain_complete_repreflight(repo: Path) -> int:
    from brick_protocol.support.operator import resume_declaration as mod

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-mid-complete-") as tmpdir:
        building = Path(tmpdir) / "building"
        building.mkdir()
        observations = iter(
            [
                {"frontier_kind": "link_paused", "frontier_reason": "human_or_coo_gate_pause"},
                {"frontier_kind": "complete", "frontier_reason": ""},
            ]
        )
        hold = {
            "hold_reason": "human_or_coo_gate_pause",
            "source_step_ref": "step-a",
            "pending_target_ref": "brick-b",
        }
        original_observe = mod.observe_building_frontier
        original_read = mod._read_written_dynamic_plan
        original_run = mod._run_approve_entry
        original_cwd = mod.resolve_dispo_adapter_cwd
        try:
            mod.observe_building_frontier = lambda _root, repo_root: next(observations)
            mod._read_written_dynamic_plan = lambda _root: (
                {},
                {"walker_mode": "dynamic", "hold": hold},
            )
            mod.resolve_dispo_adapter_cwd = lambda repo_root, building_id: Path(tmpdir) / "adapter"
            mod._run_approve_entry = lambda *args, **kwargs: {
                "ok": True,
                "frontier_kind": "link_paused",
            }
            packet = mod.run_resume_declaration(
                {
                    "building_ref": str(building),
                    "chain": "until-terminal",
                    "dispositions": [{"on": "human_or_coo_gate_pause", "action": "forward"}],
                },
                repo_root=repo,
            )
        finally:
            mod.observe_building_frontier = original_observe
            mod._read_written_dynamic_plan = original_read
            mod._run_approve_entry = original_run
            mod.resolve_dispo_adapter_cwd = original_cwd
        if not packet.get("ok") or len(packet.get("rounds") or []) != 1:
            raise AssertionError(f"mid-chain complete re-preflight was not clean: {packet!r}")
        if packet.get("error_kind"):
            raise AssertionError(f"mid-chain complete re-preflight retained error: {packet!r}")
    return 1


def _assert_adapter_cwd_automatic_removal_mutation_red(repo: Path) -> int:
    from brick_protocol.support.operator import resume_declaration as mod

    with tempfile.TemporaryDirectory(prefix="bp-resume-decl-cwd-red-") as tmpdir:
        building = Path(tmpdir) / "building"
        building.mkdir()
        adapter = Path(tmpdir) / "adapter"
        hold = {
            "hold_reason": "human_or_coo_gate_pause",
            "source_step_ref": "step-a",
            "pending_target_ref": "brick-b",
        }
        original_observe = mod.observe_building_frontier
        original_read = mod._read_written_dynamic_plan
        original_run = mod._run_approve_entry
        original_cwd = mod.resolve_dispo_adapter_cwd
        try:
            mod.observe_building_frontier = lambda _root, repo_root: {
                "frontier_kind": "link_paused",
                "frontier_reason": "human_or_coo_gate_pause",
            }
            mod._read_written_dynamic_plan = lambda _root: (
                {},
                {"walker_mode": "dynamic", "hold": hold},
            )
            mod.resolve_dispo_adapter_cwd = lambda repo_root, building_id: adapter

            def fake_run(
                building_root: Path,
                row: Mapping[str, Any],
                *,
                author_ref: str,
                repo_root: Path,
                adapter_cwd: Path,
                adapter_timeout_seconds: int,
            ) -> dict[str, Any]:
                del building_root, row, author_ref, repo_root, adapter_timeout_seconds
                if adapter_cwd != adapter:
                    raise AssertionError(
                        "adapter_cwd automatic removal mutation-RED: explicit cwd was not lowered"
                    )
                return {"ok": True, "frontier_kind": "complete"}

            mod._run_approve_entry = fake_run
            packet = mod.run_resume_declaration(
                {
                    "building_ref": str(building),
                    "chain": "single",
                    "dispositions": [{"on": "human_or_coo_gate_pause", "action": "forward"}],
                },
                repo_root=repo,
            )
        finally:
            mod.observe_building_frontier = original_observe
            mod._read_written_dynamic_plan = original_read
            mod._run_approve_entry = original_run
            mod.resolve_dispo_adapter_cwd = original_cwd
        if not packet.get("ok"):
            raise AssertionError(f"adapter_cwd explicit lowering did not complete: {packet!r}")
    return 1


def _assert_cli_and_profile_pins(repo: Path) -> int:
    cli_text = (repo / "brick_protocol/support/operator/cli.py").read_text(encoding="utf-8")
    required_cli = (
        "resume_declaration.load_resume_declaration",
        "resume_declaration.run_resume_declaration",
        'subparsers.add_parser(\n        "resume"',
        "--decl",
        "--dry-run",
    )
    missing_cli = [needle for needle in required_cli if needle not in cli_text]
    if missing_cli:
        raise AssertionError("resume CLI pin(s) missing: " + ", ".join(missing_cli))
    profile = repo / "brick_protocol/support/checkers/profiles/resume_declaration.yaml"
    if not profile.is_file():
        raise AssertionError("resume declaration profile is not registered")
    profile_text = profile.read_text(encoding="utf-8")
    if "resume_declaration" not in profile_text:
        raise AssertionError("resume declaration profile does not name its kernel check")
    return 2


def run(repo: Path) -> int:
    inspected = 0
    inspected += _assert_loader_and_shape(repo)
    inspected += _assert_preflight_class_action_reject(repo)
    inspected += _assert_class_action_prevalidation_mutation_red(repo)
    inspected += _assert_adapter_cwd_choice(repo)
    inspected += _assert_dead_end_guidance_mutation_red(repo)
    inspected += _assert_runtime_not_approval_hold_dead_end(repo)
    inspected += _assert_terminal_guards(repo)
    inspected += _assert_already_complete_noop(repo)
    inspected += _assert_chain_lowering(repo)
    inspected += _assert_mid_chain_complete_repreflight(repo)
    inspected += _assert_adapter_cwd_automatic_removal_mutation_red(repo)
    inspected += _assert_cli_and_profile_pins(repo)
    return inspected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=_REPO_ROOT)
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    inspected = run(repo)
    print(f"resume_declaration passed: inspected {inspected} probe(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
