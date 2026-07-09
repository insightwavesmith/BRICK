# G0 / G1 Exit Evidence — 0709 (Grok COO + direct patch)

| | |
|---|---|
| **Status** | support evidence only |
| **Date** | 2026-07-09 |
| **Repo** | `/Users/smith/projects/BRICK` |

## Changes landed (uncommitted until operator commit)

| File | Change |
|---|---|
| `brick_protocol/support/operator/resume_declaration.py` | `dead_end_kind` + honest `message_ko` / `next_command` (no_hold_ledger, evidence_incomplete, plan_unreadable, not_approval_hold); salvage vs harvest |
| `brick_protocol/support/operator/cli.py` | render `dead_end_kind` |
| `brick_protocol/support/operator/assembly.py` | clearer terminal-gates error hint (mid-node hold) |
| `status/kernel/OFFICIAL_ROUTE_MEMO.md` | mid-hold syntax + living memo |
| `status/kernel/fixtures/g1-mid-hold-resume-dogfood-decl-0709.yaml` | official dogfood decl for G1 live fire |

## G0 Exit probes (ALL_PASS)

```text
mid_hold_assemble:         OK  — compose includes HOLD + link-gate:coo on mid edge
term_gates_rejected:       OK  — closure per-node gates → observed 0 + hint
preflight_dead_end_kind:   OK  — evidence_incomplete classified
run_resume_dead_end_kind:  OK  — packet.dead_end_kind set
honest_next_command:       OK  — not generic harvest-only for empty root
compileall:                OK  — resume_declaration, assembly, cli
```

## G0 Exit checklist

- [x] G0-B/C resume surface honesty  
- [x] Mid-walk hold grammar documented + assemble-proven (per-node gates non-terminal)  
- [x] Terminal per-node gates fail closed with hint  
- [x] OFFICIAL_ROUTE_MEMO updated  
- [x] salvage vs resume paths distinguished in next_command  

## G1 status — EXIT

| Item | State |
|---|---|
| Assemble mid-hold → HOLD policy | **proven** |
| Resume dead_end honesty | **proven** |
| Live graph-decl → coo hold → resume → complete | **proven** building_id=`g1-mid-hold-resume-dogfood-0709` |
| Second hold (fake_landing_write_scope_diff_absent) | forward resume → **complete** |
| worktree_disposed after first fire | true (resume used evidence root only) |

### Live dogfood timeline

```text
1) brick build --graph-decl fixtures/g1-mid-hold-resume-dogfood-decl-0709.yaml --forward
   → frontier_kind=link_paused
   → hold_reason=gate_sequence_missing_required_facts:link-gate:coo
2) brick resume --decl resume-declarations/g1-mid-hold-resume-dogfood-0709-forward.json
   → first round ok; advanced past coo hold
   → next frontier human_review_waiting / fake_landing_write_scope_diff_absent
3) brick resume --decl resume-declarations/g1-mid-hold-resume-dogfood-0709-forward-b.json
   → frontier_kind=complete
```

## COO disposition

```text
G0: EXIT (forward)
G1: EXIT (forward) — official continuity dogfood complete
Next product work: G2+ via BRICK buildings only (per 04 ladder).
```

## Proof limits

Not source truth · not quality · not Movement authority · not full provider reliability.
