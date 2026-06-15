#!/usr/bin/env python3
"""Validate project Building lifecycle path shape.

This checker is support evidence only. It is not source truth, not success
judgment, not quality judgment, and not Movement authority.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any
from pathlib import Path

# stdlib-only path bootstrap so the spine event_type set (the SINGLE SOURCE in
# support/recording/spine.py) can be imported when this checker runs standalone
# under the canonical `PYTHONPATH=support/import_identity` command. The
# import_identity router governs only brick_protocol.*, not support.*.
import os.path as _osp

_REPO_ROOT = _osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_IMPORT_IDENTITY = _osp.join(_REPO_ROOT, "support", "import_identity")
if _IMPORT_IDENTITY not in sys.path:
    sys.path.insert(0, _IMPORT_IDENTITY)

# U5.5 SLICE-1A: the admitted spine event_type set (single-source). The
# events/<seq>-<type> path predicate admits only a real spine event_type.
from brick_protocol.support.recording.spine import SPINE_EVENT_TYPES
from brick_protocol.agent.return_fact import RETURNED_FORBIDDEN_KEYS
from brick_protocol.support.operator.primitives import (
    evidence_list_has_repository_artifact_ref,
)


PROJECT_ROOT = "project"
BUILDINGS_SEGMENT = "buildings"
MINIMAL_LIFECYCLE_DIRS = {
    ("work",),
    ("capture",),
    ("raw",),
    ("evidence",),
    ("evidence", "claim_trace"),
    ("evidence", "claim_trace", "brick"),
    ("evidence", "claim_trace", "agent"),
    ("evidence", "claim_trace", "link"),
    # U5.5 SLICE-1A: the Evidence Spine projection directories. ALLOW-listed
    # globally (an old building simply has no spine path); presence is
    # GENERATION-GATED (required only for a u5_5_live building, see
    # required_dirs_for / required_records_for_candidate).
    ("evidence", "spine"),
    ("evidence", "spine", "events"),
}
MINIMAL_REQUIRED_RECORDS = {
    ("raw", "raw-manifest.json"),
    ("evidence", "evidence-manifest.json"),
    ("evidence", "claim_trace", "brick", "work_contract.json"),
    ("evidence", "claim_trace", "agent", "returned_claims.json"),
    ("evidence", "claim_trace", "link", "transfer_trace.json"),
    ("evidence", "claim_trace", "link", "carry_trace.json"),
    ("evidence", "claim_trace", "link", "sufficiency_trace.json"),
    ("evidence", "claim_trace", "link", "movement_trace.json"),
}
MINIMAL_OPTIONAL_RECORDS = {
    # run_building_intake (support/operator/driver.py) writes its materialized
    # INPUT plan at the building ROOT (declared-building-plan.json) before the
    # walk; the run's own work/declared-building-plan.json declaration packet
    # is a different file. Both are admitted so the documented first-day
    # intake flow never turns this gate RED.
    ("declared-building-plan.json",),
    ("work", "building-work.json"),
    ("work", "building-map.json"),
    ("work", "task.md"),
    ("work", "building-intake.json"),
    ("work", "preset-expansion.json"),
    ("work", "declared-building-plan.json"),
    ("work", "link-launch-policy.json"),
    ("capture", "events.jsonl"),
    # E1 (U5.5 slice-3): the live gate-sequence receipts + final policy action.
    # ALLOW-listed (the forward-path writer emits them) but OPTIONAL, not required,
    # so the 154 existing buildings on disk (recorded before E1) stay green.
    ("evidence", "claim_trace", "link", "gate_receipt_trace.json"),
    ("evidence", "claim_trace", "link", "policy_action_trace.json"),
}
FRONTIER_REQUIRED_RECORDS = {
    ("raw", "raw-manifest.json"),
    ("raw", "agent-received.jsonl"),
    ("raw", "adapter-error.jsonl"),
    ("evidence", "evidence-manifest.json"),
    ("evidence", "claim_trace", "brick", "work_contract.json"),
    ("evidence", "claim_trace", "agent", "receipt_trace.json"),
    ("evidence", "claim_trace", "link", "frontier_trace.json"),
}
PARKED_REQUIRED_RECORDS = {
    ("raw", "raw-manifest.json"),
    ("raw", "agent-received.jsonl"),
    ("raw", "chat-session-park.jsonl"),
    ("evidence", "evidence-manifest.json"),
    ("evidence", "claim_trace", "brick", "work_contract.json"),
    ("evidence", "claim_trace", "agent", "receipt_trace.json"),
    ("evidence", "claim_trace", "link", "frontier_trace.json"),
}
FRONTIER_OPTIONAL_RECORDS = {
    ("work", "building-work.json"),
    ("work", "building-map.json"),
    ("work", "task.md"),
    ("capture", "events.jsonl"),
    ("raw", "brick-work.jsonl"),
    ("raw", "link.jsonl"),
}
PARKED_OPTIONAL_RECORDS = FRONTIER_OPTIONAL_RECORDS
FRONTIER_LIFECYCLE_RECORDS = (
    FRONTIER_REQUIRED_RECORDS
    | PARKED_REQUIRED_RECORDS
    | FRONTIER_OPTIONAL_RECORDS
    | PARKED_OPTIONAL_RECORDS
)
MINIMAL_LIFECYCLE_RECORDS = (
    MINIMAL_REQUIRED_RECORDS | MINIMAL_OPTIONAL_RECORDS | FRONTIER_LIFECYCLE_RECORDS
)
STEP_OUTPUT_RECORD_NAMES = {
    "step-output.json",
    "route-request.json",
    "transition-concern.json",
    "adapter-error.json",
    "work-envelope.json",
    "parked.json",
    "claim.json",
    "submission.json",
}
CHAT_SESSION_CLAIM_STATES = {"claimed", "released"}
CHAT_SESSION_TOKEN_RE = re.compile(r"[a-z]+(?:-[a-z]+){3,7}")
AXIS_OWNER_LITERALS = {"Brick", "Agent", "Link"}
RAW_RECORD_ROLES = {"primary", "support", "review"}
RAW_MANIFEST_REQUIRED_TEXT_FIELDS = {
    "path",
    "source",
    "content_shape",
    "proof_limit",
}
AGENT_SELF_CLASSIFICATION_WORDS = {
    "success",
    "failure",
    "done",
    "not_done",
    "failed",
    "result",
    "approved",
    "complete",
    "pass",
    "fail",
}
AUTHORITY_CLAIM_KEYS = {
    "source_truth",
    "success_judgment",
    "quality_judgment",
    "movement_authority",
}
AUTHORITY_CLAIM_VALUES = {
    "source_truth",
    "success_judgment",
    "quality_judgment",
    "movement_authority",
    "source truth",
    "success judgment",
    "quality judgment",
    "movement authority",
}
SENSITIVE_SK_TOKEN_RE = re.compile(r"\bsk-[a-z0-9._~+/=-]{12,}(?![a-z0-9._~+/=-])")
SESSION_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
SESSION_ULID_RE = re.compile(r"\b[0-9A-HJKMNP-TV-Z]{26}\b")
ADAPTER_ERROR_FORBIDDEN_KEYS = {
    "auth",
    "auth_body",
    "authorization",
    "credential",
    "credentials",
    "credential_body",
    "movement",
    "movement_choice",
    "next_action",
    "provider_body",
    "route_decision_basis",
    "route_replay_plan",
    "route_target",
    "session",
    "session_id",
    "target",
    "target_ref",
    "token",
    "returned",
}
WORK_ENVELOPE_KEYS = {
    "building_id",
    "agent_object_ref",
    "adapter_ref",
    "brick_instance_ref",
    "next_brick_instance_ref",
    "selected_model_ref",
    "callable_ref",
    "prompt_refs",
    "skill_refs",
    "hook_refs",
    "tool_policy_refs",
    "discipline_refs",
    "input_packet_ref",
    "output_packet_ref",
    "work_statement",
    "comparison_rule",
    "required_return_shape",
    "source_fact_bodies",
    "link_handoff_refs",
    "agent_instruction_packet",
    "write_scope",
    "building_session_ref",
    "session_scope_ref",
    "session_continuity_mode",
    "proof_limits",
    "not_proven",
}
PARK_RECORD_FORBIDDEN_KEYS = {
    "adapter_error_ref",
    "agent_fact_created",
    "error_kind",
    "exception_type",
    "message_excerpt",
    "returned",
    "movement",
    "movement_choice",
    "target",
    "target_ref",
    "route_target",
    "session",
    "session_id",
    "provider_session_id",
    "credential",
    "credential_body",
    "token",
}
FRONTIER_AGENT_FORBIDDEN_KEYS = {
    "agent_fact",
    "agent_fact_created",
    "agentfact",
    "returned",
}
FRONTIER_LINK_FORBIDDEN_KEYS = {
    "movement",
    "movement_choice",
    "movement_id",
    "next_action",
    "route_decision_basis",
    "route_replay_plan",
    "route_target",
    "target",
    "target_ref",
}
CROSS_FACT_REFERENCE_KEYS = {
    "gatefact_reference",
    "transfer_gate_reference",
    "carry_gate_reference",
}
PUBLIC_FACT_REFERENCE_KEYS = {
    "public_fact_ref",
    "public_fact_refs",
    "carried_fact_ref",
    "carried_fact_refs",
    "checked_public_fact",
    "required_public_fact",
    "required_public_facts",
}
FORBIDDEN_SEGMENTS = {
    "storage",
    "wiki",
    "runtime",
    "provider",
    "scheduler",
    "dashboard",
}
FORBIDDEN_FILENAMES = {".DS_Store", "debug.log"}
PROOF_LIMIT = (
    "proof limit: path-shape support check only; this does not prove "
    "content correctness, source truth, success judgment, quality judgment, "
    "or Movement authority."
)


def to_posix(path: str | Path) -> str:
    value = str(path).replace("\\", "/").strip()
    while value.startswith("./"):
        value = value[2:]
    return value


def read_path_list(path: Path) -> list[str]:
    paths: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        paths.append(to_posix(stripped))
    return paths


def collect_directory_paths(root: Path) -> list[str]:
    paths: list[str] = []
    base = root
    if root.name == BUILDINGS_SEGMENT and root.parent.parent.name == PROJECT_ROOT:
        base = root.parents[2]
    elif root.parent.name == BUILDINGS_SEGMENT and root.parent.parent.parent.name == PROJECT_ROOT:
        base = root.parents[3]

    current = root
    ancestors: list[Path] = []
    while current != base:
        ancestors.append(current)
        if current.parent == current:
            break
        current = current.parent
    for path in reversed(ancestors):
        relative = to_posix(path.relative_to(base))
        if lifecycle_parts(relative) is not None:
            paths.append(relative + "/" if path.is_dir() else relative)

    for path in sorted(root.rglob("*")):
        if path.name in FORBIDDEN_FILENAMES:
            continue
        # U5.5 SLICE-1A: a stale ``*.tmp`` is a torn atomic write (the spine
        # writer + os.replace consume the temp on the normal path; a crash may
        # leave one). RESIDUE-FILTER it here so the collector never hands it to
        # the allow/reject check — "ignore" = a collector residue-filter, NOT a
        # 3rd predicate allow-state.
        if path.name.endswith(".tmp"):
            continue
        relative = to_posix(path.relative_to(base))
        paths.append(relative + "/" if path.is_dir() else relative)
    return paths


def collect_paths(path: Path) -> tuple[str, list[str]]:
    if path.is_file():
        return str(path), read_path_list(path)
    if path.is_dir():
        text_lists = sorted(path.glob("*.txt"))
        if text_lists:
            paths: list[str] = []
            for text_list in text_lists:
                paths.extend(read_path_list(text_list))
            return str(path), paths
        return str(path), collect_directory_paths(path)
    raise FileNotFoundError(f"target does not exist: {path}")


def collect_repo_lifecycle_paths(repo: Path) -> tuple[str, list[str]]:
    """Collect only active CAP-BOOT lifecycle roots from a repo checkout."""

    project_root = repo / PROJECT_ROOT
    if not project_root.exists():
        return str(project_root), []
    paths: list[str] = []
    for buildings_root in sorted(project_root.glob(f"*/{BUILDINGS_SEGMENT}")):
        if buildings_root.is_dir():
            paths.extend(collect_directory_paths(buildings_root))
    return str(project_root), paths


def raw_stream_tail_allowed(tail: tuple[str, ...]) -> bool:
    if len(tail) != 2 or tail[0] != "raw":
        return False
    filename = tail[1]
    if filename in {"raw-manifest.json", "debug.log", ".DS_Store"}:
        return False
    return filename.endswith((".jsonl", ".json", ".md", ".txt", ".log"))


def step_output_tail_allowed(tail: tuple[str, ...], *, is_dir: bool) -> bool:
    if tail == ("work", "step-outputs"):
        return is_dir
    if len(tail) < 3 or tail[:2] != ("work", "step-outputs"):
        return False
    step_attempt = tail[2]
    if not step_output_attempt_segment_allowed(step_attempt):
        return False
    if len(tail) == 3:
        return is_dir
    if len(tail) == 4:
        return not is_dir and tail[3] in STEP_OUTPUT_RECORD_NAMES
    return False


def step_output_attempt_segment_allowed(value: str) -> bool:
    marker = "-attempt-"
    if marker not in value:
        return False
    step_slug, attempt_text = value.rsplit(marker, 1)
    if not step_slug or not attempt_text.isdigit():
        return False
    if attempt_text.startswith("0"):
        return False
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    return all(char in allowed_chars for char in step_slug)


def spine_event_filename_allowed(filename: str) -> bool:
    """A spine per-event file name: <seq>-<type>.(json|md).

    <seq> = one or more digits; <type> = a real spine event_type; ext = json|md.
    NEVER .tmp (a torn write the collector residue-filters; not a 3rd allow
    state). The set of admitted <type> segments is single-sourced from
    support/recording/spine.SPINE_EVENT_TYPES.
    """

    for ext in (".json", ".md"):
        if filename.endswith(ext):
            stem = filename[: -len(ext)]
            seq_text, sep, type_segment = stem.partition("-")
            if not sep:
                return False
            if not seq_text.isdigit():
                return False
            return type_segment in SPINE_EVENT_TYPES
    return False


def spine_events_tail_allowed(tail: tuple[str, ...], *, is_dir: bool) -> bool:
    """Admit ("evidence","spine","events"[, <seq>-<type>.(json|md)]) by PATTERN."""

    if tail == ("evidence", "spine", "events"):
        return is_dir
    if len(tail) != 4 or tail[:3] != ("evidence", "spine", "events"):
        return False
    if is_dir:
        return False
    return spine_event_filename_allowed(tail[3])


def lifecycle_parts(path: str) -> list[str] | None:
    clean = path.rstrip("/")
    parts = clean.split("/")
    if len(parts) < 3:
        return None
    if parts[0] != PROJECT_ROOT or parts[2] != BUILDINGS_SEGMENT:
        return None
    return parts


def candidate_key(parts: list[str]) -> tuple[str, str] | None:
    if len(parts) < 4:
        return None
    project_id = parts[1]
    building_id = parts[3]
    if not project_id or not building_id:
        return None
    return project_id, building_id


def forbidden_path_reason(parts: list[str]) -> str | None:
    clean = "/".join(parts)
    filename = parts[-1] if parts else ""
    if any(segment in FORBIDDEN_SEGMENTS for segment in parts):
        return f"{clean}: storage/wiki/runtime/provider/scheduler/dashboard paths are not allowed"
    if filename in FORBIDDEN_FILENAMES:
        return f"{clean}: {filename} is not part of the lifecycle path shape"
    if any(segment in {"", ".", ".."} for segment in parts):
        return f"{clean}: path segments must be non-empty project/building path segments"
    return None


def lifecycle_shape_for(building_id: str) -> tuple[set[tuple[str, ...]], set[tuple[str, ...]]]:
    return MINIMAL_LIFECYCLE_DIRS, MINIMAL_LIFECYCLE_RECORDS


def candidate_tails(
    paths: set[str],
    project_id: str,
    building_id: str,
) -> set[tuple[str, ...]]:
    prefix = f"project/{project_id}/buildings/{building_id}/"
    tails: set[tuple[str, ...]] = set()
    for path in paths:
        clean = path.rstrip("/")
        if not clean.startswith(prefix):
            continue
        tail_text = clean[len(prefix) :]
        if tail_text:
            tails.add(tuple(tail_text.split("/")))
    return tails


def has_adapter_error_step_output(tails: set[tuple[str, ...]]) -> bool:
    return any(
        len(tail) == 4
        and tail[:2] == ("work", "step-outputs")
        and tail[3] == "adapter-error.json"
        for tail in tails
    )


def has_parked_step_output(tails: set[tuple[str, ...]]) -> bool:
    return any(
        len(tail) == 4
        and tail[:2] == ("work", "step-outputs")
        and tail[3] == "parked.json"
        for tail in tails
    )


def has_work_envelope_step_output(tails: set[tuple[str, ...]]) -> bool:
    return any(
        len(tail) == 4
        and tail[:2] == ("work", "step-outputs")
        and tail[3] == "work-envelope.json"
        for tail in tails
    )


# U5.5 SLICE-1A: the spine records/dirs REQUIRED only for a u5_5_live building.
# (The per-event events/<seq>-<type> files are admitted by PATTERN and are not a
# fixed required record; the REQUIRED floor is the 3 index records + the spine +
# events dirs. quality/ is not a slice-1A required record.)
SPINE_REQUIRED_RECORDS = {
    ("evidence", "spine", "spine.json"),
    ("evidence", "spine", "spine.jsonl"),
    ("evidence", "spine", "spine.md"),
}
SPINE_REQUIRED_DIRS = {
    ("evidence", "spine"),
    ("evidence", "spine", "events"),
}


def complete_required_records_present(tails: set[tuple[str, ...]]) -> bool:
    return MINIMAL_REQUIRED_RECORDS <= tails


def complete_agent_return_marker_present(tails: set[tuple[str, ...]]) -> bool:
    return any(
        marker in tails
        for marker in (
            ("raw", "agent-return.jsonl"),
            ("raw", "agent-returns.jsonl"),
            ("evidence", "claim_trace", "agent", "returned_claims.json"),
        )
    )


def frontier_required_records_present(tails: set[tuple[str, ...]]) -> bool:
    return FRONTIER_REQUIRED_RECORDS <= tails and has_adapter_error_step_output(tails)


def parked_required_records_present(tails: set[tuple[str, ...]]) -> bool:
    return (
        PARKED_REQUIRED_RECORDS <= tails
        and has_parked_step_output(tails)
        and has_work_envelope_step_output(tails)
    )


def required_records_for_candidate(
    building_id: str,
    tails: set[tuple[str, ...]],
    *,
    u5_5_live: bool = False,
) -> set[tuple[str, ...]]:
    # U5.5 SLICE-1A: a building tagged evidence_generation == u5_5_live MUST carry
    # the spine index records (applied to BOTH the minimal and frontier branches —
    # the disposition/frontier cases are where the spine matters most). Untagged
    # buildings get NO spine in their required set, so all 154 existing buildings
    # stay green (the field is absent => u5_5_live is False).
    spine = SPINE_REQUIRED_RECORDS if u5_5_live else set()
    if complete_required_records_present(tails):
        return MINIMAL_REQUIRED_RECORDS | spine
    if not complete_agent_return_marker_present(tails) and parked_required_records_present(tails):
        return PARKED_REQUIRED_RECORDS | spine
    if not complete_agent_return_marker_present(tails) and frontier_required_records_present(tails):
        return FRONTIER_REQUIRED_RECORDS | spine
    return MINIMAL_REQUIRED_RECORDS | spine


def required_dirs_for(building_id: str, *, u5_5_live: bool = False) -> set[tuple[str, ...]]:
    spine = SPINE_REQUIRED_DIRS if u5_5_live else set()
    return spine | {
        ("raw",),
        ("evidence",),
        ("evidence", "claim_trace"),
        ("evidence", "claim_trace", "brick"),
        ("evidence", "claim_trace", "agent"),
        ("evidence", "claim_trace", "link"),
    }


def spine_record_tail_allowed(tail: tuple[str, ...], *, is_dir: bool) -> bool:
    """Admit the three fixed spine INDEX records spine.{json,jsonl,md}."""

    return (
        not is_dir
        and len(tail) == 3
        and tail[:2] == ("evidence", "spine")
        and tail[2] in {"spine.json", "spine.jsonl", "spine.md"}
    )


def allowed_lifecycle_tail_reason(
    clean: str,
    tail: tuple[str, ...],
    *,
    is_dir: bool,
    allowed_dirs: set[tuple[str, ...]],
    allowed_records: set[tuple[str, ...]],
) -> str | None:
    if is_dir and tail in allowed_dirs:
        return None
    if not is_dir and tail in allowed_records:
        return None
    if step_output_tail_allowed(tail, is_dir=is_dir):
        return None
    if not is_dir and raw_stream_tail_allowed(tail):
        return None
    # U5.5 SLICE-1A: the Evidence Spine projection paths (variable-filename
    # per-event artifacts admitted by PATTERN; the 3 index records by fixed name).
    # ALLOW-only here; presence is generation-gated elsewhere. (quality/ admission
    # is DEFERRED to slice-4 with its Layer-2 validator — do not admit what we do
    # not yet validate.)
    if spine_record_tail_allowed(tail, is_dir=is_dir):
        return None
    if spine_events_tail_allowed(tail, is_dir=is_dir):
        return None
    if len(tail) == 1:
        return f"{clean}: building root allows only work/, capture/, raw/, and evidence/"
    return f"{clean}: lifecycle path is not listed in the admitted Building shape"


def allowed_path_reason(path: str) -> str | None:
    is_dir = path.endswith("/")
    clean = path.rstrip("/")
    clean_parts = clean.split("/")
    if is_dir and (clean == PROJECT_ROOT or (len(clean_parts) == 2 and clean_parts[0] == PROJECT_ROOT)):
        return None
    parts = lifecycle_parts(path)
    if parts is None:
        return f"{clean}: path must be under project/<project-id>/buildings/<building-id>/"

    forbidden = forbidden_path_reason(parts)
    if forbidden:
        return forbidden

    if len(parts) == 3:
        return None if is_dir else f"{clean}: buildings must be a directory"

    if len(parts) == 4:
        return None if is_dir else f"{clean}: building id must be a directory"

    _, building_id = candidate_key(parts) or ("", "")
    allowed_dirs, allowed_records = lifecycle_shape_for(building_id)
    return allowed_lifecycle_tail_reason(
        clean,
        tuple(parts[4:]),
        is_dir=is_dir,
        allowed_dirs=allowed_dirs,
        allowed_records=allowed_records,
    )


def known_candidates(paths: set[str]) -> set[tuple[str, str]]:
    candidates: set[tuple[str, str]] = set()
    for path in paths:
        parts = lifecycle_parts(path)
        if parts is None:
            continue
        key = candidate_key(parts)
        if key is not None:
            candidates.add(key)
    return candidates


def require_path(paths: set[str], required: str, violations: list[str]) -> None:
    if required not in paths:
        violations.append(f"missing required path: {required}")


def _no_u5_5_live(project_id: str, building_id: str) -> bool:
    """Default generation resolver: nothing is u5_5_live (pure path-list mode).

    A path-only fixture .txt list has no real manifest to read, so the spine is
    not required unless a concrete resolver (repo/dir mode) reads the tag.
    """

    return False


def validate_required_shape(
    paths: set[str],
    *,
    require_candidate: bool,
    is_u5_5_live: Any = _no_u5_5_live,
) -> list[str]:
    violations: list[str] = []
    candidates = known_candidates(paths)
    if not candidates:
        return ["target contains zero lifecycle candidates"] if require_candidate else []

    for project_id, building_id in sorted(candidates):
        root = f"project/{project_id}/buildings/{building_id}"
        tails = candidate_tails(paths, project_id, building_id)
        live = bool(is_u5_5_live(project_id, building_id))
        require_path(paths, f"project/{project_id}/buildings/", violations)
        require_path(paths, f"{root}/", violations)
        for directory in sorted(required_dirs_for(building_id, u5_5_live=live)):
            require_path(paths, f"{root}/{'/'.join(directory)}/", violations)
        for record in sorted(
            required_records_for_candidate(building_id, tails, u5_5_live=live)
        ):
            require_path(paths, f"{root}/{'/'.join(record)}", violations)

    return violations


def check_paths(
    paths: list[str],
    *,
    require_candidate: bool = True,
    is_u5_5_live: Any = _no_u5_5_live,
) -> list[str]:
    normalized = [to_posix(path) for path in paths if to_posix(path)]
    violations: list[str] = []
    for path in normalized:
        reason = allowed_path_reason(path)
        if reason:
            violations.append(reason)
    violations.extend(
        validate_required_shape(
            set(normalized),
            require_candidate=require_candidate,
            is_u5_5_live=is_u5_5_live,
        )
    )
    return violations


def parse_json_file(path: Path, violations: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        violations.append(f"{path}: JSON parse failed: {exc}")
        return None


def raw_refs_from_value(value: Any) -> set[str]:
    refs: set[str] = set()
    for item in dict_values(value):
        raw_ref = item.get("raw_ref")
        if isinstance(raw_ref, str) and raw_ref.strip():
            refs.add(raw_ref)
        raw_refs = item.get("raw_refs")
        if isinstance(raw_refs, list):
            refs.update(str(ref) for ref in raw_refs if isinstance(ref, str) and ref.strip())
    return refs


def parse_jsonl_file(path: Path, violations: list[str]) -> set[str]:
    refs: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        violations.append(f"{path}: JSONL read failed: {exc}")
        return refs
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            refs.update(raw_refs_from_value(json.loads(line)))
        except json.JSONDecodeError as exc:
            violations.append(f"{path}:{line_number}: JSONL parse failed: {exc}")
    return refs


def values(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from values(child)
    elif isinstance(value, list):
        for child in value:
            yield from values(child)
    else:
        yield value


def dict_values(value: Any) -> Iterable[dict[str, Any]]:
    for item in values(value):
        if isinstance(item, dict):
            yield item


def text_values(value: Any) -> Iterable[str]:
    for item in values(value):
        if isinstance(item, str):
            yield item


def has_forbidden_authority_claim(value: Any) -> bool:
    for item in dict_values(value):
        for key, child in item.items():
            key_norm = str(key).strip().lower().replace("-", "_").replace(" ", "_")
            if key_norm in AUTHORITY_CLAIM_KEYS and child not in (False, None, "", [], {}):
                return True
    for text in text_values(value):
        if text.strip().lower() in AUTHORITY_CLAIM_VALUES:
            return True
    return False


def manifest_entries(raw_manifest: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_manifest, dict):
        return []
    entries = raw_manifest.get("entries")
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, dict)]
    streams = raw_manifest.get("raw_streams")
    if isinstance(streams, list):
        return [entry for entry in streams if isinstance(entry, dict)]
    return []


def raw_ref_set(entries: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for entry in entries:
        raw_refs = entry.get("raw_refs")
        if isinstance(raw_refs, list):
            refs.update(str(ref) for ref in raw_refs if isinstance(ref, str) and ref.strip())
        raw_ref = entry.get("raw_ref")
        if isinstance(raw_ref, str) and raw_ref.strip():
            refs.add(raw_ref)
    return refs


def raw_manifest_entry_path_reason(path: str) -> str | None:
    clean = to_posix(path)
    parts = tuple(clean.split("/"))
    if clean.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        return "raw manifest entry path must be a relative raw stream path"
    if not raw_stream_tail_allowed(parts):
        return "raw manifest entry path must point to an admitted raw stream"
    return None


def claim_facts(claim: Any) -> list[dict[str, Any]]:
    if not isinstance(claim, dict):
        return []
    facts = claim.get("facts")
    if isinstance(facts, list):
        return [fact for fact in facts if isinstance(fact, dict)]
    return [claim]


def fact_reference(fact: dict[str, Any]) -> str | None:
    for key in ("fact_ref", "fact_id", "gate_ref", "transfer_id", "carry_id", "movement_id", "id"):
        value = fact.get(key)
        if isinstance(value, str) and value.strip():
            return value
    body = fact.get("fact")
    if isinstance(body, dict):
        for key in ("fact_ref", "fact_id", "gate_ref", "transfer_id", "carry_id", "movement_id", "id"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def classify_self_classifies(fact: dict[str, Any]) -> bool:
    for item in dict_values(fact):
        for key, value in item.items():
            key_norm = str(key).strip().lower()
            if key_norm in AGENT_SELF_CLASSIFICATION_WORDS:
                return True
            if key_norm in {"status", "verdict", "classification", "result"}:
                if isinstance(value, str) and value.strip().lower() in AGENT_SELF_CLASSIFICATION_WORDS:
                    return True
    return False


def link_references_agent_endpoint(fact: dict[str, Any]) -> bool:
    for item in dict_values(fact):
        for key, value in item.items():
            key_norm = str(key).strip().lower()
            if key_norm in {
                "source_boundary_ref",
                "target_boundary_ref",
                "handoff_target_fact",
                "source",
                "target",
                "from",
                "to",
            }:
                if isinstance(value, str) and value.strip().lower().startswith("agent:"):
                    return True
    return False


def normalized_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def has_any_key(value: Any, keys: set[str]) -> bool:
    normalized = {normalized_key(key) for key in keys}
    for item in dict_values(value):
        for key in item:
            if normalized_key(str(key)) in normalized:
                return True
    return False


def has_sensitive_text(value: Any) -> bool:
    for text in text_values(value):
        lowered = text.strip().lower()
        if SENSITIVE_SK_TOKEN_RE.search(lowered):
            return True
        if any(marker in lowered for marker in ("bearer ", "api_key", "api-key")):
            return True
    return False


def has_session_identifier_text(value: Any) -> bool:
    for text in text_values(value):
        if SESSION_UUID_RE.search(text) or SESSION_ULID_RE.search(text):
            return True
    return False


def is_brick_boundary_ref(value: str) -> bool:
    return value.strip().lower().startswith("brick:")


# Present-fact field references whose target IS a present artifact in this
# building (the building's own Brick comparison observation), so a fabricated
# field can be verified-against and rejected. AgentFact./Link. references are
# NOT in this set: in a Link gate's `required_public_facts` they declare the
# required public-fact return shape the gate evaluates (and whose missing
# members the gate reports via missing_required_facts), so they legitimately
# name fields that may be absent and are accepted as shape vocabulary.
PRESENT_OBSERVATION_FIELD_REF_PREFIX = "BrickComparisonFact."
SHAPE_VOCABULARY_FIELD_REF_PREFIXES = (
    "AgentFact.",
    "Link.",
)
REPOSITORY_ARTIFACT_REF_SUFFIX = "repository_artifact_ref"
# PRE-GROUNDING-LAW (Smith-pattern dated registry, 0612): the lane-tooling
# building BUILT the artifact-grounding law while its OWN attack-QA steps still
# ran tool-less (the last blind-QA building); its closure rewrite recorded
# grounding refs its honest packet-only returns can never satisfy. That one
# building is grandfathered BY ID; any other building with unresolvable
# grounding refs stays RED.
PRE_GROUNDING_LAW_BUILDING_IDS: frozenset[str] = frozenset(
    {
        "lane-tooling-three-tier-0612",
        # LAW-TRANSITION (0612, F10 queued): the notify building ran while the
        # grounding law was BITING unevenly — its review gates RECORDED the
        # grounding fact ref without DEMANDING it for the return shapes its QA
        # used (gate forwarded; resolver cannot resolve). Registered as the
        # second and LAST dated transition id; the demand/record consistency
        # repair (F10) closes this class for every future building.
        "notify-customer-language-autowire-0612",
        # TRANSITION WINDOW CLOSURE (0612): these two walked DURING the wave
        # that BUILT the demand/record unification (f10b) — i.e. with the
        # pre-f10b gate that recorded grounding refs without demanding them.
        # With f10b merged the gate demands what it records, so this class is
        # structurally closed: no building after this commit can need an entry.
        "f9-projection-states-0612",
        "provider-ladder-fleet-presets-0612b",
    }
)
VIRTUAL_REPOSITORY_ARTIFACT_RETURN_FIELDS = frozenset(
    {
        "evidence_used",
        "evidence_refs",
    }
)


def brick_comparison_field_ref_tokens(value: str) -> tuple[str, str] | None:
    """Split `BrickComparisonFact.<top>[.<intermediate>...].<leaf>` into (top, leaf).

    The top-level token is the field that must be present on the present Brick
    comparison fact envelope; the leaf token is the deepest selected field/
    observation that must be present somewhere on that comparison fact. For a
    flat `BrickComparisonFact.<field>` reference top and leaf are the same token.
    """

    if not value.startswith(PRESENT_OBSERVATION_FIELD_REF_PREFIX):
        return None
    selector = value[len(PRESENT_OBSERVATION_FIELD_REF_PREFIX) :]
    segments = [segment for segment in selector.split(".") if segment]
    if not segments:
        return None
    return segments[0], segments[-1]


def brick_comparison_virtual_repository_artifact_selector(
    value: str,
) -> tuple[str, str] | None:
    """Return (top comparison field, returned field) for the artifact virtual leaf."""

    if not value.startswith(PRESENT_OBSERVATION_FIELD_REF_PREFIX):
        return None
    selector = value[len(PRESENT_OBSERVATION_FIELD_REF_PREFIX) :]
    segments = [segment for segment in selector.split(".") if segment]
    if (
        len(segments) == 4
        and segments[1] == "returned_field"
        and segments[2] in VIRTUAL_REPOSITORY_ARTIFACT_RETURN_FIELDS
        and segments[3] == REPOSITORY_ARTIFACT_REF_SUFFIX
    ):
        return segments[0], segments[2]
    return None


# Keys that DECLARE (record as present evidence) a concern / human-review /
# observation / review-observation public fact. A reference resolves only when
# its identifier is declared through one of these keys somewhere in the present
# building evidence; merely citing the identifier elsewhere does not count.
DECLARED_REFERENCE_KEYS = {
    "concern_ref",
    "observation_id",
    "reason_refs",
    "transition_lifecycle_reason_refs",
    "route_decision_human_review_refs",
    "route_decision_override_refs",
    "route_decision_reviewer_observation_refs",
    "route_decision_adopted_transition_concern_refs",
    "route_decision_not_adopted_transition_concern_refs",
    "transition_concern_ref",
    "request_ref",
}
DECLARED_REFERENCE_PREFIXES = (
    "transition-concern:",
    "human-review:",
    "observation:",
    "review-observation:",
)
BRICK_WORK_FIELD_PREFIX = "BrickWork."
AGENT_FACT_REF_PREFIX = "agent-fact:"


def agent_fact_step_slug(fact: dict[str, Any]) -> str:
    ref = fact_reference(fact)
    if isinstance(ref, str) and ref.startswith(AGENT_FACT_REF_PREFIX):
        parts = ref.split(":")
        if len(parts) >= 3:
            return ":".join(parts[2:]).strip()
    return ""


def agent_fact_step_slugs(agent_facts: Iterable[dict[str, Any]]) -> set[str]:
    """Step slugs of Agent facts actually present in returned_claims/receipts.

    Agent fact_refs use the `agent-fact:<attempt-index>:<step-slug>` scheme,
    while Link sufficiency traces cite `agent-fact:<building-id>:<step-slug>`.
    Both identify the same fact by its step slug, so the present fact is the
    Agent fact whose fact_ref carries that step slug.
    """

    slugs: set[str] = set()
    for fact in agent_facts:
        slug = agent_fact_step_slug(fact)
        if slug:
            slugs.add(slug)
    return slugs


def agent_return_field_values_by_step(
    agent_facts: Iterable[dict[str, Any]],
) -> dict[str, dict[str, list[Any]]]:
    """Returned payload field values keyed by AgentFact step slug."""

    fields_by_step: dict[str, dict[str, list[Any]]] = {}
    for fact in agent_facts:
        step_slug = agent_fact_step_slug(fact)
        if not step_slug:
            continue
        envelope = fact.get("fact")
        if not isinstance(envelope, dict):
            continue
        returned = envelope.get("returned")
        if not isinstance(returned, dict):
            continue
        step_fields = fields_by_step.setdefault(step_slug, {})
        for key, value in returned.items():
            step_fields.setdefault(str(key), []).append(value)
    return fields_by_step


def brick_comparison_checked_step_slug(value: Any) -> str:
    if not isinstance(value, str) or not value.startswith("brick-comparison:"):
        return ""
    parts = value.split(":")
    if len(parts) < 3:
        return ""
    return ":".join(parts[2:]).strip()


def agent_fact_building_segments(
    agent_facts: Iterable[dict[str, Any]],
    building_id: str,
) -> set[str]:
    """Present middle segments an `agent-fact:<middle>:<slug>` ref may carry.

    Agent fact_refs scope the fact by attempt index (`agent-fact:<attempt>:...`)
    while Link sufficiency traces scope the same fact by building-id
    (`agent-fact:<building-id>:...`). The present middle segments are therefore
    the attempt indices actually carried by Agent facts here plus this
    building's own id.
    """

    segments: set[str] = set()
    if building_id.strip():
        segments.add(building_id.strip())
    for fact in agent_facts:
        ref = fact_reference(fact)
        if isinstance(ref, str) and ref.startswith(AGENT_FACT_REF_PREFIX):
            parts = ref.split(":")
            if len(parts) >= 3:
                middle = parts[1].strip()
                if middle:
                    segments.add(middle)
    return segments


def brick_work_field_names(brick_facts: Iterable[dict[str, Any]]) -> set[str]:
    """Field names present on any Brick claim_trace fact envelope."""

    fields: set[str] = set()
    for fact in brick_facts:
        envelope = fact.get("fact")
        if isinstance(envelope, dict):
            fields.update(str(key) for key in envelope)
    return fields


def is_brick_comparison_fact(fact: dict[str, Any]) -> bool:
    """A Brick fact is a comparison fact (BrickComparisonFact) when its
    fact_ref is a brick-comparison ref or its envelope records comparison
    observation fields, distinguishing it from the brick-work statement fact.
    """

    ref = fact_reference(fact)
    if isinstance(ref, str) and ref.startswith("brick-comparison:"):
        return True
    envelope = fact.get("fact")
    if isinstance(envelope, dict) and (
        "comparison_evidence" in envelope or "observed_match_kind" in envelope
    ):
        return True
    return False


def envelope_field_token_set(facts: Iterable[dict[str, Any]]) -> tuple[set[str], set[str]]:
    """(top-level fields, all present field/observation tokens) for a fact set.

    The top-level set is the immediate keys of each fact envelope (the fields a
    `<FactClass>.<field>` reference names at depth one). The token set is every
    field/observation present anywhere in those envelopes: nested dict keys plus
    comma/colon/whitespace separated tokens of string values (which is how the
    comparison facts record observed/required shape fields such as
    `observed_evidence` inside `comparison_evidence` and
    `required_return_shape_evidence`). The leaf of a nested selector resolves
    only when it appears in this present-token set.
    """

    top_level: set[str] = set()
    tokens: set[str] = set()
    for fact in facts:
        envelope = fact.get("fact")
        if not isinstance(envelope, dict):
            continue
        top_level.update(str(key) for key in envelope)
        _collect_field_tokens(envelope, tokens)
    return top_level, tokens


def _collect_field_tokens(value: Any, tokens: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            tokens.add(str(key))
            _collect_field_tokens(child, tokens)
    elif isinstance(value, list):
        for child in value:
            _collect_field_tokens(child, tokens)
    elif isinstance(value, str):
        for piece in value.replace(",", " ").replace(":", " ").split():
            piece = piece.strip()
            if piece:
                tokens.add(piece)


def present_brick_boundary_ids(values_source: Iterable[Any]) -> set[str]:
    """Boundary ids declared/observed among the building's brick boundaries.

    A `brick:<boundary>` reference resolves only when `<boundary>` is one of the
    boundary ids the building actually declares (building-map / link traces):
    the raw brick instance / work identifiers, plus the boundary portion of any
    `brick:`-prefixed boundary-ref field. Bare prefix is never enough.
    """

    raw_id_keys = {
        "brick_instance_ref",
        "brick_instance_id",
        "brick_work_ref",
        "source_brick_instance_ref",
        "target_brick_instance_ref",
        "next_brick_instance_ref",
    }
    boundary_ref_keys = {
        "target_boundary_ref",
        "source_boundary_ref",
        "next_boundary_ref",
    }
    boundaries: set[str] = set()
    for source in values_source:
        for item in dict_values(source):
            for key, value in item.items():
                key_text = str(key)
                for ref in reference_values(value):
                    ref = ref.strip()
                    if not ref:
                        continue
                    if key_text in raw_id_keys:
                        boundaries.add(ref)
                    if key_text in boundary_ref_keys and is_brick_boundary_ref(ref):
                        boundaries.add(ref.split(":", 1)[1].strip())
    return boundaries


def declared_disposition_refs(values_source: Iterable[Any]) -> set[str]:
    """Concern/review/observation identifiers declared in present evidence.

    Scans every present claim_trace / step-output JSON object for the declaring
    keys above and collects the identifiers recorded under them. A reference
    only resolves if its target was declared this way, so a fabricated
    (genuinely dangling) reference whose target was never recorded is rejected.
    """

    declared: set[str] = set()
    for source in values_source:
        for item in dict_values(source):
            for key, value in item.items():
                if str(key) not in DECLARED_REFERENCE_KEYS:
                    continue
                for ref in reference_values(value):
                    if ref.startswith(DECLARED_REFERENCE_PREFIXES):
                        declared.add(ref)
    return declared


def collect_step_output_records(building_root: Path, violations: list[str]) -> list[Any]:
    """Parsed JSON for present transition-concern / route-request step outputs."""

    records: list[Any] = []
    step_outputs = building_root / "work" / "step-outputs"
    if not step_outputs.is_dir():
        return records
    for name in ("transition-concern.json", "route-request.json"):
        for path in sorted(step_outputs.glob(f"*/{name}")):
            parsed = parse_json_file(path, violations)
            if parsed is not None:
                records.append(parsed)
    return records


def reference_resolves(
    value: str,
    *,
    checked_public_fact: Any = "",
    known_fact_refs: set[str],
    declared_refs: set[str],
    agent_step_slugs: set[str],
    agent_building_segments: set[str],
    agent_return_fields_by_step: Mapping[str, Mapping[str, list[Any]]],
    brick_fields: set[str],
    brick_comparison_field_sets: tuple[set[str], set[str]],
    brick_boundary_ids: set[str],
    pre_grounding_law_building: bool = False,
) -> bool:
    """Whether a public-fact reference resolves to a present fact.

    Presence is verified for the branches whose target is a present artifact of
    this building; the remaining shape-vocabulary branch is accepted by declared
    contract and is documented as intentionally looser:
    - an exact `fact_ref` match against the facts present in this building;
    - `brick:<boundary>` resolves only when `<boundary>` is among the brick
      boundary ids this building declares/observes (present-boundary check, not
      bare prefix);
    - the virtual
      `BrickComparisonFact.<top>.returned_field.<field>.repository_artifact_ref`
      selector resolves only for artifact-grounding fields (`evidence_used` /
      `evidence_refs`) when the same checked comparison step's Agent return
      field is an evidence list carrying at least one repository-artifact-shaped
      ref;
    - every other `BrickComparisonFact.<sel>` resolves only when its top-level field is
      present on the building's own Brick comparison fact envelope AND the
      selector's leaf token is present among that comparison fact's fields/
      observations (nested selectors require both top and leaf present). The
      Brick comparison fact is the building's own present observation, so a
      fabricated comparison field genuinely cannot resolve;
    - `BrickWork.<field>` resolves only when `<field>` is present on a Brick
      fact envelope;
    - `agent-fact:<building-id-or-attempt>:<step-slug>` resolves only when its
      step slug is the slug of an Agent fact present here, and when its middle
      segment matches a present attempt index or building-id segment;
    - declared-disposition prefixes (transition-concern:/human-review:/
      observation:/review-observation:) resolve when the identifier was declared
      in present evidence through a DECLARED_REFERENCE_KEYS key. K1-note (design,
      like the AgentFact./Link. K2-note below): this declaration may live in the
      SAME fact that consumes the ref (self-declare + consume within one Link
      decision). This is intentional and is NOT tightened to require a different
      source. A real Link decision legitimately authors a human-review override
      or reviewer observation inline and references it in the same movement fact
      (e.g. link-decision-disposition-0-dogfood-0527 declares
      `human-review:ldd0-override-reroute` via route_decision_override_refs and
      cites it in public_fact_refs of the same fact, with no separate step-output
      for it because the override IS the Link decision's own recorded disposition).
      Requiring a different source would reject that legitimate inline override,
      so the family stays accept-by-present-declaration on purpose;
    - `AgentFact.<sel>` / `Link.<sel>` are accepted as the required public-fact
      return-shape vocabulary a Link gate evaluates. These INTENTIONALLY do not
      require presence: a gate's `required_public_facts` names the fields it
      requires of the Agent/Link return, and whose missing members it reports
      through `missing_required_facts`/`sufficiency`, so they legitimately name
      fields that may be absent. This branch verifies the namespace prefix only.

    Apart from the documented AgentFact./Link. shape-vocabulary branch, no branch
    accepts a reference solely because it carries a known prefix.
    """

    if value in known_fact_refs:
        return True
    if is_brick_boundary_ref(value):
        boundary = value.split(":", 1)[1].strip()
        return bool(boundary) and boundary in brick_boundary_ids
    if value.startswith(PRESENT_OBSERVATION_FIELD_REF_PREFIX):
        virtual_artifact = brick_comparison_virtual_repository_artifact_selector(value)
        if virtual_artifact is not None:
            if pre_grounding_law_building:
                # Dated grandfather: see PRE_GROUNDING_LAW_BUILDING_IDS.
                return True
            top_field, returned_field = virtual_artifact
            top_level_fields, _ = brick_comparison_field_sets
            if top_field not in top_level_fields:
                return False
            checked_step_slug = brick_comparison_checked_step_slug(checked_public_fact)
            if not checked_step_slug:
                return False
            return any(
                evidence_list_has_repository_artifact_ref(field_value)
                for field_value in agent_return_fields_by_step.get(
                    checked_step_slug,
                    {},
                ).get(returned_field, ())
            )
        tokens = brick_comparison_field_ref_tokens(value)
        if tokens is None:
            return False
        top_field, leaf_field = tokens
        top_level_fields, present_tokens = brick_comparison_field_sets
        return top_field in top_level_fields and leaf_field in present_tokens
    if value.startswith(SHAPE_VOCABULARY_FIELD_REF_PREFIXES):
        return True
    if value.startswith(BRICK_WORK_FIELD_PREFIX):
        field = value[len(BRICK_WORK_FIELD_PREFIX) :].split(".", 1)[0]
        return bool(field) and field in brick_fields
    if value.startswith(AGENT_FACT_REF_PREFIX):
        parts = value.split(":")
        if len(parts) >= 3:
            middle = parts[1].strip()
            slug = ":".join(parts[2:]).strip()
            return (
                bool(slug)
                and slug in agent_step_slugs
                and bool(middle)
                and middle in agent_building_segments
            )
        return False
    if value.startswith(DECLARED_REFERENCE_PREFIXES):
        return value in declared_refs
    return False


def reference_values(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []


def complete_content_files_present(building_root: Path) -> bool:
    return all(
        (building_root / Path(*record)).exists()
        for record in MINIMAL_REQUIRED_RECORDS
    )


def complete_agent_return_file_present(building_root: Path) -> bool:
    return any(
        (building_root / Path(*record)).exists()
        for record in (
            ("raw", "agent-return.jsonl"),
            ("raw", "agent-returns.jsonl"),
            ("evidence", "claim_trace", "agent", "returned_claims.json"),
        )
    )


def frontier_content_files_present(building_root: Path) -> bool:
    has_adapter_step = any(
        path.is_file()
        for path in (building_root / "work" / "step-outputs").glob("*/adapter-error.json")
    )
    return (
        has_adapter_step
        and all((building_root / Path(*record)).exists() for record in FRONTIER_REQUIRED_RECORDS)
    )


def parked_content_files_present(building_root: Path) -> bool:
    has_parked_step = any(
        path.is_file()
        for path in (building_root / "work" / "step-outputs").glob("*/parked.json")
    )
    has_work_envelope = any(
        path.is_file()
        for path in (building_root / "work" / "step-outputs").glob("*/work-envelope.json")
    )
    return (
        has_parked_step
        and has_work_envelope
        and all((building_root / Path(*record)).exists() for record in PARKED_REQUIRED_RECORDS)
    )


def content_branch_for(building_root: Path) -> str:
    if complete_content_files_present(building_root):
        return "complete"
    if not complete_agent_return_file_present(building_root) and parked_content_files_present(
        building_root
    ):
        return "parked"
    if not complete_agent_return_file_present(building_root) and frontier_content_files_present(
        building_root
    ):
        return "frontier"
    return "complete"


def validate_adapter_error_files(building_root: Path, violations: list[str]) -> None:
    step_outputs = building_root / "work" / "step-outputs"
    if not step_outputs.is_dir():
        return
    for adapter_error_path in sorted(step_outputs.glob("*/adapter-error.json")):
        adapter_error = parse_json_file(adapter_error_path, violations)
        if not isinstance(adapter_error, dict):
            violations.append(f"{adapter_error_path}: adapter-error record must be a JSON object")
            continue
        if adapter_error.get("agent_fact_created") is not False:
            violations.append(
                f"{adapter_error_path}: adapter-error requires agent_fact_created:false"
            )
        if has_forbidden_authority_claim(adapter_error):
            violations.append(
                f"{adapter_error_path}: adapter-error must not claim source truth, success "
                "judgment, quality judgment, or Movement authority"
            )
        if has_any_key(adapter_error, ADAPTER_ERROR_FORBIDDEN_KEYS):
            violations.append(
                f"{adapter_error_path}: adapter-error must not contain credential/session/"
                "returned/Movement/target fields"
            )
        if has_sensitive_text(adapter_error):
            violations.append(
                f"{adapter_error_path}: adapter-error must not contain credential-like text"
            )


def validate_chat_session_park_files(building_root: Path, violations: list[str]) -> None:
    step_outputs = building_root / "work" / "step-outputs"
    if not step_outputs.is_dir():
        return
    for parked_path in sorted(step_outputs.glob("*/parked.json")):
        parked = parse_json_file(parked_path, violations)
        if not isinstance(parked, dict):
            violations.append(f"{parked_path}: parked record must be a JSON object")
            continue
        if parked.get("kind") != "chat_session_park_record":
            violations.append(f"{parked_path}: parked record kind must be chat_session_park_record")
        if parked.get("schema_version") != "chat-session-park-record-0":
            violations.append(f"{parked_path}: parked record schema_version mismatch")
        if not isinstance(parked.get("parked_ref"), str) or not parked.get("parked_ref"):
            violations.append(f"{parked_path}: parked record requires parked_ref")
        if not isinstance(parked.get("work_envelope_ref"), str) or not parked.get("work_envelope_ref"):
            violations.append(f"{parked_path}: parked record requires work_envelope_ref")
        if has_any_key(parked, PARK_RECORD_FORBIDDEN_KEYS):
            violations.append(
                f"{parked_path}: parked record must be distinct from adapter-error and must "
                "not contain returned/Movement/target/session fields"
            )
        if has_forbidden_authority_claim(parked):
            violations.append(
                f"{parked_path}: parked record must not claim source truth, success "
                "judgment, quality judgment, or Movement authority"
            )
        if has_sensitive_text(parked) or has_session_identifier_text(parked):
            violations.append(f"{parked_path}: parked record must not contain credential/session text")
    for envelope_path in sorted(step_outputs.glob("*/work-envelope.json")):
        envelope = parse_json_file(envelope_path, violations)
        if not isinstance(envelope, dict):
            violations.append(f"{envelope_path}: work envelope must be a JSON object")
            continue
        if set(envelope) != WORK_ENVELOPE_KEYS:
            violations.append(
                f"{envelope_path}: work envelope keys must exactly match AgentAdapterRequest"
            )
        if envelope.get("adapter_ref") != "adapter:chat-session":
            violations.append(f"{envelope_path}: work envelope adapter_ref must be adapter:chat-session")
        if has_sensitive_text(envelope) or has_session_identifier_text(envelope):
            violations.append(f"{envelope_path}: work envelope must not contain credential/session text")
    validate_chat_session_claim_submission_files(building_root, violations)


def validate_chat_session_claim_submission_files(building_root: Path, violations: list[str]) -> None:
    step_outputs = building_root / "work" / "step-outputs"
    for claim_path in sorted(step_outputs.glob("*/claim.json")):
        claim = parse_json_file(claim_path, violations)
        if not isinstance(claim, dict):
            violations.append(f"{claim_path}: claim record must be a JSON object")
            continue
        if claim.get("kind") != "chat_session_claim_record":
            violations.append(f"{claim_path}: claim record kind must be chat_session_claim_record")
        if claim.get("schema_version") != "chat-session-claim-record-0":
            violations.append(f"{claim_path}: claim record schema_version mismatch")
        state = claim.get("claim_state")
        if state not in CHAT_SESSION_CLAIM_STATES:
            violations.append(f"{claim_path}: claim_state must be claimed or released")
        token = claim.get("claim_token")
        if not isinstance(token, str) or not CHAT_SESSION_TOKEN_RE.fullmatch(token):
            violations.append(f"{claim_path}: claim_token must be a lower-case word tuple")
        if not isinstance(claim.get("lane_ref"), str) or not claim.get("lane_ref"):
            violations.append(f"{claim_path}: claim record requires lane_ref")
        if has_sensitive_text(claim) or has_session_identifier_text(claim):
            violations.append(f"{claim_path}: claim record must not contain credential/session text")

    forbidden_return_keys = set(RETURNED_FORBIDDEN_KEYS)
    for submission_path in sorted(step_outputs.glob("*/submission.json")):
        submission = parse_json_file(submission_path, violations)
        if not isinstance(submission, dict):
            violations.append(f"{submission_path}: submission record must be a JSON object")
            continue
        if submission.get("kind") != "chat_session_submission_record":
            violations.append(f"{submission_path}: submission record kind must be chat_session_submission_record")
        if submission.get("schema_version") != "chat-session-submission-record-0":
            violations.append(f"{submission_path}: submission record schema_version mismatch")
        token = submission.get("claim_token")
        if not isinstance(token, str) or not CHAT_SESSION_TOKEN_RE.fullmatch(token):
            violations.append(f"{submission_path}: claim_token must be a lower-case word tuple")
        returned = submission.get("returned")
        if not isinstance(returned, dict):
            violations.append(f"{submission_path}: submission returned payload must be a JSON object")
        elif has_any_key(returned, forbidden_return_keys):
            violations.append(
                f"{submission_path}: submission returned payload must not contain closed "
                "AgentFact forbidden keys"
            )
        if has_sensitive_text(submission) or has_session_identifier_text(submission):
            violations.append(f"{submission_path}: submission record must not contain credential/session text")
        claim_path = submission_path.parent / "claim.json"
        if claim_path.is_file():
            claim = parse_json_file(claim_path, violations)
            if isinstance(claim, dict) and claim.get("claim_token") != token:
                violations.append(f"{submission_path}: submission claim_token must match claim.json")


def validate_minimal_content(building_root: Path, violations: list[str]) -> None:
    raw_manifest_path = building_root / "raw" / "raw-manifest.json"
    evidence_manifest_path = building_root / "evidence" / "evidence-manifest.json"
    content_branch = content_branch_for(building_root)
    validate_adapter_error_files(building_root, violations)
    validate_chat_session_park_files(building_root, violations)
    raw_manifest = parse_json_file(raw_manifest_path, violations)
    evidence_manifest = parse_json_file(evidence_manifest_path, violations)
    entries = manifest_entries(raw_manifest)
    if not entries:
        violations.append(f"{raw_manifest_path}: raw manifest requires entries/raw_streams")
    refs = raw_ref_set(entries)
    if not refs:
        violations.append(f"{raw_manifest_path}: raw manifest requires raw_refs")
    for entry in entries:
        axis_owner = entry.get("axis_owner")
        if axis_owner not in AXIS_OWNER_LITERALS:
            violations.append(
                f"{raw_manifest_path}: axis_owner must be one of Brick, Agent, Link: {axis_owner!r}"
            )
        record_role = entry.get("record_role")
        if record_role not in RAW_RECORD_ROLES:
            violations.append(
                f"{raw_manifest_path}: record_role must be one of primary, support, review: "
                f"{record_role!r}"
            )
        for field in sorted(RAW_MANIFEST_REQUIRED_TEXT_FIELDS):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                violations.append(f"{raw_manifest_path}: raw manifest entry requires {field}")
        entry_raw_refs = entry.get("raw_refs")
        if not isinstance(entry_raw_refs, list) or not entry_raw_refs:
            violations.append(f"{raw_manifest_path}: each raw manifest entry requires raw_refs")
            entry_ref_values: set[str] = set()
        else:
            entry_ref_values = {
                str(ref) for ref in entry_raw_refs if isinstance(ref, str) and ref.strip()
            }
        rel_path = entry.get("path")
        if not isinstance(rel_path, str) or not rel_path:
            violations.append(f"{raw_manifest_path}: raw manifest entry requires path")
            continue
        path_reason = raw_manifest_entry_path_reason(rel_path)
        if path_reason:
            violations.append(f"{raw_manifest_path}: {path_reason}: {rel_path!r}")
            continue
        target = building_root / to_posix(rel_path)
        if not target.exists():
            violations.append(f"{raw_manifest_path}: manifest-listed raw file is missing: {rel_path}")
            continue
        actual_raw_refs: set[str] = set()
        if target.suffix == ".json":
            actual_raw_refs.update(raw_refs_from_value(parse_json_file(target, violations)))
        if target.suffix == ".jsonl":
            actual_raw_refs.update(parse_jsonl_file(target, violations))
        for ref in sorted(entry_ref_values):
            if ref not in actual_raw_refs:
                violations.append(f"{raw_manifest_path}: raw_ref not found in listed raw file: {ref}")

    if has_forbidden_authority_claim(evidence_manifest):
        violations.append(
            f"{evidence_manifest_path}: evidence manifest must not claim source truth, "
            "success judgment, quality judgment, or Movement authority"
        )

    if content_branch in {"frontier", "parked"}:
        claim_paths = {
            "Brick": [building_root / "evidence" / "claim_trace" / "brick" / "work_contract.json"],
            "Agent": [building_root / "evidence" / "claim_trace" / "agent" / "receipt_trace.json"],
            "Link": [building_root / "evidence" / "claim_trace" / "link" / "frontier_trace.json"],
        }
    else:
        claim_paths = {
            "Brick": [building_root / "evidence" / "claim_trace" / "brick" / "work_contract.json"],
            "Agent": [building_root / "evidence" / "claim_trace" / "agent" / "returned_claims.json"],
            "Link": [
                building_root / "evidence" / "claim_trace" / "link" / "transfer_trace.json",
                building_root / "evidence" / "claim_trace" / "link" / "carry_trace.json",
                building_root / "evidence" / "claim_trace" / "link" / "sufficiency_trace.json",
                building_root / "evidence" / "claim_trace" / "link" / "movement_trace.json",
            ],
        }
        optional_receipt_trace = (
            building_root / "evidence" / "claim_trace" / "agent" / "receipt_trace.json"
        )
        if optional_receipt_trace.exists():
            claim_paths["Agent"].append(optional_receipt_trace)
        optional_frontier_trace = (
            building_root / "evidence" / "claim_trace" / "link" / "frontier_trace.json"
        )
        if optional_frontier_trace.exists():
            claim_paths["Link"].append(optional_frontier_trace)
    all_claim_facts: list[tuple[str, Path, dict[str, Any]]] = []
    known_fact_refs: set[str] = set()
    for axis, paths in claim_paths.items():
        for claim_path in paths:
            claim = parse_json_file(claim_path, violations)
            if not isinstance(claim, dict):
                violations.append(f"{claim_path}: claim_trace file must be a JSON object")
                continue
            facts = claim_facts(claim)
            if not facts:
                violations.append(f"{claim_path}: claim_trace file requires at least one fact")
            for fact in facts:
                all_claim_facts.append((axis, claim_path, fact))
                ref = fact_reference(fact)
                if ref:
                    known_fact_refs.add(ref)

    # Build the present-fact resolution index from facts that actually exist in
    # this building, so a public-fact reference is accepted only when its target
    # is present (verified), never blanket-accepted by namespace prefix.
    building_id = building_root.name
    agent_facts = [fact for axis, _, fact in all_claim_facts if axis == "Agent"]
    brick_facts = [fact for axis, _, fact in all_claim_facts if axis == "Brick"]
    brick_comparison_facts = [fact for fact in brick_facts if is_brick_comparison_fact(fact)]
    agent_step_slugs = agent_fact_step_slugs(agent_facts)
    agent_building_segments = agent_fact_building_segments(agent_facts, building_id)
    agent_return_fields_by_step = agent_return_field_values_by_step(agent_facts)
    brick_fields = brick_work_field_names(brick_facts)
    brick_comparison_field_sets = envelope_field_token_set(brick_comparison_facts)
    boundary_sources: list[Any] = [fact for _, _, fact in all_claim_facts]
    building_map_path = building_root / "work" / "building-map.json"
    if building_map_path.is_file():
        building_map = parse_json_file(building_map_path, violations)
        if building_map is not None:
            boundary_sources.append(building_map)
    brick_boundary_ids = present_brick_boundary_ids(boundary_sources)
    disposition_sources: list[Any] = [fact for _, _, fact in all_claim_facts]
    disposition_sources.extend(collect_step_output_records(building_root, violations))
    declared_refs = declared_disposition_refs(disposition_sources)

    for axis, claim_path, fact in all_claim_facts:
        fact_axis = fact.get("axis")
        if fact_axis != axis:
            violations.append(f"{claim_path}: claim_trace fact axis must be {axis}: {fact_axis!r}")
        if not isinstance(fact.get("fact"), dict):
            violations.append(f"{claim_path}: every claim_trace fact requires fact envelope")
        raw_refs = fact.get("raw_refs")
        if not isinstance(raw_refs, list) or not raw_refs:
            violations.append(f"{claim_path}: every claim_trace fact requires raw_refs")
        else:
            for ref in raw_refs:
                if ref not in refs:
                    violations.append(f"{claim_path}: raw_ref does not resolve through raw manifest: {ref}")
        if "proof_limits" not in fact or not fact.get("proof_limits"):
            violations.append(f"{claim_path}: every claim_trace fact requires proof_limits")
        if "not_proven" not in fact or not fact.get("not_proven"):
            violations.append(f"{claim_path}: every claim_trace fact requires not_proven")
        if axis == "Agent" and classify_self_classifies(fact):
            violations.append(f"{claim_path}: Agent claim_trace must not self-classify")
        is_frontier_agent_trace = claim_path.name == "receipt_trace.json"
        is_frontier_link_trace = claim_path.name == "frontier_trace.json"
        if (
            axis == "Agent"
            and (content_branch == "frontier" or is_frontier_agent_trace)
            and has_any_key(fact, FRONTIER_AGENT_FORBIDDEN_KEYS)
        ):
            violations.append(
                f"{claim_path}: frontier Agent receipt trace must not contain returned/"
                "AgentFact fields"
            )
        if axis == "Link" and link_references_agent_endpoint(fact):
            violations.append(f"{claim_path}: Link endpoint must not reference an Agent identity")
        if (
            axis == "Link"
            and (content_branch == "frontier" or is_frontier_link_trace)
            and has_any_key(fact, FRONTIER_LINK_FORBIDDEN_KEYS)
        ):
            violations.append(
                f"{claim_path}: frontier Link trace must not contain Movement/target/"
                "route disposition fields"
            )
        if axis == "Link":
            for item in dict_values(fact):
                for key in CROSS_FACT_REFERENCE_KEYS:
                    value = item.get(key)
                    if isinstance(value, str) and value and value not in known_fact_refs:
                        violations.append(f"{claim_path}: cross-fact reference does not resolve: {value}")
                for key in PUBLIC_FACT_REFERENCE_KEYS:
                    for value in reference_values(item.get(key)):
                        if not reference_resolves(
                            value,
                            checked_public_fact=item.get("checked_public_fact"),
                            known_fact_refs=known_fact_refs,
                            declared_refs=declared_refs,
                            agent_step_slugs=agent_step_slugs,
                            agent_building_segments=agent_building_segments,
                            agent_return_fields_by_step=agent_return_fields_by_step,
                            brick_fields=brick_fields,
                            brick_comparison_field_sets=brick_comparison_field_sets,
                            brick_boundary_ids=brick_boundary_ids,
                            pre_grounding_law_building=(
                                building_id in PRE_GROUNDING_LAW_BUILDING_IDS
                            ),
                        ):
                            violations.append(f"{claim_path}: public fact reference does not resolve: {value}")


def resolve_building_root(root: Path, project_id: str, building_id: str) -> Path | None:
    """Locate the real Building root for a candidate under the given label.

    Handles every label shape the checker produces:
    - --repo: label is "<repo>/project", so the root already IS the project root
      and the Building lives at <root>/<project_id>/buildings/<building_id>
      (NOT <root>/project/... which would double the "project" segment).
    - a checkout-style label that is the repo root: <root>/project/...
    - --target/--fixture pointing directly at a Building dir or its buildings/
      parent.
    """

    candidates: list[Path] = []
    if root.name == PROJECT_ROOT:
        # label is already the project root (e.g. --repo "<repo>/project").
        candidates.append(root / project_id / BUILDINGS_SEGMENT / building_id)
    candidates.append(root / PROJECT_ROOT / project_id / BUILDINGS_SEGMENT / building_id)
    if root.name == building_id and root.parent.name == BUILDINGS_SEGMENT:
        candidates.append(root)
    if root.name == BUILDINGS_SEGMENT:
        candidates.append(root / building_id)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def building_root_is_u5_5_live(building_root: Path) -> bool:
    """True iff <building_root>/evidence/evidence-manifest.json declares the tag.

    The FIELD evidence_generation is NEW: existing manifests LACK it, so .get()
    => None => not u5_5_live => the spine is never required for them (all 154
    existing buildings stay green). A missing / unparsable manifest is NOT
    treated as live (manifest presence is enforced separately as a required
    record).
    """

    manifest_path = building_root / "evidence" / "evidence-manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(manifest, dict) and manifest.get("evidence_generation") == "u5_5_live"


def make_u5_5_live_resolver(label: str):
    """A generation resolver bound to a real on-disk label (repo / dir mode).

    Returns a callable (project_id, building_id) -> bool that resolves the real
    building root under ``label`` and reads its manifest tag. In pure path-list
    (.txt fixture) mode there is no real label dir, so the resolver simply
    reports False (nothing required), which is the safe untagged default.
    """

    root = Path(label)

    def _resolve(project_id: str, building_id: str) -> bool:
        if not root.is_dir():
            return False
        building_root = resolve_building_root(root, project_id, building_id)
        if building_root is None:
            return False
        return building_root_is_u5_5_live(building_root)

    return _resolve


def collect_content_violations(label: str, candidates: set[tuple[str, str]]) -> list[str]:
    root = Path(label)
    violations: list[str] = []
    if not root.is_dir():
        return violations
    for project_id, building_id in sorted(candidates):
        building_root = resolve_building_root(root, project_id, building_id)
        if building_root is not None:
            validate_minimal_content(building_root, violations)
    return violations


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check project Building lifecycle path shape. "
            "This is support evidence only."
        )
    )
    parser.add_argument("--target", default=None)
    parser.add_argument("--fixture", default=None)
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    selected = (
        Path(args.target)
        if args.target
        else Path(args.fixture)
        if args.fixture
        else Path(args.repo) / "project"
        if args.repo
        else Path("support/checkers/fixtures/building_lifecycle_path_shape/pass_building_lifecycle_paths.txt")
    )

    try:
        if args.repo:
            label, paths = collect_repo_lifecycle_paths(Path(args.repo))
            violations = check_paths(
                paths,
                require_candidate=False,
                is_u5_5_live=make_u5_5_live_resolver(label),
            )
        else:
            label, paths = collect_paths(selected)
            violations = check_paths(
                paths,
                is_u5_5_live=make_u5_5_live_resolver(label),
            )
        if not violations:
            violations.extend(collect_content_violations(label, known_candidates(set(paths))))
    except OSError as exc:
        print(f"building lifecycle path shape rejected: {exc}", file=sys.stderr)
        return 1

    if violations:
        print("building lifecycle path shape rejected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    print(
        "building lifecycle path shape passed: "
        f"{len(paths)} path(s) in {label} follow project Building lifecycle placement."
    )
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
