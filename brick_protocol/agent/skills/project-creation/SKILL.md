---
name: project-creation
description: Use when declaring a new project vessel — a conversation fills the charter slots, the human confirms the charter, then the machine stamps the declaration via the project creation verb.
---

A project is a vessel (그릇) buildings accumulate in — not a Brick, not an
Agent, not a Link. Declaring one is a two-step act in a FIXED order:

```text
1. CHARTER FIRST  — 사람이 대화로 헌장(README.md) 내용을 확정한다.
2. STAMP SECOND   — 기계가 확정된 헌장에서 선언(project.json)을 추출·박제한다.
```

Never stamp before the human has confirmed the charter content. Never create
the vessel folder by hand — a hand-made `project/<id>/` without charter +
declaration is RED (`project_declaration` kernel check, core profile).

## Step 1 — fill the charter slots (questions only)

Ask ONLY what fills a charter slot. The questions exist to fill the slots,
nothing else — no writing-craft prescription, no "how to write a good
charter" advice (ChatPRD memo 0610, Memo 3: quality control lives in
downstream verification, not in up-front prescription).

```text
목적 (왜 존재하는가)        -> why_exists
생성 이유 (왜 지금)          -> why_now
방향성 (어디로, 한 문장)     -> direction
완료·진척의 기준             -> done_means
범위 밖 (안 하는 것)         -> out_of_scope
관리자 (사람 이름만)         -> managers
```

Also settle the two identity facts:

```text
project_id  -> [-_a-z0-9] slug (폴더 이름이 된다: project/<id>/)
label       -> 사람이 읽는 프로젝트 이름
```

Managers are HUMAN owners only. Agents are never listed — agents change, and
who worked is projected from AgentBinding evidence, not declared in a
charter. If the human names an agent, record the human owner instead.

Record answers as given. Do not grade, rewrite for quality, or demand more
detail than the human chose to give.

## Step 2 — human confirms the charter

Show the assembled slot contents back as the charter the human is about to
declare. The human's confirmation is the gate. Only after an explicit
confirmation does the machine stamp anything.

## Step 3 — machine stamping (the creation verb)

Call the creation verb — exactly this function:

```text
brick_protocol/support/operator/project_creation.py::create_project(
    repo_root, *,
    project_id, label, direction,
    why_exists, why_now, done_means, out_of_scope,
    managers, declared_by, declared_at=None,
)
```

```bash
PYTHONPATH="brick_protocol/support/import_identity:." python3 -c "
from brick_protocol.support.operator.project_creation import create_project
import json
record = create_project(
    '.',
    project_id='<id>',
    label='<label>',
    direction='<direction>',
    why_exists='<why_exists>',
    why_now='<why_now>',
    done_means='<done_means>',
    out_of_scope='<out_of_scope>',
    managers=['<human name>'],
    declared_by='<human name>',
)
print(json.dumps(record, ensure_ascii=False, indent=2))
"
```

The verb writes, in order: `project/<id>/README.md` (charter first),
`project/<id>/project.json` (the charter's shadow), then the empty skeleton
dirs `buildings/`, `status/`, `_portfolio-projections/`. It does NOT create
PROGRESS.md (machine-generated later from building evidence) and adds no
placeholder files.

The verb REFUSES, fail-closed (a rejected vessel is removed, nothing
half-declared survives):

```text
- duplicate project id    (project/<id>/ already exists)
- non-slug project id     (refused before any filesystem write)
- empty direction         (declaration loader speaks)
- agent-looking managers  (declaration loader speaks)
```

Relay a refusal verbatim to the human and return to Step 1; do not work
around it.

## Boundaries

This skill records direction facts only. It does not judge success or
quality, does not choose Movement, and the creation record is support
evidence — not source truth. After the vessel exists, work enters it through
task intake (the project check happens BEFORE a task: 어느 프로젝트의
일인가, 그릇이 없으면 먼저 이 스킬로 선언한다).

## Vessel lifecycle (create → progress → export)

After creation, the vessel's whole life runs on machine verbs — never
hand-edit the projections:

- **progress** —
  `support.operator.progress_projection.generate_project_progress("project:<id>")`
  writes `project/<id>/PROGRESS.md` from building evidence (TRUTH layer only;
  machine-generated, 손으로 고치지 않는다).
- **export** —
  `support.operator.dashboard_export.dashboard_export_packet()` projects
  EVERY declared vessel into the dashboard-readable export (read-only
  projection; per-building deltas via `dashboard_building_delta`).
