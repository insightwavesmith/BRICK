"""Dashboard read-side projection.

Reads already-written Building evidence (via the project orchestration ledger
packet) and shapes it into a single dashboard-readable packet for the read-only
dashboard surface. Reuses ``project_orchestration_ledger_packet`` — does not
re-read source truth, does not run a dashboard runtime, does not choose
Movement, does not judge success/quality.

Truth layer only: every field here is observed/derived fact (counts, board
states, frontier kinds, evidence timestamps, building-map topology). Quality
judgement is never produced here.

EVENT-DELTA addition: besides the full ``dashboard_export_packet`` snapshot
(used as the initial connect-time SEED), this module exposes
``dashboard_building_delta(building_id)`` which projects ONE building into the
SAME row/detail shape the snapshot uses for that building. The delta is a
strict SUBSET of the snapshot shape (one ``building`` row + that building's
``detail`` entry), so the dashboard can splice it in without a new schema.

PROJECT-0 S4-B (multi-project composite key): building_id uniqueness is
per-vessel, so the dashboard keys rows/detail/deltas by the COMPOSITE
``(project, building_id)`` — rendered as ``<project>/<building_id>`` — and two
vessels carrying the same building_id can never clobber each other. The
per-project blocks carry the vessel's declared direction (the parent-goal
slot, design §1) — projected from the ledger, never judged here.
"""

from __future__ import annotations

import glob
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from brick_protocol.support.operator.ledger_projection import (
    project_orchestration_ledger_packet,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DASHBOARD_PUBLIC_DATA_PATH = Path("support/dashboard/public/dashboard-data.json")
STALE_DAYS_DEFAULT = 7
WRITE_BRICK_KINDS = frozenset({"work"})

# observed_running 을 frontier_kind + 나이로 세분한 표시 상태. Non-stale
# closure_pending remains an open in-progress display state; stale pending keeps
# the archived_stale projection.
DISP_ORDER = (
    "running",
    "closure_pending",
    "archived_stale",
    "stopped",
    "review",
    "incomplete",
    "closed",
    "unknown",
)

DASHBOARD_PROOF_LIMITS = (
    "support read-side projection only",
    "reads already-written Building evidence",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not a dashboard runtime",
    "display state derived from board_state + frontier_kind + evidence age",
)
DASHBOARD_NOT_PROVEN = (
    "dashboard UI readiness",
    "that last_evidence_at reflects provider liveness rather than newest recorded evidence",
    "real-time freshness beyond export moment",
)

# EVENT-DELTA: a single-building delta carries the SAME per-building row/detail
# shape as the snapshot, plus these proof-limit notes (the delta is a subset of
# the snapshot, not a full board picture, and not source truth / provider
# liveness).
DASHBOARD_DELTA_PROOF_LIMITS = DASHBOARD_PROOF_LIMITS + (
    "single-building delta event (subset of the full snapshot shape)",
    "delta carries one building row + that building's detail only",
    "not a full board snapshot",
)
DASHBOARD_DELTA_NOT_PROVEN = DASHBOARD_NOT_PROVEN + (
    "consistency with buildings not included in this delta",
)


def _last(ref: Any) -> str:
    return str(ref).split(":")[-1] if ref else ""


def _row_building_key(row: Mapping[str, Any]) -> str:
    """COMPOSITE dashboard key for one ledger row: ``<project>/<building_id>``.

    building_id uniqueness is per-vessel (PROJECT-0 design §1), so every
    dashboard index (buildings[].key, detail keys, delta building_key) uses
    this composite — same id in two vessels stays two distinct entries.
    """

    return f"{_last(row.get('project_ref'))}/{row.get('building_id')}"


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _gen_dt(generated_at: Any) -> datetime:
    return _parse_ts(generated_at) or datetime.now(timezone.utc)


def _age_days(value: Any, gen_dt: datetime) -> int | None:
    ts = _parse_ts(value)
    return (gen_dt - ts).days if ts else None


def _disp_state(row: Mapping[str, Any], gen_dt: datetime, stale_days: int) -> str:
    board = row.get("board_state")
    frontier = row.get("frontier_kind")
    if board == "closed":
        return "closed"
    if board == "observed_running":
        if frontier == "closure_pending":
            ad = _age_days(row.get("last_evidence_at"), gen_dt)
            if ad is not None and ad >= stale_days:
                return "archived_stale"
            return "running"
        return "running"
    if board == "link_paused":
        return "stopped"
    if board == "waiting_review":
        return "review"
    if board == "evidence_incomplete":
        return "incomplete"
    return "unknown"


def _building_row(row: Mapping[str, Any], gen_dt: datetime, stale_days: int) -> dict[str, Any]:
    """Project ONE ledger row into the dashboard ``buildings[]`` row shape.

    Single source of the per-building row shape, used by both the full snapshot
    and the single-building delta (so the delta is a strict subset of the
    snapshot).
    """

    ds = _disp_state(row, gen_dt, stale_days)
    ad = _age_days(row.get("last_evidence_at"), gen_dt)
    return {
        "id": row.get("building_id"),
        "key": _row_building_key(row),
        "project": _last(row.get("project_ref")),
        "state": row.get("board_state"),
        "disp": ds,
        "frontier": row.get("frontier_kind"),
        "currentBrick": str(row.get("current_brick_ref", "")).replace("brick-", ""),
        "currentAgent": _last(row.get("current_agent_ref", "")),
        "movement": row.get("latest_movement"),
        "dispositionOwner": (row.get("link_disposition") or {}).get("required_disposition_owner"),
        "lastEvidenceAt": row.get("last_evidence_at"),
        "ageDays": ad,
        "stale": ds == "archived_stale",
        "missing": row.get("missing_required_file_count", 0),
        "nextAction": row.get("next_action_observation", ""),
    }


def _building_detail(row: Mapping[str, Any], repo: Path) -> dict[str, Any] | None:
    """Project ONE ledger row's building-map graph into the dashboard ``detail`` shape.

    Returns None when the row carries no readable building-map (the snapshot
    simply omits such rows from ``detail``). Single source of the per-building
    detail shape, used by both the snapshot and the delta.
    """

    mp = (row.get("evidence_refs", {}) or {}).get("building_map")
    if not mp:
        return None
    path = os.path.join(repo, mp)
    if not os.path.exists(path):
        return None
    try:
        bmap = json.load(open(path))
    except Exception:
        return None
    binds = {}
    for binding in bmap.get("agent_bindings", []):
        binds[binding.get("brick_instance_ref")] = _last(binding.get("agent_performer_ref", ""))
    bricks_d = []
    for inst in bmap.get("brick_instances", []):
        ref = inst.get("brick_instance_id") or inst.get("brick_instance_ref") or ""
        bricks_d.append(
            {
                "ref": ref,
                "name": ref.replace("brick-", ""),
                "agent": binds.get(ref, ""),
                "attempt": inst.get("attempt_index"),
            }
        )
    edges = []
    for edge in bmap.get("link_edges", []):
        edges.append(
            {
                "source": edge.get("source_brick_instance_ref") or edge.get("source") or "",
                "target": edge.get("target_brick_instance_ref") or edge.get("target") or "",
                "kind": edge.get("edge_role") or "",
            }
        )
    return {
        "name": row.get("building_id"),
        "project": _last(row.get("project_ref")),
        "state": row.get("board_state"),
        "bricks": bricks_d,
        "edges": edges,
        "groups": bmap.get("groups", []),
    }


def dashboard_export_packet(
    *,
    repo_root: Path | str = REPO_ROOT,
    stale_days: int = STALE_DAYS_DEFAULT,
) -> dict[str, Any]:
    """Build the dashboard packet from current Building evidence (read-only)."""

    repo = Path(repo_root).resolve()
    led = project_orchestration_ledger_packet(repo_root=repo)
    rows = list(led.get("rows", []))
    generated_at = led.get("generated_at")
    gen_dt = _gen_dt(generated_at)

    # 프로젝트 집계 — 선언된 동네 전부가 먼저 자리를 갖는다(빌딩 0개여도 사실).
    # direction = 그 동네 project.json의 선언(부모 목표 자리, 설계 §1) — 연결만.
    projects: dict[str, dict[str, Any]] = {}
    for vessel in led.get("projects", []):
        pid = vessel.get("project_ref")
        projects[pid] = {
            "id": _last(pid),
            "label": vessel.get("project_label"),
            "direction": vessel.get("project_direction"),
            "total": 0,
            "counts": {key: 0 for key in DISP_ORDER},
            "stalePending": 0,
        }
    for row in rows:
        pid = row.get("project_ref")
        proj = projects.setdefault(
            pid,
            {
                "id": _last(pid),
                "label": row.get("project_label"),
                "direction": row.get("project_direction"),
                "total": 0,
                "counts": {key: 0 for key in DISP_ORDER},
                "stalePending": 0,
            },
        )
        proj["total"] += 1
        ds = _disp_state(row, gen_dt, stale_days)
        proj["counts"][ds] += 1
        if ds == "archived_stale":
            proj["stalePending"] += 1

    # 빌딩
    buildings = [_building_row(row, gen_dt, stale_days) for row in rows]

    # 에이전트 현재 부하 (closed 아닌 빌딩의 current_agent)
    load: dict[str, int] = {}
    for row in rows:
        if row.get("board_state") != "closed":
            agent = _last(row.get("current_agent_ref", ""))
            if agent:
                load[agent] = load.get(agent, 0) + 1

    # 에이전트 로스터 (agent/objects/*.yaml 은 JSON)
    agents = []
    for path in sorted(glob.glob(str(repo / "agent" / "objects" / "*.yaml"))):
        try:
            obj = json.load(open(path))
        except Exception:
            continue
        name = obj.get("name") or os.path.basename(path)[:-5]
        skills = sorted(_last(s) for s in obj.get("skill_refs", []))
        tools = [_last(t) for t in obj.get("tool_policy_refs", [])]
        agents.append(
            {
                "id": name,
                "lane": obj.get("lane", ""),
                "skills": skills[:4],
                "tool": tools[0] if tools else "",
                "load": load.get(name, 0),
            }
        )

    # 브릭 카탈로그
    bricks = []
    for dpath in sorted(glob.glob(str(repo / "brick" / "templates" / "bricks" / "*") + os.sep)):
        kind = os.path.basename(dpath.rstrip(os.sep))
        ret = ""
        ry = os.path.join(dpath, "return.yaml")
        if os.path.exists(ry):
            fields = re.findall(r"^\s*-\s*([a-z_]+)", open(ry).read(), re.M)
            ret = ", ".join(fields[:6])
        bricks.append({"kind": kind, "write": kind in WRITE_BRICK_KINDS, "returnShape": ret})

    # 링크 집계
    movement: dict[str, int] = {}
    dispositions: dict[str, int] = {}
    for row in rows:
        mv = row.get("latest_movement")
        if mv:
            movement[mv] = movement.get(mv, 0) + 1
        owner = (row.get("link_disposition") or {}).get("required_disposition_owner")
        if owner:
            dispositions[owner] = dispositions.get(owner, 0) + 1

    # 빌딩 상세 (building-map 그래프) — 키 = (project, building_id) 복합.
    detail: dict[str, Any] = {}
    for row in rows:
        entry = _building_detail(row, repo)
        if entry is not None:
            detail[_row_building_key(row)] = entry

    # 합류/분기 집계
    fan = {"fan_in_buildings": 0, "fan_in_points": 0, "fan_out_buildings": 0, "fan_out_points": 0}
    for value in detail.values():
        gi = [g for g in value.get("groups", []) if g.get("group_role") == "fan_in"]
        go = [g for g in value.get("groups", []) if g.get("group_role") == "fan_out"]
        if gi:
            fan["fan_in_buildings"] += 1
            fan["fan_in_points"] += len(gi)
        if go:
            fan["fan_out_buildings"] += 1
            fan["fan_out_points"] += len(go)

    # 표시 상태 집계
    by_display = {key: 0 for key in DISP_ORDER}
    for row in rows:
        by_display[_disp_state(row, gen_dt, stale_days)] += 1

    return {
        "generatedAt": generated_at,
        "source": "live",
        "staleDays": stale_days,
        "source_truth": False,
        "proofLimits": list(led.get("proof_limits", [])),
        "proof_limits": list(DASHBOARD_PROOF_LIMITS),
        "not_proven": list(DASHBOARD_NOT_PROVEN),
        "summary": {
            "projects": len(projects),
            "buildings": len(rows),
            "byState": led.get("state_counters", {}),
            "byDisplay": by_display,
            "stalePending": by_display["archived_stale"],
        },
        "projects": list(projects.values()),
        "buildings": buildings,
        "agents": agents,
        "bricks": bricks,
        "links": {"movement": movement, "dispositions": dispositions, "fan": fan},
        "detail": detail,
    }


def _validate_dashboard_bake_packet(packet: Mapping[str, Any]) -> Mapping[str, Any]:
    """Fail closed before writing the baked static seed file."""

    if not isinstance(packet, Mapping):
        raise ValueError("dashboard bake packet must be a mapping")
    if packet.get("source_truth") is not False:
        raise ValueError("dashboard bake packet source_truth must be false")
    if not isinstance(packet.get("buildings"), list):
        raise ValueError("dashboard bake packet must carry a buildings list")
    return packet


def bake_dashboard_data_json(
    *,
    repo_root: Path | str = REPO_ROOT,
    out_path: Path | str | None = None,
    stale_days: int = STALE_DAYS_DEFAULT,
) -> dict[str, Any]:
    """Bake the read-side dashboard seed into support/dashboard/public.

    This is a synchronous support/operator projection verb only. It computes
    ``dashboard_export_packet`` from already-written evidence and writes the
    Vite public seed file in one step; it opens no scheduler, queue, retry loop,
    runtime authority, source-truth surface, or Movement authority.
    """

    repo = Path(repo_root).resolve()
    target = Path(out_path) if out_path is not None else repo / DEFAULT_DASHBOARD_PUBLIC_DATA_PATH
    packet = _validate_dashboard_bake_packet(
        dashboard_export_packet(repo_root=repo, stale_days=stale_days)
    )
    text = json.dumps(packet, ensure_ascii=False, indent=2)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text + "\n", encoding="utf-8")
    return {
        "path": str(target),
        "source_truth": packet.get("source_truth"),
        "buildings": len(packet.get("buildings", [])),
        "generatedAt": packet.get("generatedAt"),
        "proof_limits": [
            "support read-side projection only",
            "writes static dashboard seed only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
            "not scheduler/queue/retry runtime",
        ],
    }


def dashboard_building_delta(
    building_id: str,
    *,
    project_ref: str | None = None,
    repo_root: Path | str = REPO_ROOT,
    stale_days: int = STALE_DAYS_DEFAULT,
) -> dict[str, Any]:
    """Project ONE building into the snapshot's per-building row/detail shape.

    EVENT-DELTA publisher unit. The returned ``building`` is byte-for-byte the
    same dict the full ``dashboard_export_packet`` would place in its
    ``buildings[]`` list for this building; ``detail`` is the same dict (or
    None) the snapshot would place under the composite ``building_key``. The
    dashboard splices the delta into its existing snapshot state — NO new
    shape is invented.

    PROJECT-0 S4-B: building_id uniqueness is per-vessel, so the lookup is
    fail-closed: when the same building_id exists in MORE THAN ONE vessel and
    no ``project_ref`` narrows it, the call rejects loudly (never a silent
    first-match — the wrong vessel's delta would clobber the right one).
    The delta carries ``project_ref`` + composite ``building_key`` so the
    receiver splices by composite key.

    Raises KeyError if the building id is not present in the current ledger
    (the caller should only publish deltas for observed buildings).
    """

    if not isinstance(building_id, str) or not building_id.strip():
        raise ValueError("building_id must be a non-empty string")
    target = building_id.strip()
    target_project = project_ref.strip() if isinstance(project_ref, str) else None

    repo = Path(repo_root).resolve()
    led = project_orchestration_ledger_packet(repo_root=repo)
    rows = list(led.get("rows", []))
    generated_at = led.get("generated_at")
    gen_dt = _gen_dt(generated_at)

    matches = [
        row
        for row in rows
        if str(row.get("building_id")) == target
        and (target_project is None or str(row.get("project_ref")) == target_project)
    ]
    if not matches:
        raise KeyError(
            f"building id not present in current ledger: {target}"
            + (f" (project_ref={target_project})" if target_project else "")
        )
    if len(matches) > 1:
        vessels = ", ".join(sorted(str(row.get("project_ref")) for row in matches))
        raise ValueError(
            f"building id {target!r} exists in more than one declared vessel "
            f"({vessels}) — pass project_ref to disambiguate; a first-match "
            "delta would clobber the other vessel's building"
        )
    match = matches[0]

    building = _building_row(match, gen_dt, stale_days)
    detail = _building_detail(match, repo)

    return {
        "generatedAt": generated_at,
        "source": "live",
        "staleDays": stale_days,
        "source_truth": False,
        "delta_kind": "building",
        "building_id": target,
        "project_ref": str(match.get("project_ref")),
        "building_key": _row_building_key(match),
        "proofLimits": list(led.get("proof_limits", [])),
        "proof_limits": list(DASHBOARD_DELTA_PROOF_LIMITS),
        "not_proven": list(DASHBOARD_DELTA_NOT_PROVEN),
        "building": building,
        "detail": detail,
    }


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Write the dashboard read-side projection packet.")
    parser.add_argument("--out", default="", help="output path (default: stdout)")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--stale-days", type=int, default=STALE_DAYS_DEFAULT)
    parser.add_argument(
        "--bake-public",
        action="store_true",
        help="write support/dashboard/public/dashboard-data.json from dashboard_export_packet",
    )
    parser.add_argument(
        "--building-id",
        default="",
        help="if set, emit a single-building delta instead of the full snapshot",
    )
    parser.add_argument(
        "--project-ref",
        default="",
        help="vessel narrowing for --building-id (required when the id exists in 2+ vessels)",
    )
    args = parser.parse_args(argv)
    if args.bake_public:
        observation = bake_dashboard_data_json(
            repo_root=args.repo_root,
            out_path=args.out or None,
            stale_days=args.stale_days,
        )
        print(
            "baked {path} | buildings {buildings} | source_truth {source_truth}".format(
                **observation
            )
        )
        return 0
    if args.building_id:
        packet = dashboard_building_delta(
            args.building_id,
            project_ref=args.project_ref or None,
            repo_root=args.repo_root,
            stale_days=args.stale_days,
        )
        text = json.dumps(packet, ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text + "\n", encoding="utf-8")
            print(f"wrote {args.out} | delta building {packet['building_id']}")
        else:
            print(text)
        return 0
    packet = dashboard_export_packet(repo_root=args.repo_root, stale_days=args.stale_days)
    text = json.dumps(packet, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out} | buildings {packet['summary']['buildings']} | byDisplay {packet['summary']['byDisplay']}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
