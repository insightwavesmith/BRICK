# Brick Protocol Current Working Context

Date: 2026-06-11 (was 2026-06-10 / 2026-06-01 / 2026-05-27; refreshed for the 0611 PROJECT-0 / B4-REPAIR / checker-split-map landing)

This file is the operator-facing current view. Historical overlays were pruned
by CURRENT-CONTEXT-PRUNE-0; the detailed records remain in AGENTS.md,
`support/docs/spec/`, `project/brick-protocol/status/kernel/*support-record*`,
and `project/brick-protocol/buildings/`.

## CURRENT ANCHOR (0611) — PROJECT VESSELS + REPO-SPLIT PREP

- **PROJECT-0 landed (origin/main `a000db0`):** the project vessel is a declared concept, not a hardcoded path. `project/<id>/` = README.md charter (사람 헌장) + `project.json` declaration (기계 선언; direction/done_means/out_of_scope/managers); a vessel without charter or declaration is checker-RED (declaration law, S1 `cf06e7b`); project creation is a verb + COO `project-creation` skill, charter first (S2 `ece882b`); intake carries `project_ref` so a Building's evidence lands in its declared vessel (S3 `a199d1d`); the ledger/dashboard see every vessel and each vessel carries a machine-written PROGRESS.md (S4 `7929e5c`); codex + fresh-clone audit findings closed operator-reproduced (S5-FIX `a000db0`). `project/brick-protocol/` is frozen as vessel #1 (no migration). Design record: `project-0-design-0611.md`.
- **B4-REPAIR (`5b5a7b4`):** the hook close seam is repaired — hook-made child Buildings now close AND sit green in the tree; intake records `composition_mode` on the linear path too (graph parity, `af2e398`).
- **Checker split map (`60998fc`):** `checker-split-map-0611.md` classifies all 93 profile rules PRODUCT-LAW / MIXED / DOGFOOD-HISTORY / DEV-PROCESS as the REPO-SPLIT pre-audit; classification only — checker behavior unchanged, execution deferred to the REPO-SPLIT build.
- **Validation baseline unchanged:** `check_profile.py --all` => EXIT 0, 13 profiles (canonical command as in the 0610 anchor below).
- **Now:** CLEANUP round (잔잔바리 doc/wiring residues), then REPO-SPLIT per the split map.

## CURRENT ANCHOR (0610) — CONSOLIDATED OPERATING BASELINE

> SUPERSEDED-BY-0611: kept for continuity (the operating laws below — leader
> write law, no-silent-write-grant, observed-write parity, F-AGENT, dashboard
> delta, U5.5 — remain active; the "current state" framing is now the 0611
> anchor above).
- **Validation baseline NOW: `check_profile.py --all` => EXIT 0, 13 profiles** (post PASS-2 consolidation; agent-axis-behavioral alone carries 270 declarative observations). Canonical command unchanged: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all`. Supersedes the 45-profile count in the 0601 anchor below.
- **Leader write law:** the four team leads (cto-lead, design-lead, pm-lead, qa-lead) carry `tool-policy:read-write-scoped`; the COO stays read-only (Smith ruling 0610: the Movement/judgment authority carries no write tools); the Builder matches writers by CAPABILITY >= NEED (not equality); effective write = Brick-declared write_scope NEED ∧ Agent tool policy ∧ observed-write adapter capability; the physical native projection (Edit/Write tools) is NEED-gated, never lane-granted.
- **No-silent-write-grant:** `requires_brick_write_scope: true` is enforced STRICTLY at `run_building_plan` (walker + resume) and `run_building_once` — a write-capable agent on a Brick with no declared write_scope NEED is a hard reject, not a quiet grant.
- **Claude observed-write parity:** the canonical observed-write adapter set is `agent_adapter._OBSERVED_WRITE_ADAPTER_REFS` = {adapter:codex-local, adapter:claude-local}; gates and rendered packets derive from that set / `adapter_is_write_capable` (no codex-only literal).
- **F-AGENT operating model** is active and its per-LLM projections (codex-native TOML + claude-native subagent .md) are regenerated from the Agent Objects and gated by the codex_projection_native / claude_projection_native kernel checks.
- **Dashboard is EVENT-DELTA:** seed + delta sinks with a close-hook publish (report-sink:dashboard inside the four-sink report_sinks ceiling).
- **U5.5 Evidence Spine COMPLETE** (through slice-3+; enforced by the evidence_spine + evidence_spine_projection checkers).

## CURRENT ANCHOR (0601) — ELEGANT REFACTOR + AUTOMATION (branch codex/elegant-refactor-0531)

> SUPERSEDED-BY-0610: kept for continuity (profile counts and branch state
> below describe the 0601 baseline; the operative anchor is CURRENT ANCHOR
> (0610) above).
- **Validation baseline NOW: `check_profile.py --all` => EXIT 0, 45 profiles.** Canonical command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all`. Supersedes the older 37/40/42/43/44 baselines recorded further down (each was correct at its time).
- **Done + gated by operator own-execution + FIRE:** 4 god-modules decomposed to thin facades + single-concern modules (check_profile→lib/, evidence_assembly→recording/, dynamic_walker→walker_*, building_operation→10 modules); elegance guard G1–G6 (crossing_registry + module_registry); BUILDING-DECLARATION-INTEGRITY checker; declared-plan purity (FQ-2); Tier-A deterministic 3-axis conformance; Tier-B real-codex e2e; Tier-C real-codex 5/5 repeat + 2/2 portfolio; N=20 reliability 20/20 + live gate-adopted reroute 20/20.
- **Four codex reviews closed:** review-1 (FQ-1..6) + review-2 (F1..F7) + review-3 (3× P2) + review-4 (preflight Movement membership + G6 wording). Notes: F2 = base-freeze NOT violated, but the current facade's import-star surface was inconsistent and is now aligned; F4 G6 = a self-consistency ceiling, NOT a one-way ratchet (decision C, wording cleaned across registry/checker/profile); F7 per-step OS-process identity = blueprint-level NOT-PROVEN (decision B); review-4 added active Link-Movement membership enforcement in declared-plan preflight (was a false-green).
- **Standing NOT-PROVEN (honest):** real-provider reliability beyond N=20; live budget-exhaustion HOLD/pause + resume over a real provider; other providers (claude/gemini); per-step OS-process identity in returned evidence; production runtime.
- Design anchors: `…engine-blueprint-0531.md` (§2.1 declaration-integrity, §3.1 reporter bus, §7 guard) + `…elegant-refactor-detail-design-0531.md`.

## Current Goal

Active goal (0611):

```text
CLEANUP round (잔잔바리 doc/wiring residues) ahead of REPO-SPLIT
- stale-doc refresh + deferred small wiring only; engine untouched
- then REPO-SPLIT per status/kernel/checker-split-map-0611.md
```

Historical goal ledger below (0527–0529 era; kept verbatim, append-only):

Active goal opened in this thread:

```text
1. BAR-V2-REAL-TASK-DOGFOOD-1 commit baseline: done
2. CURRENT-CONTEXT-PRUNE-0: done
3. PROJECTION-FRESHNESS-OBSERVATION-0: done
4. TASK INTAKE RETURNED DOGFOOD 1: done
5. REAL-ROUTE-REPAIR-DOGFOOD-1: done
```

Historical BAR-v2 parent reference retained for profile continuity:

```text
goal:bar-v2-active-sequence
```

Current cleanup goal:

```text
AXIS-RECOLLAPSE-MASS-DELETE-0: done
```

Current stale-plan alignment goal:

```text
STALE-PLAN-CLASSIFICATION-0 (Phase 3): done as classification-only support evidence
```

Current active/reusable Building Plan rebase criterion:

```text
BUILDING-RUN-SURFACE-ALIGNMENT-0 rebased only plans that are active control
or reusable dogfood surfaces in the current 0527/0528 automation chain:
COO operating chain, taskshape/design contract, intake returned dogfood,
projection freshness, agent projection sync, BAR-v2 end-to-end/current work,
Link decision disposition, and Building automation complete Scope C.

Historical route-request milestone plans, older closed compact phase plans,
and 0524 open-phase plan artifacts were not mechanically rebased.
They remain historical support evidence or delete candidates until a later
declared Building admits a narrower cleanup Movement.
```

Phase 3 classification evidence (no deletion performed):

```text
link-route-replay-0-claude-qa-open.yaml
  - delete candidate only
  - evidence: 0524 open-phase plan; link-route-replay-0 support record carries this open run in historical building-sequence evidence and records dogfood closure at project/brick-protocol/buildings/link-route-replay-0-dogfood-0524/

link-route-replay-0-codex-qa-open.yaml
  - delete candidate only
  - evidence: 0524 open-phase plan; same support record sequence and dogfood closure evidence

link-route-replay-0-development-open.yaml
  - delete candidate only
  - evidence: 0524 open-phase implementation-open plan; later development-repair + QA sequence is recorded as completed support evidence with dogfood closure

link-route-replay-0-development-repair-open.yaml
  - delete candidate only
  - evidence: 0524 open-phase repair plan; repair outcome is already recorded in historical support record/report chain

session-continuity-0-design-repair-open.yaml
  - delete candidate only
  - evidence: 0524 open-phase design-repair plan; session-continuity-0 support record carries this as historical building evidence in a completed sequence

session-continuity-0-development-open.yaml
  - delete candidate only
  - evidence: 0524 open-phase development plan; later development-repair and QA returns are already recorded as historical support evidence

session-continuity-0-development-repair-open.yaml
  - delete candidate only
  - evidence: 0524 open-phase repair plan; session-continuity-0 support record carries repaired sequence and QA evidence
```

Deletion boundary:

```text
All seven files are classified as delete candidates only.
No deletion is performed in this phase.
Any deletion requires later Link/COO Movement through a declared follow-up Building.
```

The issue being repaired is module proliferation from BAR-v2 helper evidence:
case, dogfood, validation, route template, route binding, and generated
candidate files were stored under `brick/` and `link/` as if they were durable
axis modules. The selected repair is mass deletion with capability preserved in
existing homes: Brick work contracts / Building Plans / required_return_shape,
Agent returned evidence, Link `route_policies/*.yaml`, inline
`route_replay_plan`, support checker profiles, support specs, and project
evidence roots.

COO operates as boundary watcher and Building coordinator. COO may declare the
active shape / plan when delegated, but task sources, Agents, MCP, toolkit, and
support helpers do not choose Movement or route targets.

Building-default remains the operating mode. Subagent work inside a Building is
an Agent step; ad-hoc work outside a Building uses the development worktree
convention only as support isolation.

The deferred Smith review queue is empty for this follow-up as of the current
observation. Routine review did not stop the active goal.

Current Building automation completion goal:

```text
BUILDING-AUTOMATION-COMPLETE-0: done within declared Building boundaries
active proof: building-automation-complete-0-scope-c-dogfood-0527
```

This goal closes the current interview/task -> declared plan -> run -> QA
transition_concern_evidence -> Link decision packet -> repeated declared
boundary attempt-N -> max_attempts guard -> closure proof target.
`max_attempts` is Link-owned
carry inside `route_replay_plan`, declared by caller / COO at Building Plan
opening time. It is not top-level Building Plan state, support retry state, or
Agent judgment.

Current Link disposition goal:

```text
LINK-DECISION-DISPOSITION-0: done
closed order: transition concern return -> Link disposition -> frontier observation
```

This goal renames active Agent-facing repair/transition concern output from
`route_request_evidence` to `transition_concern_evidence`, keeps historical
`route-request.json` evidence readable, admits optional Link row
`route_decision_basis` and `transition_lifecycle`, and adds support-only
frontier observation. Dogfood evidence covers adopted concern reroute,
not-adopted concern forward, human override reroute, resumed transition
lifecycle evidence, and static frontier observation. Movement remains
`forward` / `reroute`; `hold` is not Movement.

Current Link-owned automation goal:

```text
LINK-OWNED-AUTOMATION-0: done
active rule: Agent concern / Brick work contract / Link gate+policy disposition / support walking+recording
```

This goal keeps full automation in scope while assigning the automatic
decision to Link-owned declared policy rather than support runtime judgment.
Compact authoring such as `link: strict+human -> dev` is only an authoring
input; it expands to an ordinary Link row with `movement: forward`,
`target_ref`, and `declared_gate_refs`. Reroute automation still requires
transition concern evidence, a Link-owned route policy mapping, caller / COO
authored `route_replay_plan`, and Link-owned `max_attempts`.
Dogfood evidence covers compact authoring, declared gate sufficiency,
non-binding transition concern evidence, Link-authored reroute basis, repeated
declared dev/qa boundaries, and closure. Delegated Opus and Gemini 3.5 reviews
returned PASS_WITH_MINOR with accepted wording/profile refinements.

Current Agent harness goal:

```text
LEGACY-AGENT-HARNESS-IMPORT-0: in progress
active order: system -> object -> template
current slice: LEGACY-AGENT-HARNESS-SYSTEM-0: done
```

This goal imports the useful legacy Agent harness intent without copying legacy
runtime ownership. The system slice closes lane vocabulary, dynamic Agent
Object resolution, leader-no-code guardrail intent (hook renamed 0610 to
hook:leader-write-need-gate), write authority
composition, adapter / brain connector policy, and delegation contract. The
object slice admits pm-lead, design-lead, cto-lead, qa-lead, and inspector
only after the system boundary is active. The template slice uses existing
Brick shape registry step templates as Brick word / Agent word / Link word
atoms, with one short contract sentence per axis (`brick_contract`,
`agent_contract`, `link_contract`). Chain presets are the actual presets and
sequence those step templates.

Current Building automation 100 development goal:

```text
BUILDING-AUTOMATION-100-DEVELOPMENT-0: COMPLETE (0529) — full declared automation path runs end-to-end with a REAL codex agent.
prerequisite: SUPPORT-SEMANTIC-AUTHORITY-REHOME-0 (ζ1–ζ7) = DONE (e1491cb; checker --all green + independent review)
phases 8–16: DONE — P8/P10/P13 (interim) ; P9 P11 P12 P14 (evidence-hardening) ; K1+K2 (lifecycle content guard restored + crossing-ref present-fact verification) ; α (native_dispatch word → agent/performance.py) ; γ (native-dispatch hook automation, option-a) ; P15 (read-only dashboard view) ; P16 = δ CAPSTONE (run.py walked a 3-step Building end-to-end with REAL codex: project/brick-protocol/buildings/run-surface-authority-boundary-codex-multistep-0-0529).
commits: e1491cb → c92f88a → 51276b5 → 52b6a36 → 4401cad → da36788 ; checker --all 37 green ; branch codex/checker-kernel-0-prep (NOT pushed).
authoritative plan + QA log: project/brick-protocol/status/kernel/brick-protocol-automation-100-execution-plan-0529.md (engine blueprint: brick-protocol-engine-blueprint-0529.md)
next: minor follow-ups only — P11b (runtime task_source_ref enforcement) · δ-b (per-step recorded_at) · K1b · P14b · γ-b · P15b · δ-c · K2-note. NOT proven: repeated provider reliability ; real reroute/attempt-N with real codex (structurally proven via scope-c synthetic) ; other providers (claude/gemini) ; production runtime.
```

Reason:

```text
Recent automation work made the declared Building path more real, but support
now contains Brick / Agent / Link semantic authority in comparison helpers,
returned-shape constants, gate sufficiency, route adoption, and checker /
recording second-spec surfaces. The automation sequence must not continue
until those contracts are rehomed or explicitly deferred.
```

Active zeta support record:

```text
project/brick-protocol/status/kernel/brick-protocol-support-authority-reconciliation-0-support-record-0529.md
```

## Active Next Sequence

Current (0611):

```text
PROJECT-0 = DONE (a000db0) ; B4-REPAIR = DONE (5b5a7b4) ; checker split map = DONE (60998fc)
-> CLEANUP round (잔잔바리) -> REPO-SPLIT (execution build over checker-split-map-0611.md)
```

Historical (0529 era, kept for continuity):

```text
SUPPORT-SEMANTIC-AUTHORITY-REHOME-0 (ζ1–ζ7) = DONE (e1491cb)
-> BUILDING-AUTOMATION-100-DEVELOPMENT-0 = COMPLETE (0529, da36788; real-codex end-to-end capstone, checker 37 green)
-> next = minor follow-ups only (see brick-protocol-automation-100-execution-plan-0529.md):
   P11b runtime task_source_ref enforcement · δ-b per-step recorded_at · K1b · P14b · γ-b · P15b · δ-c · K2-note
```

`AUTO-CHILD-CANDIDATE-REAL-DOGFOOD-1` remains a later candidate after the
Agent harness goal is validated and closed.

Current Building skill / preset / Agent tool hardening goal:

```text
BUILDING-SKILL-PRESET-AGENT-TOOL-HARDENING-0: done
active chain: Building skill -> chain preset -> step template -> Agent Object -> tool / hook guardrail
```

This goal hardens chain preset / step template and Agent resource automation
without opening native hook execution or a new runtime module. The closure step
template is now admitted as `closure / coo / forward`. Write capability is not
owned by the adapter name or by `dev` alone: effective write is opened only by
Brick-declared `write_scope`, `tool-policy:read-write-scoped`, compatible adapter
support, and write observation. Adapter refs expose adapter technical capability
only; a selected adapter ref is a brain/capability connection. Without Brick
`write_scope`, the request remains read-only even if the adapter can technically
write; with Brick `write_scope`, the write attempt must still pass Agent tool
policy, adapter capability, and write observation checks.
`adapter:codex-write-local` is retired from active/current provider-neutral
adapter refs and active Agent Object adapter refs by
CODEX-WRITE-LOCAL-ALIAS-RETIREMENT-0 v2 as a HIGH-impact active rule edit.
Historical evidence and Building Plans are not mechanically rewritten. Hook refs
remain `execution_opened:false` guardrail intent. Runner preparation now reuses
the Agent resource resolver before adapter preparation. The shape registry now
keeps step templates as compact 3-axis atoms plus per-axis contract sentences,
and exposes chain presets as the actual selectable presets. The design toolkit
exposes both as read-only context for COO selection discussion. Delegated Gemini 3.5 review returned
PASS_WITH_MINOR; delegated Opus brief review returned RETURN for missing
compact Link negative fixtures, which were accepted and patched.

Current Agent projection sync goal:

```text
AGENT-PROJECTION-SYNC-0: done pending final dual-model reconciliation report
active chain: agent/ source -> projection seed -> provider-native projection / MCP read-only context -> sync-in observation
```

This goal keeps good Brick Agent resources aligned with current LLM
orchestration surfaces without turning provider files into source truth.
`selected_model_ref` is now a declared Building Plan / step selection and is
propagated through rendering, validation, graph projection, run, and adapter
CLI model argument projection. Agent Objects still do not own models.
Sync-in is observation only; automatic local-file to `agent/` overwrite remains
forbidden. No new support module, Link module, model-specific adapter, or
provider runtime surface was added.

Current COO trigger hardening:

```text
COO-BUILDING-INTAKE-TRIGGER-0: patched as Agent-source/projection alignment
source: agent/prompts/coo.md + agent/skills/building-coordination/SKILL.md
projection: Codex and Claude COO projection refreshed from agent/
```

When a user asks to run a Building, assign a project, use a preset, move from
task to plan to run, or otherwise starts Brick / Building work, COO must open
intake questions before implementation. COO must not edit files or run the
Building before the active plan (`active_plan_ref` or fully declared intent) is
declared; `selected_shape_ref` is an optional tag, not a run precondition.
COO intake is now explicitly conversational: ask one core question, wait for
Smith's answer, extract candidate task fields, state the interpretation, ask
"이 뜻 맞나?", and only then move to the next question.

Current task-to-evidence chain goal:

```text
EVIDENCE-FROM-TASK-CHAIN-0: done
active chain: deep intake -> work/task.md -> task_source_ref -> received_work -> returned -> step-output -> building-map -> closure
```

This goal keeps `brick/templates/tasks/source-template.md` as the durable
Brick-owned task template and keeps active task instances as Building input
evidence at `project/brick-protocol/buildings/<building-id>/work/task.md`.
`task_intake` may return deep-intake question trees, extracted fields, gap
questions, and a candidate `task_source_draft`, but it must not write task
files or choose shape / plan / Movement / target. Declared Building Plans may
carry optional repo-relative `task_source_ref`; support may validate and carry
that reference through runner preparation, evidence manifests, step-output,
building-map, and closure drafts. Support must not author the task, infer
Movement, or treat the task source as success / quality judgment.

## Recently Closed / Baseline Records

```text
RUN-SURFACE-SPLIT-0
  record: project/brick-protocol/status/kernel/brick-protocol-run-surface-split-0-support-record-0527.md
  evidence: project/brick-protocol/buildings/coo-operating-chain-0-0527/

REAL-ROUTE-REPAIR-DOGFOOD-1
  request plan: brick/building_plans/real-route-repair-dogfood-1-route-request.yaml
  repair plan: brick/building_plans/real-route-repair-dogfood-1-repair-replay.yaml
  record: project/brick-protocol/status/kernel/brick-protocol-real-route-repair-dogfood-1-support-record-0527.md
  evidence:
    project/brick-protocol/buildings/real-route-repair-dogfood-1-request-0527/
    project/brick-protocol/buildings/real-route-repair-dogfood-1-repair-replay-0527/

COO-OPERATING-CHAIN-FOLLOW-UP-1-5
  record: project/brick-protocol/status/kernel/brick-protocol-coo-operating-chain-follow-up-1-5-support-record-0527.md

TASK INTAKE RETURNED DOGFOOD 1
  plan: brick/building_plans/intake-returned-dogfood-1-compact.yaml
  record: project/brick-protocol/status/kernel/brick-protocol-intake-returned-dogfood-1-support-record-0527.md
  evidence: project/brick-protocol/buildings/intake-returned-dogfood-1-0527/

PROJECTION-FRESHNESS-OBSERVATION-0
  plan: brick/building_plans/projection-freshness-observation-0-compact.yaml
  record: project/brick-protocol/status/kernel/brick-protocol-projection-freshness-observation-0-support-record-0527.md
  evidence: project/brick-protocol/buildings/projection-freshness-observation-0-0527/

CURRENT-CONTEXT-PRUNE-0
  plan: brick/building_plans/current-context-prune-0-compact.yaml
  record: project/brick-protocol/status/kernel/brick-protocol-current-context-prune-0-support-record-0527.md
  evidence: project/brick-protocol/buildings/current-context-prune-0-0527/

BAR-V2-REAL-TASK-DOGFOOD-1
  plan: brick/building_plans/bar-v2-real-work-dogfood-1-coo-projection-refresh.yaml
  record: project/brick-protocol/status/kernel/brick-protocol-bar-v2-real-task-dogfood-1-support-record-0527.md
  evidence: project/brick-protocol/buildings/bar-v2-real-work-dogfood-1-0527/

COO-OPERATING-CHAIN-0
  plan: brick/building_plans/coo-operating-chain-0-compact.yaml
  record: project/brick-protocol/status/kernel/brick-protocol-coo-operating-chain-0-support-record-0527.md
  evidence: project/brick-protocol/buildings/coo-operating-chain-0-0527/

BAR-V2-END-TO-END-DOGFOOD-0
  plan: brick/building_plans/bar-v2-end-to-end-dogfood-0-compact.yaml
  record: project/brick-protocol/status/kernel/brick-protocol-bar-v2-end-to-end-dogfood-0-support-record-0526.md
  evidence: project/brick-protocol/buildings/bar-v2-end-to-end-dogfood-0-0526/

CHECKER-KERNEL-0
  record: project/brick-protocol/status/kernel/brick-protocol-checker-kernel-0-support-record-0526.md

AXIS-RECOLLAPSE-MASS-DELETE-0
  record: project/brick-protocol/status/kernel/brick-protocol-axis-recollapse-mass-delete-0-support-record-0527.md
  summary: mass-deleted axis-root case/template/binding/dogfood folders while preserving function in existing contracts.

LEGACY-AGENT-HARNESS-SYSTEM-0
  design: support/docs/spec/brick-protocol-legacy-agent-harness-system-0-0527.md
  record: project/brick-protocol/status/kernel/brick-protocol-legacy-agent-harness-system-0-support-record-0527.md
  summary: imported system/object/template Agent harness boundaries into existing Agent resources and shape registry without copying legacy runtime.

BUILDING-AUTOMATION-COMPLETE-0
  plan: brick/building_plans/building-automation-complete-0-scope-c-dogfood.yaml
  record: project/brick-protocol/status/kernel/brick-protocol-building-automation-complete-0-support-record-0527.md
  evidence: project/brick-protocol/buildings/building-automation-complete-0-scope-c-dogfood-0527/
  summary: closed declared boundary replay automation without new Link module, support retry runtime, RoutePolicyFact, or axis-root case/template/binding/dogfood folders.

AGENT-PROJECTION-SYNC-0
  plan: brick/building_plans/agent-projection-sync-0-dogfood.yaml
  design: support/docs/spec/brick-protocol-agent-projection-sync-0-0527.md
  record: project/brick-protocol/status/kernel/brick-protocol-agent-projection-sync-0-support-record-0527.md
  evidence: project/brick-protocol/buildings/agent-projection-sync-0-dogfood-0527/
  summary: closed Agent source / projection sync, selected_model_ref propagation, MCP read-only projection context, and sync-in observation boundary without adding new modules or provider runtime authority.

LINK-DECISION-DISPOSITION-0
  plan: brick/building_plans/link-decision-disposition-0-dogfood.yaml
  spec: support/docs/spec/brick-protocol-link-decision-disposition-0-0527.md
  record: project/brick-protocol/status/kernel/brick-protocol-link-decision-disposition-0-support-record-0527.md
  evidence: project/brick-protocol/buildings/link-decision-disposition-0-dogfood-0527/
  summary: renamed active Agent concern evidence to transition_concern_evidence, admitted Link row route_decision_basis / transition_lifecycle evidence, and added support-only frontier observation.

LINK-OWNED-AUTOMATION-0
  plan: brick/building_plans/link-owned-automation-0-dogfood.yaml
  spec: support/docs/spec/brick-protocol-link-owned-automation-0-0527.md
  record: project/brick-protocol/status/kernel/brick-protocol-link-owned-automation-0-support-record-0527.md
  evidence: project/brick-protocol/buildings/link-owned-automation-0-dogfood-0527/
  summary: admitted compact Link authoring, declared gate refs, Link-owned policy disposition, and declared-boundary replay dogfood without support-chosen Movement / target or new Link modules.

BUILDING-SKILL-PRESET-AGENT-TOOL-HARDENING-0
  spec: support/docs/spec/brick-protocol-building-skill-preset-agent-tool-hardening-0-0527.md
  record: project/brick-protocol/status/kernel/brick-protocol-building-skill-preset-agent-tool-hardening-0-support-record-0527.md
  profile: support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml
  evidence: project/brick-protocol/buildings/building-skill-preset-agent-tool-hardening-0-dogfood-0527/
  summary: hardened Building skill / chain preset / step template / Agent Object / tool-hook guardrail chain with DEV-only write preflight, closure step template, shared Agent resolver validation in the runner, and 7-step chain dogfood evidence.

EVIDENCE-FROM-TASK-CHAIN-0
  profile updates: support/checkers/profiles/coo_operating_chain.yaml, support/checkers/profiles/intake_skill.yaml, support/checkers/profiles/taskshape_and_design_contract.yaml
  smoke evidence: /tmp/brick-protocol-evidence-taskref-smoke/evidence-taskref-smoke/
  summary: added deep intake fields to task source / task_intake / COO projection and carried optional repo-relative task_source_ref through runner preparation, evidence manifest, building-map, step-output, and closure draft without adding modules or support Movement authority.

PROJECT-ORCHESTRATION-DASHBOARD-0
  active sequence: 1. PROJECT-ORCHESTRATION-LEDGER-0 -> 2. PARTICIPANT-LEDGER-IMPORT-0 -> 3. DASHBOARD-PROJECTION-V1-0 -> 4. SHARED-PROJECT-COLLAB-MODEL-0
  current phase: PROJECT-ORCHESTRATION-LEDGER-0
  plan: brick/building_plans/project-orchestration-ledger-0.yaml
  task evidence: project/brick-protocol/buildings/project-orchestration-ledger-0-0528/work/task.md
  profile: support/checkers/profiles/project_orchestration_ledger.yaml
  record: project/brick-protocol/status/kernel/brick-protocol-project-orchestration-ledger-0-support-record-0528.md
  ledger export: project/brick-protocol/status/project-orchestration-ledger.json
  boundary: support ledger/export projection only; raw latest_movement values are observations, not active Movement authority; dashboard UI, multi-participant import, and shared collaboration wait for later phases.
  stop rule: Smith review required before Phase 2.

STEP-ROWS-THREE-AXIS-CONTRACT-REPAIR-0
  reason: PROJECT-ORCHESTRATION-LEDGER-0 Phase 1 showed declared gate missing facts while the road still reached closure.
  phases: A step rows contract audit -> B Agent adapter returned-field normalization -> C Link gate disposition -> D repair dogfood
  plan: brick/building_plans/preset-three-axis-contract-repair-0-dogfood.yaml
  evidence: project/brick-protocol/buildings/preset-three-axis-contract-repair-0-0528/
  profile: support/checkers/profiles/preset_three_axis_contract_repair.yaml
  record: project/brick-protocol/status/kernel/brick-protocol-preset-three-axis-contract-repair-0-support-record-0528.md
  boundary: no new BAL fact class, no new Movement literal, no new Link/support module, no new checker file.
  narrowly proven: explicit adapter JSON fields can become AgentFact.returned fields; insufficient declared Link gates are visible as Link/frontier evidence in profile/dogfood, while support remains a walker and does not become gate judge or Movement authority.
  not proven: real provider adherence to JSON return shape; dashboard UI readiness; semantic correctness of future dashboard work.

PROVIDER-JSON-RETURN-SMOKE-0
  reason: live-provider check requested before widening PROJECT-ORCHESTRATION-DASHBOARD-0 Phase 2.
  plan: brick/building_plans/provider-json-return-smoke-0.yaml
  evidence: project/brick-protocol/buildings/provider-json-return-smoke-0-0528/
  profile: support/checkers/profiles/provider_json_return_smoke.yaml
  record: project/brick-protocol/status/kernel/brick-protocol-provider-json-return-smoke-0-support-record-0528.md
  observed: adapter:codex-local / codex-cli 0.133.0 returned JSON fields for observed_evidence and not_proven; Link gate sufficient.
  not proven: repeated provider adherence, Claude/Gemini local behavior, provider reliability in longer Buildings.
```

BAR-v2 phase refs retained for profile continuity:

```text
OBJECTIVE-PRESERVATION-ROOT-0
HUMAN-GATE-TIER-AND-RECOVERY-0
LINK-CONNECTION-ROUTE-0
DEVELOPMENT-WORKTREE-CONVENTION-0
WRITE-SCOPE-DEFAULT-EXCLUDE-0
STEP-OUTPUT-AND-ROUTE-REQUEST-0
TASK-SHAPE-AND-DESIGN-CONTRACT-0
DESIGN-TOOLKIT-AND-MCP-0
TASK-INTAKE-SKILL-0
LINK-ROUTE-POLICY-RESOURCE-0
CHECKER-STRICT-VALIDATION-0
COO-OPERATING-CHAIN-0
BUILDING-AUTOMATION-COMPLETE-0
BUILDING-AUTOMATION-FINAL-COMPLETION-AUDIT-0
```

## Active Operating Surfaces

```text
AGENTS.md = current constitution / protocol boundary
brick/templates/tasks/source-template.md = Brick-owned task source template
agent/ = Agent resource source
support/connection/agent_resources.py = Agent resource renderer / toolkit
support/connection/coo_sync.py = admitted local projection writer
support/connection/coo_sync.py::observe_agent_projection_freshness = read-only projection freshness observation
support/connection/mcp_projection.py = read-only MCP call door
support/operator/building_operation.py = COO helper packets / support observations
support/operator/run.py = declared Building Plan walker / public run facade
support/operator/plan_graph.py = declared graph plan projection helper
support/operator/plan_validation.py = declared Brick / Agent / Link row validation helper
support/operator/write_observation.py = DEV write_scope / git-ref observation helper
support/operator/evidence_assembly.py = support evidence packet assembly helper
support/recording/contracts.py = support recording input contracts
support/recording/raw_claim_trace.py = raw / claim_trace writer
support/recording/step_outputs.py = step-output / transition_concern projection writer with historical route_request compatibility
support/checkers/check_profile.py = declarative profile runner
support/checkers/profiles/*.yaml = active profile checks
project/brick-protocol/buildings/ = local Building evidence roots
```

## Current Source / Projection Split

```text
agent/ = source
/Users/smith/.codex/skills/brick-protocol-coo/SKILL.md = generated projection
/Users/smith/.claude/agents/brick-protocol-coo.md = generated projection
MCP output = read-only projection / call-door context
```

If a projection differs from `agent/`, `agent/` remains authoritative and the
projection is regenerated. Projection freshness is an observation, not source
truth or provider app reload proof.

## Current Guardrails

```text
Brick = work contract / task evidence / Building Plan / required return shape
Agent = performer resources and AgentFact(received_work, returned)
Link = transfer / carry / Movement / target / route_replay_plan refs
support = mechanics and evidence only
```

Active BAL fact vocabulary retained for checker/context continuity:

```text
BrickWork boundary
optional BrickComparisonFact
ReceiptFact
TransferFact
CarryFact
GateFact
MovementFact
TransitionFact
contract observation
```

Active Movement literals remain:

```text
forward
reroute
```

Current Link shorthand:

```text
default forward connection
exception reroute
```

Forbidden for the current follow-up goal:

```text
source truth claim
success judgment
quality judgment
Movement authority claim
task-authored reroute
Agent route target choice
MCP-authored shape or plan
support-chosen Movement
RoutePolicyFact promotion
provider-native projection expansion beyond admitted AGENT-PROJECTION-SYNC-0 projection files
provider SDK/API call
credential/session/setup-token body storage
new support/checkers/check_*.py files
```

## Current Not Proven

```text
Codex app reload behavior
Claude app reload behavior
future provider behavior
production runtime readiness
semantic correctness of future task sources
semantic fitness of future selected shapes
future reviewer Movement decision correctness
RoutePolicyFact need
semantic-quality automation
```

## Validation Baseline

The current baseline before the remaining follow-up tasks:

```text
support/checkers/check_profile.py --profile bar_v2_real_task_dogfood_1: passed
support/checkers/check_profile.py --profile current_context_prune: passed
support/checkers/check_profile.py --profile projection_freshness_observation: passed
support/checkers/check_profile.py --profile intake_returned_dogfood_1: passed
support/checkers/check_profile.py --profile real_route_repair_dogfood_1: passed
support/checkers/check_profile.py --all: passed
py_compile for touched helpers: passed
git diff --check: passed
residue find after cleanup: no output
```

## Next Movement Candidate

```text
movement: forward
target: final validation
```
