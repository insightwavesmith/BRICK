"""PROJECT-0 S4-C: per-vessel PROGRESS.md machine projection (TRUTH layer only).

``project/<id>/PROGRESS.md`` is the charter's "어디까지 왔나" companion: a
MACHINE-ONLY projection from already-written Building evidence. This module
renders and writes it. Facts only:

  * Building counts by observed board_state / frontier_kind,
  * the latest Buildings by recorded evidence timestamp (ids + dates),
  * the vessel's declared direction echoed as header context
    (project.json — the declared parent-goal slot, design §1).

NO judgment vocabulary is produced (no success/quality/done-ness opinion —
those words appear below only as NEGATIONS of what this file is), and NO
human prose slot exists here: humans append judgment elsewhere
(TRUTH-before-QUALITY). The body carries NO wallclock timestamp, so
regeneration over unchanged evidence is byte-identical (idempotent).

The file is OPTIONAL output, generated on demand by the verb below — the
project declaration checker never requires it.

Support evidence only: the written file and returned record prove a
projection was rendered from current evidence. NOT source truth, NOT success
judgment, NOT quality judgment, NOT Movement authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.building_operation_common import REPO_ROOT
from brick_protocol.support.operator.ledger_projection import (
    project_orchestration_ledger_packet,
)
from brick_protocol.support.operator.project_declaration import load_project_declaration
from brick_protocol.support.recording.capture import (
    buildings_root_for,
    project_ref_for_building_root,
)

PROGRESS_FILENAME = "PROGRESS.md"

# Stamped first line: the no-hand-edit contract of a machine projection.
PROGRESS_MACHINE_HEADER = (
    "<!-- machine-generated: brick_protocol/support/operator/progress_projection.py — "
    "do not hand-edit. 빌딩 증거에서 기계가 다시 생성한다 "
    "(generate_project_progress). 같은 증거면 같은 바이트(본문에 생성시각 없음). -->"
)

LATEST_BUILDINGS_LIMIT = 10


def render_project_progress(
    project_ref: str,
    *,
    repo_root: Path | str = REPO_ROOT,
) -> str:
    """Render one vessel's PROGRESS.md body (deterministic, facts only).

    The vessel must be a declared project (the S1 loader speaks on rejection).
    Rows come from the multi-vessel orchestration-ledger packet filtered to
    this vessel — membership stays the Building root's path fact. The body
    carries no wallclock, so unchanged evidence renders byte-identical.
    """

    repo = Path(repo_root).resolve()
    # Form fail-close THROUGH the seam, then the S1 loader (single validator).
    vessel_dir_name = buildings_root_for(project_ref).parent.name
    declaration = load_project_declaration(repo, vessel_dir_name)

    packet = project_orchestration_ledger_packet(repo_root=repo)
    rows = [
        row
        for row in packet.get("rows", [])
        if isinstance(row, Mapping) and row.get("project_ref") == declaration.project_ref
    ]

    board_counts: dict[str, int] = {}
    frontier_counts: dict[str, int] = {}
    for row in rows:
        board = str(row.get("board_state") or "unknown")
        frontier = str(row.get("frontier_kind") or "unknown")
        board_counts[board] = board_counts.get(board, 0) + 1
        frontier_counts[frontier] = frontier_counts.get(frontier, 0) + 1

    dated_rows = [row for row in rows if row.get("last_evidence_at")]
    dated_rows.sort(
        key=lambda row: (str(row.get("last_evidence_at")), str(row.get("building_id"))),
        reverse=True,
    )
    undated_count = len(rows) - len(dated_rows)

    lines: list[str] = []
    lines.append(PROGRESS_MACHINE_HEADER)
    lines.append("")
    lines.append(f"# {declaration.label} — PROGRESS (기계 투영)")
    lines.append("")
    lines.append(
        "이 파일은 buildings/ 의 빌딩 증거에서 기계가 생성한 사실 투영이다. "
        "성공/품질/완성도 판단은 여기 없다 — 판단은 사람이 다른 곳에 따로 적는다"
        " (TRUTH-before-QUALITY)."
    )
    lines.append("")
    lines.append("## 방향성 (선언 echo — project.json direction)")
    lines.append("")
    lines.append(declaration.direction)
    lines.append("")
    lines.append(f"## 빌딩 집계 — 총 {len(rows)}개")
    lines.append("")
    lines.append("board_state 기준:")
    if board_counts:
        for board_state in sorted(board_counts):
            lines.append(f"- {board_state}: {board_counts[board_state]}")
    else:
        lines.append("- (빌딩 없음)")
    lines.append("")
    lines.append("frontier_kind 기준:")
    if frontier_counts:
        for frontier_kind in sorted(frontier_counts):
            lines.append(f"- {frontier_kind}: {frontier_counts[frontier_kind]}")
    else:
        lines.append("- (빌딩 없음)")
    lines.append("")
    lines.append(
        f"## 최근 증거 빌딩 (last_evidence_at 상위 {LATEST_BUILDINGS_LIMIT})"
    )
    lines.append("")
    if dated_rows:
        for row in dated_rows[:LATEST_BUILDINGS_LIMIT]:
            lines.append(
                f"- {row.get('building_id')} — {row.get('last_evidence_at')}"
                f" — {row.get('board_state')}"
            )
    else:
        lines.append("- (기록된 Link 증거 타임스탬프가 있는 빌딩 없음)")
    if undated_count:
        lines.append(
            f"- (타임스탬프 없는 빌딩 {undated_count}개는 이 목록에서 제외 —"
            " 집계에는 포함)"
        )
    lines.append("")
    lines.append("## 이 파일이 증명하지 않는 것")
    lines.append("")
    lines.append("- 빌딩 작업의 의미적 올바름 (개수·상태는 frontier 관측 사실일 뿐)")
    lines.append("- 프로세스 생존 여부 (last_evidence_at 은 기록된 증거 시각이지 심장박동이 아님)")
    lines.append("- source truth 아님 / Movement 권한 없음 / 성공·품질 판단 없음")
    lines.append("")
    return "\n".join(lines)


def generate_project_progress(
    project_ref: str,
    *,
    repo_root: Path | str = REPO_ROOT,
) -> dict[str, Any]:
    """Write ``project/<id>/PROGRESS.md`` from current Building evidence.

    Returns a facts-only generation record. Idempotent: unchanged evidence
    yields a byte-identical file (``changed`` records whether bytes moved).
    """

    repo = Path(repo_root).resolve()
    text = render_project_progress(project_ref, repo_root=repo)
    vessel_dir_name = buildings_root_for(project_ref).parent.name
    progress_path = repo / "project" / vessel_dir_name / PROGRESS_FILENAME
    previous = (
        progress_path.read_text(encoding="utf-8") if progress_path.is_file() else None
    )
    progress_path.write_text(text, encoding="utf-8")
    return {
        "kind": "project-progress-projection-record",
        "schema_version": "project-progress-projection-0",
        "project_ref": project_ref,
        "progress_path": f"project/{vessel_dir_name}/{PROGRESS_FILENAME}",
        "byte_count": len(text.encode("utf-8")),
        "changed": previous != text,
        "proof_limits": [
            "machine projection over already-written Building evidence only",
            "facts only: counts/ids/recorded timestamps + declared direction echo",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic correctness of the projected Building work",
            "that any provider process is currently alive",
        ],
    }


def refresh_project_progress_for_building_event(
    *,
    building_root: Path | str,
    event_kind: str,
    repo_root: Path | str = REPO_ROOT,
    last_completed_step_ref: str = "",
) -> dict[str, Any]:
    """Refresh a vessel PROGRESS.md after a walker step event.

    The trigger is support projection only. The building root path determines
    the project through the capture inverse seam; non-project/legacy roots are
    skipped so temp and historical walks keep their old behavior.
    """

    repo = Path(repo_root).resolve()
    root = Path(building_root)
    project_ref = project_ref_for_building_root(root, repo_root=repo)
    base: dict[str, Any] = {
        "kind": "project-progress-refresh-observation",
        "schema_version": "project-progress-refresh-0",
        "event_kind": event_kind,
        "last_completed_step_ref": last_completed_step_ref,
        "source_truth": False,
        "proof_limits": [
            "support projection refresh observation only",
            "triggered after already-written walker step evidence",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic correctness of the projected Building work",
            "that any provider process is currently alive",
        ],
    }
    if project_ref is None:
        return {
            **base,
            "progress_refresh_observation": "skipped_non_project_building_root",
            "changed": False,
        }
    try:
        generation = generate_project_progress(project_ref, repo_root=repo)
    except Exception as exc:  # noqa: BLE001 - refresh must not break the walker.
        return {
            **base,
            "progress_refresh_observation": "refresh_exception_observed",
            "project_ref": project_ref,
            "changed": False,
            "delivery_status_class": "exception_observed",
            "provider_response_status_class": exc.__class__.__name__,
            "reason": str(exc),
            "not_proven": [
                *base["not_proven"],
                "project progress projection refreshed for this event",
            ],
        }
    return {
        **base,
        "progress_refresh_observation": "project_progress_refreshed",
        "project_ref": project_ref,
        "progress_path": generation.get("progress_path", ""),
        "byte_count": generation.get("byte_count", 0),
        "changed": bool(generation.get("changed")),
    }


__all__ = [
    "LATEST_BUILDINGS_LIMIT",
    "PROGRESS_FILENAME",
    "PROGRESS_MACHINE_HEADER",
    "generate_project_progress",
    "refresh_project_progress_for_building_event",
    "render_project_progress",
]
