# BRICK Onboarding + Provider-Registration Redesign

## 1. Problem statement

Today a fresh-install run of `brick init` (support/operator/cli.py:764-776, `_cmd_init`) hung: the onboarding demo-Building step (`_example_step`, onboard.py:289-341) resolved to a Gemini adapter the user had never authenticated. Confirmed root cause this session: BRICK has no persisted provider-registration record anywhere. `preflight_provider()` (adapter_subprocess.py:85-259) is a pure read-only probe — it returns ready/unauthed/missing/unknown and prints it, never writes to disk (confirmed: no I/O in that function or its callers). The adapter actually used at runtime instead comes from a static, build-time YAML field: `plan_rendering.py`'s `_resolve_casting_field()` ladder (lines 411-495) falls back to each matched Agent Object's `preferred_adapter_ref` in `agent/objects/<name>.yaml`. 6 of 8 objects default to `adapter:codex-local`; 2 (inspector, qa-lead) default to `adapter:gemini-local`. None of these steps consult preflight output or any live registration record, so a user who never configured Gemini is still routed to it the moment a plan touches inspector/qa-lead — silently, at runtime. In one sentence: static declaration and live availability are two disconnected data sources, and nothing bridges them.

## 2. Hermes: what to learn vs what does not apply

**Worth adopting:**
- One-provider-at-a-time registration as a first-class, re-runnable path shared by wizard and standalone command (Hermes: `select_provider_and_model()`, main.py:2738, used by both `run_setup_wizard()` and `hermes model`/`hermes auth add`).
- First-registered-provider-becomes-default, explicit and testable (Hermes: `mark_provider_active_if_unset()`, auth.py:1202-1217 — sets `active_provider` only when unset).
- Model and a separate tier/effort dial as two distinct, independently-skippable steps (Hermes: model picker then `_prompt_reasoning_effort_selection()`, main.py:1152-1235, persisted separately).
- Incremental persistence so a Ctrl-C mid-registration leaves partial-but-valid state, not corruption.

**Does not apply / must not copy:**
- Hermes' curses/blocking interactive wizard shape. `brick init` is architecturally non-interactive (scripted argparse, cli.py:746-882) and run by both humans and automation (install.sh, CI). BRICK needs staged, confirmable steps, not TTY-blocking prompts.
- Hermes' two-file split (config.yaml + auth.json + .env). BRICK already has one canonical per-user directory (`~/.brick/`); one new record is enough.
- Hermes never validates credentials at registration time (`_prompt_api_key()`, main.py:3973-4053, zero network call). BRICK must not copy this — `preflight_provider()` already is a real check; the point is to use it at registration time, not skip it.
- Hermes has no Agent Objects / lanes / adapter_refs allow-lists. Any registration record must speak BRICK's own vocabulary, not a bolted-on Hermes-shaped credential store.

## 3. Proposed BRICK flow

Extend `brick init` with a new PROVIDER phase, inserted between PRESENT (doctor) and PLUGIN, non-interactive-safe but interactive-aware:

1. **PRESENT (unchanged)**: `run_doctor()` runs `preflight_provider()` per host, prints readiness.
2. **PROVIDER (new)**: `run_provider_register_step()`. If `--host` was passed and preflight reports `ready`: auto-register that adapter, write the record, mark it preferred (first one wins), no prompt. If interactive TTY with no ready adapter: one flat prompt — "Register a provider now? [codex/claude/gemini/skip]" — not a nested wizard; only a `ready` preflight result gets persisted. If non-interactive and nothing ready: skip with a one-line advisory ("no provider registered — run `brick provider add <host>` later"); never fall through to an unauthenticated adapter for the smoke test.
3. **PLUGIN / SLACK (unchanged)**.
4. **SMOKE TEST (renamed from ONBOARD+EXAMPLE)**: `_example_step()` resolves its adapter from the registration record's preferred entry, not a hardcoded `allow_real_provider` flag. No registration → explicit, announced `adapter:local` run, not a silent per-object default.
5. **VERIFY (unchanged)**.
6. **New standalone command**: `brick provider add <host>` — the same registration sub-step from step 2, callable any time to add a second/third provider without rerunning all six phases (mirrors Hermes' `hermes model`/`hermes auth add` reuse pattern, as a thin wrapper around `run_provider_register_step()`).

This satisfies the operator's stated vision directly: terminal run -> install -> LLM registration -> one Building smoke test -> more (via `brick provider add`).

## 4. Proposed persistence

New file: `~/.brick/providers.yaml` (sibling to `report.env`, same 0600 permission convention). Concrete shape:

```yaml
version: 1
preferred_adapter_ref: adapter:codex-local
providers:
  - adapter_ref: adapter:codex-local
    registered_at: "2026-07-01T09:12:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T09:12:00Z"}
    model_ref: model:codex:default
    reasoning_tier: medium
  - adapter_ref: adapter:gemini-local
    registered_at: "2026-07-01T09:20:00Z"
    last_preflight: {status: unauthed, checked_at: "2026-07-01T09:20:00Z"}
    model_ref: model:gemini:default
    reasoning_tier: null
```

Field notes: `preferred_adapter_ref` is set once, on first successful registration (`status: ready`), never silently reassigned later — mirrors Hermes' `mark_provider_active_if_unset` but as one flat pointer, not a nested active-provider system. `providers` is an ordered list (registration order = ladder tie-break order). `last_preflight` caches the most recent `preflight_provider()` result, refreshable by `brick doctor` — explicitly a cache, not a live guarantee, so the smoke-test step still re-runs preflight before use. `model_ref`/`reasoning_tier` are the two separately-settable fields answering "model/tier selection happens too," deliberately named to match the `model:codex:default`-style refs already used in `agent/objects/*.yaml` so no new ref vocabulary is invented.

## 5. Proposed adapter-resolution change

In `plan_rendering.py`'s `_resolve_casting_field()` ladder (lines 411-495), insert new rungs **before** the static Agent-Object fallback:

1. explicit step-level `selected_adapter_ref` (unchanged, highest priority).
2. **NEW**: if the Agent Object's static `preferred_adapter_ref` is present in `~/.brick/providers.yaml` and its cached `last_preflight.status == ready`, use it as-is (fast path — no change when the static default is also registered and working).
3. **NEW**: if the static `preferred_adapter_ref` is unregistered or not ready, fall back to `providers.yaml`'s `preferred_adapter_ref` (first-registered default) *if* that adapter_ref is in the Agent Object's own `adapter_refs` allow-list (capability-satisfies-need still holds — never route to an adapter the object doesn't declare acceptable).
4. static Agent Object `preferred_adapter_ref` (now last-resort, not primary) — this is what breaks the bug: a static preference no longer wins blindly over live registration.
5. plan-level building default (unchanged, final floor).

Additive: rungs 2/3 are pure reads of a new optional file; absent `providers.yaml` degenerates to today's behavior (rung 4 fires immediately) — old checkouts and untouched objects see zero change.

## 6. Scope/risk and migration strategy

Risk: this ladder is load-bearing for every Building across all 8 agent objects; a bug here breaks all dispatch. Migration strategy — additive-only, feature-detected:

- `providers.yaml` absence is the explicit "not migrated" signal — no file means no behavior change (rung 4 fires exactly as today). No agent-object YAML is edited by this change.
- Gate the new rungs behind one check: `if not providers_file.exists(): return existing_ladder(...)`. Strict superset, testable independently of any object's static config.
- Do not touch `preferred_adapter_ref` in any `agent/objects/*.yaml` in this pass — they stay the documented, human-auditable ceiling; the record only demotes their priority when unregistered/not-ready, never deletes or overrides the file.
- Add one checker (fold into `check_profile.py --all`) asserting every `adapter_ref` in `providers.yaml` also appears in some Agent Object's `adapter_refs` allow-list — catches stale/typo'd registrations before silent no-op.
- Regression gate: existing 15-profile `--all` green bar, plus a new fixture — fresh `~/.brick` (no providers.yaml) running `brick init --host codex` end-to-end — as the literal reproduction of today's bug, asserted to no longer hang/misroute.

## 7. Phased rollout

**Phase 0 (smallest, ships the actual fix):** persistence file + rung 2/3 insertion + smoke-test reading it instead of blind `allow_real_provider`. No new CLI commands; registration happens implicitly inside `brick init` using whatever `--host` was passed. Alone, this fixes today's bug: an unregistered/not-ready adapter can no longer be silently selected for the smoke test.

**Phase 1:** `brick provider add <host>` as a standalone re-runnable command (section 3, step 6) — "register one at a time, add more later" without a full `brick init` rerun.

**Phase 2:** interactive single-prompt registration for TTY sessions with no ready adapter (section 3, step 2's prompt branch) — closes "terminal run -> install -> LLM registration" for humans running it live; non-interactive/CI callers untouched.

**Phase 3:** `model_ref`/`reasoning_tier` selection UX (Phase 0-2 just default from the Agent Object's static `preferred_model_ref`) — full "model/tier selection happens too" requirement, lowest urgency since it didn't cause today's bug.
