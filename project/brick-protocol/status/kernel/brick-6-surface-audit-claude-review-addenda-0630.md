# BRICK 6-Surface Audit — Claude Review: Additions & Corrections — 2026-06-30

## Provenance

- Reviewer: Claude (Opus 4.8), operator-gated, independent of the original Codex audit.
- Target: `/Users/smith/projects/BRICK` at HEAD `17eaade696998cd0de7bbd85ceb7525f349588e9`
  — **identical to the audit's stated commit**, so every `file:line` citation is d;
  any mismatch is a real locator error, not commit drift.
- Method: a 16-agent workflow — one verifier per audit packet (S1–S6 + synthesis)
  re-checking every citation/quantitative/behavioral claim against code and hunting
  uninspected seams, then an **independent adversarial re-checker per packet** that
  defaulted to rejecting each proposed correction/gap unless code clearly supported it,
  plus two cross-cutting agents (uninspected-territory, methodology). 2 first-pass
  proposals were rejected by the adversarial pass and are excluded here. Read-only;
  no source edits; no `check_profile --all`; no live providers/builds.
- Verify tags below: `[self]` = I re-ran the command myself this session; `[wf]` = first-hand
  `file:line` by a workflow agent that survived the independent adversarial recheck;
  `[wf-narrowed]` = survived but the adversarial pass narrowed the claim (stated in narrowed form).

## Bottom line on the audit

The audit is **high quality and trustworthy as a findings inventory.** Quantitative claims
(28 presets, 28 profiles, 0 `.github` files, kernel_checks 9931 / case_runners 8503 lines)
all reproduce exactly; ~95% of `file:line` citations are exact; the misses are line-precision,
not fabrication. **One factual claim is wrong (S4-F8)**, several severities/attributions
need recalibration, and there is a coherent set of **uninspected seams** — most importantly
two evidence-integrity holes that are live today (raw-stream secret scrub; resume-outside-sandbox)
and an honesty defect in the declared test surface (dead pytest). My structural/method critique
is in the separate file `brick-6-surface-audit-claude-opinion-0630.md`.

---

## PART A — Corrections (수정)

### A1. Citation / locator precision (content correct, locator off)

| # | Target | Audit locator | Correct locator | Evidence | Tag |
|---|--------|---------------|-----------------|----------|-----|
| C1 | S1-F5 (+ synthesis echo) "defines `brick()`" | `brick/spec.py:522-566` | `522-576` (covers `def brick(` at 569 + agent param at 576) | `def brick(` is line **569**, three past the cited 566; 522-533 is only the intro comment | [self] |
| C2 | S2-F3 "COO only reroute author…" | `coo.md:39-40` | `coo.md:40-41` | line 39 is a different sentence ("COO stays pure read-only…"); cited sentence is 40-41 | [wf] |
| C3 | S3-F5 stale error string | `walker_reroute_budget.py:158` | `:161` | 158 is `def _required_disposition_action`; the stale string is at 161 | [wf] |
| C4 | S4-F10 / synthesis "derives INGEST_SECRET" | `index.mjs:14-17` | `14-16` | line 17 is `IS_PRODUCTION`, a separate constant | [wf] |
| C5 | S5-F2 evidence grouping | run_chat_session.py listed among "lib" reads | it is `support/operator/run_chat_session.py` | name the chain: `_validate_chat_session_submission_return` → `primitives._validate_no_payload_forbidden(…, _RETURN_FORBIDDEN_KEYS)` → `return_fact.py:86 = ALWAYS_SECRET_KEYS` | [wf] |
| C6 | Synthesis C7 evidence range | "S5-F1 through S5-F11" | S5 has **F1–F13**; F12/F13 are deliberately carried in C12 / C9+C10 | no citation is actually broken — add a one-line note rather than widen the range | [wf-narrowed] |
| C7 | S3 Map | `link/route_policies/*.yaml` (plural) | only one file exists: `basic_qa_repair.yaml` | `find link/route_policies -type f` → 1 file | [wf] |
| C8 | S2 Map flow | `make_agent_fact(received_work, returned)` | keyword-only: `make_agent_fact(received_work=…, returned=…)` | `return_fact.py:167` uses `def make_agent_fact(*, …)`; positional form is not callable (cosmetic) | [wf] |

### A2. Factual error (the one real wrong claim)

**C9 — S4-F8 "`~/.brick/builds` appears in CLI/status/init metadata" is WRONG.** `[self]`
The **only** occurrence of `.brick/builds` in the repo is `support/checkers/lib/kernel_checks.py:8541`
— a checker assertion message that **guards against reviving** the legacy path
(`"…preset/task default revived legacy ~/.brick/builds"`). The live default is
`~/.brick/goal-runs` (`onboard.py:2081, 2104, 2404`). The claim was attributed to "subagent
evidence," not a direct read — a provenance weakness.
**Reframe S4-F8 to:** there is a checker actively preventing the `~/.brick/builds` revival;
the residual `building-evidence/` wording in README/docs is **intentional and current**
(`project/brick-protocol/building-evidence/` is the active evidence destination per
`AGENTS.md:188`, `README.md:244`), not stale.

### A3. Severity recalibration

**C10 — S3-F1 (missing `declared_gate_refs` → default adoption), severity `high`.** `[wf]`
In tension with the constitution, which **sanctions** default-transition auto-advance:
`AGENTS.md:450-452` ("may advance a static order or exactly-one eligible next target") and
`walker_step_fixture.py:196-197` documents the absence→default mapping as "the autonomy dial."
The *seam* (a raw row may omit `declared_gate_refs` and absence is silently mapped to template
adoption with no admitted normalization step) is real and checkable, but the resulting *behavior*
is constitutionally admitted. **Down-calibrate, or add an explicit constitution-reconciliation
sentence** — the finding's own hedge already says "not proof of support inventing an arbitrary target."

**C11 — S3-F5 (stale reroute error text), severity `medium` overstates.** `[wf]`
Both stale sites pass `action` through `_DISPOSITION_ACTIONS` (imported from
`link.transition.DISPOSITION_ACTIONS`; `plan_validation.py:29`, `walker_reroute_budget.py:28`),
which **does accept `reroute`** at runtime. So the bug is purely the human-facing error string —
zero behavioral risk. This is a low/cosmetic wording fix.

### A4. Overclaim (narrow)

**C12 — S4-F2 "frontier queue collides with the no-scheduler/queue/retry rule" is an overclaim.** `[wf]`
The walker's **own** wording (`walker_common.py:30,42`) treats "scheduler/queue/retry" as a
`NOT_PROVEN` / fan-topology proof-limit disclaimer, **not** a prohibition. The prohibition wording
lives on the reporter/projection bus (`report_sinks.py:173,184`; `reporter.py:198`) and
`AGENTS.md:782` ("forbidden E features"). So the live `_FANOUT_AUTO_POOL` ThreadPool
(`walker_frontier_driver.py:179` → `walker_kernel.py:1104`) is exactly the parallel execution the
walker **disclaims proving** — not something the no-queue rule forbids.
**Reframe to:** "the walker owns a real internal frontier queue + ThreadPool that the
projection-bus no-queue rule does not cover, and the walker's own wording only disclaims proving it."
(Concurrency correctness of that pool is separately addressed — see the opinion file; it is
sound-by-construction and checker-tested.)

### A5. Underclaim (strengthen)

**C13 — S2-F1 (chat-session verdict-key intake).** `[wf]` Add the fail-safe rationale: a verdict-key
payload is **always** rejected before any *accepted* AgentFact (`run.py:1443-1444 / 1640-1641`
run `make_agent_fact`, which rejects verdict keys). **But do not minimize to "only late failure"**
— a poisoned `submission.json` can wedge the building non-recoverably (see **ADD-9**). Keep `high`.

**C14 — S4-F1 (`onboard approve` default disposition).** `[self]` Both approve paths enforce an
author-prefix gate (`coo:`/`human:`; `onboard.py:1713, 2354`), so the leak is the silent **default
action** (`forward`) + **default identity** (`coo:smith`), not an unbounded author field. Distinguish
the two surfaces: `goal-approve` (1667) is a **pre-run** approval inside the worktree-sandbox bracket;
`approve` (2281) is a **post-HOLD resume that calls `resume_building_plan` without a sandbox wrapper**
(2545). The default-action concern is **sharper on the post-HOLD path** — and that path is itself an
isolation seam (see **ADD-1**).

**C15 — S4-F11 (provider env in `os.environ`).** `[wf]` Credit the existing mitigations so the residual
is precise: `runtime_env.py` loads only a narrow allowlist (`BRICK_REPORT_`/`BRICK_DASHBOARD_` +
exactly `GEMINI_API_KEY`/`GOOGLE_API_KEY`), enforces a TOCTOU-safe `0600` gate, masks values, and
threads REPORT keys. The residual gap is **solely** that the two provider keys must land in global
`os.environ` because the gemini adapter has no threaded-env seam (`runtime_env.py:27-34`).

**C16 — S6-F11 / dashboard ingest (merge with the "dev-secret" gap).** `[self]` Two additions beyond
"shared-secret equality": the check at `index.mjs:112` uses a **non-constant-time `!==`** (no
`crypto.timingSafeEqual`), and `INGEST_SECRET` **defaults to the literal `'dev-secret'`** when unset
(`index.mjs:16`), refused only when `IS_PRODUCTION` (`index.mjs:39-40`). A reachable deployment **not
flagged production accepts the publicly-known default secret.** This is a concrete auth-bypass seam.

**C17 — S4-F9 / S6-F9 (release export).** `[self]` Cite the script's own denylist:
`EXCLUDE_PATHS = ('project', 'brick_protocol.egg-info')` (`release_export.sh:61-64`); `is_excluded`
matches only those two roots; the copy loop has **no** secret/credential/key filter. So the leak path
is unguarded **end-to-end** (both the `.gitignore` stage and the copy stage), not merely a gitignore gap.

**C18 — S3-F2 (invalid concern shapes a HOLD target).** `[wf]` Add the mitigating control the finding
omits: an invalid concern routes to a **HOLD** (`hold_reason='invalid_transition_concern_evidence'`,
`disposition_required=True`, `transition_lifecycle_state='paused'`; `walker_kernel.py:1703-1721`,
`walker_hold.py:88,91`) — **not** an executed reroute; human/COO disposition is required before any
movement. `high` stays defensible (invalid evidence still shapes the pending target the human sees),
but state explicitly that no autonomous movement occurs.

**C19 — S1-F6 (GOAL non-catalog shapes).** `[wf]` Quantify: **8 of 10** distinct GOAL
`selected_shape_ref` values are non-catalog (only `design-needed` and `reviewable-work` exist in
`shapes.yaml`). Strengthens the drift from "a few edge cases" to "the bulk."

---

## PART B — Additions (추가)

Ordered by importance. The first three are the ones I'd act on regardless of ship timing.

### B-tier: live evidence-integrity + honesty (act now)

**ADD-1 — Resume / post-HOLD disposition runs OUTSIDE the worktree-sandbox isolation the audit credited. (high)** `[self]`
`run_approve_entry` calls `resume_building_plan(building_root, adapter_cwd=…)` directly
(`onboard.py:2545-2549`) with **no `_run_in_worktree_sandbox` wrapper** (confirmed: zero matches in
2281-2600), and the original sandbox was force-disposed (`driver.py:847`). The audit's "Controls That
Hold — customer build wrappers isolate writes in worktree/temp sandboxes" does **not** cover the resume
path that S4-F1 itself depends on. Concrete isolation-regression seam. *Caveat:* the actual write risk
depends on what `adapter_cwd` the operator supplies; the point is the **wrapper provides no isolation**.

**ADD-2 — Raw agent transcript streams are written with NO secret/PII scrub. (medium-high)** `[self]`
`contains_raw_secret_text` is applied at only **3** runtime sites (`step_outputs.py:501`,
`adapter_error_frontier.py:908`, `building_design_toolkit.py:730`). The raw streams —
`raw/agent-received.jsonl`, `raw/brick-work.jsonl`, `raw/adapter-error.jsonl` — are written by
`raw_claim_trace.py` via `_write_jsonl`, whose body is a bare `path.write_text` with **zero** guard
calls. The denylist itself is ~8 patterns (`sk-`, `sk-ant-`, `xoxb-`, `ghp_/gho_/github_pat_`, `AIza`,
PEM) — missing AWS `AKIA`, Slack `xoxp-/xapp-`, bearer tokens, DB URLs, and all PII. The audit's secret
discussion (S4-F9 / C9) is **entirely** about `.env`/`*.key` *files* at export time; it never examined
credentials/PII written **into** the evidence ledger by the engine — which then ships via
`release_export.sh` if `output_root` is in-repo. Uninspected territory between Support (writes),
Product (ships), and Checker (no pin on raw writers). *Repair:* run a broadened scrub over raw records
before `_write_jsonl`, or pin "raw-stream writers are guarded" with a checker.

**ADD-3 — Declared pytest surface is dead AND breaks if invoked. (medium-high)** `[self]`
`pyproject.toml:25-27` declares `[tool.pytest.ini_options] testpaths = ["support/checkers"]`, and
S5-F12 cites it approvingly. But there are **zero** pytest tests (no `test_*.py`/`conftest.py`); the
only two `def test_*` are checker-internal rule bodies (`check_adapter_usage_meter.py:311, 935`), and
`:935` takes a `repo` arg → bare `pytest` would collect it and **error** with `fixture 'repo' not
found`. `brick verify` is just `check_profile.main(['--all'])` — never pytest. So the declared test
surface is dead and misleading; **BRICK's only self-verification is static checker analysis** (this
underwrites the runtime-blindness point in the opinion file). *Repair:* delete the dead block, or
rename the two `test_*` and add ≥1 real runtime test, or wire `pytest`→`check_profile`.

### M-tier: scope gaps inside named surfaces

| # | Addition | Sev | Where / evidence | Tag |
|---|----------|-----|------------------|-----|
| ADD-4 | `brick/work.py` — the canonical return-shape tokenizer (`parse_required_return_shape`, splits on comma **and** slash, normalizes `-`→`_`, rejects JSON-shaped strings; `work.py:9-46`) — is in S1 scope but never inspected, despite the whole S1-F1/F2 thesis being return-shape integrity. It diverges from the assembly strip (`_materializer_strip_field`, comma-only exact-token; `composition_common.py:36-38`): **latent** — no current template triggers it (all snake_case), but a slash/hyphen shape would defeat the strip and then the naive substring guard `assembly.py:1230` (`field in shape`, which `composition_common.py:41-52` itself warns false-matches superstrings) would RAISE. Add an equivalence test. | med | `work.py:9-46`; `composition_common.py:36-52`; `assembly.py:1230` | [wf] |
| ADD-5 | `walker_carry.py` (669 lines) never inspected, though **carry is the first Link scope item** (`AGENTS.md:387`). The audit ran `chained_carry_dependency` green and listed `link/carry.py` but produced **zero** carry-runtime findings. The authority-boundary question — can support synthesize a carry, rewrite `source_owner_axis`, or advance a write node with an empty `carry_gate` — was never asked (the same class of check the audit DID run for gate adoption S3-F1 and concern adoption S3-F2). | med-high | `walker_carry.py` 669L; `link/carry.py:14,24` | [wf] |
| ADD-6 | Fan-in **classification** error path unaudited. `_customer_graph_fan_in_source_node_ids` (`driver.py:182-210`) silently yields an empty/changed set on malformed input (non-Sequence groups, wrong `group_role`, str `member_refs`). The `required_return_shape` override exception (`driver.py:236-237`) keys **entirely** on this classification: a mis-wired intended-fan-in node loses the exception and is rejected, while a node mis-classified AS fan-in source **gains** the override — the exact authority-leak surface S1-F1 worries about, probed only on its happy path. | med | `driver.py:182-210, 236-239` | [wf] |
| ADD-7 | **Verdict-key validator asymmetry** — a correctness trap for the S2-F1 / P0#4 fix. The chat-session guard `_validate_no_payload_forbidden` (`primitives.py:391-409`) is **recursive**; the AgentFact verdict gate `_validate_returned_top_level_keys` (`return_fact.py:119-125`) is **top-level-only by design** (`return_fact.py:83-85` comment). If the fix naively passes `TOP_LEVEL_VERDICT_KEYS` into the recursive helper it will over-reject legitimate **nested** `result`/`status`/`target`/`score` keys. The pre-persist validator must replicate top-level-only semantics. | med | `primitives.py:391-409`; `return_fact.py:83-125` | [wf] |
| ADD-8 | AgentFact rejection at resume can **wedge** the building. S2-F1's "fails late, not an engine collapse" understates: the parked resume runs in a try/except (`run.py:788-814`) catching only `AdapterFrontierEvidenceWritten`/`ChatSessionParkFrontierEvidenceWritten` — **no** `except ValueError`/HOLD-conversion. `make_agent_fact` raises uncaught; `submission.json` is write-exclusive (`run_chat_session.py:150-152`, O_EXCL) so a poisoned submission can't be overwritten → stuck building. AND (synthesis) the fix point is the **shared** validator: both submission intake and the resume read (`run.py:842`) use the same secret-only `_validate_chat_session_submission_return`. (The "re-fails forever" clause is reasoned inference.) | med | `run.py:788-814, 842`; `run_chat_session.py:150-152` | [wf] |
| ADD-9 | **No sensitive-write re-validation anywhere on the commit/resume path** — positively verified, not just "no block in the bracket." `grep observed_sensitive_path_writes\|sensitive_path` over `driver.py` AND `run.py` → 0 hits. The commit decision (`driver.py:838-839`, `frontier=='complete'` → `commit_sandbox_output`) never consults the recorded flag (`write_observation.py:141-144`); `commit_sandbox_output` lives in `worktree_sandbox.py:153`, fully decoupled. Note: this also corrects S5-F13's wording — there is no `def write_observation` *function* (the module records the flag), and the decoupling is **global**, not bracket-local. | med | grep 0 hits; `driver.py:838-839`; `worktree_sandbox.py:153` | [self] |
| ADD-10 | Fixed fixture `vessel_id` makes the checker sweep **non-reentrant**. `read_side_projection_boundary.yaml:479` uses a fixed `'checker-projection-fixture-vessel'`; `case_runners.py:7808-7814` hard-raises if the dir exists; cleanup is `finally`-only (not signal-safe). A SIGKILLed `--all` leaves the orphan → the **next** `--all` goes hard-RED until manual cleanup (self-inflicted denial-of-green); two concurrent `--all` runs collide. S5-F4 saw only the happy-path transient. | med | `read_side_projection_boundary.yaml:479`; `case_runners.py:7808-7814, 8014-8016` | [wf] |
| ADD-11 | `make-an-agent/SKILL.md` carries the stale `read-write-scoped` taxonomy (3rd+4th drift location, **highest-leverage** — it instructs new Agent-Object authoring). S2-F2/F5 covered `AGENTS.md` + `agent-axis-detail.md` but missed `agent/skills/make-an-agent/SKILL.md:43,45` (0 `probe-write`) and its **byte-identical** dup under `brick/templates/skills/`. Bonus: `agent/disciplines/closed-agentfact.md:9` already mandates the pre-persist closure S2-F1 found missing → reframes S2-F1 as a **discipline-vs-implementation** gap. | med | `make-an-agent/SKILL.md:43,45`; `closed-agentfact.md:9` | [wf] |
| ADD-12 | CLI error path emits raw `str(exc)` on the **product** surface. `cli.py:916-931` wraps every command in `try/except Exception` and prints `error_message=str(exc)` (may carry local filesystem paths / internal detail) with an unconstrained `error_kind`/`error_message` taxonomy. The S6 method probed only `--help`/parser happy paths. | med | `cli.py:916-931` | [wf] |
| ADD-13 | `setup.md:28` hard-codes "24 profiles live under `support/checkers/profiles/`" inside a sentence describing **live runner output** — a customer running the gate sees **28** `profile passed:` lines vs a doc claiming 24: an observable first-use contradiction. Highest-friction instance of the F7 count drift. | med | `setup.md:28`; `ls …/profiles/*.yaml \| wc -l` = 28 | [wf] |
| ADD-14 | **Portfolio adoption authority boundary** in `driver.py` never probed. Portfolio adoption is Link-owned (`AGENTS.md:388`); the audit treated `driver.py` only as a godmodule (F6). The adoption-authority seam (`_DECLARED_ADOPTER_PREFIXES` `driver.py:80`; `_FORBIDDEN_ADOPTER_PREFIXES` `:81` = `support:`/`agent:`) was never probed for the class of check done for single-Building gate adoption (S3-F1). A guard exists, so this is a coverage gap, not a known hole. | med | `driver.py:7,66,80-81`; `AGENTS.md:388,462` | [wf] |
| ADD-15 | `crossing_registry.yaml` (418 lines) + `module_registry.yaml` (2042 lines) — both named in S5 scope, never inspected for drift/dead rows; only the `module_registry` `checker_strict_validation` phantom (S5-F6) was cited. Coverage gap, not a demonstrated defect. | med | both files; packet Map lines 24-25 | [wf] |

### L-tier (note / fold-in)

- **ADD-16** `[wf]` `assembly.py:1230` fan-in guard uses the naive substring matcher the codebase's own `composition_common.py:41-52` documents as false-matching superstring fields (e.g. `transition_concern_evidence_summary`). (low; folds into ADD-4.)
- **ADD-17** `[wf]` `brick/building.py` (`BuildingWork`) named in S1 key-files but its empty-fact / non-text error paths (`building.py:16-28, 45-60`) are uninspected. (low.)
- **ADD-18** `[wf]` Bare `brick` with no args silently runs `status` (`cli.py:908-910`), bypassing `--help` — undocumented first-run default; belongs in the product-surface map. (low.)
- **ADD-19** `[wf]` Dashboard server holds module-global `participants = {}` / `clients` mutated by `/ingest` and iterated by SSE with no eviction → memory growth / stale-participant surface (not a race — single event loop). Anchor for the C10 "participant sequence" repair at `index.mjs:120-131`. (low.)
- **ADD-20** `[wf-narrowed]` Resume target-divergence: rather than an open risk, **add a Control** citing the existing static guards `walker_resume.py:469-474` (rejects building-boundary / self-reroute, requires pending_target in the declared plan) and `walker_kernel.py:551` (binds `re_instruction` only to the matching declared step). The adversarial pass showed these mostly answer the divergence question "yes, validated."

---

## How to apply

These are review notes, not edits to your packets — I did not modify the six audit files.
Corrections C1–C9 are locator/factual patches; C10–C19 are framing/severity edits; ADD-1…20 are
new findings to fold in (or to spawn as their own repair Buildings). The two items the adversarial
pass **rejected** (a chat-session severity wholesale-downgrade, and a checker error-path finding that
duplicated ADD-10) are intentionally absent.
