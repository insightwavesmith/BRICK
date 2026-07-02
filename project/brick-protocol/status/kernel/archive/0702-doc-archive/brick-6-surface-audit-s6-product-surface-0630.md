# BRICK 6-Surface Architecture Audit - S6 Product Surface - 2026-06-30

## Surface

- Surface: Product surface.
- Target checkout: `/Users/smith/projects/BRICK`.
- Commit: `17eaade696998cd0de7bbd85ceb7525f349588e9`.
- Mode: audit only. No source repair was performed.
- Verdict: `ISSUE`.

## Map

Product surface owns customer-facing entry, install/init/doctor/onboarding wording, CLI ergonomics, release/install shell surfaces, docs/FIRST_USE, and the declaration experience for "make X". It does not own Brick work meaning, Agent performer meaning, Link Movement, source truth, success judgment, quality judgment, provider proof, or customer-ready proof.

Primary product surfaces inspected:

- `pyproject.toml`
- `README.md`
- `support/operator/cli.py`
- `support/operator/onboard.py`
- `support/onboarding/install.sh`
- `support/docs/references/quickstart.md`
- `support/docs/references/setup.md`
- `support/docs/references/launch-guide.md`
- `support/docs/references/architecture-map.md`
- `support/docs/references/checker-profile-map.md`
- `support/checkers/profiles/brick_cli_entrypoint.yaml`
- `support/checkers/check_first_use_wizard.py`
- `brick/templates/skills/brick-task-author/SKILL.md`
- `brick/templates/skills/building-sizing-method/SKILL.md`
- `agent/skills/task_intake/SKILL.md`

Observed public route:

1. `pyproject.toml` exposes the `brick` console script through `brick_protocol.support.operator.cli:main`.
2. `brick init` runs the install wizard.
3. `brick status`, `brick doctor`, and `brick check` expose read-side/customer diagnostics.
4. `brick build --task ... [--preset ...]` uses the `preset_task` input mode.
5. `brick build --graph ...` uses the `graph_packet` input mode.
6. Both build modes delegate to official support wrappers and then to `run_building_plan()` / graph walking evidence.
7. Helper APIs such as `run_building_plan`, `run_composed_graph_intake`, `assembly.build`, `fan`, and `fire` are internal/advanced support surfaces, not separate customer routes.

Observed declaration route for large work:

1. `task_intake` extracts project, scope, risk, artifact, and shape candidates.
2. `brick-task-author` chooses preset mode when an existing shape is enough.
3. `brick-task-author` chooses graph-packet mode when fan-out, fan-in, or a new multi-stage shape is needed.
4. `building-sizing-method` describes the desired large-work shape: task intake -> design -> design QA / axis QA -> closure plan confirm -> parallel dev lanes -> per-lane QA -> fan-in -> final Codex QA + Gemini axis QA -> Codex closure.
5. The official route remains `brick build`; the large-work declaration should be sugar over `preset_task` or `graph_packet`, not a new engine, CLI lane, or hidden `--large` path.

## Evidence

Parallel attack review used product-surface lanes plus external model support evidence:

- `S6-map`
- `S6-cli`
- `S6-install-onboard`
- `S6-doc-stale`
- `S6-declaration-ergonomics`
- `S6-adversarial`
- ai-cli product-route attack review
- ai-cli P3 easy-building attack review
- ai-cli fresh-machine/customer-ready attack review

Codex operator direct checks:

- `git -C /Users/smith/projects/BRICK status --branch --short --untracked-files=no`
- `git -C /Users/smith/projects/BRICK rev-parse HEAD`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 -m brick_protocol.support.operator.cli --help`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 -m brick_protocol.support.operator.cli build --help`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 -m brick_protocol.support.operator.cli status --json`
- Parser probes for `build --graph`, `build --graph ... --task ...`, `build --large`, and `onboard`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile brick_cli_entrypoint`
- Targeted reads of CLI, driver, run, onboard, install, docs, product skills, and checker profile sources.

Direct green evidence:

- `brick_cli_entrypoint` passed.
- `brick --help` exposes `init`, `build`, `verify`, `check`, `doctor`, `status`, and `auth`.
- `brick build --help` exposes `--task`, `--task-source-ref`, `--preset`, `--adapter`, `--real-provider`, and `--graph/--graph-packet`.
- `brick build --large ...` is rejected.
- `brick onboard` is rejected; onboard remains a module/helper seam, not the public CLI verb.
- `brick status --json` reports repo root, default build root, proof limits, and not-proven claims.
- The profile forbids `adapter:gemini-api`, `--large`, `_p3_easy_large`, `--dev-lanes`, and `lane_return`.

Proof limit: product docs, CLI output, Slack packets, checker green, and model review are support evidence only. They do not prove customer comprehension, provider reliability, install reliability, source truth, success, quality, or Link Movement.

## Findings

### S6-F1 - The official customer route exists and is checker-covered

- Severity: positive finding with proof limits.
- Axis attribution: support/product projection walking Brick-declared plans, Agent-selected adapters, and Link-owned movement.
- Evidence:
  - `pyproject.toml` maps `brick` to `brick_protocol.support.operator.cli:main`.
  - `cli.py` exposes `brick build` with `preset_task` and `graph_packet` modes.
  - `driver.py` routes task mode through `run_customer_building_in_sandbox()`.
  - `driver.py` routes graph mode through `run_customer_graph_building_in_sandbox()`.
  - `run.py` remains the public single-Building runner and auto-loads local report/provider environment.
  - `brick_cli_entrypoint` passed.
- Meaning: P3 should not invent a second build route. The product surface already has one official route; repair should improve declaration ergonomics and docs around it.
- Proof status: confirmed current implementation. Fresh-machine and customer comprehension are not proven.

### S6-F2 - Install/init/onboard wording is drifted across the customer docs

- Severity: high.
- Axis attribution: product/support projection drift.
- Evidence:
  - `README.md` and `quickstart.md` still teach `uv run python3 -m brick_protocol.support.operator.onboard codex` as a visible early step.
  - `install.sh` now installs the `brick` entrypoint and runs `brick init --non-interactive`.
  - Actual install output names `5) brick 진입점 설치 완료` and `6) brick init 완료`.
  - README/quickstart expected output still mentions the older `5) 설치 점검 완료` wording.
  - `brick onboard` is not a valid CLI command.
- Meaning: the code path has moved toward `brick init` and `brick build`, but customer docs still expose the older module seam in a way that can look like a second route.
- Proof status: confirmed by direct parser probe and file reads.

### S6-F3 - Graph packet docs blur compact graph packets with full Building Plan internals

- Severity: high.
- Axis attribution: product docs exposing support/Brick plan internals.
- Evidence:
  - `brick build --graph` expects a compact JSON object with `task_statement`, `declared_by`, `building_id`, nodes, and edges.
  - `driver.py` rejects customer graph packets that include template-authority fields such as `required_return_shape`, `carries_forward_fields`, `brick_instruction_body`, or `brick_template_refs`.
  - `quickstart.md` documents `brick build --graph`, then immediately shows a direct `run_building_plan()` full plan with `plan_shape`, `execution_order`, `brick_steps`, and `link_edges`.
- Meaning: users and future operators can confuse "declared graph packet" with "full internal Building Plan". That is how manual return-shape/ref mistakes re-enter.
- Proof status: confirmed docs/implementation mismatch.

### S6-F4 - P3 Easy Building is only partially surfaced

- Severity: high.
- Axis attribution: product declaration ergonomics over Brick/Agent/Link composition.
- Evidence:
  - `brick-task-author` and `building-sizing-method` describe the intended large-work flow.
  - `agent/skills/task_intake` explicitly says not to hard-code one `work -> QA -> closure` path and to extract LLM, Brick kinds, and graph shape.
  - `--large` and `_p3_easy_large` are absent/rejected, which is correct.
  - Public CLI has no guided "this is big; design first; split into parallel lanes" option.
  - Current docs do not clearly teach the natural-language-to-graph workflow.
  - The existing `design-build-parallel` preset is a useful preset, but it is not proof of the full desired dynamic design -> reviewed split -> parallel dev lane materialization.
- Meaning: P3 should be framed as declaration sugar and operator skill over the official route, not a hard-coded `large` mode or a new engine. Current product surface does not yet make that easy enough for a customer.
- Proof status: partially confirmed. The desired ergonomics are not proven.

### S6-F5 - Provider story is mostly current, but customer-ready provider reliability is not proven

- Severity: medium-high.
- Axis attribution: Agent adapter projection and product readiness wording.
- Evidence:
  - Active CLI real-provider selection order is Claude, Codex, Gemini.
  - `adapter:gemini-api` is rejected by checker/profile; active Gemini is local CLI with API key environment.
  - `doctor` reports adapter refs, auth state, `api_key_env_present`, and credential validity.
  - `brick build --real-provider` uses first ready provider and falls back honestly when none is ready.
  - Prior proof docs record provider-backed and dogfood runs, but they are narrow and at older commits/proof scopes.
- Meaning: there is no proven hidden requirement that only Claude can run the customer route, but current product proof still does not establish repeated provider reliability or a clean fresh-machine provider story at this exact commit.
- Proof status: current wiring confirmed. Provider reliability and fresh auth proof not proven.

### S6-F6 - Slack/reporting is optional support evidence, but docs still imply manual setup details that drifted

- Severity: medium.
- Axis attribution: support reporter/product docs.
- Evidence:
  - `run.py` auto-loads `~/.brick/report.env` and passes reporter environment to Slack/dashboard sinks when configured.
  - `reporter.py` has local inbox, Slack, and dashboard event policy, with Slack/dashboard environment-gated.
  - `launch-guide.md` still tells the user to manually `source ~/.brick/report.env`.
  - Slack delivery is not a source truth, quality judgment, success judgment, or Movement authority.
- Meaning: Slack can be useful progress evidence, but lack of Slack is not itself proof the official route did not run. The docs should match the auto-load behavior and state the support-evidence limit clearly.
- Proof status: implementation confirmed; Slack reliability not proven.

### S6-F7 - Customer docs contain stale counts, stale worktree references, and stale provider timing

- Severity: medium-high.
- Axis attribution: product/support projection drift.
- Evidence:
  - Live profile count is 28, but active docs still contain 24-profile and 13-profile references.
  - `brick/templates/README.md` still says 17 presets while live preset count is 28.
  - `checker-profile-map.md` still references `struct-surgery-0623`.
  - Product skills contain stale weekend/Monday Claude-token wording.
  - Some project status docs expose machine-local proof paths such as `.brick` worktrees as proof evidence.
- Meaning: stale references are not source truth, but they are dangerous on the product surface because customers and future agents can mistake them for current operation.
- Proof status: confirmed drift. Safe rewrite scope not performed in this audit.

### S6-F8 - Fresh-machine customer-ready claim is not proven at current HEAD

- Severity: high.
- Axis attribution: product proof boundary.
- Evidence:
  - Existing P7/P8/proof docs are useful support evidence but were produced under narrower commits, scopes, or host assumptions.
  - Direct status/doctor checks in this audit are current-machine evidence only.
  - `install.sh` is clone-first and owner/repo dependent.
  - ai-cli support review found one-command fresh install, real provider auth, Slack delivery, and customer comprehension not proven.
- Meaning: BRICK may be much closer than the old worktrees suggest, but broad customer-ready language needs a fresh proof at current main or a narrower claim.
- Proof status: not proven at `17eaade696998cd0de7bbd85ceb7525f349588e9`.

### S6-F9 - Release/export path is bounded but can still carry untracked unignored files

- Severity: high.
- Axis attribution: product release support mechanics.
- Evidence:
  - External static deployment reports identified this as the highest productization risk.
  - Direct read confirmed `support/onboarding/release_export.sh:114-125` uses `git ls-files -z --cached --others --exclude-standard`.
  - Direct read confirmed `.gitignore:1-16` does not ignore `.env`, `.env.*`, `*.pem`, `*.key`, `.npmrc`, credential, secret, or token patterns.
  - The release script then creates a fresh git repository and initial commit from copied files.
  - Current untracked audit docs live under excluded/project-local status surfaces for this audit, so they are not evidence of an actual leak.
  - Claude review C17 adds that the export script's own denylist excludes only
    `project` and `brick_protocol.egg-info`; it does not provide a second
    secret/key/credential denylist at copy time.
  - No source mutation was performed.
- Meaning: this is not an observed release leak, but it is a P0/P1 customer-publication risk. A local `.env` or key file in the checkout can be untracked, unignored, and copied into the public export.
- Proof status: risk confirmed by support review; live release leak not proven.

### S6-F10 - Product surface names still mix "front door" and "internal helper"

- Severity: medium.
- Axis attribution: product/support terminology.
- Evidence:
  - `launch-guide.md` clearly says helper APIs are advanced/internal and the customer route is `brick build`.
  - `architecture-map.md` still labels `assembly.py` as a customer front door.
  - `brick-task-author` correctly warns that `fire()`, `assemble()`, and helper calls are material, not the public route.
- Meaning: the official route can remain one route, but vocabulary drift makes future operators re-open side routes or hand-build graph internals.
- Proof status: confirmed wording mismatch.

### S6-F11 - Dashboard product surface lacks ingest integrity and container hardening

- Severity: high.
- Axis attribution: product/dashboard support projection.
- Evidence:
  - Direct read confirmed `support/dashboard/server/index.mjs:107-139` accepts ingest with shared-secret equality through `x-ingest-secret`.
  - Claude review C16 adds two product-hardening details: ingest uses ordinary
    string inequality rather than constant-time comparison, and non-production
    deployment can accept the literal default `dev-secret` when no explicit
    secret is configured.
  - No HMAC, timestamp skew check, event id, replay cache, or participant sequence was observed.
  - Direct read confirmed `support/dashboard/src/data/useDashboard.js:20-34` has no sequence handling; a delta without prior seed is ignored.
  - Direct read confirmed `support/dashboard/Dockerfile:1-16` uses `node:22-slim` without digest pin, non-root user, or healthcheck.
  - `Link.jsx:7-10` and `labels.js:42-49` keep active Movement and historical/lifecycle aliases close together in the UI.
- Meaning: dashboard remains a projection, not source truth. The product risk is that the operator-visible projection can be stale, replayed, out of order, or visually confusing during deployment.
- Proof status: confirmed static gap. Network exploit, Docker build, and Cloud Run/IAP configuration were not tested.

### S6-F12 - Provider write boundary needs customer-visible matrix

- Severity: high.
- Axis attribution: Agent adapter projection exposed through product CLI/docs.
- Evidence:
  - External deployment reports separated provider boundary strength by adapter.
  - Direct read confirmed Codex uses an isolated temp `CODEX_HOME` shape in `adapter_local_cli.py:89-110`.
  - Direct read confirmed Claude keeps real `HOME` for keychain auth and relies on provider flags/settings rather than an OS-level hard sandbox.
  - Direct read confirmed Gemini provider keys are carried through env paths and `runtime_env.py` injects Gemini keys into global `os.environ`.
- Meaning: customer docs/JSON should not imply that all write-capable providers have the same hard boundary. Effective write is still Brick NEED + Agent policy + adapter capability + observation, but provider boundary strength differs.
- Proof status: static wiring confirmed. Live provider behavior not proven.

### S6-F13 - CI/branch-protection release gate is not proven

- Severity: high.
- Axis attribution: product release governance / checker support evidence.
- Evidence:
  - Direct measurement found zero files under `.github` in this checkout.
  - S5 showed local `check_profile.py --all` can pass, but local green is support evidence only.
  - Claude ADD-3 adds that the declared pytest surface is misleading: current
    verification is BRICK's checker/profile system, not a real pytest test
    suite.
  - External deployment reports correctly distinguish strong checker design from required merge/release enforcement.
- Meaning: checker strength is not product protection unless CI or an admitted release process requires it before main/public export.
- Proof status: local workflow absence confirmed. GitHub branch protection was not checked.

### S6-F14 - Dependency/release reproducibility policy is unclear

- Severity: medium.
- Axis attribution: product packaging.
- Evidence:
  - Direct read confirmed `pyproject.toml:18-20` declares `PyYAML>=6.0`.
  - Direct read confirmed `.gitignore:12` ignores `uv.lock`.
  - No release-resolution record or explicit no-lock policy was observed in this audit.
- Meaning: this is not a runtime bug, but a customer/release reproducibility gap. Either commit a lockfile for product releases or record the resolved dependency set during export.
- Proof status: static policy gap confirmed. Dependency resolution was not executed.

### S6-F15 - Install supply-chain and docs density need product treatment

- Severity: medium.
- Axis attribution: product install/docs.
- Evidence:
  - External deployment reports flagged the `curl | sh` uv installer path and dense README/AGENTS surface.
  - This audit already found install/init/onboard docs drift and stale counts/worktree/provider timing.
  - `README.md`, `AGENTS.md`, quickstart, setup, and launch-guide each carry different slices of the customer/operator story.
- Meaning: the install path can remain pragmatic, but customer-ready publication needs a short truth table and an enterprise/airgap/pinned-installer note.
- Proof status: product-doc risk confirmed. Installer network path was not executed.

### S6-F16 - Product surface should translate evidence into operator action without becoming authority

- Severity: high.
- Axis attribution: product projection over Brick/Agent/Link evidence.
- Evidence:
  - The attached product-surface strategy note argues that BRICK core is already a strong protocol/evidence/boundary/checker engine, and the missing layer is a safe operating surface.
  - Direct read confirmed CLI build output includes `frontier_kind`, `customer_visible_frontier_state`, `customer_visible_frontier_message`, `evidence_root`, `proof_limits`, and `not_proven`.
  - Direct read confirmed CLI output does not yet standardize every command around the four product fields: current state, reason, next action, proof limit.
  - Direct read confirmed `dashboard_export.py` carries a `nextAction` row field, and dashboard pages already group running / stopped / review / incomplete / closure pending states.
  - Direct read found no full dashboard Attention Queue / Next Action Card / Proof Limit Badge / Provider Boundary Badge product layer.
  - Current dashboard Building view distinguishes `마감 대기` from closed work, but product readiness states such as `needs_operator_action`, `ready_for_human_review`, and `manually_approved` are not a visible taxonomy.
- Meaning: the dashboard and CLI should not gain hidden route/Movement/success/quality authority. They should become an operator decision console: show what happened, why it is not ready, what evidence to open, who must dispose, and what remains not proven.
- Proof status: confirmed product-surface gap. No UI implementation was performed.

### S6-F17 - Ordinary customer product work should not expose checker complexity as the main interface

- Severity: medium-high.
- Axis attribution: product surface over checker support evidence.
- Evidence:
  - S5 confirms the checker system is large and high-tooth because BRICK is currently developing its own protocol, engine, evidence, and boundary system.
  - S5 also confirms checker green is support evidence only and not source truth, success judgment, quality judgment, Movement authority, provider proof, or complete coverage proof.
  - The product-surface strategy note distinguishes BRICK-internal protocol development from ordinary customer product work.
  - Direct product-surface review shows customer output already has `frontier_kind`, `customer_visible_frontier_state`, `evidence_root`, `proof_limits`, and `not_proven`, but does not yet fully translate checker/profile complexity into simple product status and next action.
- Meaning: when BRICK is used to build ordinary products, checker/profile detail should sit behind the product surface. Checkers should act as safety gates for contract violations, permission violations, evidence integrity, dangerous writes, and deployment risks. They should not become the design/implementation interface customers must operate.
- Product rule: BRICK-internal protocol development may expose checker detail. Customer-facing product runs should translate checker outcomes into `state`, `reason`, `next_action`, `evidence_root`, `proof_limits`, and `not_proven`.
- Proof status: product-surface principle admitted by audit; no UI/CLI change was implemented.

### S6-F18 - BRICK needs an explicit accountability/readiness projection, not AI blame language

- Severity: high.
- Axis attribution: product projection over Brick/Agent/Link/support evidence.
- Evidence:
  - Smith's product philosophy note defines BRICK as an AI work accountability
    protocol and shared operating protocol for humans and agents.
  - Direct measurement during this audit confirmed current support projection
    already exposes many deterministic ingredients: `frontier_kind`,
    `board_state`, `missing_required_file_count`, `next_action_observation`,
    Link disposition owner, GateFact missing facts, write-scope comparison, and
    proof limits.
  - No single `failure_attribution`, `readiness_blocker_observation`, or
    `protocol_compliance_observation` product object was found in the current
    code search.
  - CLI and dashboard already expose partial status fields but do not yet
    standardize the customer language around reason categories and compliance
    checklist.
- Meaning: BRICK should not say "the AI failed" as a product answer. It should
  show the observed blocker class and evidence: input/evidence gap, Brick
  contract gap, Agent return shape gap, provider runtime failure, Link gate
  insufficiency, human disposition required, write-scope mismatch, checker
  limit, or dashboard projection stale. Many categories can be rule-based now;
  semantic categories can be marked `semantic_review_required` rather than
  guessed.
- Product rule: add read-side projection language such as
  `readiness_blocker_observation` and `protocol_compliance_observation`. These
  are support/product observations only. They do not become source truth,
  success judgment, quality judgment, or Movement authority.
- Proof status: product gap confirmed. No projection implementation was added.

## External Review Incorporation

Claude review, Smith/operator follow-up, and external deployment reports sharpened
S6 in seven ways.

1. The flat `ISSUE` verdict hides the product gradient.
   - Claude Opinion 1 says S6 contains positive proof that the official route
     exists while still carrying ship blockers.
   - Future product verdicts should use a readiness tuple, not only `ISSUE`.

2. Axis-integrity and ship-safety must be scored separately.
   - Claude Opinions 2-4 distinguish protocol/axis cleanliness from release
     security and deployment hardening.
   - Product priorities should expose whether the next order is
     `protocol-live-order` or `ship-imminent-order`.

3. Customer-ready proof is dynamic, not only static.
   - Claude Opinion 6 says static audit cannot certify runtime/fresh-machine
     behavior.
   - S6 should require at least one current-main fresh-machine or stubbed
     end-to-end proof before broad customer-ready language.

4. Product docs must stop teaching internal routes by accident.
   - `brick build` remains the public route.
   - `run_building_plan`, `assembly.fire`, full Building Plans, and module
     onboard seams are advanced/internal unless explicitly admitted.

5. First-use docs must align with real verification surfaces.
   - Claude ADD-13 notes `setup.md` still mentions 24 profiles while live
     profile count is 28.
   - Claude ADD-18 notes bare `brick` defaults to status; this may be useful but
     should be documented if it is intended first-run behavior.
   - Pytest should not be presented as a customer verification surface unless
     repaired.

6. CLI/dashboard must be careful with raw/internal detail.
   - Claude ADD-12 notes CLI error handling can print raw `str(exc)` on the
     product surface.
   - Customer-facing errors should be classified and bounded, with internal
     detail behind evidence/debug refs.
   - Claude ADD-19 adds dashboard stale participant/client memory growth as a
     deployment detail to bound or document.

7. Smith's product identity should lead the user experience.
   - "AI 탓으로 끝내지 않는다."
   - "모두 같은 규칙으로 일한다."
   - The product surface should make these visible through state, reason,
     next action, evidence refs, proof limits, and protocol-compliance status.

## Rejected Shortcuts

- Rejected "engine is broken": the product finding is mostly docs/entrypoint/declaration ergonomics. The official route and checker profile exist.
- Rejected "just add `--large`": large work must be shape declaration over `preset_task` or `graph_packet`, not a hard-coded side route.
- Rejected "Slack absence means no official build": Slack is support evidence only and can be environment-gated.
- Rejected "fresh proof docs prove current main": prior proof docs are support evidence with commit/scope limits; they do not prove current fresh-machine readiness.
- Rejected "graph packet equals full Building Plan": customer graph packets must not carry template authority fields.
- Rejected "Gemini issue means retire Gemini": active Gemini path is `adapter:gemini-local`; the retired path is `adapter:gemini-api`.
- Rejected "release export risk proves a secret leaked": the risk is confirmed
  statically, but no exported secret was observed.
- Rejected "dashboard hardening makes dashboard source truth": dashboard remains
  projection; the issue is projection integrity and deployment trust.
- Rejected "checker green means release gate": CI/branch-protection wiring was
  not proven.
- Rejected "product surface means more automation buttons": the product surface
  should guide safe human/operator action over declared evidence, not create a
  scheduler, retry loop, Movement chooser, or quality judge.
- Rejected "hide proof limits for UX": proof limits are a trust feature of the
  product, not internal noise to suppress.
- Rejected "checker complexity is the customer interface": checker detail may
  be visible for BRICK-internal protocol work, but ordinary product runs should
  surface checker outcomes as clear status, reason, next action, and proof
  limits.
- Rejected "failure attribution means AI judgment": blocker/readiness
  projection should be rule-based where possible and mark semantic review
  needed where not, without becoming source truth or success judgment.

## Verdict

`ISSUE`

The public `brick build` route is real and checker-covered, and the bad `--large` path is not canonical. The product surface still has high-impact drift in install/init/onboard wording, graph packet documentation, large-work declaration ergonomics, stale docs/counts, provider proof wording, and fresh-machine proof boundaries. The deployment-report integration raises additional customer-publication blockers: release export can include untracked unignored local files, dashboard ingest lacks HMAC/replay/sequence protection, provider write boundaries are not customer-visible as a strength matrix, required CI/release gates are not proven, and dependency/release reproducibility policy is unclear.
The product-surface strategy addendum further clarifies the intended product
direction: do not add a new authority layer. Turn CLI and dashboard into a safe
operating surface that translates evidence into state, reason, next action,
proof limit, provider boundary, and approval/readiness separation.
For ordinary customer product work, the same principle applies to checkers:
checker/profiles remain behind the surface as safety gates and support evidence,
not as the customer's primary control interface.
Smith's accountability framing is now part of the product verdict: BRICK should
not reduce stops to "AI failed." It should expose a protocol-compliance and
readiness-blocker observation that shows the condition, evidence, proof limits,
and next human/COO action.

This is not a Link Movement verdict. It is an architecture audit verdict for the product surface.

Readiness tuple: use `brick-6-surface-audit-readiness-tuples-0630.md` for implementation priority. S6 is `core_sound: partial`, `axis_integrity_blockers: 3`, `ship_safety_blockers: 9`, `dynamic_runtime_not_proven: yes`, and `worst_severity: high`. The flat `ISSUE` label is only a findings-inventory label; product readiness remains not proven.

## Next Work Candidates

- Repair customer docs so `brick init`, `brick status`, `brick doctor`, and `brick build` are the only public first-use route.
- Keep `onboard.py` documented as an internal/support seam unless explicitly admitted as public CLI.
- Add or clarify a compact graph-packet schema reference and keep full Building Plan examples in an advanced/internal section.
- Turn P3 Easy Building into official declaration ergonomics over `preset_task` and `graph_packet`: task intake -> sizing -> optional design QA -> graph packet -> official `brick build`.
- Remove stale profile/preset/worktree/provider timing wording from active customer docs.
- Align Slack/reporting docs with runtime auto-load and support-evidence limits.
- Re-run a current-HEAD fresh-machine proof before making any broad customer-ready claim.
- Harden release/export before publishing customer install instructions: tracked-only default, dirty-tree guard, explicit `--include-untracked`, and secret/local denylist.
- Add dashboard ingest integrity and deployment hardening: HMAC, timestamp, event id, sequence, replay rejection, non-root/pinned container policy, and viewer access-wall warning.
- Expose provider write-boundary strength in CLI JSON/docs so Codex/Claude/Gemini are not described as equivalent hard sandboxes.
- Wire checker/profile/dashboard build/release export negative probes into CI or an admitted release gate.
- Define dependency lock/release-resolution policy.
- Standardize CLI output around `state`, `reason`, `next_action`,
  `evidence_root`, `proof_limits`, and `not_proven`.
- Promote dashboard from status board to operator decision console: Attention
  Queue, Next Action Card, Proof Limit Badge, Provider Boundary Badge, and
  evidence links.
- Separate engine state from product readiness: `complete` / `held` /
  `closure_pending` are not the same as `ready_for_human_review` or
  `manually_approved`.
- Hide checker/profile complexity in ordinary product runs: translate checker
  outcomes into customer-readable state, reason, next action, evidence refs,
  proof limits, and not-proven facts.
- Add `readiness_blocker_observation` and
  `protocol_compliance_observation` as read-side product projections over
  existing evidence, with deterministic categories first and
  `semantic_review_required` where AI/human review is actually needed.
- Bound CLI error output so customer-facing messages do not dump raw internal
  exception detail without evidence/debug separation.
- Document or adjust bare `brick` default status behavior as part of first-use.
