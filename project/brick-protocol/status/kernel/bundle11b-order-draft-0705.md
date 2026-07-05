# 묶음11B 발주문 초안 (0705 밤) — walker 인접, Smith 승인 게이트 대기

Status: 발주-준비 초안. **승인 전 발사 금지** (T10 S2/S4 선례 — walker/support 핵심 수정은
"엔진 — Smith 게이트" 라벨 필수, harness-roadmap-orders-t7-t11-0704.md:19). 시공 대상이
onboard.py·walker 인접부라 11A(비-walker 조각, 별도 걷는 중)와 분리했다.

## 대상 2건 (enforcement-ledger.yaml:17-22)

1. **adopted-reroute 재파견 텍스트 게이트** (reroute-defaults.yaml:7 선언) — 채택된
   reroute의 re_instruction 재파견 텍스트가 선언 규칙을 지키는지 Link-측 소비.
2. **re_instruction 종료선 규칙 기계 집행** (reroute-defaults.yaml:21 not_proven) —
   re_instruction_endline_rules 3행(종료선 재진술 / 레인 환경-실행가능 증명만 / scope 밖
   수리는 COO 게이트)의 내용 검사. 현행은 존재 검사만 있음(onboard.py:3327-3333
   "missing_re_instruction" — 내용 규칙 미시행).

## 예상 쓰기 표면 (0705 표면 조사 실측)

- support/operator/onboard.py:3327 근방 — re_instruction 존재 검사를 내용 규칙 검사로 확장
- support/operator/walker_kernel.py:716-720 인접부(resume_seed.re_instruction 주입 지점 —
  `_run_dynamic_graph_walker`(:994) 본문은 불가침, 인접 헬퍼만) · walker_resume.py:384-402
- link/spec.py GATE_REGISTRY APPEND(신규 게이트 행 필요 시 — make-a-gate 절차)
- 동반 체커 + 프로파일 등재 + enforcement-ledger.yaml 2행 상태 갱신

## 제안 그래프·게이트

design(claude·xhigh — 소비 지점을 walker 본문 무접촉으로 좁힐 수 있는지 최우선 판정,
불가면 정지 보고) → work(codex, write) → fan(code-attack-qa claude·xhigh, review codex·xhigh)
→ closure. **per-node gates=("human-review",)를 work 노드에** — walker 인접 diff는 머지 전
사람 게이트로 정지(0702 실측: per-node는 HOLD를 실제로 박는다).

## D-초안

D1: 재파견 텍스트 게이트 소비 diff(위반 재파견 텍스트 → 채택 거부/HOLD + 안내).
D2: 종료선 규칙 내용 검사 diff(3행 각각 위반 픽스처 RED / 준수 green 재현 쌍).
D3: 등재 표면 + enforcement-ledger 2행 갱신.
D4: 회귀 — 기존 reroute/resume 픽스처 green + 격리 --all rc=0.
종료선: D1~D4 전수면 DONE — walker 본문 수정 필요 판정 시 시공 대신 정지 보고, 그 밖의 다듬기 금지.

## Smith 결정 요청

①이 초안대로 발사 승인 여부 ②work 노드 human-review 게이트 유지 여부(승인 시 홀드
1회가 생기고 Smith 또는 COO가 diff 검수 후 forward — 권고: 유지) ③11A 랜딩 결과를 보고
발사할지(11A의 정지-보고 산출이 이 초안의 좌표를 정련할 수 있음 — 권고: 11A 랜딩 후).

증거 한계: 발주-준비 초안. 좌표는 0705 표면 조사 실측이나 발사 시점 재확인 필수.
