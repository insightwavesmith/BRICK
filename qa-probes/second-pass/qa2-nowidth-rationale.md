# graph-draft rationale — brick-draft-20260706T224522Z-1d93fc24

support evidence only; not source truth / success / quality / Movement.

## sizing answers
- walker_adjacent: no
- size: medium
- splittable: yes
- file_conflict: no
- failure_cost: low
- human_approval: no
- termination_shape: doc
- difficulty: medium
- width_signals: 0

## rationale rows

| rule_id | decision | basis |
| --- | --- | --- |
| rule-width-decision | N=1 (신호=0, 비충돌 파티션=2, 상한=3) | 폭=min(신호 사다리, 비충돌 파티션 수, 3) — walk-results-adopted-0707 §A (감지→제안; note-split-candidate 흡수) |
| rule2-work-casting | work → adapter:codex-local | difficulty/escalation-proportional casting (Smith 0706) |
| shape-fan-qa | work → fan(2 lens) → closure | honest/medium/escalated tier QA fan |

## precheck
- composed_ok: True
- literal: COMPOSED OK brick-draft-20260706T224522Z-1d93fc24
