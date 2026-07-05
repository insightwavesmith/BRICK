# T10 첫 실전 확장 운전 runbook (0705 밤) — S14 채택 + COO 재검증 정본

출처: 지피티 S14 보고(T10 확장 운전 절차 공격, Smith 전달 0705 밤) → COO 현행 HEAD
재검증(4a5c16d4). 발주-준비/운전-절차 문서이며 source truth·성공 판정 아님.
G3(A+ 착수 게이트 마지막 항목 = T10 첫 실전 확장 운전 1회)의 절차 정본.

## 1. S14 발견 6건 검수 이력 — 재발주 금지 목록 포함

지피티 감사는 업로드 아카이브 기준이라 Phase1(fc7dd571)·묶음6(1ce52761) 랜딩분이
미반영이다. **아래 스테일 2건을 S14 근거로 재발주하지 마라** (phases §0 원칙과 동일).

| id | 지피티 판정 | COO 처분 | 현행 HEAD 실물 근거 |
|---|---|---|---|
| S14-T10-001 홀드 identity 재사용 | MAJOR·CONFIRMED | **스테일 — 반증** | 제안 수리가 이미 시공됨: revision packet에 approval_hold_ref 기록(declaration_packets.py:352), _verify_approval_not_consumed가 hold identity도 거부(:737-755, 호출 :732), RED 픽스처 same-hold-new-approval-reuse 실재(check_plan_revision_chain.py:561-574). Phase1 묶음1잔여 산출 |
| S14-T10-002 bool 예산 | MAJOR·CONFIRMED | **스테일 — 3표면 반증** | _verify_expansion_budget_available bool 명시 거부 / _positive_int_mapping bool 거부 / plan_expansion._validate_expansion_node_budgets는 require_positive_int(묶음6 헬퍼) 경유. writer-reader 패리티(Rule 11) 성립 |
| S14-T10-003 strict checker 필수 | MINOR | **수용 — 단계 5로 각인** | reader가 corrupt 최신 rev를 직전 rev로 조용히 후퇴시키는 기전 실물 그대로(declaration_packets.py:369-399). "실행됨"≠"최신 rev 정상" |
| S14-T10-004 approval-only crash retry | MINOR·OK | 수용(문서화) | retry 프로브 실재(check_plan_revision_chain.py:309-312) |
| S14-T10-005 fan-in member_refs | OK | 유지 | plan_expansion.py에서 reject 실측 |
| S14-T10-006 approval 부재/스테일/재사용 | OK | 유지 | 3종 reject 실측 |

## 2. 운전 대상 결정 (0705 밤 실측)

- **cleanup-wave-a-0705 부적격**: base plan `expansion_budget: None`(갭1 c89f1732 랜딩
  이전 출생) — _verify_expansion_budget_available가 fail-closed 거부. 출생 선언 없는
  판에 소급 부여 경로는 없음(의도된 설계).
- **채택: 신규 목적 빌딩 + 2-개정 구조(Smith 0705 심야 지시 — "design(fable)→홀드→
  병렬개발 N→각 QA" 구조화를 T10으로 실증)**: 출생 `expansion_budget=2` +
  design(fable5, 전제 재확인·계획) —[coo 게이트]→ **홀드#1** → rev-1 = 발견 조각 v3.2
  (design×2 fable5 → QA fable5 fan-in, QA 경계 edge에 coo 게이트) → **홀드#2** →
  rev-2 = 발견이 확정한 exact 경로별 **병렬 dev×N + 각 QA + fan-in closure** → 완주.
  홀드#2가 곧 발견→파괴시공 커밋 게이트(지피티 ATT-004의 유기적 해소 — 지피티 자신도
  "T10 second revision pattern 정식화" 권고). 홀드#1·#2 = 상이한 hold identity →
  동일-홀드 재사용 가드 실전 검증 동반. rev-2 write 노드는 Brick row-내 write_scope
  (ATT-001 규율) + 발견-확정 exact allowlist(ATT-002 해소). **선결: gap1b 랜딩**
  (base expansion_budget 저작 인자). 전제 조각(v3.2) 캐스팅: QA=fable5 xhigh 승격
  (고비용 일회성 트리거), design 레인은 design-lead 개정 선호(fable5 xhigh) 자동.
- **조각 v1 폐기(0705 밤)**: 리허설 초안(cleanup-wave-a design 산출)의 커널 아카이브
  이동 3건은 cleanup-wave-b(73673bf9)가 이미 집행 — 지피티 감사 세션의 정합성 발견을
  COO 로컬 재검증으로 확정. 부수 발견 2건: 초안은 엔진 스키마(Brick+Agent rows) 불일치
  + QA 완료 edge 누락 — 그대로 운전했으면 단계 2 거부. **조각 v2** = 잔여 실작업 재단:
  ①census '기타 z6 판정분' 4번째 후보 확정+이동 원장(미확정 경로도 원장 행 diff 강제 —
  fake-landing 가드 정합) ②buildings-residue 분류(제안-전용). 4노드(design×2·work·qa
  fan-in), assemble_expanded_graph_plan dry-run PASS. **교훈: 조각/발주문의 앵커 재확인은
  스키마 dry-run만이 아니라 작업 실존(이미 랜딩됐는가)까지.**
- 운전 직전 확장 조각 지피티 공격 예약(외부감사 핸드오프 §5) — 조각은 미커밋 증거,
  COO가 추출·전달.

## 3. 운전 절차 (S14 §3 채택, 단계 3 주석 1건 정정)

단계 0 — 대상 빌딩 HOLD identity 확인 (evidence-manifest의 dynamic_walker_evidence:
held / hold_reason / paused_at_ref / pending_target_ref).
단계 1 — latest valid plan hash 확인 (latest_valid_declared_plan_packet, declaration_packets.py:370).
단계 2 — expansion fragment dry-run **4단**(0705 지피티 공격 V2-ATT-001 교훈 — 1단만으론
"live write node로 동작함"을 증명 못 한다): ①assemble_expanded_graph_plan(모양·예산·fan-in)
②graph→linear 투영(_linear_plan_from_graph_plan) ③validate_declared_building_plan(linear 형)
④write 노드가 있으면 write_scope가 **Brick row에** 실렸는지 확인(plan_graph 투영은 step
top-level write_scope를 운반하지 않는다 — plan_validation.py:1047·write_observation.py
_write_scope_from_brick_row 전부 row에서만 읽음, 실측 확정).
단계 3 — approval row 수동 검사 (work/expansion-approvals.jsonl: 새 approval_evidence_ref /
gate_ref=link-gate:expansion-approval / hold_paused_at_ref = 현재 hold identity).
**정정: 동일 hold identity 재소비는 이제 기계가 막는다**(declaration_packets.py:749-755)
— S14 원문의 "사람이 봐야 함"은 이중 안전으로 강등.
단계 4 — write_declared_plan_revision (declaration_packets.py, exclusive link 쓰기).
단계 5 — **strict checker 필수**: `PYTHONPATH=support/import_identity:. python3
support/checkers/check_plan_revision_chain.py --repo .` (reader fallback 때문에 생략 불가).
단계 6 — resume (run.py:621 resume_building_plan, adapter_cwd는 세션ID 없는 중립 경로).

## 4. 조각 v2→v3 검수 이력 (지피티 공격 0705 밤 — 발견 6건 처분)

| id | 지피티 | COO 처분 | 근거 |
|---|---|---|---|
| V2-ATT-001 row-외 write_scope (FATAL) | 수정 필수 | **확정·수용 — 분리 운전안으로 구조 소멸** | plan_graph.py 투영에 write_scope 운반 0줄(grep 공백)·plan_validation.py:1047·write_observation 전부 Brick row에서만 읽음 — COO 실물 재확인. v3=발견-전용(쓰기 노드 0) |
| V2-ATT-002 fnmatch 광폭 글롭 (MAJOR) | matcher 세그먼트화 | **확정·수용 — v3에서 소멸 + 근본수리 백로그(A+ W1 합류)** | fnmatch가 kernel/*.md로 archive 하위까지 매칭 — 실측 True. 기존 "fnmatch 함정" 각인의 새 사례 |
| V2-ATT-003 typed handoff 부재 (MAJOR) | 스키마 강제 | **수용(조정)** — candidate_file_changes 안에 typed 스키마(candidate_status 4상태) 명시. return_shape 확장(blocked_or_missing_evidence 추가)은 KIND 수용성 미확인이라 보류 | v3 work_statement에 각인 |
| V2-ATT-004 커밋 게이트 부재 (MAJOR) | coo 게이트 or 분리 | **수용 — 분리 운전안**(지피티 자신의 최선 권고와 일치): 발견(v3 조각)과 이동(후속 승인 빌딩 v2b) 분리 | 미지-발견→파괴-이동 커밋게이트 패턴은 블록 코퍼스 각인 후보로 백로그 |
| V2-ATT-005 source_facts 3층 부재 (MAJOR) | 최신 처분 문맥 추가 | **수용** — z6-design source_facts에 runbook+repair-orders 추가(원자료/원장/최신처분 3층) | v3 반영 |
| V2-ATT-006 forbidden 미동기 (MINOR) | 3건 forbidden 추가 | **수용(v3에서 무의미화)** — 규칙 "prose 제외 ⊆ forbidden_paths"는 체커 후보로 백로그 | v2b 발주 시 적용 |

v3 확장 dry-run 4단 전부 PASS(투영 5스텝·linear 검증·신규 row write_scope 부재 전수 확인).
후속 등재: **v2b**(4번째 후보 exact path 확보 후 좁은 스코프 이동+원장 — 일반 빌딩, T10 불요).

증거 한계: 이 문서는 support evidence이며 성공 판정 아님. 검증은 0705 밤 HEAD 기준 —
운전 시점에 단계 1~2로 재확인. 처분·품질 판정은 사람 몫.
