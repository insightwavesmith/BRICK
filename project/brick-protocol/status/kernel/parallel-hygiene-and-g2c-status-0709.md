# Parallel Hygiene + G2-c (cleanup-10e order-chain) Status — 0709

| | |
|---|---|
| **Status** | support evidence only |
| **Date** | 2026-07-09 |
| **Live repo** | `/Users/smith/projects/BRICK` |
| **Proof limit** | not source truth · not success/quality judgment · not Movement authority |
| **Not done by this note** | product code edits · skill/ship-copy repair · directory deletes · vessel moves |

---

## 1. What "cleanup-10e order-chain" (#3 / G2-c) means

```text
Name chain:
  ⑩e (phase under GOAL/02 unified cleanup) 
    = COO order-chain skill/prompt/hook consistency
  cleanup-10e = operational shorthand for ⑩e repair follow-on
  #3 = remaining-frontier item in GOAL/03
  G2-c = same item as a G2 sub-slot in GOAL/04 ladder
```

**Intent:** keep the COO ordering path consistent across Agent skills, ship-copy
skills, Building Call menus/code, and related checker pins:

```text
small work  → direct_preset only after admission + fast_confirm
normal work → order_authoring Building (default)
critical    → human_gate_first
```

Brick-facing authoring must not expose adapter/model/provider/`selected_*`
authority. Movement stays `forward | reroute` only.

**Map already done (docs-only):**

```text
project/brick-protocol/status/kernel/coo-order-chain-consistency-0709.md
```

That map states: core Quick Path policy is largely aligned across
`brick-task-author`, `building-call-authoring`, `building_call.py`,
`building_call_menus.py`. **No wording repair has been executed.**

**Candidate repair Building (not fired):**

```text
building_id_candidate: cleanup-10e-order-chain-consistency-0709a
```

No `project/brick-protocol/buildings/cleanup-10e*` (or equivalent) intake/evidence
was found at report time.

---

## 2. Files / surfaces (G2-c)

### Authority / status

| Path | Role |
|---|---|
| `project/brick-protocol/status/kernel/coo-order-chain-consistency-0709.md` | ⑩e map + repair plan |
| `project/brick-protocol/status/kernel/cleanup-scope-invariants-0709.md` | ⑩a parent scope; ⑩e slot |
| `project/brick-protocol/status/kernel/skills-ship-copy-drift-map-0709.md` | ⑩d; feeds Watch A/C/D |
| `project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md` | ⑩e marked map-done; optional repair remaining |
| `project/brick-protocol/status/kernel/GOAL/03-remaining-frontier-goal-0709.md` | frontier **#3** optional small |
| `project/brick-protocol/status/kernel/GOAL/04-goal-phases-0709-route-and-frontier.md` | **G2-c** checkbox open |
| `project/brick-protocol/status/kernel/ACTIVE_COO_GOAL.md` | G2 includes #3 order-chain; G2 Exit still pending |
| `project/brick-protocol/status/kernel/handoff-coo-0709-remaining-frontier.md` | #3 parallel-with-W1 note |
| `project/brick-protocol/status/kernel/parent-goal-closure-0709.md` | optional cleanup-10e still not closed |
| `project/brick-protocol/status/kernel/building-plans-location-decision-0709.md` | lists cleanup-10e as alternate candidate |

### Likely write_scope if repair Building runs

From `coo-order-chain-consistency-0709.md` §5:

```text
brick_protocol/agent/skills/building-coordination/SKILL.md
brick_protocol/brick/templates/skills/building-coordination/SKILL.md
brick_protocol/agent/skills/brick-task-author/SKILL.md          (review/repair if selected_* confuses)
brick_protocol/brick/templates/skills/brick-task-author/SKILL.md
brick_protocol/support/checkers/profiles/coo_operating_chain.yaml
brick_protocol/support/checkers/profiles/building_skill_preset_builder_composition.yaml
brick_protocol/support/checkers/profiles/building_call_menus.yaml
GOAL/status notes
```

**Forbidden for this slice:** route/walker, Link axis, AgentFact, provider runtime.

### Watch items still open (map §3.2)

| ID | Item | Size hint |
|---|---|---|
| A | `building-coordination` ship-copy missing hold-disposition section vs Agent source | strongest small patch |
| B | `brick-task-author` `selected_*` in example block — classify allowed vs confusing | review, maybe rewrite |
| C | `building-sizing-method` ship-copy overlay — do **not** blind-sync | leave unless checker pin co-updates |
| D | maybe-ship skills (`building-call-authoring`, etc.) packaging | out of minimal ⑩e; needs own Building |

---

## 3. Current status — code fix still needed?

| Layer | State |
|---|---|
| Consistency **map** | **Done** (docs-only) |
| Runtime Building Call policy | **Already enforcing** core direct/order/human_gate rules (per map §3.1) |
| Skill/ship-copy **repair** | **Not done** — still optional open work |
| Declared Building run | **Not started** (`cleanup-10e-order-chain-consistency-0709a` candidate only) |
| G2-c Exit checkbox (GOAL/04) | **Open** `[ ]` |
| ACTIVE G2 | **IN PROGRESS** — W1b/product Exit is the bulk; #3 is residual parallel |

**Answer:** a **runtime engine fix is not the remaining work**. Remaining work is
**optional small wording/ship-copy classification + sync** (docs/skills/checker
pins), via declared Building if chosen. Product behavior already has the policy
in `building_call.py` / menus; the gap is consistency projection, not a missing
Movement or walker feature.

---

## 4. Work size

```text
Size class: 소형 (optional)
Primary patches: ~1–2 skill pairs (coordination sync; task-author label/review)
Checker profiles: pin-aware only if wording changes pins
Forbidden: route/walker/Link expansion
Proof: focused coo_operating_chain + skill/composition/menus profiles;
       clean detached --all when landing resource changes
```

Estimate relative to ladder: **much smaller than G2-b authoring product** or
**G3 prevention live**. Suitable for a short declared Building or even
docs-only if only classification notes land (direct_preset rules in ⑩a still
apply).

---

## 5. Can G2-c run parallel to G3?

**Yes — route-nondependent; safe to parallel with G3.**

Evidence:

```text
GOAL/04:
  - G2-c listed "소형, 병렬 가능"
  - Exception: G2-a / G2-c parallel even with G0 (route 비의존)
  - Parallel graph: G2 Authoring ∥ G3 Prevention after G1;
    G2-a/c smalls explicitly parallel-allowed
  - Master queue: G2-c under "병렬 소형 (route 비의존)"

GOAL/03 / handoff:
  - #3 with W1 parallel small
```

**Caveats for parallel with G3:**

```text
- Do not touch walker_kernel / prevention hook surfaces in the same write_scope.
- Prefer skill/ship-copy only; avoid co-editing G3 live prevention files.
- G3 still depends on G1 path for Exit honesty; G2-c does not.
- ACTIVE next operator move prioritizes G2 Exit (profiles) then G3 fire;
  G2-c can ride beside either without unblocking G3.
```

G4 note: ACTIVE maps residual #3 also under G4 customer surfaces in the summary
table; GOAL/04 G2 owns G2-c as Exit checklist item. Treat G2-c as closable
whenever repair lands — do not wait for G4 UX if #3 finishes earlier.

---

## 6. "BRICK directory / worktree cleanup" — where it sits

**Not a G0–G6 phase name.** It is operational hygiene / phase-⑩ cleanup family
work, not an Exit gate on the 04 ladder.

### 6.1 03 log: worktrees 106→3

From `GOAL/03-remaining-frontier-goal-0709.md` progress log:

```text
[✅ 정리] 워크트리 106→3 (BRICK + 도는 v2 2),
  buildings 산출물 30개 /tmp 아카이브 (비파괴),
  미커밋 전량 salvage (refs/brick-salvage/ 21개),
  디스크 ~1.1G 회수.
```

This is **operator disk hygiene already performed** (non-destructive archive +
salvage). It is **not** G2-c order-chain and **not** G5 vessel split.

### 6.2 `cleanup-scope-invariants-0709.md` (⑩a)

Defines **what may later be cleaned** under unified GOAL phase ⑩:

```text
⑩b blocks map
⑩c building_plans location decision
⑩d skills ship-copy drift
⑩e COO order-chain consistency   ← G2-c / #3
⑩f customer UX
⑩g dogfood vessel separation      ← structural, human gate
```

Global rules: no blind directory delete/move; no vessel move while active
GOAL/status lives under `project/brick-protocol/`.

### 6.3 G5 vessel split (#4 / ⑩g)

```text
G5-a = project vessel physical split / template migration
     = design-first + human gate
```

**⑩g human gate already closed as Option A KEEP+clarify**  
(`dogfood-vessel-separation-approval-0709.md`):

```text
Keep project/brick-protocol as active dogfood vessel.
No move/delete/archive/split now.
Future physical split = new human gate + declared Building.
```

So "directory/vessel cleanup" as **structural migration** sits in **G5 / ⑩g**,
currently **frozen keep**, not open for destructive ops.

### 6.4 Classification table

| Work | Is G0–G6 phase? | Status |
|---|---|---|
| Worktree reap 106→3 + buildings /tmp archive | No — ops hygiene in 03 log | Done (evidence) |
| ⑩a scope/invariants map | No — support map under ⑩ | Done |
| ⑩e / cleanup-10e / #3 / **G2-c** order-chain | **Yes — G2-c** (optional small) | Map done; repair open |
| ⑩g vessel physical split | **Yes — G5-a** (structural) | Gate: KEEP; no migrate |
| Blind BRICK tree delete | Forbidden | Not admitted |

---

## 7. Operator summary

```text
G2-c = optional skill/ship-copy consistency repair after ⑩e map.
       Not a route/prevention blocker. Parallel-OK with G3.
Work size = small. Runtime policy largely already green.
Directory/worktree cleanup ≠ G2-c; 106→3 already done as hygiene.
Vessel split = G5-a / ⑩g KEEP; not a phase named "directory cleanup".
Next if chosen: declare cleanup-10e-order-chain-consistency-0709a
  (Watch A sync first; classify B; leave C unless pin co-update).
```

## 8. Not proven by this note

```text
- That Watch A/B are defects vs allowed intentional drift
- That a repair Building is required for G2 product Exit
  (ACTIVE G2 Exit still centers W1b/profiles; #3 is residual)
- Live worktree count today (03 log is historical snapshot)
- Installed/live provider skill projection freshness
```
