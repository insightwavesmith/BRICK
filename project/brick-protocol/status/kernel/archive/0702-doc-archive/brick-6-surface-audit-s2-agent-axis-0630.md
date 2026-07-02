# BRICK 6-Surface Architecture Audit - S2 Agent Axis - 2026-06-30

## Surface

- Surface: Agent axis.
- Target checkout: `/Users/smith/projects/BRICK`.
- Commit: `17eaade696998cd0de7bbd85ceb7525f349588e9`.
- Mode: audit only. No source repair was performed.
- Verdict: `ISSUE`.

## Map

Agent owns performer identity, receipt, tool policy ceiling, adapter references, instruction resources, and the closed returned fact.

Primary Agent-owned surfaces inspected:

- `agent/objects/*.yaml`
- `agent/prompts/*.md`
- `agent/skills/*/SKILL.md`
- `agent/hooks/*.yaml`
- `agent/tool_policies/*.yaml`
- `agent/disciplines/*.md`
- `agent/spec.py`
- `agent/receipt.py`
- `agent/return_fact.py`

Main support/projection consumers inspected:

- `support/connection/agent_resources.py`
- `support/connection/agent_adapter.py`
- `support/connection/adapter_grant_policy.py`
- `support/operator/run.py`
- `support/operator/run_chat_session.py`
- `support/connection/coo_sync.py`
- Codex/Claude local projection files under `~/.codex/skills/brick-protocol-*` and `~/.claude/agents/brick-protocol-*`.

Observed Agent flow:

1. Agent Object resources are resolved from `agent/objects/*.yaml`.
2. Support renders an Agent instruction packet from Agent resources.
3. Building step rows select an Agent Object and adapter/model refs.
4. Adapter support builds an `AgentAdapterRequest`.
5. Runtime returns are closed through
   `agent.return_fact.make_agent_fact(received_work=..., returned=...)`
   (Claude review C8 corrected the keyword-only call shape).

## Evidence

Parallel attack review used 9 lanes:

- `S2-map`
- `S2-godmodule`
- `S2-dup-dead`
- `S2-axis-leak`
- `S2-contract`
- `S2-runtime`
- `S2-checker`
- `S2-simplicity`
- `S2-adversarial`

Codex operator direct checks:

- `git status --branch --short --untracked-files=no`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_agent_resource_resolution.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/agent_axis_behavioral.yaml`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/building_skill_preset_agent_resource_boundary.yaml`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 - <<'PY' ... observe_agent_projection_freshness(Path('.'))`
- Targeted reads of `AGENTS.md`, `agent/return_fact.py`, `support/operator/run_chat_session.py`, `support/operator/run.py`, Agent skills/prompts, and support docs.

Direct green evidence:

- Agent resource resolution passed: 111 declared Agent Object resource refs resolve.
- `agent_axis_behavioral.yaml` passed: 258 declarative observations and 9808 kernel targets inspected.
- `building_skill_preset_agent_resource_boundary.yaml` passed: 96 declarative observations and 5422 kernel targets inspected.
- Active Agent Objects do not carry retired adapter refs such as `adapter:gemini-api` or `adapter:codex-write-local`.
- Gemini-local remains an active local adapter path in Agent/resource checks; Gemini API is retired from active Agent resource refs.

Proof limit: checker green is support evidence only. It does not prove source truth, provider behavior, quality, success, Movement authority, or complete future coverage.

## Findings

### S2-F1 - Chat-session submission can persist an Agent-return payload that AgentFact later rejects

- Severity: high.
- Axis attribution: Agent contract crossing, with support submission boundary.
- Evidence:
  - `support/operator/run_chat_session.py:458-487` validates returned payload mapping, forbidden payload/session text, and required return-shape fields.
  - That boundary does not call the AgentFact top-level verdict-key validator.
  - `agent/return_fact.py:42-66` defines forbidden top-level verdict/Movement keys such as `movement`, `result`, `status`, `success`, `target`, and `verdict`.
  - `agent/return_fact.py:119-125` rejects those keys.
  - `agent/return_fact.py:167-184` applies the rejection in `make_agent_fact`.
  - `support/operator/run.py:842-846` reads chat-session submission returned payload during resume, and later replay closes it through AgentFact.
- Meaning: a chat-session submission can be admitted to disk and only fail later at replay/AgentFact closure. That is not an engine collapse, but it is an Agent contract boundary weakness. Claude review C13/ADD-8 strengthens the impact: later AgentFact closure still fail-safes before an accepted AgentFact, but a poisoned `submission.json` can wedge the Building because resume does not convert that closure `ValueError` into a clean HOLD and the submission file is write-exclusive.
- Proof status: confirmed by code inspection. No mutation performed.

### S2-F2 - Active constitution text still describes write capability as read-write-scoped only

- Severity: high.
- Axis attribution: Agent policy contract drift.
- Evidence:
  - `AGENTS.md:119-132` states write capability as `tool-policy:read-write-scoped` plus observed-write adapter and gives the effective-write formula with only `tool-policy:read-write-scoped`.
  - Live Agent Objects use `tool-policy:probe-write-scoped` for `qa-lead`, `qa`, and `inspector`.
  - `support/checkers/profiles/agent_axis_behavioral.yaml` and `support/checkers/lib/kernel_checks.py` exercise probe-write behavior for QA/Inspector and Gemini-local.
  - Claude ADD-11 adds that `agent/skills/make-an-agent/SKILL.md` and its byte-identical copy under `brick/templates/skills/` still teach the stale `read-write-scoped` taxonomy and do not carry `probe_write` / `source_write` wording.
- Meaning: code/checkers have moved to `read / probe_write / source_write`, but the visible constitution still carries older wording. This can mislead future operators and agents into blaming the wrong axis.
- Proof status: confirmed by direct line reads and profile green.

### S2-F3 - Agent skills/prompts contain Brick/Link authority language

- Severity: high.
- Axis attribution: Agent projection/instruction leak into Brick and Link ownership.
- Evidence:
  - `agent/prompts/coo.md:5-7` says COO is not Movement authority, but `agent/prompts/coo.md:40-41` says COO remains the only reroute author on the native-dispatch close seam. Claude review C2 corrected the earlier `39-40` locator.
  - `agent/skills/make-a-brick/SKILL.md:8` says declaration can be produced directly by COO outside Building.
  - `agent/skills/make-a-brick/SKILL.md:14-28` instructs helper creation of `brick.md`, `return.yaml`, `link_movement_literal`, and required return shape.
  - `agent/skills/make-a-gate/SKILL.md:25-61` instructs direct Link gate registry/spec/YAML/AGENTS updates.
  - `agent/skills/brick-task-author/SKILL.md:269-313` contains gate/disposition/runbook wording that reads like operator-side Link handling rather than purely Agent instruction.
  - `agent/skills/building-sizing-method/SKILL.md:24-33` says Brick kind determines role/provider/write/verdict.
- Meaning: some skills are useful operational recipes, but as Agent-axis resources they blur source ownership. They should not teach Agent projection to own Brick template admission, Link gate admission, provider verdict authority, or Movement authoring.
- Proof status: confirmed by direct line reads. Exact repair should be checker-first and human-gated if constitutional language changes.

### S2-F4 - Agent support surfaces are godmodule candidates

- Severity: medium.
- Axis attribution: support projection/mechanics, not Agent source truth by itself.
- Evidence:
  - `support/connection/agent_resources.py` is 2007 lines and includes resolution, validation, instruction rendering, native grants, and projection seed mechanics.
  - `support/connection/agent_adapter.py` is 1202 lines and includes request shape, provider specs, dispatch, returned-key filtering, and effective-write observation.
  - `agent/spec.py` is 802 lines and mixes Agent schema/resource declarations with native projection hints.
- Meaning: no direct authority leak is proven by size alone, but the support boundary is dense enough that future changes can easily create Agent/support confusion.
- Proof status: issue candidate, not a safe split/delete instruction.

### S2-F5 - Duplicate and stale Agent projection surfaces exist

- Severity: medium.
- Axis attribution: support/projection drift around Agent resources.
- Evidence:
  - Five skills are byte-identical under both `agent/skills/*/SKILL.md` and `brick/templates/skills/*/SKILL.md`: `brick-task-author`, `building-sizing-method`, `make-a-brick`, `make-a-gate`, `make-an-agent`.
  - `support/docs/references/agent-axis-detail.md:53-67` still says QA/Inspector use `tool-policy:read-write-scoped` and calls it the only write-capable policy.
  - `observe_agent_projection_freshness(Path('.'))` returned `all_present: True` and `all_match_rendered_agent_resource: False` for local Codex/Claude projections.
- Meaning: `agent/` remains source truth, but local/provider projections and duplicated skill copies are stale enough to affect operator or model behavior.
- Proof status: confirmed as projection drift. App reload/provider behavior remains not proven.

### S2-F6 - Probe-write vs source-write is policy/prompt/checker-separated, not fully filesystem-enforced

- Severity: medium.
- Axis attribution: Agent max policy plus adapter native grant; support sandbox implementation.
- Evidence:
  - QA/Inspector use `probe-write-scoped` in Agent Objects.
  - Profiles and kernel checks prove prompt/native grant shape and source-mutation RED cases.
  - Adapter prompt text acknowledges the reviewer no-source-mutation rule, but no direct filesystem mechanism proving all source paths are impossible was observed in this audit.
- Meaning: the semantic split exists and has checker teeth, but it should not be overclaimed as hard filesystem isolation.
- Proof status: partially proven; hard isolation is `NOT_PROVEN`.

## External Review Incorporation

Claude review and Smith/operator follow-up sharpened S2 in seven ways.

1. AgentFact closure has two separate risks.
   - Existing S2-F1 is the pre-persistence admission gap.
   - Claude ADD-8 adds the operational wedge risk: a bad chat-session
     submission can persist and then repeatedly fail replay because the shared
     submission validator is still secret-only and the stored submission is
     exclusive.
   - Repair belongs at shared submission intake before persistence, not only at
     replay.

2. The forbidden-key fix must preserve top-level-only semantics.
   - Claude ADD-7 warns that `_validate_no_payload_forbidden` is recursive,
     while `AgentFact` verdict-key rejection is intentionally top-level-only.
   - A naive recursive reuse with `TOP_LEVEL_VERDICT_KEYS` would over-reject
     legitimate nested evidence keys such as nested `status`, `result`,
     `target`, or `score`.
   - Correct invariant: AgentFact returned top-level verdict/Movement keys are
     forbidden; nested evidence keys need schema-specific checks.

3. The Agent tool taxonomy must be reflected in Agent resources, not only in
   checkers.
   - Smith's taxonomy is `read` for inspection, `probe_write` for disposable
     verification outputs, and `source_write` / `artifact_write` for real
     product/code/document output.
   - Agent Objects, tool policies, prompts, and authoring skills must all use
     this vocabulary consistently.

4. QA/Inspector write ability is capability, not authority.
   - QA/Inspector may need probe-write to run checkers and synthetic fixtures.
   - That must not become source mutation authority.
   - If a QA lane mutates source, the evidence should be treated as HOLD/repair
     evidence, not a clean QA pass.

5. Projection drift remains support evidence only.
   - Local Codex/Claude projections may be stale or mismatched, but `agent/`
     remains source for Agent resources.
   - Sync-in observations are candidates for later Building work, not automatic
     Agent resource updates.

6. Smith's readiness/failure-attribution idea partly belongs on S2.
   - Agent-side deterministic categories already exist for
     `agent_return_shape_gap`, forbidden top-level keys, adapter/provider
     runtime failure, and missing returned fields.
   - Semantic categories such as task-definition gap require Brick and Link
     evidence too; do not attribute them to Agent alone.

7. No provider-specific law should be added.
   - Gemini-local, Codex-local, and Claude-local may differ in native sandbox
     mechanics, but Agent capability classes should stay provider-neutral.
   - Adapter/native grant translates the capability; it does not define
     constitutional authority.

## Rejected Shortcuts

- "Gemini is retired" was rejected. `adapter:gemini-local` is active; `adapter:gemini-api` is retired from active Agent refs.
- "Adapter identity owns write" was rejected. Runtime checks still use Brick write need, Agent policy, adapter technical support, and write observation.
- "Checker green proves Agent correctness" was rejected. Profiles passed but remain support evidence only.
- "Skill wording alone proves runtime breakage" was rejected. The wording is an authority/projection risk, not proof that runtime Link Movement is wrong.
- "Retired literals are dead code" was rejected. Several retired refs are intentionally present as negative probes/backstops.

## Verdict

`ISSUE`.

The Agent resource core is largely intact: objects resolve, active adapters are provider-neutral, Agent rows remain separated from runtime adapter selection, and write gating is not owned by adapter identity alone. The surface is not clear because chat-session submission admits payloads before full AgentFact verdict-key closure, active constitution text lags the probe-write taxonomy, Agent skills/prompts carry Brick/Link authority language, projections are stale, and source/probe isolation is not proven as filesystem-hard.

Readiness tuple: use `brick-6-surface-audit-readiness-tuples-0630.md` for implementation priority. S2 is `core_sound: partial`, `axis_integrity_blockers: 4`, `ship_safety_blockers: 2`, `dynamic_runtime_not_proven: yes`, and `worst_severity: high`. The flat `ISSUE` label is only a findings-inventory label.

## Next Work Candidates

1. Add a pre-persistence chat-session submission validator that rejects AgentFact top-level verdict/Movement keys before `submission.json` is admitted.
2. Preserve top-level-only verdict-key semantics; do not recursively ban common nested evidence keys by accident.
3. Update constitutional, Agent Object, tool-policy, and authoring-skill wording for `read / probe_write / source_write-artifact_write` without granting QA source mutation.
4. Split or clearly mark Agent skills that are operational helper recipes versus Agent-axis source resources.
5. Regenerate or review local provider projections after the Agent resource source is corrected.
6. Add a focused checker for exact AgentFact field closure, chat-session pre-persist forbidden-key rejection, and poisoned-submission wedge prevention.
7. Add a direct checker guard against ordinary profile sweeps invoking live provider/Gemini APIs outside a declared Building Agent step.
8. Treat support godmodule splits as later cleanup only, with facade preservation and conservation checks.

## Not Proven

- Provider credential validity.
- Native provider/hook execution behavior.
- Codex/Claude app reload behavior after projection regeneration.
- Complete filesystem-level prevention of QA/Inspector source mutation.
- Safe deletion of duplicated skills or retired adapter literals.
- Semantic correctness of future `transition_concern_evidence` returns.
