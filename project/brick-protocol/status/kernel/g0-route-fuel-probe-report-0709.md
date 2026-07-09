# G0 Route Fuel Probe Report — 0709

| | |
|---|---|
| **Status** | support evidence only · probe / investigation · not source truth |
| **Date** | 2026-07-09 |
| **Live repo** | `/Users/smith/projects/BRICK` |
| **Scope** | route/resume G0 — graph-decl lower, mid-hold, resume dead_end |
| **Proof limit** | not success/quality judgment · not Movement authority · no product commit |

---

## Findings

### 1. How `--graph-decl` lowers gates today

Trace (official front door):

```text
cli._run_graph_declaration_build
  → load_graph_declaration(path)
  → assemble_graph_declaration(declaration)
       → _reject_graph_packet_keys  (raw packet keys refused)
       → build([_graph_decl_item(n) for n in nodes])
       → assemble(graph, gates=top-level, …)
            → _lower_graph
                 → stamp_profile_gates(top-level gates)
                 → _stamp_node_gate_sequence_policies(per-node gates)
            → compose_building(…)
  → run_goal_approve_entry(proposal, action=…)
```

**Citations**

| Step | File:line |
|---|---|
| CLI graph-decl entry | `brick_protocol/support/operator/cli.py:567-570` |
| assemble_graph_declaration | `brick_protocol/support/operator/assembly.py:844-881` |
| packet-key reject | `assembly.py:809-820`, `943-949` |
| build() linear/fan | `assembly.py:576-695` |
| per-node opts incl. gates | `assembly.py:979-1041`, `1031-1032` |
| _lower_graph stamp order | `assembly.py:1950-1963` |
| top-level stamp_profile_gates | `assembly.py:1778-1818` |
| per-node stamp + error | `assembly.py:1967-1998` |
| merge → gate_sequence_policy | `assembly.py:2001-2046` |
| HOLD entry synthesis | `assembly.py:2088-2149` |
| human boundary policy | `composition_gate_translation.py:91-120` |
| walk-time hold | `gate_sequence.py:67-214` + `walker_kernel.py:2156-2183` |

**Two gate dials (do not confuse)**

| Dial | Graph-decl syntax | Effect |
|---|---|---|
| **Top-level** `gates:` | `gates: ["human-review"]` on the declaration root | `stamp_profile_gates`: only **final** edges (`target` starts with `building-boundary:`) get human HOLD policy. Mid edges stay auto-forward. `coo-review` alone adds gate ref on final edge but **does not** stamp HOLD policy (`assembly.py:1801-1817`; skill truth at `brick-task-author` §게이트 진실). |
| **Per-node** `gates:` | node mapping `gates: ["human-review"]` or `["coo-review"]` | `_stamp_node_gate_sequence_policies` merges policy onto that node's **single** outgoing EdgeSpec completion edge. Both tokens synthesize **HOLD** on missing disposition facts (`assembly.py:2109-2148`). |

**When `"exactly one outgoing completion edge; observed 0"` fires**

```text
assembly.py:1979-1988
  for each BrickSpec with non-empty gates:
    refs = outgoing EdgeSpec edge_refs only  # NOT the synthetic boundary edge
    if len(refs) != 1:
      raise ValueError(
        "brick gates for {label!r} require exactly one outgoing completion edge; "
        "observed {len(refs)}. Declare the gate_sequence_policy explicitly to disambiguate."
      )
```

| Case | `len(refs)` | Result |
|---|---|---|
| Mid spine node with one forward EdgeSpec | 1 | merge HOLD policy on that edge (mid-walk gate hold) |
| Fan-out source / multi-out | N>1 | error `observed N` |
| **Terminal** node with per-node gates | **0** | error `observed 0` — boundary edge is added in `_lower_edges` (`assembly.py:2297-2306`) but is **not** an `EdgeSpec` and is **not** counted in `_stamp_node_gate_sequence_policies` (`1974-1977`) |
| Isolated single-node building + per-node gates | 0 | same observed-0 |

Contrast: `_lower_graph` **does** count the boundary when setting multi-out `completion_edge_ref` (`assembly.py:1911-1918`). Stamp and completion_edge_ref disagree on the terminal boundary.

**Gate hold evaluation at walk**

`run_gate_sequence_policy` (`gate_sequence.py:67+`) reads Link-row `gate_sequence_policy`. For `link-gate:human` / `link-gate:coo`, missing `human_review_refs` / `override_refs` → missing required facts → policy action HOLD (`link/gate.py:233-240`, `gate_sequence.py:181-214`). Walker records hold with `hold_reason` like `gate_sequence_missing_required_facts:link-gate:human` (`walker_kernel.py:2156-2176`).

---

### 2. Mid-walk approval-hold without raw graph packet keys?

**Yes — already present as assemble-arg / graph-decl syntax.**

Raw packet keys rejected at top-level (`assembly.py:809-820`):  
`brick_steps`, `declared_plan_copy`, `edges`, `execution_order`, `groups`, `link_edges`, `plan_ref`, `plan_shape`, `steps`.  
No need to author `node_id` / `completion_edge_ref` / `edges` lists for mid-hold.

**Documented / code-backed mid-hold path**

```yaml
# assemble-arg / --graph-decl body (sketch)
declared_by: coo
task: "…"
action: forward
# optional top-level human final hold:
# gates: [human-review]
nodes:
  - kind: design
    work_statement: "…"
    gates: [coo-review]   # MID: one outgoing EdgeSpec → HOLD after design
  - kind: work
    work_statement: "…"
    write: true
  - kind: closure
    work_statement: "…"
```

| Mechanism | Mid-walk gate_sequence HOLD? | Notes |
|---|---|---|
| Per-node `gates: [human-review\|coo-review]` on **non-terminal** with exactly 1 EdgeSpec out | **Yes** | `_merge_node_gate_sequence_policy` + `_node_gate_sequence_entry` HOLD |
| Top-level `gates: [human-review]` | **No (final only)** | HOLD on boundary edge only |
| Top-level `gates: [coo-review]` | **No HOLD** | ref stamp only on final |
| Per-node gates on **terminal** | **Assemble fails** | observed 0 |
| `route: [{action: hold, on: <concern>}]` | Fan-in converge only | `closure_transition_target_policy` hold marks — not gate_sequence_policy; only on fan-in converge (`assembly.py:1044-1058`, `1822-1849`) |
| Agent `transition_concern` under default binding | sometimes HOLD | `none`/`ambiguous` target → hold; many concerns walk on as `non_reroute` (`walker_transition_concern.py:143-150`, `walker_kernel.py:2534-2548`) — **not** the intentional mid gate-hold dial |

**Operator knowledge gap (G0 symptom):** skill already documents mid vs top-level (`brick_protocol/agent/skills/brick-task-author/SKILL.md` ~385-391). Production launches often use `gates: []` / no per-node gates → concern walk-on to closure → no hold ledger → resume surface dead_ends with a harvest-oriented message.

**Probe note:** import-time assemble probe was not executed in this investigation (read-only path analysis + skill 0702 실측). Exit probes below should execute the in-memory assemble cases.

---

### 3. `resume_declaration.preflight` dead_end conditions

File: `brick_protocol/support/operator/resume_declaration.py` · `preflight_resume_declaration` at **303-377**.

Exact branches that set `dead_end`:

| # | Condition | Lines | Packet extras |
|---|---|---|---|
| **P1** | `frontier_kind == "evidence_incomplete"` | 324-326 | `dead_end=True` only |
| **P2** | `_read_written_dynamic_plan(building_root)` raises `OSError \| ValueError \| TypeError \| json.JSONDecodeError` | 327-337 | `dead_end=True`, `error_kind`, `error_message` |
| **P3** | dynamic_walker evidence has **empty/absent** `hold` mapping | 338-342 | `dead_end=True` only |

**Not dead_end**

| Branch | Lines | Result |
|---|---|---|
| `frontier_kind == "complete"` | 321-323 | `matched=True`, `already_complete=True` |
| hold present + disposition row matches | 349-376 | `matched=True`, `selected_disposition` |
| hold present + no matching disposition | 377 | return packet with `matched=False` (**not** dead_end) |

**Runtime dead_end promotion** (`run_resume_declaration`, not preflight itself):

| # | Condition | Lines |
|---|---|---|
| **R1** | `preflight.dead_end` | 178-186 · error_kind `resume_declaration_dead_end` · harvest next_command |
| **R2** | approve round returns `error_kind == "not_approval_hold"` | 223-232 |
| **R3** | chain next-round preflight.dead_end | 267-275 |

Misleading honesty bug: **P3 and R1** always use the same Korean message / `_DEAD_END_NEXT_COMMAND` harvest text (`45-49`, `182-184`) even when the building simply **walked on with no hold ledger** (not an orphan ledger tail). That is the G0-B/C surface defect.

---

### 4. Recommendation — prefer **G0-B first** (thin + honest), then optional G0-A one-liner

#### Preferred track: **G0-B (+ thin G0-C messaging)** first

**Why first**

1. Mid-walk gate hold **already works** via per-node gates on non-terminals — G0-A is not a greenfield feature.
2. Production death mode is **resume dead_end with harvest prose** after walk-on / no-hold evidence (G0 phase doc §1.2-1.3).
3. Smallest safe product change: classify dead_end **kind** and stop lying about COO_GATE_HARVEST.

**Minimal code change (proposal only — not applied)**

| File | Change |
|---|---|
| `brick_protocol/support/operator/resume_declaration.py` | In preflight: when setting dead_end, stamp `dead_end_kind` + distinct `message_ko` / `next_command`: e.g. `evidence_incomplete` · `plan_unreadable` · `no_hold_ledger` (P3: hold empty; include `frontier_kind`/`frontier_reason`) · keep harvest hint only for true incomplete-tail cases if still wanted |
| same + `cli.py` `_render_resume` | Print `dead_end_kind` so operators see A-hold vs B-walk-on without JSON spelunking |
| skill / OFFICIAL_ROUTE_MEMO (doc only) | 1 table: hold graph (`gates` mid/final) vs walk-on → salvage / re-launch (not resume) |

**Risk:** low. Observation-only fields; no Movement, no gate synthesis, no walker change. Residual risk: message wording drift vs checkers that pin Korean strings — grep for `막다른 길` / `COO_GATE_HARVEST` before landing.

#### Optional follow-on: **G0-A** (if G1 dogfood needs terminal per-node gates)

**Problem:** terminal per-node gates → observed 0 because stamp ignores boundary edge.

**Smallest code fix**

| File | Change |
|---|---|
| `assembly.py` `_stamp_node_gate_sequence_policies` (~1974-1988) | When building `outgoing_by_handle`, also index **lowered** edges by `source` (so synthetic `edge:…-to-boundary-closed` counts as the single completion edge for terminals). Prefer this over inventing a new graph-decl key. |
| skill one line | "terminal per-node gates attach to the boundary edge" once stamp is fixed |

**Risk:** medium-low. Touches gate stamping; need focused checks that (1) mid-node still requires exactly one EdgeSpec, (2) fan-out still fails multi-out, (3) terminal+gates merge HOLD onto boundary without double-stamping vs top-level `gates: [human-review]`. Do **not** re-admit raw packet edges authoring.

**Not recommended as first move:** full raw packet revival, new Movement literal, or binding all concerns into hold (that is G0-B product semantics and broader).

#### Goal doc alignment

`04-goal-phases-0709-route-and-frontier.md` §G0 already ranks: **G0-C honesty → G0-A or G0-B**. This probe picks **B/C honesty first** because A mid-hold already exists; A residual is terminal observed-0 polish + fixture documentation.

---

## Exact files to touch

### G0-B / C (recommended first)

1. `/Users/smith/projects/BRICK/brick_protocol/support/operator/resume_declaration.py` — dead_end_kind + messages
2. `/Users/smith/projects/BRICK/brick_protocol/support/operator/cli.py` — `_render_resume` surface
3. Doc (pick one): `project/brick-protocol/status/kernel/OFFICIAL_ROUTE_MEMO.md` and/or `brick_protocol/agent/skills/brick-task-author/SKILL.md` PHASE 3 hold table

### G0-A (optional second)

4. `/Users/smith/projects/BRICK/brick_protocol/support/operator/assembly.py` — `_stamp_node_gate_sequence_policies` include boundary outgoing
5. Focused checker/fixture under existing profile family (no new standalone `check_*.py` without admission)

**Do not touch for G0:** walker Movement, driver dispose as “fix”, raw packet CLI revival, constitution.

---

## 3 probe commands for Exit

Run from repo root with the active import path used for BRICK (adjust PYTHONPATH if needed).

### Probe 1 — assemble mid-hold exists (G0-A syntax already green)

```bash
cd /Users/smith/projects/BRICK && PYTHONPATH=brick_protocol/support/import_identity:. python3 - <<'PY'
from brick_protocol.support.operator.assembly import assemble_graph_declaration

decl = {
    "declared_by": "coo-probe",
    "task": "g0 mid-hold assemble probe",
    "building_id": "g0-mid-hold-probe-0709",
    "adapter": "local",
    "nodes": [
        {"kind": "work", "work_statement": "mid hold after work", "gates": ["coo-review"]},
        {"kind": "closure", "work_statement": "close after disposition"},
    ],
}
composed = assemble_graph_declaration(decl, repo_root=".")
holds = []
for edge in composed.edges:
    pol = edge.get("gate_sequence_policy") or []
    for step in pol:
        if not isinstance(step, dict):
            continue
        miss = (step.get("on_missing_required_facts") or {}).get("action")
        if str(miss).lower() == "hold":
            holds.append((edge.get("edge_ref"), step.get("gate_ref"), miss))
print("edges", len(composed.edges))
print("hold_policies", holds)
assert holds, "expected mid-node gate_sequence HOLD"
print("PROBE1_OK")
PY
```

**Expect:** at least one HOLD policy on the work→closure edge (`link-gate:coo`).

### Probe 2 — terminal per-node gates currently RED (observed 0)

```bash
cd /Users/smith/projects/BRICK && PYTHONPATH=brick_protocol/support/import_identity:. python3 - <<'PY'
from brick_protocol.support.operator.assembly import assemble_graph_declaration

decl = {
    "declared_by": "coo-probe",
    "task": "g0 terminal gates probe",
    "building_id": "g0-terminal-gates-probe-0709",
    "adapter": "local",
    "nodes": [
        {"kind": "closure", "work_statement": "terminal with gates", "gates": ["human-review"]},
    ],
}
try:
    assemble_graph_declaration(decl, repo_root=".")
    print("PROBE2_UNEXPECTED_SUCCESS")
except ValueError as exc:
    text = str(exc)
    print(text)
    assert "exactly one outgoing completion edge" in text
    assert "observed 0" in text
    print("PROBE2_OK_observed_0")
PY
```

**Expect:** ValueError with `observed 0` (documents G0-A residual until stamp fix).

### Probe 3 — resume dead_end kind honesty (G0-B; run after messaging patch; pre-patch documents status quo)

```bash
# Pick a real evidence root that completed WITHOUT a hold ledger (walk-on complete or agent_incomplete).
# Replace BUILDING_ROOT with an absolute path from a known walk-on run.
BUILDING_ROOT="<ABSOLUTE_EVIDENCE_ROOT_WITHOUT_HOLD>"
cd /Users/smith/projects/BRICK && PYTHONPATH=brick_protocol/support/import_identity:. python3 - <<PY
import json, tempfile
from pathlib import Path
from brick_protocol.support.operator.resume_declaration import (
    preflight_resume_declaration,
    validate_resume_declaration,
    run_resume_declaration,
)

building = Path("$BUILDING_ROOT").resolve()
decl = validate_resume_declaration({
    "building_ref": str(building),
    "dispositions": [{"on": "gate_sequence_policy_hold", "action": "forward"}],
    "author_ref": "coo:g0-probe",
})
pre = preflight_resume_declaration(decl, repo_root=".")
print(json.dumps(pre, indent=2, default=str))
# After G0-B: assert pre.get("dead_end_kind") in {"no_hold_ledger", "evidence_incomplete", ...}
# or already_complete when frontier_kind==complete
# Status quo today: dead_end True + empty kind when hold missing and not complete
print("dead_end", pre.get("dead_end"), "already_complete", pre.get("already_complete"),
      "frontier", pre.get("frontier_kind"), pre.get("frontier_reason"))
packet = run_resume_declaration(decl, repo_root=".", dry_run=True)
print("error_kind", packet.get("error_kind"), "message_ko", packet.get("message_ko"))
print("next_command", packet.get("next_command"))
PY
```

**Expect (status quo):** dead_end or already_complete; harvest next_command when dead_end regardless of walk-on.  
**Expect (G0-B Exit):** `dead_end_kind` distinguishes no-hold walk-on vs evidence_incomplete; harvest text not the default for pure no-hold.

---

## Summary table

| Question | Answer |
|---|---|
| How graph-decl lowers gates | assemble → build → stamp_profile (top) + stamp_node (per-node) → gate_sequence_policy on edges |
| observed 0 | per-node gates on terminal / zero EdgeSpec out; stamp ignores boundary edge |
| Mid hold without raw packet? | **Yes:** non-terminal node `gates: [human-review\|coo-review]` |
| Preflight dead_end | evidence_incomplete · plan unreadable · empty hold |
| Recommend first | **G0-B/C** honesty; G0-A only if terminal stamp fix needed for dogfood |
| Commit | **none** (this report is support evidence only) |

---

## Not proven

- Live Building dogfood of mid-hold → resume forward → complete in this session  
- Exact production building roots that hit dead_end (need vessel paths)  
- Whether top-level + per-node double-stamp on boundary is always merge-safe  
- Checker pin coverage for new `dead_end_kind` fields  

---

**복기:** 공식 앞문은 이미 per-node gates로 mid gate-HOLD를 찍을 수 있다. 죽은 쪽은 (1) terminal gates observed-0 불일치, (2) 무-gates 발사 → concern walk-on → hold 없는 resume이 harvest 문장으로 위장하는 표면이다. G0는 먼저 resume 표면을 정직하게 가른 뒤(B/C), 필요하면 stamp 한 줄로 terminal A를 닫는다.
