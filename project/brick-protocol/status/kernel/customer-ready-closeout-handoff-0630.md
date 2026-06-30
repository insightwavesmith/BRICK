# Customer-Ready Closeout — handoff checkpoint — 0630

Status: HANDOFF / support evidence only. Not source truth, not success judgment,
not quality judgment, and not Link Movement authority.

## Reload order for next session

```text
1. AGENTS.md
2. project/brick-protocol/status/kernel/customer-ready-goal-anchor-v01.md
3. project/brick-protocol/status/kernel/customer-ready-closeout-goal-0630.md
4. project/brick-protocol/status/kernel/customer-ready-closeout-requirements-audit-0630.md
5. this handoff: customer-ready-closeout-handoff-0630.md
6. git status / git log / latest evidence roots (live)
```

Live repo evidence overrides this handoff if drift is found.

## Current git state at handoff

```text
repo = /Users/smith/projects/BRICK
branch = main
current HEAD before this handoff commit = 1486bb8
origin/main relation before this handoff commit = ahead 6, behind 0
worktree before this handoff doc = clean, then this handoff/status doc update
push status = NOT pushed; external publish requires Smith OK
```

Recent local commits:

```text
1486bb8 Goal: G3 provider_preflight leaf via main-agent-fired Building (parallel fan-out confirmed)
f13d6e7 Goal: track main-agent draw-fire rule in closeout audit
ec380ca Goal: add binding rule — main agent must draw+fire Buildings for impl slices
9a970e1 Goal: prove G2 release export payload parity
c3d8e03 Goal: G3 extract install/release-export lint leaf from kernel_checks
fb130da Goal: sync G3 closeout doc to landed no_smith_residue leaf + per-leaf reqs
a779a2c Goal: extract no_smith_residue leaf from kernel_checks
```

## Goal status

Goal remains ACTIVE. Do not mark complete.

Three closeout tracks:

```text
G1 route-default policy
G2 customer release pruning finalization
G3 FINAL architecture cleanup
```

Binding operating rule added this session:

```text
0c / R1a: the main agent must draw and fire real Buildings for G1/G2/G3
implementation slices so the main-agent building-running skill chain is exercised
end to end. Direct implementation patching is no longer the default.
```

## Completed / narrowly proven this checkpoint

### R1a — main-agent draw+fire Building proof

First real main-agent-fired implementation Building landed:

```text
building_id   = g3-provider-preflight-leaf-0630
evidence_root = ~/.brick/project/brick-protocol/buildings/g3-provider-preflight-leaf-0630
proof doc     = project/brick-protocol/status/kernel/customer-ready-final-architecture-provider-preflight-proof-0630.md
frontier_kind = complete
sandbox commit = 3ec650238090758c1329e5586c312c835e745738
integrated commit = 1486bb8
```

Graph drawn by main agent:

```text
build([
  work(Codex, write),
  fan([code-attack-qa(Claude), axis-attack-qa(Gemini)]),
  closure(Codex, route=[implementation_gap -> work, verification_gap -> HOLD])
])
```

Honest proof scope:

```text
PROVEN:
- main agent drew and fired `fire(graph)` via official customer route
- declared graph had fan_out + fan_in groups
- closure received both QA handoffs
- frontier complete + sandbox commit produced and integrated
- engine fan-out parallelism confirmed by controlled same-shape timing probe

NOT SOURCE TRUTH / NOT QUALITY / NOT MOVEMENT AUTHORITY:
- all model/checker/proof outputs are support evidence only
```

Parallel correction / lesson:

```text
execution_order is canonical/topological record order, not serial-execution proof.
Current engine semantics: drawn fan() is the parallel declaration; fan groups with
no explicit fanout_dispatch_pool_size use _FANOUT_AUTO_POOL=8 and ThreadPoolExecutor.
Controlled timing probe showed code QA and axis QA on distinct threads with ~1.2s
overlap. Parallel fan-out confirmed.
```

### G3 provider_preflight leaf

Moved via Building output:

```text
new: support/checkers/lib/provider_preflight_check.py
modified: support/checkers/lib/kernel_checks.py
modified: support/checkers/lib/yaml_subset.py
modified: support/checkers/module_registry.yaml
```

Conservation:

```text
provider_preflight bodies byte-identical vs pre-move HEAD f13d6e7 span 3000-3132
_ensure_import_identity helper byte-identical into yaml_subset.py + re-exported
kernel_checks.py: 11151 -> 11017 LOC (net -134)
cumulative kernel_checks.py: 11452 -> 11017 LOC (net -435 across 3 leaves)
```

Verification done before 1486bb8:

```text
compileall changed modules = PASS
re-export identity = True
dispatch identity KERNEL_DISPATCH['provider_preflight'] = True
mutation-RED missing keys = fired
mutation-RED bad authed literal = fired
focused profile agent_axis_behavioral = PASS
REAL HOME check_profile.py --all = rc=0, 28 profiles, 0 failure markers
```

## Current closeout track state

### G1 — route-default policy

Narrowly proven:

```text
- no-link/default policy documented in skills/docs
- engine route/reroute behavior green for n2 single-reroute case
- fan-in QA concern -> Link reroute -> work replay -> closure measured in building_operator_driver0
```

Remaining / not_proven:

```text
- deep L2 cascade replay beyond n2
- customer comprehension of no-link/materialized-forward/reroute distinction
```

### G2 — customer release pruning finalization

Narrowly proven:

```text
- release export excludes project/ and brick_protocol.egg-info/
- Smith-local literal scrub outside README allowance
- fresh export CLI smoke: uv sync/import/CLI help/brick verify
- provider-free first-run docs honestly caveat agent_incomplete/not_ready
- release export payload parity across two runs (excluding generated .git metadata)
```

Remaining / not_proven:

```text
- real provider-backed fresh export build reaching frontier_kind=complete
- customer reading-comprehension / first-run UX validation
```

### G3 — FINAL architecture cleanup

Narrowly proven:

```text
- no_smith_residue leaf extracted
- install/release-export lint leaf extracted
- provider_preflight leaf extracted by real main-agent-fired Building
- current kernel_checks.py = 11017 LOC
```

Remaining / not_proven:

```text
- kernel_checks.py still largest godmodule
- more leaves remain (candidate: onboard_smoke, design_ai_text_seams, codex_connect_stall, gemini_local_only)
- G3 STOP CONDITION not declared
```

## Next best move after break

Recommended next action:

```text
1. Do NOT start with another direct patch.
2. Declare a G3 STOP CONDITION with Smith, OR pick the next G3 leaf if Smith wants momentum.
3. Main agent draws and fires the next Building (0c/R1a), likely:
   design/ledger -> work(write) -> fan([code QA, axis QA]) -> closure.
4. If continuing leaf extraction: candidate onboard_smoke or design_ai_text_seams.
5. Use same proof discipline: conservation ledger, byte-identical move, module_registry row,
   mutation-RED, focused profile, REAL HOME --all, honest proof limits.
```

Do not claim goal complete until:

```text
G1 deep cascade/customer comprehension disposition is settled
G2 provider-backed fresh export complete/customer comprehension settled
G3 stop condition declared and reached or remaining debt explicitly accepted
main = origin/main (after Smith OK to push)
worktree clean
final closeout record written
REAL HOME --all green at final close
Smith/COO forward disposition
```

## Commands to resume quickly

```bash
cd /Users/smith/projects/BRICK
git status --short --branch
git rev-list --left-right --count origin/main...main
git log --oneline -10
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
```

## Push note

At handoff, main is ahead of origin. Do not push unless Smith explicitly says OK.

## Update — onboard_smoke leaf attempt (0630, in progress)

```text
G3 next leaf attempted via main-agent fire: g3-onboard-smoke-leaf-0630
Result: frontier_kind=link_paused (NOT complete), no sandbox commit, twice.
Route worked (QA -> closure -> Link pause), so this is route-default behaving.

Attempt 1: closure implementation_gap = sibling missing `from typing import Any`
  (my fire prompt's import list omitted typing.Any). Fixed prompt, re-fired.
Attempt 2: closure implementation_gap = QA lane reports onboard_smoke_check.py
  "missing in current checkout" + "git status no changed paths", yet WORK node
  returned made_changes=True with the 3 expected files.
  => suspected work-write-invisible-to-QA in the graph worktree sandbox.
  Earlier delegated read-only root-cause to a Codex ai-cli process (later corrected: future 실측 진단 should be a single diagnostic Building, not a named Codex Ultra/gpt tier).

Token-cost note: investigation delegated to Codex per 0d; main thread did only
bounded field-extraction checks.

NEXT: read Codex diagnosis; decide whether this is (a) a fire-prompt/work-quality
issue to re-fire, or (b) an engine fan-in/worktree visibility bug = separate
Brick/Link track. onboard_smoke is still a valid leaf target once the dispatch
visibility question is settled.
```

## Update — onboard_smoke re-fire after 0d (0630)

```text
Re-fired `g3-onboard-smoke-leaf-0630` with prompt corrected to include `from typing import Any`.
Latest frontier: agent_incomplete (NOT complete), no sandbox commit.
Work node returned made_changes=False with note:
  - "No verification commands could be run after the environment stopped creating processes."
  - "No file edits were recorded as applied."

Interpretation:
- This latest failure is not a successful route/HOLD closure; it is provider/work execution incomplete.
- Do not re-fire blindly. First determine whether this is provider process health, work prompt/tool failure,
  or a real sandbox/adapter issue.
- A Codex ai-cli diagnosis process for the earlier work-invisible-to-QA symptom was observed running
  (pid observed live at this checkpoint). Main thread should recover its bounded result before deciding
  whether to retry onboard_smoke or route an engine/support bug.
```

## Finalize verification checkpoint (0630)

```text
BUILD: PYTHONPATH=support/import_identity:. python3 -c "import brick_protocol, support.checkers.check_profile" = OK
TESTS: REAL HOME check_profile.py --all = rc=0, 28 profiles passed, 0 failure markers
WORKTREE: clean (0 uncommitted)
MAIN: ahead origin/main by 12, not pushed (Smith OK required)

onboard_smoke leaf: correctly NOT integrated — its Building never reached frontier=complete
  (attempt1 link_paused: missing typing.Any; attempt2 agent_incomplete: work process stopped).
  main carries NO partial/broken onboard_smoke code; kernel_checks.py still owns run_onboard_smoke.

COMPLETION AUDIT (finalize): GOAL IS NOT COMPLETE. Remaining not_proven:
  G1.3 deep L2 cascade replay; G1.4 customer comprehension
  G2.5 provider-backed fresh export build -> complete; G2.6 customer comprehension
  G3.3 kernel_checks still largest godmodule; G3.4 STOP CONDITION undeclared
  C1 main != origin/main (unpushed); final closeout record + Smith forward pending
Therefore update_goal(complete) is NOT called. Repo is in a clean, building, all-green state safe to pause.
```

## Update — diagnostic process status (0630)

```text
Earlier Codex ai-cli diagnosis pid 39918 is no longer running, and ai-cli no longer has
that process result (`Process with PID 39918 not found`). Treat its result as not
captured. If the onboard_smoke work-invisible / agent_incomplete question remains
important, re-run a bounded diagnosis Building/subagent rather than relying on
that lost process.

Latest live frontier for `g3-onboard-smoke-leaf-0630`: agent_incomplete, no
sandbox commit. Do not integrate. Next action = either re-fire with provider health
confirmed or route a focused diagnostic Building on adapter/worktree visibility.
```


## Update — onboard_smoke leaf completed (0630)

```text
g3-onboard-smoke-leaf-0630b reached frontier=complete and produced sandbox commit aa8dbccc204e5a1b8705ce36913193f9f219df0b.
Integrated onboard_smoke leaf into main: support/checkers/lib/onboard_smoke_check.py new sibling, kernel_checks.py 11017 -> 10814.
COO verification: byte-identical, dispatch identity, mutation-RED, focused building_operator_driver0 PASS, REAL HOME --all 28/0.
Earlier g3-onboard-smoke-leaf-0630 paused/incomplete attempts remain evidence only and were not integrated.
```


## Update — G3 stop condition declared (0630)

```text
Stop doc: customer-ready-g3-stop-condition-0630.md
Closeout G3 target: kernel_checks.py < 10000 LOC OR all remaining >=200 LOC candidates explicitly deferred.
Current kernel_checks.py: 10814 LOC.
Next recommended leaves: codex_connect_stall_classification, design_ai_text_seams, gemini_local_only_adapter.
G3 stop condition is declared but not yet met.
```


## Update — operating correction: no Codex Ultra / diagnostics as single Building (0630)

```text
Smith correction: there is no “Codex Ultra” model/tier in this operating vocabulary.
Do not write or plan around Codex Ultra / gpt-5.5 xhigh as the default diagnostic route.

For 실측 진단 / code-heavy inspection / broad evidence scan:
  - main agent remains COO/operator and does not spend broad-token context reading raw/code;
  - declare and fire ONE diagnostic Building;
  - assign Codex as the performer lane/adapter when useful;
  - closure returns bounded observed_evidence / narrowly_proven / not_proven / next.

Subagents are not the default planning primitive for this closeout. Use Buildings.
```

## Resume todo list (current, 0630)

```text
0. Current repo: main clean, origin/main behind by local commits; do not push without Smith OK.
1. G3 remaining: stop condition declared but not met. kernel_checks.py = 10814 LOC; closeout target <10000 LOC OR defer all remaining >=200 LOC candidates with owner/reason.
   Next candidate Building: codex_connect_stall_classification OR design_ai_text_seams.
   Diagnostic/AST audit should be a single diagnostic Building, not a subagent assumption.
2. G2 remaining: provider-backed fresh export build reaching frontier_kind=complete; customer comprehension/first-run UX still not_proven.
3. G1 remaining: deep L2 cascade replay beyond n2; customer comprehension of route-default/no-link policy.
4. Final closeout: REAL HOME --all, final closeout record, main clean, push after Smith OK, requirement-by-requirement completion audit.
```
