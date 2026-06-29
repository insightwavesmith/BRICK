# Resume surface — design principle (Smith's model + judgment) — 0626

## Smith's model (0626)
Resume should be ONE clean API/module surface (factored out, not buried) that signals the RESTART of an existing held building. At that surface the operator can:
- **FORWARD** (approve) — continue as-is.
- **REROUTE / send-back** ("이건 이렇게 수정해라") — return the held step with corrections.

And resume must be a **transparent continuation**: the held building resumes EXACTLY as it was declared (parallel stays parallel); the operator only supplies forward/reroute. Smith: "버튼 누르면 멈춘 그대로 다시 굴러가야 한다."

## Current state (measured 0626)
- `run_approve_entry` (support/operator/onboard.py:2170) ALREADY does most of this: appends a human/COO disposition row + resumes. `action ∈ {forward, stop, raise, reroute}`, plus `reroute_target_ref=`, `re_instruction=`, `budget_increment=`, `author_ref="coo:smith"`. So the forward/reroute disposition surface EXISTS.
- GAPS vs the model:
  1. **Not cleanly surfaced.** `run_approve_entry` is buried — the brick-hold-triage skill didn't name it (cost a failed resume attempt 0626). `resume_building_plan` alone fails with `ValueError: no human/COO disposition row found for held pending_target_ref ...` = a two-verb footgun. The model wants ONE obvious surface.
  2. **Not behavior-preserving.** Resume UNCONDITIONALLY serializes declared-parallel fans, while forward auto-parallelizes (pool=8). So the SAME building runs parallel forward but serial on resume — it does NOT resume "as it was." (Live 0626: engine-feature-hard's 3 attack-QA ran serial both times the building HELD then resumed.)
     - **MEASURED root cause (0626, walker_kernel.py:2554-61):** `dispatch_pool_size = _fanout_dispatch_pool_size(linear_plan)` (=8 with the env override) is then CLOBBERED by `if resume_seed is not None or not has_fan_groups: dispatch_pool_size = 1`. On resume `resume_seed is not None` → forced to 1 BEFORE the override is ever honored. The override only survives the FORWARD path (the `elif not _has_explicit...` branch is skipped, leaving 2554's value). **The env override does NOT win on resume — my earlier "explicit override wins" code-read was WRONG (the comment at :2560 is self-contradictory; the code implements resume-serial).** `BRICK_FANOUT_DISPATCH_POOL_SIZE=8` on resume is a no-op (env propagates fine — verified `uv run sees: 8` — but 2556 overwrites it).
     - **Concrete fix (the behavior-preserving change):** line 2555 must distinguish REPLAY of completed steps (stay serial, deterministic rehydration) from the NEW continuation after the hold (parallelize like forward). Minimal stopgap-as-real-fix: exempt the explicit override — `if (resume_seed is not None and not _has_explicit_fanout_pool_override(linear_plan)) or not has_fan_groups:` — but the proper fix parallelizes the continuation regardless. This is a checker-pinned engine building (#3).
  3. The re-instruction/reroute ergonomics ("fix it this way") exist as params but aren't surfaced as the operator's clean choice.

## Judgment (Claude, invited by Smith)
Smith's model is RIGHT and ~80% already built (`run_approve_entry`). The work is NOT "build a resume surface" but:
- (a) **Promote `run_approve_entry` to THE canonical, documented resume surface** (skill + a thin CLI/MCP verb); retire the `resume_building_plan`-alone footgun (or make it auto-forward / point to approve).
- (b) **Make it behavior-preserving:** resume's NOT-yet-run continuation uses the SAME pool logic as forward (parallel fan groups). Replay of COMPLETED steps stays serial (correct — deterministic rehydration); only the new continuation parallelizes. Record order stays canonical (FIFO drain) so determinism holds — so the serial-resume guard is over-conservative, not necessary.
- (c) Surface **forward / reroute(+re-instruction) / stop** as the clean operator choices at that one verb.

## Maps to goal
Track B-1 (launch/operate ergonomics) — the resume surface is the "operate" half of "build as fluent as a workflow" ([[build-fluency-roadmap-0626]]). Folds with C6 (one honest run() call). The behavior-preserving fix (resume parallelizes the continuation like forward) is an engine change = building candidate (#3, concrete fix location measured above: walker_kernel.py:2555). ⚠️ **There is NO env stopgap:** `BRICK_FANOUT_DISPATCH_POOL_SIZE=8` does NOT parallelize a resumed fan (measured 0626 — line 2556 clobbers the override on resume). Resume QA stays serial until the engine fix lands; accept the latency.
