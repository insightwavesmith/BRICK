# BRICK 6-Surface Architecture Audit - S4 Support Machine - 2026-06-30

## Surface

- Surface: Support machine.
- Target checkout: `/Users/smith/projects/BRICK`.
- Commit: `17eaade696998cd0de7bbd85ceb7525f349588e9`.
- Mode: audit only. No source repair was performed.
- Verdict: `ISSUE`.

## Map

Support owns mechanics for expanding declared inputs, walking declared Building
roads, isolating customer worktrees, recording evidence, rendering projections,
and delivering admitted report packets. It is not a Brick / Agent / Link axis.

Primary support surfaces inspected:

- `support/operator/cli.py`
- `support/operator/driver.py`
- `support/operator/run.py`
- `support/operator/dynamic_walker.py`
- `support/operator/walker_*.py`
- `support/operator/plan_validation.py`
- `support/operator/composition_*.py`
- `support/operator/assembly.py`
- `support/operator/onboard.py`
- `support/operator/evidence_assembly.py`
- `support/operator/frontier_observation.py`
- `support/operator/reporter.py`
- `support/operator/report_sinks.py`
- `support/operator/runtime_env.py`
- `support/operator/native_dispatch.py`
- `support/recording/*`
- `support/connection/*`

Observed official route:

1. Public CLI entry is `brick = brick_protocol.support.operator.cli:main`.
2. `brick build` task/preset mode calls `run_customer_building_in_sandbox`.
3. `brick build --graph-packet` mode calls `run_customer_graph_building_in_sandbox`.
4. The driver writes a declared graph plan and delegates to `run_building_plan`.
5. `run_building_plan` validates the declared plan and walks it through the
   dynamic graph walker.
6. Evidence writers persist raw, step-output, claim trace, lifecycle, building
   map, and read-side projections.
7. Frontier observation reads persisted evidence and reports state; it does not
   prove success, quality, Movement authority, or provider behavior.

## Evidence

Parallel attack review used 9 lanes:

- `S4-map`
- `S4-godmodule`
- `S4-dup-dead`
- `S4-axis-leak`
- `S4-contract`
- `S4-runtime`
- `S4-checker`
- `S4-simplicity`
- `S4-adversarial`

Codex operator direct checks:

- `git status --branch --short --untracked-files=no`
- `git rev-parse HEAD`
- `nl -ba` reads of `support/operator/onboard.py`, `driver.py`, `run.py`,
  `cli.py`, `assembly.py`, `reporter.py`, `report_sinks.py`,
  `walker_frontier_driver.py`, `walker_kernel.py`, `plan_validation.py`, and
  `pyproject.toml`.
- `rg -n` for approval defaults, report policy, graph wrappers, and support
  authority terms.
- `wc -l` over large support modules.
- Checkout hook activation probes for `.codex/hooks.json` and
  `.claude/settings.local.json`.

Direct checker evidence:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile core`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile driver_public_intake_seal`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile building_operator_driver0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile read_side_projection_boundary`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile report_env_autoload`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile native_dispatch_brick_backstop`

All listed profiles passed. Proof limit: profile green is support evidence
only. It does not prove source truth, success judgment, quality judgment,
Movement authority, live provider behavior, Slack delivery reliability, or
complete future coverage.

## Findings

### S4-F1 - `onboard approve` carries hidden default Link disposition author/action

- Severity: high.
- Axis attribution: Link lifecycle disposition, with support CLI/convenience
  wrapper as the leaking surface.
- Evidence:
  - `support/operator/onboard.py:1667-1687` defines
    `run_goal_approve_entry` with default `action="forward"` and
    `author_ref="coo:smith"`.
  - `support/operator/onboard.py:2281-2299` defines `run_approve_entry` with
    the same default `action="forward"` and `author_ref="coo:smith"`.
  - `support/operator/onboard.py:2504-2531` writes a disposition row into
    `raw/link.jsonl` with `transition_lifecycle_disposition_action` and
    `transition_author_ref`.
  - `support/operator/onboard.py:2544-2549` then calls `resume_building_plan`.
  - CLI defaults repeat at `support/operator/onboard.py:2622-2631` and
    `support/operator/onboard.py:2681-2690`.
- Meaning: this is not the core Link engine inventing Movement. It is a support
  convenience surface silently defaulting the human/COO disposition action and
  author when the caller omits them. That is too close to Link/caller/COO
  authority and should fail closed or require explicit disposition input. Claude
  review C14 sharpens this: author prefixes are still checked, so the leak is
  not unbounded authoring; the sharper risk is silent default action/identity,
  especially on the post-HOLD `approve` path that resumes a Building.
- Proof status: confirmed by direct code reads. No mutation performed.

### S4-F2 - Support owns a live frontier queue/pool for dynamic fan execution

- Severity: medium-high.
- Axis attribution: Support runtime mechanics, with Link/Brick boundary wording
  risk.
- Evidence:
  - `support/operator/walker_frontier_driver.py:24-34` says `_FrontierDriver`
    owns the live frontier queue and cursor.
  - `support/operator/walker_kernel.py:947-973` seeds the initial attempt queue
    and instantiates `_FrontierDriver`.
  - `support/operator/walker_kernel.py:1004-1012` defaults declared fan graphs
    to `_FANOUT_AUTO_POOL` when no explicit override is present.
  - `support/operator/walker_kernel.py:1086-1117` dispatches ready batches with
    `ThreadPoolExecutor`.
  - `support/operator/walker_kernel.py:1292-1336` drains pending outcomes and
    ready batches.
- Meaning: this is not proven to be Link target or Movement selection; it walks
  a declared graph. Claude review C12 narrows the original wording: the walker
  owns an internal frontier queue and ThreadPool for declared fan execution, but
  the no-scheduler/queue/retry prohibition is mainly aimed at undeclared product
  scheduler/queue/retry runtime and projection buses. This is a dynamic-runtime
  proof gap and wording seam, not an automatic constitutional violation.
- Proof status: confirmed as support runtime complexity and wording tension,
  not confirmed as route invention.

### S4-F3 - Absent report policy defaults to external sink refs with real-delivery flags

- Severity: medium-high.
- Axis attribution: support reporting/projection side effects, not BAL Movement.
- Evidence:
  - `support/operator/reporter.py:219-228` says an absent
    `report_event_policy` defaults to local inbox plus env-gated external
    sinks.
  - `support/operator/reporter.py:206-210` includes local inbox, Slack, and
    dashboard in the default sink refs.
  - `support/operator/reporter.py:308-323` sets
    `allow_real_slack_delivery=True` and
    `allow_real_dashboard_delivery=True` in the default policy.
  - `support/operator/reporter.py:1398-1407` removes external sinks for
    non-real-vessel roots.
  - `support/operator/report_sinks.py:359-409` fans packets out to Slack and
    dashboard sink handlers.
  - `support/operator/report_sinks.py:525-543` still requires
    `allow_real_delivery=True` before real Slack send.
  - `support/operator/report_sinks.py:545-560` records missing env as
    not-attempted without storing token bodies.
- Meaning: external delivery is gated and bounded, but support defaulting
  external targets and real-delivery flags is not the same as an explicit caller
  report policy. This is a projection side-effect risk.
- Proof status: confirmed by direct code reads. Live Slack/dashboard delivery
  remains `NOT_PROVEN`.

### S4-F4 - Official route has multiple wrapper surfaces and a checker blind spot

- Severity: medium.
- Axis attribution: support entrypoint/projection, not Brick/Link authority by
  itself.
- Evidence:
  - `pyproject.toml:22-23` exposes the `brick` CLI.
  - `support/operator/cli.py:330-409` routes graph packets and task/preset
    builds into customer sandbox wrappers.
  - `support/operator/driver.py:323-462` materializes intent and delegates to
    the run surface.
  - `support/operator/driver.py:604-675` exposes preset sandbox dispatch.
  - `support/operator/driver.py:678-737` exposes graph-packet sandbox dispatch.
  - `support/operator/assembly.py:763-830` exposes `fire()` as P3 sugar over
    the same graph route.
  - `driver_public_intake_seal` passed and reports `making_intake_exports` only
    as `run_building_intake`; it does not make wrapper/public-sugar ambiguity a
    behavioral proof.
- Meaning: the official route is present, but its public/support surfaces are
  broader than a single obvious function name. Future operators can still drift
  into `assembly.fire()` or wrapper semantics unless Product/P3 docs make the
  route rule sharper.
- Proof status: confirmed as route-surface complexity. No duplicate engine was
  proven.

### S4-F5 - Source-fact body carrying is fail-closed for task/step-output refs but best-effort for other file refs

- Severity: medium.
- Axis attribution: Brick/Agent source-fact crossing, support prompt assembly.
- Evidence:
  - `support/operator/plan_validation.py:935-997` fail-closes
    `task_source_ref` admission for missing or unsafe task files.
  - `support/operator/run.py:2116-2132` fails closed for missing
    step-output source fact bodies.
  - `support/operator/run.py:2173-2187` skips unreadable, missing, or
    undecodable non-step-output source facts.
- Meaning: task source and step-output references are protected, but arbitrary
  source-fact refs are not uniformly hard requirements. Do not overclaim
  complete source-fact preservation across every prompt input.
- Proof status: confirmed as a policy gap / proof limit.

### S4-F6 - Native-dispatch auto-recording is not active in this checkout

- Severity: medium.
- Axis attribution: support hook/projection activation, not Agent source truth.
- Evidence:
  - `support/onboarding/claude-hooks/*` and `support/onboarding/codex-hooks/*`
    exist.
  - Direct probes returned no `.codex/hooks.json` and no
    `.claude/settings.local.json` in this checkout.
  - `native_dispatch_brick_backstop` passed, proving the seam/evidence shape,
    not the machine hook installation state.
- Meaning: code/templates for child native-dispatch recording exist, but this
  checkout did not prove live hook activation. Claims that subagent child
  spawning is auto-recorded here should remain `NOT_PROVEN` unless onboarding
  recording evidence is shown.
- Proof status: confirmed as not active in this checkout by file-presence probe.

### S4-F7 - Support godmodule pressure is high and should not be treated as a safe-delete signal

- Severity: medium.
- Axis attribution: support mechanics concentration.
- Evidence:
  - `support/recording/spine_projection.py` is 2902 lines.
  - `support/operator/onboard.py` is 2849 lines.
  - `support/operator/walker_kernel.py` is 2306 lines.
  - `support/operator/reporter.py` is 2260 lines.
  - `support/operator/run.py` is 2240 lines.
  - `support/operator/plan_validation.py` is 2198 lines.
  - `support/connection/agent_resources.py` is 2007 lines.
  - `support/operator/report_sinks.py` is 1704 lines.
  - `support/operator/assembly.py` is 1478 lines.
  - `support/operator/composition_graph_emit.py` is 1353 lines.
  - `support/operator/composition_compose.py` is 1180 lines.
- Meaning: large support files are real architecture drag. Size alone does not
  prove authority leakage, and cleanup must be conservation-ledger/checker-first
  rather than deletion-first.
- Proof status: confirmed as maintenance risk.

### S4-F8 - Legacy path wording claim corrected after Claude review

- Severity: low-medium.
- Axis attribution: support/product projection drift correction.
- Evidence:
  - Original subagent evidence claimed `~/.brick/builds` appeared in
    CLI/status/init metadata.
  - Claude review challenged that claim, and direct re-measurement confirmed it:
    the only current repo occurrence of `.brick/builds` is
    `support/checkers/lib/kernel_checks.py:8541`, where it is an anti-regression
    checker message preventing revival of the legacy path.
  - Live resume/help wording points at `~/.brick/goal-runs`
    (`support/operator/onboard.py:2676`, `support/operator/onboard.py:2713`).
  - `building-evidence/` remains an admitted active evidence-destination term
    via `AGENTS.md:188` and `README.md:244`, not automatically stale wording.
  - Direct `core` and `read_side_projection_boundary` profiles passed, so this
    is not a proven active runtime root break.
- Meaning: the original S4-F8 finding was over-broad and partially false. Keep
  only a narrow stale-doc watch item for future root wording; do not list
  `~/.brick/builds` or `building-evidence/` as active drift based on this audit.
- Proof status: correction confirmed by direct repo search. Runtime root failure
  remains not proven.

### S4-F9 - Release export can include untracked unignored local files

- Severity: high.
- Axis attribution: support release mechanics and product/public export surface.
- Evidence:
  - External static deployment reports (`BRICK_main_static_architecture_deployment_review.md` and `.docx`) flagged release export as the highest deployment risk.
  - Direct read confirmed `support/onboarding/release_export.sh:114-125` collects files with `git ls-files -z --cached --others --exclude-standard`.
  - Direct read confirmed `.gitignore:1-16` ignores common caches but not `.env`, `.env.*`, `*.pem`, `*.key`, `.npmrc`, credential, secret, or token patterns.
  - Claude review C17 adds that the release script's own denylist excludes only
    `project` and `brick_protocol.egg-info`, so the copy stage itself has no
    secret/key/credential denylist.
  - The release script then initializes a fresh repo and creates an initial commit from the copied export tree.
- Meaning: a local untracked but unignored secret/config/report file can enter a public release export. This is support/product hardening, not a Brick/Agent/Link meaning change.
- Proof status: confirmed static path risk. No live secret leak was observed.

### S4-F10 - Dashboard ingest integrity is shared-secret-only

- Severity: high.
- Axis attribution: support dashboard/report projection.
- Evidence:
  - Direct read confirmed `support/dashboard/server/index.mjs:14-16` derives `INGEST_SECRET`; Claude review C4 corrected the earlier `14-17` locator because line 17 is a separate production flag.
  - Direct read confirmed production refuses absent/dev secret at `server/index.mjs:39-40` and `108-112`.
  - Direct read confirmed `/ingest` accepts seed/delta after only `x-ingest-secret` equality at `server/index.mjs:107-139`.
  - Claude review C16 adds that ingest uses ordinary string inequality rather
    than constant-time comparison, and that a non-production deployment without
    an explicit secret can accept the literal default `dev-secret`.
  - No timestamp, event id, HMAC over raw body, replay cache, or participant monotonic sequence was found in the ingest path.
  - `useDashboard.js:20-34` applies deltas only after a seed exists and does not track sequence.
- Meaning: dashboard is still only a projection, but projections drive operator perception. A leaked shared secret or old delta replay can alter the displayed projection without becoming source truth.
- Proof status: confirmed static gap. Network/dashboard exploit not executed.

### S4-F11 - Provider env and sensitive-write handling are deployment hardening gaps

- Severity: high.
- Axis attribution: support runtime/env and customer worktree commit bracket.
- Evidence:
  - `runtime_env.py:21-35` and `75-89` explicitly split report keys from provider keys and inject `GEMINI_API_KEY` / `GOOGLE_API_KEY` into global `os.environ` because Gemini reads them directly.
  - Claude review C15 credits the existing mitigations: runtime env loading is
    narrow, masks values, and enforces local file mode constraints. The residual
    is specifically the two provider key names entering parent `os.environ`
    because the Gemini path lacks a threaded subprocess-env seam.
  - `write_observation.py:85-92` and `281-295` explicitly say support records sensitive path writes and raises nothing.
  - `write_observation.py:141-144` records `observed_sensitive_path_writes` when present.
  - `driver.py:837-845` commits sandbox output when the frontier is `complete`; no sensitive-path commit block is visible in that bracket.
  - Claude ADD-9 strengthens the decoupling: direct search over `driver.py` and
    `run.py` found no consumer of `observed_sensitive_path_writes` /
    `sensitive_path` on commit or resume paths.
- Meaning: this is not source-tree mutation of the live checkout, because customer work runs in a sandboxed worktree/temp dir. It is still a deployment hardening gap: `complete` must not be confused with permission to publish sensitive file edits.
- Proof status: confirmed static gap. No live provider write was executed.

### S4-F12 - Dashboard container and viewer access rely on deployment environment hardening

- Severity: medium-high.
- Axis attribution: support dashboard deployment mechanics.
- Evidence:
  - `support/dashboard/Dockerfile:1-16` uses `node:22-slim` for build/runtime and defines no non-root `USER`, no digest pin, and no `HEALTHCHECK`.
  - `server/index.mjs:142-164` serves `/events`, `/dashboard-data.json`, and static assets after the external deployment wall; viewer auth is not implemented in the app itself.
  - External deployment reports correctly classify this as product hardening, not dashboard source-truth authority.
- Meaning: Cloud Run/IAP or reverse-proxy access walls can be the intended auth boundary, but customer deployment docs should make that precondition loud and fail-closed where possible.
- Proof status: confirmed static gap. Cloud Run/IAP configuration was not verified.

## External Review Incorporation

Claude review, Smith/operator follow-up, and external deployment reports sharpened
S4 in eight ways.

1. Resume/post-HOLD isolation is a first-order support seam.
   - Claude ADD-1 shows `run_approve_entry` calls `resume_building_plan`
     directly after writing a disposition row.
   - That path does not route through the same `_run_in_worktree_sandbox`
     wrapper credited for fresh customer runs.
   - The risk depends on supplied `adapter_cwd`, but the wrapper itself does not
     enforce the live-tree-untouched invariant on this resume path.

2. Raw evidence stream scrub is separate from release export scrub.
   - Claude ADD-2 shows raw streams such as `raw/brick-work.jsonl`,
     `raw/agent-received.jsonl`, and `raw/adapter-error.jsonl` are persisted by
     raw recording writers before release/export hardening ever sees them.
   - The audit had focused on local secret files entering export. This is an
     earlier ledger-persistence integrity issue.
   - Repair should add a guard/redaction seam or a checker proving raw stream
     writers are covered.

3. Release export is unguarded at both input and copy stages.
   - External reports and Claude C17 agree that tracked plus untracked-unignored
     export is risky.
   - `.gitignore` lacks common secret/local config patterns, and the export
     script's own denylist is not a secret denylist.

4. Dashboard ingest needs deployment-grade integrity.
   - Shared-secret equality is not enough for a customer/public dashboard.
   - Required repair candidates: HMAC over body, timestamp skew, event id replay
     cache, participant sequence, and fail-closed production secret rules.
   - Claude ADD-19 adds a lower-tier memory/stale-participant surface: module
     globals for participants/clients can grow or preserve stale state unless
     the product deployment model bounds them.

5. Provider env and sensitive-write handling must be explained as deployment
   hardening, not axis law.
   - Provider keys entering `os.environ` is a support runtime/env compromise for
     Gemini-local behavior, not Agent source truth.
   - Sensitive path writes are observed, not blocked; publication/commit policy
     must decide what to do with the observation.

6. Internal frontier queue/pool is not a fourth axis.
   - It walks declared graph work. It does not by itself select Movement.
   - The remaining S4 issue is dynamic proof and wording: static audit cannot
     certify ordering/interleaving behavior.

7. Deployment/security findings should not be forced into Brick/Agent/Link
   attribution.
   - Smith and Claude both pushed this distinction: some S4 findings are
     infra/support hardening, not axis ownership defects.
   - The report should name them as support/product deployment risks while
     preserving the rule that support is not a fourth meaning axis.

8. Readiness/failure attribution can be projected from existing support facts.
   - `frontier_kind`, `missing_required_file_count`, `next_action_observation`,
     adapter-error frontier evidence, write observations, and dashboard rows
     already provide deterministic reason categories.
   - The missing product layer is a read-side `readiness_blocker_observation` /
     `protocol_compliance_observation`, not a new Movement or success judge.

## Controls That Hold

- `run_building_intake` states it sequences materialize -> write plan ->
  `run_building_plan`, and does not choose Movement, preset, sufficiency,
  quality, or success.
- Customer build wrappers isolate writes in worktree/temp sandboxes and commit
  only after the persisted frontier reports `complete`.
- `plan_validation` and `run_building_plan` still validate declared rows before
  dynamic walking.
- Reporter packet and sink validators forbid authority fields and credential
  bodies.
- Report env loading is allowlist/permission gated and the
  `report_env_autoload` profile passed.
- Native dispatch seam shape is checked by `native_dispatch_brick_backstop`.
- `support_no_axis_judgment` passed inside `core`.
- Customer build wrappers isolate writes from the live checkout; the sensitive
  write concern is about commit/publication of sandbox output, not direct live
  repo mutation.
- Dashboard/export/report surfaces continue to state projection/proof-limit
  boundaries; the hardening gaps do not make them source truth.

## Rejected Shortcuts

- "Support is the fourth axis" was rejected. Support remains mechanics and
  evidence/projection.
- "The core engine chooses Movement" was rejected. No arbitrary support-invented
  Movement/target was proven in the checked run/walker/composition path.
- "Queue word means broken engine" was rejected. The observed queue is an
  internal frontier queue for declared fan graph execution, but it conflicts
  with broad no-queue wording and needs disposition.
- "Checker green proves customer readiness" was rejected. It proves scoped
  checker invariants only.
- "Slack arriving proves the official route" was rejected. Slack is a support
  projection sink and can be defaulted; route proof must still come from
  declared plan/run evidence.
- "Native-dispatch checker green proves live hook installation" was rejected.
  The hook templates exist, but local checkout activation was not observed.
- "Dashboard ingest risk makes dashboard source truth" was rejected. The risk is
  projection integrity and operator perception, not authority over BAL facts.
- "Release export risk proves a leak happened" was rejected. The static path can
  include untracked unignored files, but no actual exported secret was observed
  in this audit.

## Verdict

`ISSUE`.

The support machine is mostly walking declared roads rather than owning Brick /
Agent / Link meaning. The official `brick build` route exists and core
validation/projection checkers are green. The surface is not clear because
support defaults human/COO disposition values in `onboard approve`, owns a live
frontier queue/pool whose wording collides with the no scheduler/queue rule,
defaults absent report policy to external sink refs with real-delivery flags,
exposes multiple route wrapper/sugar surfaces, skips arbitrary source-fact file
refs best-effort, has unproven local native-dispatch hook activation, and carries
large godmodule pressure across key support files. The deployment addendum raises
additional support/product hardening issues: public release export can include
untracked unignored local files, dashboard ingest lacks HMAC/replay/sequence
protection, provider keys still enter global `os.environ` for Gemini, sensitive
path writes are recorded but do not block sandbox output commit, and dashboard
container/viewer hardening is environment-dependent.

Readiness tuple: use `brick-6-surface-audit-readiness-tuples-0630.md` for implementation priority. S4 is `core_sound: partial`, `axis_integrity_blockers: 3`, `ship_safety_blockers: 8`, `dynamic_runtime_not_proven: yes`, and `worst_severity: high`. The flat `ISSUE` label is only a findings-inventory label; support remains support, not a fourth axis.

## Next Work Candidates

1. Make `onboard approve` and `goal-approve` require explicit action/author, or
   clearly separate default examples from actual Link disposition rows.
2. Narrow the constitution/checkers around "no scheduler/queue/retry runtime" so
   declared-graph internal frontier queues are either admitted as support
   walking mechanics or rejected with a focused checker.
3. Require explicit `report_event_policy` for external sinks, or make absent
   policy default to local-only while preserving declared external delivery.
4. Extend route-surface checks so `brick build`, graph-packet mode, driver
   wrappers, and `assembly.fire()` are classified as official route, sugar, or
   internal surface with no ambiguity.
5. Decide whether non-step-output `source_facts` are best-effort context or
   required prompt evidence; add a negative probe for whichever policy is
   admitted.
6. Add a machine-state/onboard-recording proof for native-dispatch hook
   activation before claiming child native-dispatch recording is live.
7. Treat support godmodule cleanup as later facade-preserving decomposition with
   conservation ledgers, not broad deletion.
8. Harden `release_export.sh`: tracked-only by default, explicit
   `--include-untracked`, dirty-tree guard, and secret/local denylist.
9. Add dashboard ingest integrity: timestamp, event id, HMAC over raw body,
   replay cache, and participant sequence.
10. Add a provider-env threaded seam so provider keys do not need parent
    `os.environ` mutation.
11. Block or loudly mark sandbox output commits when sensitive path writes are
    observed.
12. Harden dashboard container/deploy docs: pinned image/digest policy,
    non-root runtime, healthcheck, and explicit viewer access-wall requirement.
13. Add raw evidence stream scrub/redaction or refusal before JSONL persistence,
    with checker coverage for common credential/token/PII-looking patterns.
14. Route post-HOLD resume through an equivalent sandbox/isolation bracket or
    require explicit isolated `adapter_cwd` before `resume_building_plan`.
15. Add dynamic proof for fan-out/fan-in and resume-across-HOLD before treating
    static audit reassurance as runtime proof.

## Not Proven

- Live provider behavior and provider credential validity.
- Production runtime behavior.
- Slack/dashboard/thread-wake delivery reliability.
- Dashboard ingest replay/HMAC/sequence protection.
- Release export cleanliness with synthetic untracked secret fixtures.
- Raw stream secret/PII scrub coverage.
- Post-HOLD resume live-tree isolation.
- Container hardening and production viewer access wall configuration.
- Native child-spawn auto-recording in this checkout.
- Semantic correctness of Agent `transition_concern_evidence`.
- Caller/COO disposition correctness after HOLD.
- Complete absence of future support-authority leaks.
- Safe deletion or split of large support modules.
