"""Declarative hold disposition surface.

This module lowers a caller/COO-authored JSON declaration into the existing
``onboard.run_approve_entry`` resume seam. It is support mechanics only: it
validates declaration shape, observes already-written evidence, selects a
matching caller-supplied disposition row, and records the existing resume result.
It does not choose Movement, route targets, sufficiency, quality, or success.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.frontier_observation import observe_building_frontier
from brick_protocol.support.operator.walker_resume import (
    _read_written_dynamic_plan,
    hold_disposition_action_menu,
    validate_hold_disposition_action,
)
from brick_protocol.support.operator.worktree_sandbox import probe_worktree_capable


RESUME_DECL_ACTIONS = ("raise", "forward", "stop")
_RESUME_DECL_TOP_KEYS = frozenset(
    {
        "building_ref",
        "dispositions",
        "chain",
        "author_ref",
        "adapter_timeout_seconds",
    }
)
_DISPOSITION_KEYS = frozenset({"on", "action", "budget_increment"})
_CHAIN_MODES = ("single", "until-terminal")
_MAX_CHAIN_ROUNDS = 24
_DEFAULT_AUTHOR_REF = "coo:resume-decl"
_FORWARD_OVERRIDE_WARNING = (
    "warning: forward means continuing while recording an override for "
    "hold concern {reason!r}."
)
_DEAD_END_NEXT_HARVEST = (
    "next: run COO_GATE_HARVEST_SHA=<anchor> through the COO gate runner to "
    "harvest the orphan ledger tail, then author a new COO/human declaration "
    "only after the missing ledger rows are present."
)
_DEAD_END_NEXT_SALVAGE = (
    "next: this pause is not an approval-hold ledger. Do not expect resume. "
    "Salvage WIP (refs/brick-salvage or wip anchor) or re-fire with mid-node "
    "gates: [coo-review|human-review] on a non-terminal graph-decl node so a "
    "hold ledger is written. See OFFICIAL_ROUTE_MEMO mid-walk hold sketch."
)
_DEAD_END_NEXT_EVIDENCE = (
    "next: frontier is evidence_incomplete. Inspect evidence_root / dynamic plan "
    "before resume. Salvage if the walk-on closed without a hold ledger."
)
_DEAD_END_NEXT_PLAN = (
    "next: dynamic plan/evidence could not be read. Fix evidence root path or "
    "repair the written plan, then re-run resume preflight."
)
# Back-compat alias used by older call sites / tests that import the name.
_DEAD_END_NEXT_COMMAND = _DEAD_END_NEXT_HARVEST


def _dead_end_payload(
    kind: str,
    *,
    message_ko: str,
    next_command: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Uniform dead_end fields for preflight and run_resume_declaration."""

    payload: dict[str, Any] = {
        "dead_end": True,
        "dead_end_kind": kind,
        "error_kind": "resume_declaration_dead_end",
        "message_ko": message_ko,
        "next_command": next_command,
    }
    if extra:
        payload.update(dict(extra))
    return payload


def _frontier_key(preflight: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(preflight.get("frontier_kind") or ""),
        str(preflight.get("frontier_reason") or ""),
        str(preflight.get("paused_at_ref") or ""),
    )


def load_resume_declaration(path: Path | str) -> Mapping[str, Any]:
    """Load one JSON resume declaration from disk."""

    decl_path = Path(path).expanduser().resolve()
    if decl_path.suffix != ".json":
        raise ValueError("resume declaration must be a .json file")
    loaded = json.loads(decl_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise TypeError("resume declaration must be a mapping")
    unknown = sorted(str(key) for key in loaded if str(key) not in _RESUME_DECL_TOP_KEYS)
    if unknown:
        raise ValueError(
            "resume declaration rejects unknown keys: " + ", ".join(unknown)
        )
    return loaded


def validate_resume_declaration(decl: Mapping[str, Any]) -> dict[str, Any]:
    """Return normalized declaration rows, or raise before any ledger write."""

    building_text = str(decl.get("building_ref") or "").strip()
    if not building_text or not Path(building_text).is_absolute():
        raise ValueError(
            "resume declaration building_ref must be an ABSOLUTE evidence-root path"
        )
    raw_rows = decl.get("dispositions")
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ValueError("resume declaration dispositions must be a non-empty list")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(raw_rows):
        if not isinstance(item, Mapping):
            raise TypeError(f"resume declaration dispositions[{index}] must be a mapping")
        unknown = sorted(str(key) for key in item if str(key) not in _DISPOSITION_KEYS)
        if unknown:
            raise ValueError(
                f"resume declaration dispositions[{index}] rejects unknown keys: "
                + ", ".join(unknown)
            )
        on_text = str(item.get("on") or "").strip()
        action_text = str(item.get("action") or "").strip().lower()
        if not on_text:
            raise ValueError(f"resume declaration dispositions[{index}].on is required")
        if action_text not in RESUME_DECL_ACTIONS:
            raise ValueError(
                "resume declaration action must be one of "
                + ", ".join(RESUME_DECL_ACTIONS)
            )
        normalized: dict[str, Any] = {"on": on_text, "action": action_text}
        if "budget_increment" in item:
            if action_text != "raise":
                raise ValueError("budget_increment is admitted only for action=raise")
            try:
                increment = int(item.get("budget_increment"))
            except (TypeError, ValueError):
                increment = 0
            if increment <= 0:
                raise ValueError("raise budget_increment must be a positive integer")
            normalized["budget_increment"] = increment
        elif action_text == "raise":
            raise ValueError("raise action requires budget_increment")
        rows.append(normalized)
    chain = str(decl.get("chain") or "single").strip()
    if chain not in _CHAIN_MODES:
        raise ValueError("resume declaration chain must be single or until-terminal")
    author_ref = str(decl.get("author_ref") or _DEFAULT_AUTHOR_REF).strip()
    if not (author_ref.startswith("coo:") or author_ref.startswith("human:")):
        raise ValueError("resume declaration author_ref must start with coo: or human:")
    timeout_raw = decl.get("adapter_timeout_seconds", 120)
    try:
        timeout = int(timeout_raw)
    except (TypeError, ValueError):
        timeout = 0
    if timeout <= 0:
        raise ValueError("adapter_timeout_seconds must be a positive integer")
    return {
        "building_ref": building_text,
        "dispositions": rows,
        "chain": chain,
        "author_ref": author_ref,
        "adapter_timeout_seconds": timeout,
    }


def run_resume_declaration(
    decl: Mapping[str, Any],
    *,
    repo_root: Path | str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Preflight and optionally run one declaration chain."""

    normalized = validate_resume_declaration(decl)
    repo = Path(repo_root).resolve()
    building_root = Path(normalized["building_ref"]).expanduser().resolve()
    preflight = preflight_resume_declaration(normalized, repo_root=repo)
    packet: dict[str, Any] = {
        "command": "resume",
        "decl_valid": True,
        "dry_run": bool(dry_run),
        "building_ref": str(building_root),
        "chain": normalized["chain"],
        "preflight": preflight,
        "rounds": [],
        "ok": False,
        "proof_limits": [
            "support declaration lowering only",
            "existing onboard.run_approve_entry owns disposition row persistence",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "future Building correctness",
            "provider reliability",
            "semantic correctness of the caller/COO disposition",
        ],
    }
    if preflight.get("dead_end"):
        kind = str(preflight.get("dead_end_kind") or "unknown")
        packet.update(
            {
                "error_kind": "resume_declaration_dead_end",
                "dead_end_kind": kind,
                "message_ko": str(
                    preflight.get("message_ko")
                    or "막다른 길: resume 불가 (approval-hold ledger 없음 또는 evidence 불완전)."
                ),
                "next_command": str(
                    preflight.get("next_command") or _DEAD_END_NEXT_SALVAGE
                ),
            }
        )
        if preflight.get("error_message"):
            packet["error_message"] = preflight["error_message"]
        return packet
    if preflight.get("matched") is not True:
        packet.update(
            {
                "error_kind": "resume_declaration_no_match",
                "message_ko": "현재 hold/frontier에 맞는 disposition 선언이 없습니다.",
                "next_command": (
                    "next: adjust dispositions[].on to match hold_reason / frontier_reason, "
                    "or stop. This is not a harvest problem if a hold ledger exists."
                ),
            }
        )
        return packet
    if preflight.get("already_complete"):
        packet["ok"] = True
        packet["message_ko"] = "resume declaration observed an already-complete Building."
        return packet
    if dry_run:
        packet["ok"] = True
        packet["message_ko"] = "resume declaration dry-run preflight passed."
        return packet

    adapter_cwd = resolve_dispo_adapter_cwd(
        repo_root=repo,
        building_id=building_root.name,
    )
    seen: set[tuple[str, str, str]] = {_frontier_key(preflight)}
    current_preflight = preflight
    for _round_number in range(1, _MAX_CHAIN_ROUNDS + 1):
        selected = current_preflight.get("selected_disposition") or {}
        if not isinstance(selected, Mapping):
            break
        result = _run_approve_entry(
            building_root,
            selected,
            author_ref=str(normalized["author_ref"]),
            repo_root=repo,
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=int(normalized["adapter_timeout_seconds"]),
        )
        packet["rounds"].append(result)
        if result.get("error_kind") == "not_approval_hold":
            packet.update(
                _dead_end_payload(
                    "not_approval_hold",
                    message_ko=(
                        "막다른 길: runtime frontier가 approval hold가 아닙니다 "
                        "(walk-on concern / 비-hold pause 가능)."
                    ),
                    next_command=_DEAD_END_NEXT_SALVAGE,
                    extra={"runtime_error_kind": "not_approval_hold"},
                )
            )
            return packet
        if not result.get("ok") or result.get("error_kind"):
            packet.update(
                {
                    "error_kind": str(result.get("error_kind") or "resume_round_not_ok"),
                    "message_ko": str(result.get("message_ko") or ""),
                }
            )
            return packet
        frontier_kind = str(result.get("frontier_kind") or "")
        if frontier_kind == "complete":
            packet["ok"] = True
            packet["message_ko"] = "resume declaration chain reached complete frontier."
            return packet
        if normalized["chain"] == "single":
            packet["ok"] = True
            packet["message_ko"] = "resume declaration single round finished."
            return packet
        try:
            current_preflight = preflight_resume_declaration(normalized, repo_root=repo)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            packet.update(
                {
                    "error_kind": type(exc).__name__,
                    "message_ko": "next-round preflight failed.",
                    "error_message": str(exc),
                }
            )
            return packet
        if current_preflight.get("already_complete"):
            packet["ok"] = True
            packet["message_ko"] = (
                "resume declaration chain observed an already-complete Building."
            )
            return packet
        if current_preflight.get("dead_end"):
            kind = str(current_preflight.get("dead_end_kind") or "unknown")
            packet.update(
                {
                    "error_kind": "resume_declaration_dead_end",
                    "dead_end_kind": kind,
                    "message_ko": str(
                        current_preflight.get("message_ko")
                        or "막다른 길: 다음 frontier에서 resume 불가."
                    ),
                    "next_command": str(
                        current_preflight.get("next_command") or _DEAD_END_NEXT_SALVAGE
                    ),
                }
            )
            return packet
        if current_preflight.get("matched") is not True:
            packet.update(
                {
                    "error_kind": "resume_declaration_no_match",
                    "message_ko": "다음 hold에 맞는 disposition 선언이 없습니다.",
                    "next_command": (
                        "next: adjust dispositions[].on for the next hold_reason, "
                        "or stop the chain."
                    ),
                }
            )
            return packet
        key = _frontier_key(current_preflight)
        if key in seen:
            packet.update(
                {
                    "error_kind": "resume_declaration_no_progress",
                    "message_ko": "같은 frontier가 반복되어 chain을 멈췄습니다.",
                }
            )
            return packet
        seen.add(key)
    packet.update(
        {
            "error_kind": "resume_declaration_round_cap",
            "message_ko": f"chain round cap {_MAX_CHAIN_ROUNDS} reached.",
        }
    )
    return packet


def preflight_resume_declaration(
    normalized_decl: Mapping[str, Any],
    *,
    repo_root: Path | str,
) -> dict[str, Any]:
    """Observe the current hold and select the first matching declaration row."""

    repo = Path(repo_root).resolve()
    building_root = Path(str(normalized_decl.get("building_ref") or "")).resolve()
    frontier = dict(observe_building_frontier(building_root, repo_root=repo))
    frontier_kind = str(frontier.get("frontier_kind") or "")
    frontier_reason = str(frontier.get("frontier_reason") or "")
    packet: dict[str, Any] = {
        "building_ref": str(building_root),
        "frontier_kind": frontier_kind,
        "frontier_reason": frontier_reason,
        "matched": False,
    }
    if frontier_kind == "complete":
        packet.update({"matched": True, "already_complete": True})
        return packet
    if frontier_kind == "evidence_incomplete":
        packet.update(
            _dead_end_payload(
                "evidence_incomplete",
                message_ko=(
                    "막다른 길: frontier=evidence_incomplete. "
                    "approval-hold ledger 유무와 무관하게 resume 불가 상태일 수 있음."
                ),
                next_command=_DEAD_END_NEXT_EVIDENCE,
            )
        )
        return packet
    try:
        _plan, evidence = _read_written_dynamic_plan(building_root)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        packet.update(
            _dead_end_payload(
                "plan_unreadable",
                message_ko="막다른 길: written dynamic plan/evidence를 읽지 못했습니다.",
                next_command=_DEAD_END_NEXT_PLAN,
                extra={
                    "error_message": str(exc),
                    "read_error_kind": type(exc).__name__,
                },
            )
        )
        return packet
    hold_record_raw = evidence.get("hold") or {}
    hold_record = hold_record_raw if isinstance(hold_record_raw, Mapping) else {}
    if not hold_record:
        packet.update(
            _dead_end_payload(
                "no_hold_ledger",
                message_ko=(
                    "막다른 길: approval-hold ledger가 없습니다 "
                    "(closure walk-on concern 등). resume 대상이 아님."
                ),
                next_command=_DEAD_END_NEXT_SALVAGE,
            )
        )
        return packet
    allowed = hold_disposition_action_menu(hold_record, frontier_reason=frontier_reason)
    packet["allowed_disposition_actions"] = list(allowed)
    packet["paused_at_ref"] = _hold_value(hold_record, "paused_at_ref")
    packet["source_step_ref"] = _hold_value(hold_record, "source_step_ref")
    packet["pending_target_ref"] = _hold_value(hold_record, "pending_target_ref")
    packet["hold_reason"] = _hold_value(hold_record, "hold_reason")
    for row in normalized_decl.get("dispositions") or ():
        if not isinstance(row, Mapping):
            continue
        if not _row_matches_current_hold(str(row.get("on") or ""), hold_record, frontier):
            continue
        action = str(row.get("action") or "")
        try:
            validate_hold_disposition_action(
                action,
                hold_record,
                frontier_reason=frontier_reason,
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        selected = dict(row)
        warning = ""
        if action == "forward" and (frontier_reason or packet["hold_reason"]):
            warning = _FORWARD_OVERRIDE_WARNING.format(
                reason=frontier_reason or packet["hold_reason"]
            )
        packet.update(
            {
                "matched": True,
                "selected_disposition": selected,
                "warning": warning,
            }
        )
        return packet
    return packet


def resolve_dispo_adapter_cwd(*, repo_root: Path | str, building_id: str) -> Path:
    """Choose the explicit adapter cwd used for every declaration round."""

    choice = _dispo_adapter_cwd_choice(repo_root=repo_root, building_id=building_id)
    path = Path(str(choice["adapter_cwd"])).resolve()
    if choice["choice_kind"] in {"residue", "existing_fallback"}:
        return path
    if choice["choice_kind"] == "fallback_probe_unavailable":
        path.mkdir(parents=True, exist_ok=True)
        return path
    if choice["choice_kind"] != "git_worktree_add":
        raise ValueError(f"unknown adapter_cwd choice kind: {choice['choice_kind']!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "worktree", "add", "--detach", str(path), str(choice["base_sha"])],
        cwd=str(Path(repo_root).resolve()),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _dispo_adapter_cwd_choice(*, repo_root: Path | str, building_id: str) -> dict[str, Any]:
    """Purely choose adapter cwd policy; caller performs git/filesystem effects."""

    repo = Path(repo_root).resolve()
    residue = Path.home() / ".brick" / "worktrees" / building_id
    if residue.is_dir():
        return {
            "choice_kind": "residue",
            "adapter_cwd": str(residue.resolve()),
            "fallback_warning": "",
        }
    fallback = Path("/tmp") / f"brick-coo-dispo-{building_id}"
    if fallback.is_dir():
        return {
            "choice_kind": "existing_fallback",
            "adapter_cwd": str(fallback.resolve()),
            "fallback_warning": "",
        }
    probe = probe_worktree_capable(repo)
    if not probe.ok:
        return {
            "choice_kind": "fallback_probe_unavailable",
            "adapter_cwd": str(fallback.resolve()),
            "fallback_warning": "adapter_cwd fallback: git worktree capability probe was not ok",
        }
    return {
        "choice_kind": "git_worktree_add",
        "adapter_cwd": str(fallback.resolve()),
        "base_sha": probe.base_sha,
        "fallback_warning": "",
    }


def _run_approve_entry(
    building_root: Path,
    row: Mapping[str, Any],
    *,
    author_ref: str,
    repo_root: Path,
    adapter_cwd: Path,
    adapter_timeout_seconds: int,
) -> dict[str, Any]:
    from brick_protocol.support.operator.onboard import run_approve_entry

    kwargs: dict[str, Any] = {
        "action": str(row.get("action") or ""),
        "author_ref": author_ref,
        "repo_root": repo_root,
        "adapter_cwd": adapter_cwd,
        "adapter_timeout_seconds": adapter_timeout_seconds,
    }
    if "budget_increment" in row:
        kwargs["budget_increment"] = int(row["budget_increment"])
    return dict(run_approve_entry(building_root, **kwargs))


def _row_matches_current_hold(
    on_text: str,
    hold_record: Mapping[str, Any],
    frontier: Mapping[str, Any],
) -> bool:
    token = on_text.strip()
    if not token:
        return False
    candidates = {
        str(frontier.get("frontier_kind") or "").strip(),
        str(frontier.get("frontier_reason") or "").strip(),
        _hold_value(hold_record, "hold_reason"),
        _hold_value(hold_record, "frontier_reason"),
        _hold_value(hold_record, "frontier_kind"),
        _hold_value(hold_record, "source_step_ref"),
        _hold_value(hold_record, "pending_target_ref"),
    }
    return token in candidates


def _hold_value(hold_record: Mapping[str, Any], key: str) -> str:
    return str(hold_record.get(key) or "").strip()


__all__ = [
    "RESUME_DECL_ACTIONS",
    "load_resume_declaration",
    "preflight_resume_declaration",
    "resolve_dispo_adapter_cwd",
    "run_resume_declaration",
    "validate_resume_declaration",
    "_dispo_adapter_cwd_choice",
]
