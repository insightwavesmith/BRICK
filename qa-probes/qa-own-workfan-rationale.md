# graph-draft rationale — brick-draft-20260706T221534Z-317e5dc4

support evidence only; not source truth / success / quality / Movement.

## sizing answers
- walker_adjacent: no
- size: large
- splittable: yes
- file_conflict: no
- failure_cost: low
- human_approval: no
- termination_shape: doc
- difficulty: honest
- width_signals: 3

## rationale rows

| rule_id | decision | basis |
| --- | --- | --- |
| rule1-contract-gate-vocab | risk-proportional escalation | answers/task-text |
| rule-width-decision | N=3 (신호=3, 비충돌 파티션=3, 상한=3) | 폭=min(신호 사다리, 비충돌 파티션 수, 3) — walk-results-adopted-0707 §A (감지→제안; note-split-candidate 흡수) |
| rule-fan-proposal | design fan ×3 → closure (상호 열람 금지) | 2단 표준형: 1단=설계 수렴 홀드, 2단=새 선언 (§A1.3, §E) |
| rule8-timeout-raise | adapter_timeout_seconds=10800 | 심층 시공 timeout 자동 상향 |

## precheck
- composed_ok: True
- literal: COMPOSED OK brick-draft-20260706T221534Z-317e5dc4
