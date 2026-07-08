# ⑩d Skills Ship-Copy Drift Map — 0709

Status: support evidence only. This document does not copy, delete, rename,
install, sync, or edit any skill file. It records the current drift between
`brick_protocol/agent/skills/` (Agent-axis operating source) and
`brick_protocol/brick/templates/skills/` (Brick template ship-copy surface) so a
later declared Building can repair drift without guessing. It is not source
truth, success judgment, quality judgment, or Movement authority.

## 0. Scope

This is phase ⑩d from:

```text
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

It follows:

```text
⑩a: project/brick-protocol/status/kernel/cleanup-scope-invariants-0709.md
⑩b: project/brick-protocol/status/kernel/blocks-retained-map-0709.md
```

The goal is to map source vs ship-copy drift before any skill sync, repackaging,
or cleanup. It is intentionally document-only.

## 1. Governing contract

`brick_protocol/brick/templates/skills/APPLY-LIST.md` defines the direction:

```text
agent/skills/ = 운영 정본 (checker pin target)
brick_protocol/brick/templates/skills/ = 선적(ship) 사본
~/.claude/skills/ = live 배포면
방향 고정: agent -> template -> live
```

Important exception already recorded in APPLY-LIST:

```text
building-sizing-method:
  agent 정본 -> template/live 재복사
  template은 pin 호환문구 추가 보유
```

Therefore byte-identity is expected for most copied skills, but not necessarily
for `building-sizing-method` until the checker pin compatibility phrase is
retired through a coordinated checker/doc Building.

## 2. Live measurement snapshot

Measured at live repo HEAD `fc92d736b` before this document:

```text
tracked agent SKILL.md files:      18
tracked template SKILL.md files:    7
tracked template APPLY-LIST files:  1
common skill names:                 7
template-only skills:               0
agent-only skills:                  11
tracked agent .DS_Store residue:    1
```

Common skill set:

```text
brick-task-author
building-coordination
building-sizing-method
make-a-brick
make-a-gate
make-an-agent
task_intake
```

Agent-only skill set:

```text
building-call-authoring
code-analyzer
design-depth-check
evidence-shape-check
evidence-verification
native-dispatch-recording
project-creation
protocol-boundary-watch
scoped-implementation
software-architecture
zero-script-qa
```

Template-only skill set:

```text
none
```

## 3. Common skill byte drift

| Skill | Agent source | Template ship-copy | Status | ⑩d disposition candidate |
|---|---|---|---|---|
| `brick-task-author` | present | present | byte-identical | no action |
| `building-coordination` | present | present | drift | repair candidate: template missing agent-source hold disposition vocabulary reference |
| `building-sizing-method` | present | present | drift | intentional/pinned overlay candidate: template carries checker compatibility phrase; do not blind sync |
| `make-a-brick` | present | present | byte-identical | no action |
| `make-a-gate` | present | present | byte-identical | no action |
| `make-an-agent` | present | present | byte-identical | no action |
| `task_intake` | present | present | byte-identical | no action |

Observed hashes / line counts:

```text
brick-task-author:       equal=True  agent_lines=502 template_lines=502
building-coordination:   equal=False agent_lines=307 template_lines=286
building-sizing-method:  equal=False agent_lines=206 template_lines=208
make-a-brick:            equal=True  agent_lines=105 template_lines=105
make-a-gate:             equal=True  agent_lines=95  template_lines=95
make-an-agent:           equal=True  agent_lines=92  template_lines=92
task_intake:             equal=True  agent_lines=397 template_lines=397
```

## 4. Drift details

### 4.1 `building-coordination` drift

Observed diff shape:

```text
agent source contains an additional "Hold disposition vocabulary reference"
section pointing to:
  project/brick-protocol/status/kernel/hold-disposition-vocabulary-0704.md

template ship-copy lacks that section.
```

Candidate interpretation:

```text
This is likely real ship-copy drift. The APPLY-LIST does not record an exception
for building-coordination. If Smith wants ⑩d implementation, the likely repair is
agent -> template sync for building-coordination only, then checker proof.
```

Why not repair in this document:

```text
This document is a drift map only. Updating a ship-copy skill changes Agent/Brick
projection surfaces and should be done as a declared Building or an explicitly
confirmed direct quick_fix with fast_confirm.
```

### 4.2 `building-sizing-method` drift

Observed diff shape:

```text
template adds the line:
  P3 운영자-facing 기본은 **`build()`만**이다.

template also retains:
  Profile compatibility note: the old phrase "graph packet / materialization /
  official-route 내부 sugar" is retained here only as historical checker text,
  not current operating guidance.
```

Checker/profile evidence:

```text
brick_protocol/support/checkers/profiles/building_skill_preset_builder_composition.yaml
pins the template file to contain:
  graph packet / materialization / official-route 내부 sugar

The same profile separately pins the agent source to contain:
  이 공식 DSL의 부분이고 `compose_building()`은 그 아래 엔진이다
```

Candidate interpretation:

```text
This is not safe for blind agent -> template overwrite. It is an intentional or
at least checker-admitted template overlay for profile compatibility. A later
repair must either preserve the compatibility note or update the profile in the
same declared Building.
```

## 5. Agent-only skills classification

Agent-only does not automatically mean missing ship-copy. The current template
ship-copy corpus is a curated operator/distribution subset, not a mirror of every
Agent skill. Classification candidates:

| Agent-only skill | Current ship-copy classification candidate | Reason |
|---|---|---|
| `building-call-authoring` | maybe-ship | Product-facing order-authoring docs may need a template copy, but current profiles pin only agent source + brick-task-author ship-copy. Needs ⑩e decision. |
| `evidence-verification` | maybe-ship | APPLY-LIST says building-coordination / evidence-verification live sync happened, but repo template copy is absent. Needs source-vs-live-vs-template decision. |
| `protocol-boundary-watch` | maybe-ship | Operational boundary skill; may belong in ship-copy if COO order-chain projection is packaged. Needs ⑩e decision. |
| `project-creation` | maybe-ship | Customer UX layer may need packaged project-creation skill. Decide in ⑩f. |
| `native-dispatch-recording` | agent-only for now | Has helper scripts/profiles; shipping as template copy is not proven. |
| `code-analyzer` | agent-only for now | Performer/tooling skill; no current template contract observed. |
| `design-depth-check` | agent-only for now | Performer/review skill; no current template contract observed. |
| `evidence-shape-check` | agent-only for now | Performer/review skill; no current template contract observed. |
| `scoped-implementation` | agent-only for now | Implementation discipline skill; no current template contract observed. |
| `software-architecture` | agent-only for now | Performer/design skill; no current template contract observed. |
| `zero-script-qa` | agent-only for now | QA skill; no current template contract observed. |

No agent-only skill is approved for copy/delete by this map.

## 6. Tracked residue observation

`git ls-files` shows:

```text
brick_protocol/agent/skills/.DS_Store
```

Candidate interpretation:

```text
This is likely packaging residue under the Agent skill source directory.
Deleting it would be a small cleanup candidate, but it still changes tracked repo
content and should be handled by a declared cleanup Building or explicit direct
quick_fix confirmation. This document does not delete it.
```

## 7. ⑩d disposition summary

```text
byte-identical common ship-copy skills: 5
real drift repair candidate:           building-coordination
checker/pin overlay candidate:         building-sizing-method
agent-only maybe-ship candidates:      building-call-authoring, evidence-verification,
                                       protocol-boundary-watch, project-creation
agent-only keep-as-agent candidates:   native-dispatch-recording, code-analyzer,
                                       design-depth-check, evidence-shape-check,
                                       scoped-implementation, software-architecture,
                                       zero-script-qa
tracked residue candidate:             brick_protocol/agent/skills/.DS_Store
```

Recommended next Building candidate:

```text
⑩d-repair-1:
  - sync building-coordination agent -> template, OR record why template should
    intentionally diverge;
  - decide whether evidence-verification/protocol-boundary-watch/project-creation
    need ship-copy entries before customer UX packaging;
  - do not overwrite building-sizing-method unless the profile compatibility
    pin is updated in the same Building;
  - consider removing tracked .DS_Store only with explicit changed_files proof.
```

## 8. Required proof for any ⑩d repair Building

```text
- changed_files list
- deleted_files or explicit none
- copied/synced skill names
- for each non-identical ship-copy skill: intentional divergence vs repair reason
- checker/profile coverage, at minimum:
  python3 -m compileall -q brick_protocol
  python3 brick_protocol/support/checkers/check_profile.py --profile coo_operating_chain
  python3 brick_protocol/support/checkers/check_profile.py --profile building_skill_preset_builder_composition
  python3 brick_protocol/support/checkers/check_profile.py --profile building_call_menus
  clean detached worktree: python3 brick_protocol/support/checkers/check_profile.py --all
  git diff --check
- GOAL/status update with remaining_delta
```

## 9. Not proven by this ⑩d map

```text
- No skill drift has been repaired.
- No ship-copy corpus membership has been changed.
- No live installed skill surface has been inspected.
- No .DS_Store removal has been approved or performed.
- No customer UX packaging decision has been made.
```
