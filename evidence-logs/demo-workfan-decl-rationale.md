# graph-draft rationale — brick-draft-20260706T220638Z-0d27e671

support evidence only; not source truth / success / quality / Movement.

## sizing answers
- walker_adjacent: no
- size: medium
- splittable: yes
- file_conflict: no
- failure_cost: low
- human_approval: no
- termination_shape: checker-pinned
- difficulty: medium
- width_signals: 2

## rationale rows

| rule_id | decision | basis |
| --- | --- | --- |
| rule6-source-fact-verified | support/operator/graph_draft.py exists + tracked | test -f + git ls-files --error-unmatch |
| rule-width-decision | N=2 (신호=2, 비충돌 파티션=2, 상한=3) | 폭=min(신호 사다리, 비충돌 파티션 수, 3) — walk-results-adopted-0707 §A (감지→제안; note-split-candidate 흡수) |
| rule-fan-proposal | work fan ×2 → merge → QA fan → closure (write 구역 서로소) | 비충돌 파티션 2개 실측 — RED-2 서로소 by construction |

## precheck
- composed_ok: True
- literal: COMPOSED OK brick-draft-20260706T220638Z-0d27e671
