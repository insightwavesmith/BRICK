# GP3 문턱 조사 — 증명 파이프라인이 mutation-RED 하네스 전제를 대체하는가 (0703)

Smith 비준 큐 ③. 판정 근거는 전부 main 실물(HEAD e74b53e1)과 실행 결과다.

## 결론: 그대로는 대체 못 한다 — 단, 엔진 수정 없이 command-kind로 의미론을 실을 수 있다

### 실측 1 — `kind=mutation_red`는 형(shape)만 본다
`brick/comparison.py` `_mutation_red_observation_present`(233~256)는
`mutation_red_runs` 필드의 4요소(revert_ref/red_cmd/red_rc/restore_rc) **존재와
타입만** 검사한다. `red_rc=0`(변이가 RED를 못 만듦)도, `restore_rc≠0`(복원 실패)도
형만 맞으면 통과한다. 즉 이 kind는 레인이 수행한 변이 관측의 **기록 계약**이지,
변이가 실제로 물었는지의 **집행 계약이 아니다**.

### 실측 2 — `command` kind는 실행·집행한다
support(`proof_observation.py`)가 선언된 `{command, expect_rc}`를 직접 실행해
rc를 기록하고, 불일치면 기계 저작 반려 concern(`transition-concern:proof-obligation:*`)
→ 재파견(예산 5) → HOLD까지 라이브로 돈다(P8 주문 3 실증, p8-dogfood-probe-0703.md).

### 따라서 — §4-1 분해 레인의 mutation-RED 집행 패턴
분해 계약에 변이 프로브를 **command kind로 선언**하면 의미론이 집행된다:

```python
proof_obligations=[{
    # 프로브 스크립트: 변이 적용 → 체커 rc==1 확인 → 복원 → 그때만 exit 0
    "command": "python3 support/checkers/probes/<decomposition>-mutation-red.py",
    "expect_rc": 0,
}]
```

프로브 스크립트는 레인 write_scope 안(support/checkers/**)에 커밋시키고, 그 자신이
"변이→RED 확인→복원→green 확인"의 전 사이클을 수행한 뒤에만 rc=0을 반환한다.
스크립트가 거짓말하면? — 스크립트 실물도 diff로 남고, COO 게이트가 변이를 직접
재실행한다(오늘 link-part4 게이트에서 양방향 변이-RED를 손으로 실행한 선례).

## GP3 진입 판정
- 전제 "mutation-RED 하네스": **command-kind 래핑 패턴으로 충족** — 별도 하네스
  빌딩 불요. §4-1 분해 발주 계약에 위 패턴을 박는 것으로 갈음.
- 다음 순서(비준 큐): 전제2 = case_runners vs C1 비교 1레인 → §4-1 kernel_checks
  분해 → §4-2 → §4-4.

## 이번 조사가 함께 등재하는 후속 후보 (조사 워크플로 0703 확정분)
1. `_mutation_red_observation_present` 의미론 강화(red_rc≠0·restore_rc==0 요구) —
   기록 계약을 집행 계약으로 승격할지는 설계 논점(형-검사가 의도일 수 있음). 소형.
2. `check_session_continuity_adapter.py`에 resume argv의 `approval_policy="never"`
   pin 부재 — bde20514 패리티가 소스 확인만 된 상태. 소형 pin 추가 후보.
3. reason_refs 접수 문법은 슬래시 없는 bare 산문을 허용(불투명 토큰 설계) —
   related_boundary_refs(0703 랜딩)는 산문 거부로 더 엄격. 정합 논점.
4. QA 산문의 픽스처 세션ID 리터럴(`sess-…`)이 잔해 vessel을 redaction 위반자로
   만드는 재발 위험 — 재발 시 레인 계약 지침(리터럴 인용 금지) 승격.
5. 라이브 --all은 걷는 빌딩의 보고 패킷 착지와 경합 가능(reporter_notification_
   projection의 inbox 스냅샷 창) — 운영 규칙: rc=1이면 착지 직후인지 확인 후 재실행.
