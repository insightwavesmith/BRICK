# 홀드 패킷 자기서술 — hold_reason별 {합법 처분·실제 의미·오판 사례} 매핑 정본 (0704 — T6, 선언만)

Status: support evidence only. 이후 홀드를 만난 운영자가 hold_reason별 합법 처분과 각
처분의 실제 의미(특히 forward의 '채택 아님 — 선언 경로 계속')를 오판 실사례와 함께 한 곳에서
읽도록 세운 자기서술 슬라이스. 이 문서는 선언(정본 인용)만이며, walker가 홀드에 메뉴를 실어
나르는 소비 슬라이스는 엔진(Smith 게이트) 별도다. source truth·성공 판정·품질 판정·Movement
권한 아님. 처분 의미론은 발명하지 않고 커밋된 실측·정본 인용만 옮긴다 — 실측 없는 hold_reason은
'실측 없음'으로 정직 표기한다.

## 처분 동사(disposition action)의 실제 의미

resume/approve 경로에서 사람/COO 처분 행은 action을 하나 고른다. 각 처분의 실제 의미:

```text
raise   = 막힌 노드의 예산을 declared budget_increment만큼 올려 막혔던 랜딩이 큰 예산
          위에서 '자연 채택'된다(더 큰 예산의 fresh forward walk와 byte-identical 검증).
          budget_delta[pending_target]=increment.
forward = ★채택이 아니다 — 선언된 현재 경로를 계속 간다. 예산 delta 없음(no delta).
          concern이 있어도 '재파견/HOLD 근거가 없으면' Link/COO는 forward 엣지를 그대로
          물린다(building-coordination §G1). '오판 아님'을 판정하는 자리이지, 자동 승인 아님.
stop    = Building lifecycle/리뷰-마감 상태로 정지. 예산 delta 없음. adapter_error 홀드는
          별도의 paper-stop 경로.
reroute = 다른 선언된 Brick 경계로 이동(pending_target_ref 지정). 예산 delta 없음.
          re_instruction(정정된 how-to)이 있으면 재시도 타깃 프롬프트에 실린다; 부재면 원본
          work 무변경.
```

- 실측·정본 근거: `project/brick-protocol/status/kernel/resume-raise-budget-bridge-0704.md`
  (raise 예산 브리지 COMPLETE 재현: 예산 소진→budget_exhaustion HOLD→raise(budget_increment=3)
  →resume; after_node_reroute_budgets=4, after_node_reroute_landings=2, classification=
  bridge_observed_budget_increment_reached_kernel_evidence). 처분 4종의 delta 유무는 코드
  주석 `support/operator/walker_resume.py:261-263`("raise => bump ... forward/stop/reroute =>
  no delta")로 실측 확인.

## hold_reason 매핑 표

각 hold_reason은 커밋된 코드의 실측 리터럴이다. '정상/합법 처분'과 '오판 사례'는 커밋된 정본
문서 참조를 가진다. 실측된 처분 사례가 없는 hold_reason은 '실측 없음'으로 표기한다.

표의 대상 집합 = `support/operator` 안에서 관측된 hold_reason 리터럴 전부(정적 `hold_reason=`
할당 + 동적 f-string 형태 포함). 정적 리터럴 외에 write-scope 가드 상수형(`driver.py`
`_..._REASON` 상수)과 게이트 시퀀스의 동적 형(`gate_sequence.py`의 `:{gate_ref}` 접미형)도
빠짐없이 실는다. 스캔 표면은 `support/operator/*.py`이며, 그 밖의 코드 경로에서 추가 리터럴이
발화할 가능성은 not_proven으로 남긴다(발명 금지 — 스캔 밖은 실측이 아님).

| hold_reason (실측 리터럴) | 합법 처분 클래스 | forward/raise/stop 실제 의미 | 오판·정상 실사례 참조 | 홀드 시 읽을 관측 지점 |
|---|---|---|---|---|
| `target_node_budget_exhausted` (`support/operator/walker_kernel.py:2086`; S-a 문서는 "budget_exhaustion HOLD") | raise(예산 증분)·forward·stop | raise=예산 올려 자연 채택; forward=증분 없이 선언 경로 계속; stop=마감 | 정상: raise 브리지 COMPLETE(`resume-raise-budget-bridge-0704.md`). 오판: 0702 raise/forward 혼동 2회 — `harness-roadmap-orders-0704.md`(§T6 오판 실사례), `resume-raise-budget-bridge-0704.md`(결함① stale 판정) | after_node_reroute_budgets / after_node_reroute_landings / after_frontier_kind (`resume-raise-budget-bridge-0704.md` §판정) |
| `fake_landing_write_scope_diff_absent` (`support/operator/driver.py:106`, `support/operator/frontier_observation.py:129`) | forward(검수 후)·reroute(수리 시) | forward=검수 후 정상 종결(가짜 랜딩 아님 확정); reroute=수리 필요 시 | 정상: 무수정 조사 발주의 정상 경로, 검수→forward 2회 관측(`resume-raise-budget-bridge-0704.md` §운영 처분). 보존 맥락: `wip-preservation-principle-0704.md`(no-diff HOLD 매트릭스) | driver.py 가짜-랜딩 홀드 기록 + `wip-preservation-principle-0704.md` §preservation matrix |
| `write_scope_forbidden_diff_present` (`support/operator/driver.py:107`; frontier 매핑 `support/operator/frontier_observation.py:130`) | forward(검수 후)·reroute(수리 시) — fake_landing과 형제인 write-scope 가드 HOLD | forward=검수 후 금지 경로 diff가 오확정 아님을 확인하고 정상 종결; reroute=수리 필요 시. 두 write-scope 가드 모두 `human_review_waiting` 프런티어로 승격(`frontier_observation.py:133`) | 실측 없음(커밋된 정본에 이 reason의 처분 실사례 부재 — 코드 경로만: 홀드 기록 `driver.py:1129`·`driver.py:1167`, 온보드 `onboard.py:3515`) | driver.py 금지-diff 홀드 기록 + write-scope 가드가 `human_review_waiting`로 올리는 `frontier_observation.py:125-134` |
| `human_or_coo_gate_pause` (`support/operator/walker_kernel.py:2013`) | forward·reroute·stop(사람/COO 처분) | forward=선언 경로 계속(채택 아님); reroute=선언된 다른 경계로; stop=마감/리뷰 | 오판: 0703 reroute-제안 홀드에 forward 오판(채택이 아니라 선언 경로 계속으로 처리 → work 재파견 없이 boundary 닫힘, re_instruction 미도달) — `harness-roadmap-orders-0704.md`(§T6 오판 실사례) | 실측 없음(구체 관측표 부재; 정본은 오판 서술뿐) |
| `multi_candidate_no_agent_transition_concern` (`support/operator/driver.py:1947`) | 실측 없음 | 실측 없음 | 실측 없음 | 실측 없음 |
| `multi_candidate_requires_declared_policy` (`support/operator/driver.py:1977`) | 실측 없음 | 실측 없음 | 관련: 0704 ② 설계-질문 concern에도 route policy가 재파견 채택(implementation_gap 하위구분 부재, 공전 위험) — `harness-roadmap-orders-0704.md`(§T6 0704 신규 실측 ②) | 실측 없음(정책 하위구분 부재만 서술) |
| `proposed_candidate_not_in_declared_set` / `no_declared_candidate_proposed` (`support/operator/driver.py:1960`) | 실측 없음 | 실측 없음 | 실측 없음 | 실측 없음 |
| `adapter_error_frontier` (`support/operator/walker_frontier.py:291`) | stop(paper-stop 경로) | stop=adapter_error 홀드는 별도 paper-stop(`support/operator/walker_resume.py:199-213`) | 실측 없음(정본 처분 사례 부재; 코드 경로만) | 실측 없음 |
| `chat_session_park_frontier` (`support/operator/walker_frontier.py:334`) | 실측 없음 | 실측 없음 | 실측 없음 | 실측 없음 |
| `unresolvable_reroute_address` (`support/operator/walker_transition_concern.py:209`) | 실측 없음 | 실측 없음 | 실측 없음 | 실측 없음 |
| `invalid_transition_concern_evidence` (`support/operator/walker_transition_concern.py:366`) | 실측 없음 | 실측 없음 | 실측 없음 | 실측 없음 |
| `fan_in_wait_all_missing_source` (`support/operator/walker_fan_in.py:261`) | 실측 없음 | 실측 없음 | 실측 없음 | 실측 없음 |
| `target_node_has_no_link_assigned_budget` (`support/operator/walker_kernel.py:2051`) | 실측 없음 | 실측 없음 | 실측 없음 | 실측 없음 |
| `gate_sequence_unadmitted_action:{gate_ref}` (동적 f-string, `support/operator/gate_sequence.py:125`) | hold(caller-or-coo 처분 대기) | 게이트 정책 action이 admitted 집합 밖일 때 발화 → hold. 처분은 caller/COO가 gate_ref별로 결정 | 실측 없음(정본 처분 실사례 부재 — 코드 경로만) | `gate_sequence.py:115-146`(unadmitted action → hold, pending_target_ref=target_brick) |
| `gate_sequence_missing_required_facts:{gate_ref}` (동적 f-string, `support/operator/gate_sequence.py:189` hold / `:222` reroute) | hold 또는 reroute(선언된 action_row에 따름) | 게이트 required facts 미충족 시; action_row.action=hold면 pending_target에 홀드, =reroute면 target으로 재경로 | 실측 없음(정본 처분 실사례 부재 — 코드 경로만) | `gate_sequence.py:180-213`(hold), `:214-233`(reroute) |

## 처분 공간 밖: resume seed-build 무결성 거부 (hold_reason 아님)

resume 재개 거부 중 하나는 disposition HOLD가 아니라 **resume seed-build 무결성 거부**다 —
action(raise/forward/stop/reroute)과 무관하게 seed 조립 시 발화한다. 두 원장(step-outputs 프런티어
vs raw/agent-return.jsonl + returned_claims.json)이 어긋난 방향(완료>기록, 또는 claim_trace 부재)일
때 ValueError로 재개를 거부한다. 이것은 hold_reason별 처분 분기가 아니므로 위 표에 넣지 않는다.

- 정본: `project/brick-protocol/status/kernel/resume-ledger-mismatch-recovery-0704.md`(S-c).
- 합법 회복 경로 = FRESH 재발주(새 building; replay 의무 0이라 불일치 가드 미발화). 원장 손편집 금지.
- 홀드 시 읽을 관측 지점(S-c §observation command 재사용, 재발명 금지):
  (1) `work/step-outputs/*/step-output.json` 중 step_ref별 개수 = (a) 프런티어;
  (2) `raw/agent-return.jsonl`의 해당 step_ref 라인 수 = (b);
  (3) `evidence/claim_trace/agent/returned_claims.json` 존재 여부.
  (a)>(b) 또는 (3) 부재가 거부 사유이며, 어느 step_ref가 앞섰는지는 에러 메시지에 이미 인용된다.

## 오판 실사례 카탈로그 (커밋된 정본 인용만)

- 0702 budget_exhaustion raise/forward 혼동 2회 — `harness-roadmap-orders-0704.md`(§T6),
  `resume-raise-budget-bridge-0704.md`(결함① stale, 예산 브리지는 완결로 실측 확정).
- 0703 reroute-제안 홀드에 forward 오판 — 채택이 아니라 '선언 경로 계속'인데 work 재파견 없이
  boundary가 닫히고 re_instruction이 미도달 — `harness-roadmap-orders-0704.md`(§T6).
- 0704 ② 설계-질문 concern에도 route policy가 재파견 채택(implementation_gap의 수리가능/
  설계결정 하위구분 부재로 공전 위험; COO 직접 게이트가 처방) — `harness-roadmap-orders-0704.md`(§T6).
- 0704 ④ 거부-후-정정 경로/보존 매트릭스 — `resume-ledger-mismatch-recovery-0704.md`(S-c),
  `wip-preservation-principle-0704.md`(S-d).
- WIP 보존 미판정(temp_dir wip_anchor='' 예외 vs 결함)은 정본상 Smith/COO 몫 —
  `wip-preservation-principle-0704.md` §미판정, `goal-phases-consolidated-0702.md`(인용, 미재현).

## not_proven / 실측 없음

- 위 표의 '실측 없음' 행들: 커밋된 정본 문서에 forward/raise/stop 처분 실사례가 없어 발명하지 않음.
- `human_or_coo_gate_pause`의 구체 관측표는 부재(오판 서술만 존재).
- 중첩 reroute·fan/fan-in 노드의 예산·처분 거동은 실측 없음(`resume-raise-budget-bridge-0704.md`
  §not_proven과 정합).
- 홀드 소비 슬라이스(walker가 홀드 패킷에 처분 메뉴를 싣는 배선)는 엔진 수정이라 이 발주 범위 밖
  (Smith 게이트).

증거 한계: 이 문서는 선언 슬라이스이며 각 hold_reason 리터럴은 커밋된 코드 실측, 각 처분 사례는
커밋된 status/kernel 정본 인용이다. 홀드 발생 시 재확인하라. source truth·성공 판정·품질 판정·
Movement 권한이 아니다.
