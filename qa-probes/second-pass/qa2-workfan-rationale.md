# graph-draft rationale — brick-draft-20260706T224448Z-1489ffe9

support evidence only; not source truth / success / quality / Movement.

## sizing answers
- walker_adjacent: no
- size: medium
- splittable: yes
- file_conflict: no
- failure_cost: low
- human_approval: yes
- termination_shape: checker-pinned
- difficulty: medium
- width_signals: 3

## rationale rows

| rule_id | decision | basis |
| --- | --- | --- |
| rule6-source-fact-verified | README.md exists + tracked | test -f + git ls-files --error-unmatch |
| rule-width-decision | N=3 (신호=3, 비충돌 파티션=3, 상한=3) | 폭=min(신호 사다리, 비충돌 파티션 수, 3) — walk-results-adopted-0707 §A (감지→제안; note-split-candidate 흡수) |
| rule-fan-proposal | work fan ×3 → merge → QA fan → closure (write 구역 서로소) | 비충돌 파티션 3개 실측 — RED-2 서로소 by construction |
| rule16-human-gate | gates: ['human-review'] | human_approval==yes → link-gate:human on the final transition |

## precheck
- composed_ok: True
- literal: COMPOSED OK brick-draft-20260706T224448Z-1489ffe9
