# god-module + checker-diet decomposition — Decision Table — 0626

Source: building `godmodule-design-0626` (4 parallel design-lead Bricks → closure, read-only, frontier=complete, 0 adapter errors). True multi-root live proof (see [[single-entry-multiroot-finding-0626]]). Quality-judged by workflow `w0xfa8l7y` (append results when landed).

## Targets (split vs facade)

**kernel_checks** — 10232 LOC, ~24 independent kernel-check domains, single importer check_profile.py:125-150
- RECOMMEND: **facade-preserving split** — per-domain `lib/*.py` + `kernel_common.py` (shared call_main/_ensure_import_identity); keep kernel_checks.py as thin re-export facade so import block + registry pins stay byte-stable.
- RISK: chat_session bodies non-contiguous (move by symbol not line range); 3 axis-vocab self-allowlist pins :115/:123/:130 must relocate or axis_vocab_drift REDs; each leaf needs a G4 registry row + G5 forbidden_ownership echo.

**case_runners** — 10223 LOC, ~33 public run_*_case + ~80 helpers, no __all__
- RECOMMEND: **split by support-surface (route-B, facade removed)**; facade-kept = lower-blast-radius fallback. Leaves: case_runners_{adapter,materialize,intake,drain,link}.py + common.
- RISK: 2 private helpers cross-imported (kernel_checks.py:4401,5276; driver0.py:75) must land in common leaf; cluster-local constant tuples must travel with their function; circular-import if common depends on surface leaves; RULE_RUNNERS keyset must stay byte-identical.

**walker_kernel** — 3804 LOC (post-P3c residual), 5 leaf clusters
- RECOMMEND: **split clusters A-E** (A frontier-driver, B carry/step-output/wiki, C runtime-mail, D resume-seed, E report-events; optionally F) to sibling walker_* modules; keep walker_kernel as slim orchestrator. facade-vs-no-facade = secondary separable choice.
- DO-NOT-SPLIT: **_run_dynamic_graph_walker** (~1447 LOC, ~30 shared mutable locals, 7 nested closures) — not splittable without a WalkerState dataclass; defer as a separately-gated change.
- RISK: ResumeSeed/replay_gate/_runtime_handoff_unresolved_address/wiki_carry_* imported by run.py, walker_resume.py, dynamic_walker.py, case_runners.py AND check_bounded_agent_proposed_routing_loop0.py — need re-export (A1) or atomic importer update (A2); pool=1 vs pool=N byte-identity asserted.

**checker-diet** — 97 case labels (building_skill_preset_agent_tool_hardening.yaml)
- RECOMMEND: **option A — complete-the-split then DELETE the original** (facade structurally impossible); facade fallback = keep original canonical + downgrade the 3 copies to documented "partial concern view".
- KEY: check_profile.py has NO extends/include/inherit/facade primitive — a true delegating facade must physically retain all 97 bodies = defeats the diet.
- Conservation today: 12/97 labels duplicated (8 builder_composition + 4 intake_adapter_gate), 85/97 carried ONLY by the original, agent_resource_boundary carries 0 labels.
- RISK: deleting original orphans 85 labels; concern families (p5/p6 source-fact-carry, gate-sequence, hard-graph, multi-leader, governance-hint) have NO matching split home (may need a 4th split or explicit "retained" decision); 12 duplicated labels can drift (no equivalence check); B2b mutation-RED probe per moved label required before deletion.

## Quality judgment (workflow w0xfa8l7y — claims verified vs real code, 0626)
Adversarial verify of each recommendation against ground truth OVERTURNED the naive size-based read.

| target | grounded/complete/sound | trust | verdict |
|---|---|---|---|
| **walker_kernel** | 5/5/5 | **HIGH** | gold standard. line count exact (3803), 1447-LOC god-fn span exact, 7 closures exact, full reverse-dep map confirmed. only 2 cosmetic line-pointer slips. **SAFEST FIRST.** |
| case_runners | 3/5/4 | MEDIUM | plan sound + most complete, but coordinates STALE — kernel_checks cross-imports actually :3978/:4853 (not 4401/5276); text-pin in agent_axis_behavioral.yaml:180-185 (not check_package_path_admission). Re-derive all offsets; plan survives. |
| checker-diet | 4/3/4 | MEDIUM | label arithmetic (97/12/85) + no-facade fact CORRECT, but **WRONG invariant**: "stale path_allowlist entry for deleted file → core RED" is FALSE (run_path_allowlist never REDs on a missing allowlisted file). Missed pin module_registry.yaml:1362 + docs. **RE-INVESTIGATE the deletion gate.** |
| **kernel_checks** | 2/2/3 | MEDIUM (weakest) | line count off by 424 (**9808, not ~10232**) → EVERY coordinate stale. **MISSED BLAST RADIUS**: facade re-exports only public run_*, but building_automation.yaml:153-163 pins the private _chat_session_* helpers being moved + read_side_projection_boundary.yaml:265-277 pins reporter literals in moved bodies → BOTH go RED on split. "unchanged_surfaces" claim REFUTED. **RE-INVESTIGATE** (≥3 pin families, not 1; whole coord map stale). |

## Operator read (quality-corrected)
- **Start with walker_kernel** — the ONLY 5/5/5, risk surface actually mapped to ground truth. (Mind the 1 do-not-split god-fn + refresh 2 slipped line pointers.)
- **case_runners** — sound plan, but treat its file:line as NON-authoritative; implementer re-derives offsets.
- **RE-INVESTIGATE before acting**: kernel_checks (false "unchanged surfaces" + 424-line drift) and checker-diet (false RED-gate invariant + missed deps). The directions are right; the specifics are unsafe to act on as-is.
- Next: Smith picks target(s) + order → **A-dev building** (byte-identical verbatim relocation + G4 row/G5 echo per leaf + re-point importers/pins; codex; `check_profile.py --all` EXIT 0 as the behavior oracle + close gate). **Recommended first = walker_kernel.**

## Lesson (dogfood)
The design building's recommendations were architecturally sound but had stale coordinates + 2 understated blast radii. The QUALITY-JUDGE workflow (verify every claim vs real code) caught it — without it, an implementer would have trusted a 424-line-shifted reading map and a refuted "unchanged surfaces" premise. **Design output → adversarial verify vs ground truth is mandatory before A-dev.**

## A2 scope note (god-module decision)
This decision table answers the open A2 question (split vs facade) in [[customer-ready-goal-plan-2track-0626]]. 3 of 4 targets recommend SPLIT (facade as sub-choice/fallback); checker-diet's facade is structurally impossible.
