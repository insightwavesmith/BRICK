<!-- 방지책 3층 설계 — Smith 0709 지시 "어떤 AI도 정식루트만 사고" 강구 결과.
워크플로 wf_36994c47-3d4 (11에이전트, 우회로 59건 열거, 3층 설계+적대검증). 설계만 — 구현은 Smith 승인 후 정식 빌딩. -->

# BRICK Official-Route-Only Enforcement — 3-Layer Design (decision-ready for Smith)

*Synthesis lead output. Every mechanism below is verified against repo source and the 2026-07-08 Claude Code hooks docs. Items I could not prove are marked `[NOT PROVEN]`. This is a DESIGN — no product code was edited.*

---

## 1. Goal (restated)

Smith's directive: **any AI opening any new session in this repo must think, and be forced to launch, only via the official route** — regardless of whether it read the handoff.

Verified official route (facts §5–8, re-confirmed from source):
- Exactly **two** launch verbs: `brick build` and `brick resume`.
- Both = console entry `brick = brick_protocol.support.operator.cli:main` (pyproject.toml:23). `python -m brick_protocol.support.operator.cli build|resume` routes through the **same** `main()` → genuinely official/equivalent, must be **allowlisted, not denied**.
- All launches converge on one chokepoint: `_run_dynamic_graph_walker` (walker_kernel.py:1313).

**The hard problem, proven live this session:** the chokepoint has NO admission gate. Its only entry check (walker_kernel.py:1354) is `plan_shape=='graph'` + write-need markers. I imported and confirmed **all 8 bypass routes are callable right now**:

```
OK  walker_kernel._run_dynamic_graph_walker        OK  run.run_building_plan
OK  dynamic_walker._run_dynamic_graph_walker        OK  run.run_building_once
OK  dynamic_walker._resume_dynamic_graph_walker      OK  run.resume_building_plan
OK  onboard.launch_assembled_building                OK  driver.run_customer_graph_building_in_sandbox
```

A document does not fix this (facts §37: already tried, unread). Memory lesson (§38): skill-load ≠ compliance; only machine forcing is hard. So the design is three layers of **increasing hardness**, and it is honest that **only Layer 3 physically closes the bypass routes.**

---

## 2. The three layers (each with buildable artifact + what it blocks)

### Layer 1 — SessionStart hook — THOUGHT INJECTION (primes; enforces nothing)

**Artifacts (2 files):**
- `/Users/smith/projects/BRICK/.claude/settings.json` — slot verified **empty** (`.claude/` holds only `worktrees/`). Project-scoped so every session in this repo inherits it; a single AI cannot delete a project hook mid-session (facts §22).
- `/Users/smith/projects/BRICK/.claude/hooks/session_start_official_route.py` — committed, reviewable, unit-testable script.

**settings.json:**
```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command",
        "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/session_start_official_route.py\"" } ] }
    ]
  }
}
```
**No `matcher` field** — deliberate. (Reason below; this is the corrected design.)

**What it emits:** exit 0 with `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"<FIXED TEXT>"}}`. Claude Code auto-injects `additionalContext` into model context with no AI opt-in — verified against docs. The FIXED TEXT: the two official verbs, the `python -m ...cli` equivalent explicitly ALLOWLISTED, the forbidden bypass list (the 8 routes + launcher-script + subprocess-wrapper class), and a **pre-flight declaration obligation** (before any launch, emit a block naming the verb, the exact command line, and a confirmation that no operator submodule is being imported/called directly).

**DECISIVE CORRECTIONS to the draft (the adversarial verdict broke the original, docs confirm the break):** SessionStart fires on **four** sources — `startup`, `resume`, `clear`, `compact` (confirmed from docs). The original design chose "emit nothing on `clear`" and never handled `compact`. That silences the layer at the exact moments context was just wiped — precisely when re-priming is most needed. **Fix, mandatory:**
- **Re-inject on ALL sources.** Emit the fixed context for `startup`, `resume`, `clear`, AND `compact`. The only silent path is an internal error (fail-open). Unknown/future source values default to EMIT, not skip. (This is why `matcher` is dropped — the script branches on the stdin `source` itself and never uses silence as a branch.)
- **[Optional, stronger] `initialUserMessage`.** Docs confirm SessionStart also accepts `initialUserMessage` (seeds the first user turn), which survives more robustly than `additionalContext`. Use it to carry the pre-flight-declaration obligation so it reads as a task, not ambient text. `[NOT PROVEN]` that this fully survives a `/compact` — treat as belt-and-suspenders, not a guarantee.

**Pointer hardening (the draft invented a poisoning surface — remove it):** the draft's `.claude/brick-entry-canon` feature interpolates a raw repo-file's contents into context as authoritative ("read it before launch"). That re-creates the mis-recorded-pointer trap from memory (`feedback-verify-official-path-in-skill.md`: a bad pointer cost 3h on a retired path; fail-open catches a *missing* read but not a *confidently-wrong* one). **Recommendation: drop the concrete-pointer feature entirely.** Layer 1 has no enforcement value, so a static "ask the COO for today's entry canon" costs nothing and avoids vouching for an unverified pointer. (If Smith insists on a live pointer: validate it resolves to an existing file under the repo, matches an allowlisted name pattern, mtime within threshold; and phrase as "COO-declared pointer is X — independently confirm it is today's canon," never "read it before launch.")

**What it blocks:** *Nothing physically.* Honest scope — Layer 1 **PRIMES** the official-route rule (raises salience) and **PLANTS** the pre-flight-declaration obligation that Layers 2/3 cross-check. It **CLOSES NOTHING.** All lazy-bypass and seam-call routes are closed only by Layers 2 and 3. (The draft's "covers: closes at the intent layer" was overclaiming; corrected here.)

---

### Layer 2 — PreToolUse(Bash) hook — IN-SESSION LAUNCH BLOCK (real deny, but leaky)

**Artifacts (add to same settings.json + one script):**
```json
"PreToolUse": [
  { "matcher": "Bash", "hooks": [ { "type": "command",
    "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/pretooluse_block_offroute_launch.py\"" } ] }
]
```
Script reads the Bash `command` string from stdin and, on a bypass pattern, exits 0 with:
```json
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny",
  "permissionDecisionReason":"Off-route Building launch. Use `brick build`/`brick resume` (or `python -m brick_protocol.support.operator.cli build|resume`). Direct walker/run/onboard/driver imports are non-official and are blocked."}}
```
Verified from docs: matcher matches on tool name `"Bash"`; deny is exit 0 + those exact fields; `permissionDecisionReason` is fed back to the model.

**Match logic (deny-list of bypass substrings, allow-list of official):**
- DENY if the command imports/calls any of: `_run_dynamic_graph_walker`, `_resume_dynamic_graph_walker`, `run_building_plan`, `run_building_once`, `resume_building_plan`, `launch_assembled_building`, `run_customer_graph_building_in_sandbox`, or matches `python .*\.py` invoking a script that isn't the CLI (heuristic for `/tmp/launch.py` launchers), or `subprocess`/`os.system` wrapping any of the above.
- ALLOW (never deny): `brick build|resume`, `python -m brick_protocol.support.operator.cli build|resume`.

**What it blocks:** the naive `python -c "from ...walker import _run_dynamic_graph_walker"` and `from ...run import run_building_plan` one-liners typed directly as Bash — the highest-frequency lazy route.

**Honest leak (why Layer 2 is not sufficient — proven by the route map):** a Bash **string** matcher is defeated by (a) a file launcher — `python /tmp/launch.py` where the forbidden import lives *inside* the file, so the matcher sees only `python /tmp/launch.py`; (b) a `subprocess`/`os.system` wrapper that assembles the import string dynamically; (c) any obfuscation (`importlib.import_module`, base64'd module name). You cannot pattern-match your way to completeness against an adversary that controls the command string. **Layer 2 raises cost for the lazy path; it does not close the class.** This is the entire reason Layer 3 exists.

---

### Layer 3 — Walker provenance gate — OUT-OF-HARNESS / BYPASS CLOSURE (the only hard layer)

This is the load-bearing layer. It makes the chokepoint itself refuse any entry that did not come through the official CLI, regardless of harness, launcher, subprocess, cron, or Jupyter. Assets already exist to build on: `import_identity.py` + checker `check_import_identity_modes.py` (facts §6, §17).

**Mechanism — an official-launch token that only `cli:main` can mint, checked at the chokepoint:**

- **Stamp (mint):** the official CLI path (`cli:main` → the four verified walker-invocation sites) sets a process-scoped **official-launch token** — cleanest as a `contextvars.ContextVar` set inside `cli:main` before dispatch, so every internal caller inherits it through the call stack. Verified: the walker is invoked from exactly **four** sites (`run.py:729`, `run.py:834`, `run.py:987`, `walker_resume.py:470`), and `cli.py` never calls the walker directly — it always goes through the `run.py`/`driver` seam. So a single mint at `cli:main` covers all legitimate paths. `[NOT PROVEN]` that no legitimate non-CLI caller exists (e.g. a checker/fixture that drives the walker in-process) — Stage 1 below exists precisely to surface those before the gate turns lethal.
- **Gate (check):** at `_run_dynamic_graph_walker` entry (walker_kernel.py:1354, alongside the existing `plan_shape` check), if the token is absent → `raise` a `RuntimeError` naming the official verbs. A bare `python -c "from ...run import run_building_plan; run_building_plan(...)"` never ran `cli:main`, so the token is unset → it raises. This closes **all 8 callable routes I proved live**, plus the launcher-script and subprocess-wrapper routes Layer 2 cannot see, plus every out-of-harness runtime (cron/Jupyter/fugu) that never triggers a hook at all (facts §23).

**Why a token, not `declared_by`:** verified this session — `declared_by` (cli.py:443, etc.) is a public, masked "who authored" descriptive field on the declaration, NOT an admission credential. It is set from user input and is trivially forgeable in a hand-built packet. It must NOT be reused as the gate. The token must be un-forgeable-from-a-packet: a contextvar set only by executing `cli:main` cannot be supplied by a caller who bypassed `cli:main`.

**MANDATORY 2-STAGE ROLLOUT (stamp-then-gate) — never ship the raise first:**
- **Stage 3a — STAMP + OBSERVE (non-lethal):** mint the token at `cli:main`; at the walker entry, if the token is absent, **record an observation** (log/BAL fact) but **do not raise**. Migrate the four internal invocation sites so every legitimate path carries the token. Run the full suite + real `brick build`/`brick resume`/`resume` and confirm **zero** absent-token observations on legitimate launches. This surfaces any `[NOT PROVEN]` legitimate non-CLI caller without breaking it.
- **Stage 3b — GATE (lethal):** only after Stage 3a shows a clean floor, flip absent-token from observe to `raise`. Guard the checker `check_import_identity_modes.py` (or a sibling) to assert the gate is present and that all four invocation sites are inside the stamped path (single-source guard, mirroring the repo's existing single-source discipline).

**What it blocks:** everything. This is the layer that satisfies Smith's "even out-of-band" requirement.

---

## 3. Coverage matrix (every bypass route → blocking layer)

| # | Route | L1 primes | L2 Bash deny | L3 walker gate | Net |
|---|-------|:--:|:--:|:--:|-----|
| 1 | `python -c` import `walker_kernel._run_dynamic_graph_walker` | ✓ | ✓ | **✓ closes** | Closed (L3) |
| 2 | `python -c` `dynamic_walker` facade (fwd+resume) | ✓ | ✓ | **✓ closes** | Closed (L3) |
| 3 | `python -c` `run.run_building_plan(adapter_cwd=live)` | ✓ | ✓ | **✓ closes** | Closed (L3) |
| 4 | `python -c` `run.run_building_once` | ✓ | ✓ | **✓ closes** | Closed (L3) |
| 5 | `python -c` `run.resume_building_plan` | ✓ | ✓ | **✓ closes** | Closed (L3) |
| 6 | `python -c` `onboard.launch_assembled_building` | ✓ | ✓ | **✓ closes** | Closed (L3) |
| 7 | `python -c` `driver.run_customer_graph_building_in_sandbox` | ✓ | ✓ | **✓ closes** | Closed (L3) |
| 8 | **Launcher script** `/tmp/launch.py` importing any of the above | ✓ | ✗ **leaks** | **✓ closes** | Closed (L3 only) |
| 9 | **subprocess / os.system** wrapper of any above | ✓ | ✗ **leaks** | **✓ closes** | Closed (L3 only) |
| 10 | Out-of-harness (cron / Jupyter / fugu / CI import) | ✗ no hook | ✗ no hook | **✓ closes** | Closed (L3 only) |
| 11 | `/clear` or `/compact` un-primes, then off-route | fixed→re-primes | ✓ | **✓ closes** | Closed (L2+L3) |
| 12 | `python -m ...operator.cli build\|resume` (LEGIT) | ✓ allowlist | ✓ allow | ✓ token minted | **Correctly ALLOWED** |
| 13 | `python -m ...operator.run` (dead end — no `__main__`) | — | — | — | N/A (verified inert) |

**Reading:** routes 1–7 are defense-in-depth (all three layers touch them); routes **8, 9, 10 are closed by Layer 3 ALONE** — this is the proof that Layer 3 is non-negotiable and Layers 1–2 are cost-raising, not closure.

---

## 4. Staged rollout order (build sequence + why)

1. **Layer 3 Stage 3a (STAMP + OBSERVE) — build FIRST.** It is the only layer that closes routes 8/9/10, and its observe-mode is the safe way to discover any hidden legitimate caller before anything can break. Ship nothing lethal yet.
2. **Layer 2 (Bash deny) — second.** Independent, low-risk, immediate value against the common lazy one-liners while Stage 3a's observation floor is being confirmed. Get the allowlist right (route 12 must pass).
3. **Layer 1 (SessionStart) — third.** Pure priming; safe to add anytime, but it references what Layers 2/3 enforce, so wire it after they exist so the injected text is truthful ("WILL be denied / WILL raise").
4. **Layer 3 Stage 3b (GATE, lethal) — LAST.** Flip observe→raise only after Stage 3a shows a clean floor across the full suite + real `build`/`resume`/`resume`. Add the single-source checker guard in the same step.

Rationale: build the hard layer first but keep it non-lethal; add the cheap layers; make the hard layer lethal only when the evidence floor is proven. Never the reverse (a lethal gate shipped before the stamp migration would break legitimate launches).

---

## 5. Honest residual limits (what NONE of the three layers can close)

- **Wholesale hook disable via `--disable-all-hooks` / stripping project settings.** Verified from docs: this is lockable ONLY through **org-managed settings** (`allowManagedHooksOnly`; `disableAllHooks` is overridable only at the managed level). The design proposes project `.claude/settings.json`, which does **not** lock it. Closing this is a **Smith/org-policy decision**, not an AI-buildable step. Note: Layer 3 lives in **product code**, not a hook — so disabling hooks does NOT reopen routes 1–10; it only removes Layers 1–2's priming/deny. Layer 3 still raises. This meaningfully de-fangs the gap.
- **Deliberate token forgery.** If an adversary reads the source and replicates the exact contextvar mint outside `cli:main`, the gate passes. This is the "AI 격리서명" isolated-signature problem (facts §33) — a harder, later item (cryptographic/process-attested token). The current token stops **accidental and lazy** bypass and every route enumerated here; it does not stop a determined forger who studies the mint. Marked as a known, deferred limit.
- **Stale entry-canon pointer** — eliminated by dropping the pointer feature (§2, Layer 1). If Smith keeps it, it remains a poisoning surface the hook cannot fully validate.
- **`[NOT PROVEN]` legitimate non-CLI walker caller** — Stage 3a observe-mode is the mitigation; if one exists it will show up as an absent-token observation and must be routed through the mint before Stage 3b.

---

## 6. Recommended official-Building order to implement (authoring hint — COO authors via the authoring preset, NOT a task.md)

Suggested node shape for when Smith approves implementation (sizing per `building-sizing-method`, authored per `brick-task-author`):

- **Node A — Layer 3 Stage 3a (stamp + observe).** Scope: `cli.py` mint (contextvar), the 4 walker-invocation sites (`run.py:729/834/987`, `walker_resume.py:470`), observe-only branch at `walker_kernel.py:1354`. Write scope = product code. QA lens: full suite + real `build`/`resume`/`resume` show zero absent-token observations. **This is the highest-risk node → deepest QA (opus xhigh, per operating rules).**
- **Node B — Layer 2 Bash-deny hook** (`.claude/settings.json` + `pretooluse_block_offroute_launch.py`). Parallelizable with A. QA: unit tests for deny-list AND allowlist (route 12 passes; routes 1–7 denied; document the 8/9 leak as expected).
- **Node C — Layer 1 SessionStart hook** (`.claude/settings.json` SessionStart block + `session_start_official_route.py`). Depends on A+B existing (so injected text is truthful). QA: assert emit on all 4 sources, fail-open on error, allowlist text present.
- **Node D — Layer 3 Stage 3b (flip to raise) + single-source checker guard.** Depends on A's clean floor. QA: gate raises on all 8 bypass routes (reuse this session's callable-probe as the fixture); legitimate launches unaffected.
- **Out-of-band follow-up (separate, Smith-decision):** managed-settings lock (`allowManagedHooksOnly`) and the deferred token-forgery hardening — NOT part of this Building.

---

### Files referenced (all absolute)
- Chokepoint / gate site: `/Users/smith/projects/BRICK/brick_protocol/support/operator/walker_kernel.py` (def :1313, entry check :1354)
- Stamp sites: `/Users/smith/projects/BRICK/brick_protocol/support/operator/run.py` (:329, :676, :729, :773, :834, :987), `/Users/smith/projects/BRICK/brick_protocol/support/operator/walker_resume.py` (:470)
- Facade re-exports (bypass): `/Users/smith/projects/BRICK/brick_protocol/support/operator/dynamic_walker.py` (:77, :84)
- Other bypass entries: `.../onboard.py:2938`, `.../driver.py:739`
- Mint point: `/Users/smith/projects/BRICK/brick_protocol/support/operator/cli.py` (`main`, :2161)
- Existing asset to extend: `/Users/smith/projects/BRICK/brick_protocol/support/operator/import_identity.py` + checker `check_import_identity_modes.py`
- New hook artifacts: `/Users/smith/projects/BRICK/.claude/settings.json` (empty slot), `/Users/smith/projects/BRICK/.claude/hooks/session_start_official_route.py`, `.../pretooluse_block_offroute_launch.py`

**Bottom line for Smith:** Layers 1–2 raise the cost of the lazy path but close nothing on their own (proven: routes 8/9/10 leak past both). **Layer 3 is the only hard closure** — I verified all 8 bypass routes are callable today, and a contextvar token minted solely by `cli:main` and checked at the walker chokepoint refuses every one of them, in any runtime. Build Layer 3 first in observe-mode, add the cheap layers, then flip the gate lethal. Two residuals stay open by nature and are Smith/org decisions, not code: managed-settings hook-lock, and deliberate token forgery.