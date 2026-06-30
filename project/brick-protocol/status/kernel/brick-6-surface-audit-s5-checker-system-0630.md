# BRICK 6-Surface Architecture Audit - S5 Checker System - 2026-06-30

## Surface

- Surface: Checker system.
- Target checkout: `/Users/smith/projects/BRICK`.
- Commit: `17eaade696998cd0de7bbd85ceb7525f349588e9`.
- Mode: audit only. No source repair was performed.
- Verdict: `ISSUE`.

## Map

Checker owns support evidence production only. It does not own Brick work meaning, Agent performer meaning, Link Movement, source truth, success judgment, quality judgment, provider proof, or complete coverage proof.

Primary checker surfaces inspected:

- `support/checkers/check_profile.py`
- `support/checkers/profiles/*.yaml`
- `support/checkers/lib/kernel_checks.py`
- `support/checkers/lib/case_runners.py`
- `support/checkers/lib/rule_runners.py`
- `support/checkers/lib/*.py`
- `support/checkers/check_*.py`
- `support/checkers/module_registry.yaml`
- `support/checkers/crossing_registry.yaml`
- `support/operator/checker_runner.py`

Observed checker flow:

1. `check_profile.py --all` enumerates `support/checkers/profiles/*.yaml`.
2. Each profile runs every registered declarative rule runner.
3. Each profile then runs only its declared `kernel_checks`.
4. Profile runner prints a proof limit and never converts green into source truth.
5. Some checker cases generate temp or fixture evidence as support observations.

Measured surface:

- 28 profile YAML files.
- 41 top-level `support/checkers/check_*.py` files.
- 19 `support/checkers/lib/*.py` files.
- 63 registered `KERNEL_DISPATCH` IDs, all used by current profiles.
- 50 `RULE_RUNNERS` keys.
- Largest files: `kernel_checks.py` 9931 lines, `case_runners.py` 8503 lines, `check_bounded_agent_proposed_routing_loop0.py` 6923 lines.

## Evidence

Parallel attack review used 9 lanes:

- `S5-map`
- `S5-godmodule`
- `S5-dup-dead`
- `S5-axis-leak`
- `S5-contract`
- `S5-runtime`
- `S5-checker`
- `S5-simplicity`
- `S5-adversarial`

Codex operator direct checks:

- `git rev-parse HEAD`
- `git status --branch --short --untracked-files=all`
- `find support/checkers/profiles -maxdepth 1 -type f -name '*.yaml' | wc -l`
- `find support/checkers -type f \( -name '*.py' -o -name '*.yaml' \) -print | xargs wc -l | sort -nr | head -30`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --self-test`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all`
- Targeted reads of `check_profile.py`, `kernel_checks.py`, `case_runners.py`, `adapter_capability_checks.py`, `provider_preflight_check.py`, `run_chat_session.py`, `plan_validation.py`, `walker_step_fixture.py`, `assembly.py`, `check_assembly_equivalence.py`, dashboard/reporter support files, and profile YAMLs.

Direct green evidence:

- `check_profile.py --self-test` passed.
- `check_profile.py --all` exited 0.
- `--all` ran 28 profiles and printed the runner proof limit.
- No running `check_profile.py` process remained after the audit.
- Final tracked tree stayed clean; untracked files were the S1-S5 audit notes.
- `BRICK_CHECKER_PROFILE_SWEEP=1` is set during profile sweeps.
- Gemini/local provider checks use fixture command runners or explicit live-call rejection probes, not live Gemini credential validation.

Proof limit: checker green is support evidence only. It does not prove source truth, success judgment, quality judgment, Movement authority, provider behavior, semantic correctness, or complete coverage.

## Findings

### S5-F1 - `--all` is green, but green preserves known bad or conflicting invariants

- Severity: high.
- Axis attribution: checker support evidence preserving mixed Brick/Agent/Link boundaries.
- Evidence:
  - S1 direct repro showed fan-in source `required_return_shape` override can be accepted and composed.
  - `assembly.py:447-468` and `assembly.py:1103-1112` strip `transition_concern_evidence` from fan-in source return shapes.
  - `check_assembly_equivalence.py:1863-1869` raises if fan-in source shapes still carry `transition_concern_evidence`, so green preserves the stripped behavior.
  - Brick `return.yaml` files for QA kinds include full shapes with `transition_concern_evidence`.
- Meaning: `assembly_equivalence` green currently proves the shrink remains, not that the Brick return contract boundary is correct.
- Proof status: confirmed by direct repro and checker source.

### S5-F2 - Chat-session ingestion can accept AgentFact-forbidden top-level verdict keys before replay

- Severity: high.
- Axis attribution: Agent contract coverage gap at support submission boundary.
- Evidence:
  - `agent/return_fact.py` forbids top-level verdict/Movement keys such as `success`, `status`, `movement`, and `target`.
  - Claude review C5 corrected the evidence chain: the relevant intake surface
    is `support/operator/run_chat_session.py`, which currently routes through a
    secret-key forbidden family rather than AgentFact's top-level verdict-key
    closure.
  - Sidecar probe observed chat submission accepting a payload with `status`/`success`, while `make_agent_fact` later rejected the same shape.
  - Existing mutation coverage injects secret-like keys, not verdict keys, at the chat submission boundary.
- Meaning: checker coverage catches AgentFact closure later, but not the pre-persistence chat-session intake seam.
- Proof status: confirmed by code inspection and sidecar direct probe.

### S5-F3 - Missing `declared_gate_refs` is not negatively probed as raw absence

- Severity: high.
- Axis attribution: Link gate declaration / support walker fallback coverage gap.
- Evidence:
  - `plan_validation.py` returns when `declared_gate_refs` is absent.
  - `walker_step_fixture.py` can convert missing declared gate evidence into `template:default-transition` adoption.
  - Sidecar probe observed missing `declared_gate_refs` validation accepted and disposition adopted by `template:default-transition`.
  - Existing `link_routing_behavioral` negative fixtures cover many bad route cases, but not raw absence of `declared_gate_refs`.
- Meaning: Movement literals are well guarded, but one Link gate declaration absence path still needs a focused negative probe or an explicit admission that default transition is allowed there.
- Proof status: confirmed by code inspection and sidecar direct probe.

### S5-F4 - `check_profile.py --all` is not strictly read-only over the inspected checkout

- Severity: high.
- Axis attribution: support checker runtime behavior.
- Evidence:
  - `case_runners.py:1930` creates fixture vessels under `repo / "project" / vessel_id`.
  - `case_runners.py:2138-2168` creates and removes a charterless fixture directory in `finally`.
  - `case_runners.py:7808-8016` creates a read-side projection fixture vessel under the live repo and removes it in `finally`.
  - `check_profile.py:1366-1377` guards only live inbox fixture packet count, not the whole worktree.
  - One sidecar observed a transient `project/checker-projection-fixture-vessel/` during sweep; it cleared before manual cleanup.
- Meaning: final status can be clean, but the ordinary profile sweep is not strictly read-only in the filesystem sense. It performs support fixture writes in live `project/` paths.
- Claude ADD-10 strengthens this into a reentrancy issue: fixed fixture vessel
  IDs and `finally` cleanup are not signal-safe, so a killed or concurrent sweep
  can leave a fixture that makes a later sweep fail until cleaned.
- Proof status: confirmed by code inspection and observed transient side effect.

### S5-F5 - Checker mechanics are godmodule-heavy

- Severity: high.
- Axis attribution: support mechanics overgrowth, not direct Brick/Agent/Link source truth.
- Evidence:
  - `kernel_checks.py` is 9931 lines and spans axis vocabulary, Agent adapter capability, reporter/Slack, dashboard productization, CLI/MCP smoke, projections, and session redaction.
  - `case_runners.py` is 8503 lines and spans adapter selection, route materialization, transition disposition, compose-building, auto-repair, child-building, native dispatch, workflow import, and Link evidence cases.
  - `check_bounded_agent_proposed_routing_loop0.py` is 6923 lines and acts as an executable encyclopedia for bounded route/HOLD/resume/disposition behavior.
  - `check_profile.py` remains the central registry/dispatch facade with 50 rule runners and 63 kernel dispatches.
- Meaning: no authority leak is proven from size alone, but the checker system now carries enough protocol fixtures and literals that future agents can confuse checker examples with axis law.
- Proof status: confirmed godmodule pressure. Safe split not proven.

### S5-F6 - Active checker map/count docs are stale

- Severity: medium-high.
- Axis attribution: support map/projection drift.
- Evidence:
  - Live profile count is 28.
  - `AGENTS.md:725-727` still says BRICK has 13 profile files.
  - `support/docs/references/checker-profile-map.md:5-20` records a 24-profile map and 54 distinct kernel checks.
  - Current AST/profile inventory found 63 registered and used kernel IDs.
  - `module_registry.yaml` still names a `checker_strict_validation profile` even though no live `checker_strict_validation.yaml` exists.
  - Claude ADD-15 adds that `crossing_registry.yaml` and the full
    `module_registry.yaml` were named in scope but not inspected for drift/dead
    rows beyond the single phantom profile.
- Meaning: the checker system itself may run, but its operator map is stale enough to mislead planning and cleanup.
- Proof status: confirmed by direct measurement and line reads.

### S5-F7 - Support output wording leaks source-truth/pass/done language and profiles pin some of it

- Severity: medium-high.
- Axis attribution: support projection wording around Link lifecycle and evidence.
- Evidence:
  - `AGENTS.md:623-630` says checker/reporter/dashboard output is support evidence only and not source truth.
  - `support/dashboard/DEPLOY.md:40` says the source of truth stays in the repo ledger and written Building evidence.
  - `read_side_projection_boundary.yaml` pins adjacent dashboard deploy wording.
  - `walker_report_events.py:86` emits `gate_passed`.
  - `walker_report_events.py:183-188` maps both reroute and default gate notes to pass/next-step wording.
  - `report_sinks.py:1357-1358` renders `building_finished` as a done message.
- Meaning: not proven that support chooses Movement or judges success, but checker-pinned reader wording blurs sufficiency/lifecycle with pass/done language.
- Proof status: confirmed wording/projection risk. Runtime Movement authority leak not proven.

### S5-F8 - Profile contract closure is strong today but weak as a future contract

- Severity: medium.
- Axis attribution: checker schema/admission.
- Evidence:
  - `check_profile.py --self-test` rejects arbitrary checker file paths, unknown rule keys, unknown kernel IDs, and duplicate YAML keys.
  - `validate_profile()` requires schema/profile ID and known kernel IDs, but does not require non-empty `description`, `proof_limits`, `not_proven`, or at least one active tooth.
  - Current profiles do have proof limits and kernel/rule coverage, but this is observed current-state, not enforced future-state.
- Meaning: present profiles are mostly well-formed, but a future low-tooth profile could be admitted unless another guard catches it.
- Proof status: partially proven. Future contract hardness not proven.

### S5-F9 - Duplicate and text-pin-heavy profile rows create diet pressure

- Severity: medium.
- Axis attribution: checker/profile maintainability.
- Evidence:
  - `agent_axis_behavioral.yaml` repeats path pins for `AGENTS.md`, `agent_adapter.py`, `plan_validation.py`, and `run.py`.
  - `link_routing_behavioral.yaml` repeats path pins and retired path absence rows.
  - `read_side_projection_boundary.yaml` repeats path pins and absence rows.
  - `coo_operating_chain.yaml` uses only generic kernel checks plus path/text pins for specific COO chain behavior.
  - `rule_runners.py` implements text rules as substring matching.
- Meaning: not all text pins are decorative, but several profile areas are brittle and repetitive. This is cleanup pressure, not a deletion license.
- Proof status: confirmed duplication/text-pin pressure. Safe deletion not proven.

### S5-F10 - Live provider prevention mostly holds, but the invariant is distributed

- Severity: medium.
- Axis attribution: support checker runtime / adapter preflight.
- Evidence:
  - `check_profile.py` sets `BRICK_CHECKER_PROFILE_SWEEP=1` during profile runs.
  - `adapter_local_cli.py` rejects live provider invocation during sweep when no fixture `command_runner` is injected.
  - `adapter_capability_checks.py` probes that rejection.
  - `provider_preflight_check.py` injects a fake runner for preflight checks.
  - `preflight_provider()` can still run cheap `--version` if called with `command_runner=None` outside that guarded checker path.
- Meaning: ordinary profile sweeps did not directly call live Gemini in this audit, but the invariant lives across several support surfaces instead of one central checker-runtime gate.
- Proof status: current sweep holds-with-limits. Future direct preflight misuse not proven safe.

### S5-F11 - Out-of-band mutation probes can still write inside the inspected repo

- Severity: medium.
- Axis attribution: checker debug mode / support mutation probe.
- Evidence:
  - `check_adapter_usage_meter.py` exposes `--probe-mutation-red`.
  - That mode mutates `support/connection/adapter_local_cli.py`, runs the checker, then restores via `cp`.
  - Its help text still references the older `agent_adapter.py` surface.
- Meaning: normal profile runs use temp/in-memory mutation probes, but an admitted checker debug mode can still mutate live source if invoked manually.
- Proof status: confirmed code path. Not invoked during this audit.

### S5-F12 - Checker strength is not proven as a required release gate

- Severity: high.
- Axis attribution: checker support evidence and product/release governance.
- Evidence:
  - External static deployment reports flagged CI/required-gate absence as a deployment risk.
  - Direct measurement found no `.github` workflow files in this checkout.
  - `pyproject.toml:25-27` points pytest at `support/checkers`, and direct S5 evidence showed `check_profile.py --all` can pass locally.
  - Local checker green is support evidence; it does not prove that pull requests, public release exports, or main branch updates are blocked by the same checks.
  - Claude review ADD-3 challenged the pytest implication. Direct re-measurement
    found no `test_*.py`/`conftest.py` files and only checker-internal
    `def test_*` helper names in `support/checkers/check_adapter_usage_meter.py`,
    including one helper that takes a `repo` argument. Therefore pytest is not
    currently the same runnable verification surface as `brick verify` or
    `support/checkers/check_profile.py --all`.
- Meaning: the checker system has teeth locally, but product hardening requires those teeth to be wired into CI/branch protection or an equivalent release gate.
- Proof status: confirmed absence of workflow files in checkout and confirmed
  pytest-surface mismatch. GitHub branch protection was not queried in this
  audit.

### S5-F13 - Deployment hardening gaps need negative probes, not only text pins

- Severity: high.
- Axis attribution: checker coverage for support/product deployment surfaces.
- Evidence:
  - Release export risk is directly measurable: `release_export.sh` includes `--others --exclude-standard` and `.gitignore` lacks secret/local deny patterns.
  - Dashboard ingest risk is directly measurable: `/ingest` uses `x-ingest-secret` equality without HMAC/timestamp/event_id/sequence.
  - Sensitive write risk is directly measurable: `write_observation` records sensitive writes and `driver` commits sandbox output on `frontier_kind == "complete"`.
  - Claude ADD-9 corrects the wording: there is no single `def write_observation`
    function; the module records the flag, and the decoupling is global because
    `driver.py`/`run.py` do not consume the sensitive-write observation.
  - Claude ADD-2 adds a checker gap for raw evidence stream secret/PII scrub
    before ledger persistence.
  - Current S5 direct evidence already found several text-pin-heavy profiles and checker-map drift.
- Meaning: for deployment surfaces, the next checker improvement should be executable negative probes: synthetic `.env` export fails, replayed dashboard event fails, sequence rollback fails, and sensitive path write prevents output commit.
- Proof status: confirmed gap. No new checker was added in this audit.

## External Review Incorporation

Claude review, Smith/operator follow-up, and external deployment reports sharpened
S5 in six ways.

1. Green is useful, but the audit method is still mostly static.
   - Claude Opinion 6 says the current method cannot certify concurrency,
     resume/replay interleavings, real provider behavior, or fresh-machine
     integration.
   - Checker green remains support evidence, not customer-ready proof.

2. The checker system needs dynamic proof companions.
   - At least one end-to-end live or stubbed Building should exercise worktree
     isolation, fan-out/fan-in, HOLD/resume, and evidence/report projection.
   - This is not a replacement for checkers; it is a different proof class.

3. Pytest and BRICK checkers must not be conflated.
   - ADD-3 is now incorporated in S5-F12.
   - If pytest remains declared in `pyproject.toml`, it must either run real
     tests or intentionally delegate to BRICK verification.

4. Negative probes must cover evidence integrity, not just protocol text.
   - Raw stream secret/PII persistence.
   - Release export of tracked/untracked forbidden secret paths.
   - Dashboard ingest replay/signature/sequence.
   - Sensitive-write observation blocking or marking output commit.
   - Post-HOLD resume isolation.

5. Checker fixture hygiene is itself a product-readiness concern.
   - Fixed fixture roots and live-repo writes can make later checks fail for
     environmental reasons.
   - Ordinary sweeps should prefer temp roots or deterministic cleanup guards
     strong enough to survive interruption.

6. Registry drift needs direct inspection before checker diet.
   - `module_registry.yaml` and `crossing_registry.yaml` must be checked before
     deleting or splitting checker/kernel families.
   - Checker diet should follow negative-probe coverage, not precede it.

## Rejected Shortcuts

- "`--all` green means customer-ready" was rejected. The runner itself disclaims source truth, success, quality, Movement, provider behavior, and complete coverage.
- "Checker system is broken because it writes temp fixtures" was rejected. The issue is not final dirty state; it is that ordinary sweeps are not strictly read-only over the checkout.
- "Text pins are all useless" was rejected. Some text pins guard user-facing rejection wording and negative surface admission.
- "Retired refs are stale by default" was rejected. Retired `check_*0.py`, `--large`, and retired adapter refs are often intentional negative guards.
- "This is a Link engine bug" was rejected. Missing gate and fan-in issues are coverage/design-boundary findings, not proof that Link owns the wrong thing.
- "Gemini was live-called by `--all`" was rejected. This audit saw fixture/env and explicit live-call-blocking behavior, not real Gemini credential validation.
- "Local checker green proves release protection" was rejected. CI/branch
  protection required-gate wiring was not proven.
- "Deployment hardening can be captured by text pins only" was rejected. The
  high-risk surfaces need fixture or behavioral negative probes.

## Verdict

`ISSUE`.

The checker system has real teeth: `--self-test` passes, `--all` passes, profile dispatch is closed, arbitrary checker file paths are rejected, YAML duplicate false-greens are blocked, live provider calls are guarded during sweeps, and many high-risk boundaries have executable probes. It is not clear because green preserves some disputed invariants, several high-risk gaps are untested, ordinary sweeps can write transient fixture vessels into the checkout, checker files are godmodule-heavy, and maps/wording lag current reality.
The deployment addendum also leaves the checker surface `ISSUE`: local checker
strength is not proven as a CI/branch-protection release gate, and deployment
risks such as release-export secrets, dashboard ingest replay, and sensitive
write publication need executable negative probes.

Readiness tuple: use `brick-6-surface-audit-readiness-tuples-0630.md` for implementation priority. S5 is `core_sound: partial/strong-with-gaps`, `axis_integrity_blockers: 2`, `ship_safety_blockers: 5`, `dynamic_runtime_not_proven: yes`, and `worst_severity: high`. The flat `ISSUE` label is only a findings-inventory label; checker green remains support evidence, not release/customer readiness by itself.

## Next Work Candidates

1. Add a checker-first repair for fan-in return-shape preservation: Brick return shape remains full; Link carry/closure synthesis filters downstream fields.
2. Add a pre-persistence chat-session validator for AgentFact forbidden top-level verdict/Movement keys.
3. Add a negative probe for missing `declared_gate_refs` or explicitly admit the default-transition fallback as current law.
4. Add a runner-level no-live-worktree-mutation guard for `--all`, or move fixture vessels to temp repo copies/output roots.
5. Split `kernel_checks.py`, `case_runners.py`, and `check_bounded_agent_proposed_routing_loop0.py` by family with facade-preserving dispatch IDs.
6. Refresh checker count/map docs and avoid fixed counts in constitutional text unless the count is mechanically checked.
7. Convert high-risk text pins into structured or behavioral checks where possible; keep exact-message pins only where the text itself is the invariant.
8. Add profile-lint coverage for duplicate path pins, non-empty proof limits, non-empty `not_proven`, and at least one active tooth.
9. Centralize checker-sweep no-live-provider enforcement so preflight and local CLI surfaces cannot drift.
10. Convert live-source mutation debug probes to temp-copy probes or clearly separate them from ordinary checker usage.
11. Add release-export negative probes for untracked `.env`, tracked forbidden
    secret paths, dirty checkout refusal, and explicit safe `--include-untracked`.
12. Add dashboard ingest negative probes for missing signature, wrong HMAC, old
    timestamp, duplicate event id, and sequence rollback.
13. Add a customer-sandbox negative probe where a provider writes a sensitive
    path and the output commit is blocked or explicitly marked.
14. Add CI workflow/required-gate evidence or a checker that fails when the
    release profile is not wired into the admitted release path.
15. Add raw evidence stream secret/PII scrub negative probes.
16. Add post-HOLD resume isolation probes.
17. Remove or repair the dead pytest declaration.
18. Make profile fixture roots reentrant or temp-isolated.
19. Inspect `module_registry.yaml` and `crossing_registry.yaml` before checker
    diet or deletion.

## Not Proven

- Real provider, Slack, dashboard, or network behavior.
- Semantic correctness of every checker green.
- Complete BRICK six-surface coverage.
- That all profile text pins are meaningful.
- Safe deletion of duplicated pins, retired refs, pycache residue, or old checkers.
- That future profiles cannot be toothless without additional schema guards.
- That `--all` can be treated as read-only beyond final clean tracked state.
- GitHub Actions or branch protection required checks.
- Deployment negative probes for release export, dashboard ingest integrity, and
  sensitive-write commit blocking.
