# Customer-Ready FINAL Architecture — provider_preflight leaf extraction proof — 0630

Status: FORWARD candidate / support evidence only. Not source truth, not success
judgment, not quality judgment, and not Link Movement authority.

## What this proves (and what it does NOT)

This is the FIRST G3 leaf produced through a REAL Building drawn and fired by the
MAIN AGENT (goal rule 0c / requirement R1a), not a direct operator patch. It is
also the third kernel_checks.py leaf overall (after no_smith_residue and
install/release-export lint).

```text
PROVEN:
  - main agent drew the graph with assembly.build/fan/fire (no caller JSON packet)
  - official customer route fired: run_customer_graph_building_in_sandbox (W1 worktree sandbox)
  - real providers ran: Codex (work) / Claude (code-attack-qa) / Gemini (axis-attack-qa) / Codex (closure)
  - declared graph carried fan_out + fan_in groups
  - closure received BOTH QA lane handoffs (fan-in evidence collection)
  - frontier_kind = complete
  - sandbox commit 3ec6502 produced on genuine completion, parent == main HEAD f13d6e7
  - byte-identical relocation (verified by COO below)

PARALLELISM CONFIRMED (controlled timing probe, 0630):
  - The engine semantics: a drawn fan() IS the parallel declaration — when a plan
    has fan groups and no explicit fanout_dispatch_pool_size override, the walker
    defaults dispatch_pool_size to _FANOUT_AUTO_POOL=8 and submits ready fan-out
    lanes through ThreadPoolExecutor (support/operator/walker_kernel.py,
    walker_frontier_driver.py). This plan had fan groups and NO override.
  - A controlled same-shape timing probe (work -> fan[code-attack-qa,
    axis-attack-qa] -> closure, wall-clock-stamping command_runner) showed the two
    QA lanes ran on DISTINCT threads with ~1.2s wall-clock OVERLAP (= full lane
    duration), while work and closure ran alone. VERDICT: PARALLEL CONFIRMED,
    frontier=complete. So fan-out lanes execute concurrently, not serially.
  - execution_order in the plan is the canonical/topological RECORD order (FIFO
    drain), NOT proof of serial physical execution. (Earlier reading of
    execution_order as "serial" was a documented misjudgment, 0630.)

NOT SEPARATELY ASSERTED:
  - The ORIGINAL real-provider run's per-lane wall-clock timestamps were not
    separately recorded (the recorded evidence stamps are canonical drain-time).
    Concurrency is proven by the controlled same-shape probe above, not by the
    original run's stamps.
```

Lesson captured (0630): execution_order (canonical record order) must NOT be read
as serial-execution evidence. Graph fan-out walk and physical concurrency are
distinct claims.

## Building

```text
building_id   = g3-provider-preflight-leaf-0630
evidence_root = ~/.brick/project/brick-protocol/buildings/g3-provider-preflight-leaf-0630
isolation     = worktree (git-head-resolved), disposed after commit
commit_sha    = 3ec650238090758c1329e5586c312c835e745738 (parent f13d6e7 == main HEAD)
adapters      = codex-local (work, closure), claude-local (code-attack-qa), gemini-local (axis-attack-qa)
graph         = build([ work(write), fan([code-attack-qa, axis-attack-qa]), closure ])
                closure route: reroute(IMPLEMENTATION_GAP -> back(1) work, budget 2); hold(VERIFICATION_GAP)
```

## What moved

```text
support/checkers/lib/provider_preflight_check.py   (new, 154 lines)
```

Symbols moved VERBATIM from kernel_checks.py:

```text
_PROVIDER_PREFLIGHT_REQUIRED_KEYS, _PROVIDER_PREFLIGHT_AUTHED_LITERALS,
_provider_preflight_assert_shape, run_provider_preflight
```

Enabling relocation: the shared 4-line helper `_ensure_import_identity` moved
byte-identical into the base lib `support/checkers/lib/yaml_subset.py` and is
re-exported from kernel_checks.py (keeps all 9 in-file call sites working).

## Conservation result

```text
kernel_checks.py: 11151 -> 11017 LOC (net -134)
provider_preflight_check.py: new flat sibling, byte-identical bodies
cumulative kernel_checks.py decomposition: 11452 -> 11017 (net -435 across 3 leaves)
```

## COO independent verification (this turn, not trusting agent returns alone)

```text
byte-identical: provider_preflight bodies vs pre-move HEAD f13d6e7 span 3000-3132 = EMPTY diff
byte-identical: _ensure_import_identity in yaml_subset vs HEAD def = EMPTY diff
compileall (kernel_checks, provider_preflight_check, yaml_subset, check_profile) = PASS
re-export identity: kc.run_provider_preflight IS pp.run_provider_preflight = True
helper re-export identity: kc._ensure_import_identity IS ys._ensure_import_identity = True
dispatch identity: KERNEL_DISPATCH['provider_preflight'] IS pp.run_provider_preflight = True
const re-export: kc._PROVIDER_PREFLIGHT_REQUIRED_KEYS == pp._PROVIDER_PREFLIGHT_REQUIRED_KEYS = True
GREEN baseline: run_provider_preflight(repo) inspected=6
mutation-RED: missing-required-keys status -> ProfileError fired
mutation-RED: bad authed literal -> ProfileError fired
git diff --check (staged) = clean
REAL HOME check_profile.py --all = rc=0, 28 profiles passed, 0 failure markers
```

## Three-axis attribution

```text
Brick evidence: declared leaf-extraction work; module/file boundary only.
Agent evidence: real provider performers returned closed AgentFact(received_work, returned);
  closure received both QA handoff refs.
Link evidence: declared graph edges + fan_out/fan_in groups; closure carried route marks
  (reroute on implementation_gap, hold on verification_gap); Movement forward on complete.
Support surface: checker-lib module + registry; support recorded facts only.
Rejected shortcut: do not relocate by module name alone — admitted because the AST
  dependency audit proved a true leaf (only shared dep _ensure_import_identity, relocated).
```

## Not proven / caveats

```text
- wall-clock parallel overlap of QA lanes not separately timestamp-measured (engine
  is auto-parallel-eligible; measurement is a separate probe).
- Direct provider behavior / future Building correctness / source truth / success /
  quality / Movement authority remain not_proven.
- kernel_checks.py (11017) is still the largest godmodule; more leaves remain and a
  G3 STOP CONDITION is still undeclared.
```

## Next Movement candidate

Forward this leaf (integrated into main by cherry-pick of 3ec6502). Continue G3 by
the main agent drawing + firing the next leaf Building (e.g. onboard_smoke /
design_ai_text_seams clusters), each under conservation-ledger + byte-identical +
mutation-RED discipline, until a declared STOP CONDITION.
