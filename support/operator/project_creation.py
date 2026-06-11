"""PROJECT-0 S2-A: project creation verb (charter-first 기계 박제).

A project is a vessel (그릇), not an axis. This verb materializes ONE new
vessel the same way project #1 is shaped, in the binding order the design
fixed (project-0-design-0611 §2 step 0):

  1. CHARTER FIRST — ``project/<id>/README.md`` rendered from the filled
     charter slots (목적 / 생성 이유 / 방향성 / 완료·진척의 기준 / 범위 밖 /
     관리자 / 어디까지 왔나 / 처음 온 사람은). The charter is the human
     document; the human has already confirmed its content in conversation
     (the project-creation skill) BEFORE this verb is called.
  2. SHADOW SECOND — ``project/<id>/project.json``, the machine declaration
     extracted from the same slots (brick.md+return.yaml ≅
     README.md+project.json).
  3. SKELETON — the vessel dirs ``buildings/``, ``status/``,
     ``_portfolio-projections/`` (empty dirs only; NO placeholder files —
     the admission gate rejects stray files, empty dirs are admitted as dirs).

Validation is fail-closed and SINGLE-SOURCED: after writing, the verb
round-trips the result through ``load_project_declaration`` (the S1 loader —
the SAME validator the project_declaration kernel check drives). If the
loader rejects (empty direction, agent-looking managers, judgment key, bad
timestamp, ...), the verb REMOVES the vessel it created and re-raises the
loader's own rejection — the loader speaks, the verb does not restate its
rules. Only two rules are the verb's own, because the loader cannot see them:

  * duplicate project id — the vessel path already exists (a vessel is
    declared once; the loader REQUIRES existence, creation requires absence);
  * non-slug id — refused BEFORE any filesystem touch via the loader's
    exported predicate (``is_admissible_project_id``), so a traversal-shaped
    id never becomes a mkdir.

The verb performs NO judgment: it records direction facts only. It does not
create PROGRESS.md (machine-generated on demand from building evidence by
support/operator/progress_projection.py — S4) and it never lists agents as
managers (who worked is AgentBinding evidence).

Support evidence only: the returned record proves the vessel was written and
round-tripped the declaration loader. It is NOT source truth, NOT success
judgment, NOT quality judgment, and NOT Movement authority. It cannot prove
the charter text is truthful nor that manager strings name real humans.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.project_declaration import (
    PROJECT_CHARTER_FILENAME,
    PROJECT_DECLARATION_FILENAME,
    PROJECT_REF_PREFIX,
    ProjectDeclaration,
    is_admissible_project_id,
    load_project_declaration,
)

# Vessel skeleton (project-0-design-0611 §1): empty dirs only, no placeholder
# files — package_path_admission admits these as dirs and rejects stray files.
PROJECT_SKELETON_DIRS = ("buildings", "status", "_portfolio-projections")

# Charter slots that live ONLY in the charter (the loader cannot validate
# them because they are not project.json keys). The verb owns their
# non-emptiness: a charter section with no text is a silent vessel.
_CHARTER_ONLY_SLOTS = ("why_exists", "why_now")


def _reject(project_id: str, reason: str) -> ValueError:
    return ValueError(f"project creation rejected (project/{project_id}): {reason}")


def _render_charter(
    *,
    project_id: str,
    label: str,
    why_exists: str,
    why_now: str,
    direction: str,
    done_means: str,
    out_of_scope: str,
    managers: list[str],
) -> str:
    """Render the charter mirroring project #1's section structure, generically."""

    manager_lines = "\n".join(f"- {entry}" for entry in managers)
    return f"""# {label} — 프로젝트 헌장

이 문서는 이 동네(project/{project_id}/)의 헌장이다. 여기서 일하는 모든 사람과
에이전트가 먼저 읽는다. 기계 선언은 project.json(이 헌장의 그림자)에 있다.

## 목적 (왜 존재하는가)

{why_exists}

## 생성 이유 (왜 지금)

{why_now}

## 방향성 (어디로)

{direction}

## 완료·진척의 기준

{done_means}

## 범위 밖 (안 하는 것)

{out_of_scope}

## 관리자

{manager_lines}

(사람 owner만 기록한다. 에이전트는 계속 바뀌므로 헌장에 적지 않는다 —
누가 일했나는 AgentBinding 증거가 투영한다.)

## 어디까지 왔나

PROGRESS.md 참조 — 기계가 빌딩 증거로부터 생성하는 사실 투영이다(생성 전이면
아직 없음). buildings/의 증거가 원본 사실 기록이다.

## 처음 온 사람은

1. 이 헌장을 먼저 읽는다.
2. 저장소 루트의 AGENTS.md — 이 동네에서 일하는 규칙.
3. project.json — 이 헌장의 기계 선언(그림자).
4. buildings/ — 모든 작업의 증거가 쌓이는 곳. 빌딩 하나가 작업 하나다.
"""


def create_project(
    repo_root: Path | str,
    *,
    project_id: str,
    label: str,
    direction: str,
    why_exists: str,
    why_now: str,
    done_means: str,
    out_of_scope: str,
    managers: list[str],
    declared_by: str,
    declared_at: str | None = None,
) -> dict[str, Any]:
    """Create ONE project vessel: charter first, shadow declaration, skeleton.

    Fail-closed: the written vessel must round-trip ``load_project_declaration``
    (the S1 single-source validator); on rejection the vessel is removed and
    the loader's rejection is re-raised. Returns a facts-only creation record
    built FROM the loaded declaration (not from the inputs).
    """

    repo = Path(repo_root).resolve()

    # The verb's own two rules (the loader cannot see them) — everything else
    # is the loader's voice via the round-trip below.
    if not is_admissible_project_id(project_id):
        raise _reject(
            project_id,
            "project id must be a non-empty [-_a-z0-9] slug (the same rule the "
            "declaration loader enforces; refused before any filesystem write)",
        )
    vessel = repo / "project" / project_id
    if vessel.exists():
        raise _reject(
            project_id,
            f"project/{project_id}/ already exists — duplicate project id; a "
            "vessel is declared once (declare a new id instead of re-declaring "
            "an existing vessel)",
        )
    for slot_name, slot_value in (("why_exists", why_exists), ("why_now", why_now)):
        if not isinstance(slot_value, str) or not slot_value.strip():
            raise _reject(
                project_id,
                f"charter slot {slot_name} must be a non-empty string — these "
                "slots live only in the charter, so the verb (not the loader) "
                "refuses their absence",
            )

    # PROJECT-0 S5-FIX: every charter slot and every managers entry must be a
    # str BEFORE any filesystem write. A non-str value used to survive past
    # mkdir and explode inside json.dumps with a TypeError the rollback did
    # not catch (operator reproduced: managers=['smith', object()] left a
    # partial vessel on disk). Loud TypeError naming the slot, fail-closed,
    # zero filesystem footprint.
    for slot_name, slot_value in (
        ("label", label),
        ("direction", direction),
        ("done_means", done_means),
        ("out_of_scope", out_of_scope),
        ("declared_by", declared_by),
    ):
        if not isinstance(slot_value, str):
            raise TypeError(
                f"project creation rejected (project/{project_id}): charter slot "
                f"{slot_name} must be str, got {type(slot_value).__name__} — "
                "refused before any filesystem write"
            )
    if declared_at is not None and not isinstance(declared_at, str):
        raise TypeError(
            f"project creation rejected (project/{project_id}): declared_at "
            f"must be str or None, got {type(declared_at).__name__} — "
            "refused before any filesystem write"
        )
    if not isinstance(managers, (list, tuple)):
        raise TypeError(
            f"project creation rejected (project/{project_id}): managers must "
            f"be a list of str, got {type(managers).__name__} — "
            "refused before any filesystem write"
        )
    for index, entry in enumerate(managers):
        if not isinstance(entry, str):
            raise TypeError(
                f"project creation rejected (project/{project_id}): managers[{index}] "
                f"must be str (human owner name), got {type(entry).__name__} — "
                "refused before any filesystem write"
            )

    if declared_at is None:
        declared_at = datetime.now().astimezone().isoformat(timespec="seconds")

    manager_entries = list(managers)

    vessel.mkdir(parents=True)
    try:
        # 1. CHARTER FIRST — the human document.
        charter_text = _render_charter(
            project_id=project_id,
            label=str(label),
            why_exists=why_exists.strip(),
            why_now=why_now.strip(),
            direction=str(direction),
            done_means=str(done_means),
            out_of_scope=str(out_of_scope),
            managers=manager_entries,
        )
        (vessel / PROJECT_CHARTER_FILENAME).write_text(charter_text, encoding="utf-8")

        # 2. SHADOW SECOND — the machine declaration extracted from the slots.
        declaration_record = {
            "project_ref": f"{PROJECT_REF_PREFIX}{project_id}",
            "label": label,
            "direction": direction,
            "done_means": done_means,
            "out_of_scope": out_of_scope,
            "managers": manager_entries,
            "declared_by": declared_by,
            "declared_at": declared_at,
            "charter_ref": f"project/{project_id}/{PROJECT_CHARTER_FILENAME}",
        }
        (vessel / PROJECT_DECLARATION_FILENAME).write_text(
            json.dumps(declaration_record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        # 3. SKELETON — empty vessel dirs only (no placeholder files).
        for skeleton_name in PROJECT_SKELETON_DIRS:
            (vessel / skeleton_name).mkdir()

        # 4. FAIL-CLOSED ROUND-TRIP — the S1 loader is the single validator;
        #    its rejection removes the vessel and speaks verbatim.
        loaded: ProjectDeclaration = load_project_declaration(repo, project_id)
    except Exception:
        # PROJECT-0 S5-FIX: rollback on ANY failure after mkdir (was
        # ValueError/OSError only — a TypeError from json.dumps left a partial
        # vessel on disk). Cleanup, then re-raise unchanged.
        shutil.rmtree(vessel, ignore_errors=True)
        raise

    return {
        "kind": "project-creation-record",
        "schema_version": "project-creation-0",
        "project_ref": loaded.project_ref,
        "project_dir": f"project/{project_id}",
        "charter_path": loaded.charter_ref,
        "declaration_path": f"project/{project_id}/{PROJECT_DECLARATION_FILENAME}",
        "skeleton_dirs": [
            f"project/{project_id}/{skeleton_name}"
            for skeleton_name in PROJECT_SKELETON_DIRS
        ],
        "declaration": {
            "project_ref": loaded.project_ref,
            "label": loaded.label,
            "direction": loaded.direction,
            "done_means": loaded.done_means,
            "out_of_scope": loaded.out_of_scope,
            "managers": list(loaded.managers),
            "declared_by": loaded.declared_by,
            "declared_at": loaded.declared_at,
            "charter_ref": loaded.charter_ref,
        },
        "proof_limits": [
            "creation record proves the vessel was written and round-tripped "
            "load_project_declaration only",
            "not source truth, not success judgment, not quality judgment, "
            "not Movement authority",
        ],
        "not_proven": [
            "that manager strings name real humans",
            "that the charter text is truthful or current",
        ],
    }


__all__ = [
    "PROJECT_SKELETON_DIRS",
    "create_project",
]
