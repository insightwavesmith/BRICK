# 운영 골 페이즈 통합 (0702 정본 — Smith·COO 합의 프레임, 0703 밤 정리)

교훈 계보: lessons-ledger.yaml (처방 1건=1행, T11 — 0704 신설)

Status: support evidence only. 운영 순서의 정본. 골 오브 레코드 자체는
customer-ready-goal-phases-0629.md(+GOAL/)가 소유 — 이 문서는 그걸 향해 가는
워크스트림들의 통합 순서표다. 상태값은 0703 밤 기준 실측(HEAD f4d7b58b).
시간순 갱신 로그 원문(0702 심야~0703 밤, 커밋 sha·게이트 증거 전수)은
archive/goal-phases-updates-log-0702-0703.md 로 이관.

## 최상위 (불변)

**골 오브 레코드 = P8 도그푸드**: 고객이 설치 → LLM 연결 → `make X` → 공식 build 경로가
Brick/Agent/Link로 일을 선언·수행 → 아티팩트+증거 반환. 최종 증명은 그 고객 경로로
브릭이 제 일을 하는 것. 아래 GP0~GP3은 전부 이걸 향한 순서다.

## GP0 — 엔진 신뢰 기반 ✅ 종료 (잔여 1건 백로그)

reroute 기록자 / 슬랙 벨+fan 렌더링 / reaper liveness+WIP 앵커 / one-call build()
인자 통과 — 전부 랜딩. 잔여: 그래프 admission-gate 라이브 배선(Rule 8 후반)만 백로그.
완료 기준(발사→완주→벨→회수, 병행 안전)은 P7/P8에서 라이브 실증됨.

## GP1 — 운영면 정비 ✅ 종료

배치 1~6 전부 랜딩(헌법 BRICK-CONSTITUTION.md Smith 비준 포함) + 0703 스킬 각인 3건
(레인 문서전달 계약 / 발주 크기 원칙 / 레인-불가능 D-항목 분리 원칙 26cab276).

## GP2 — 도그푸딩 크리티컬 패스 ✅ 실질 종료 (신뢰성 반복만 후속)

| 항목 | 상태 |
|---|---|
| 온보딩 Phase 0~3 (registry/sink/벨 + 대화형 등록·모델선택) | ✅ 전부 랜딩 |
| 발사 인체공학 3종 (returns= / llm= / 결과 요약 패킷) | ✅ 완결 |
| 등록 엔진 결함 5종 (#17 가짜완공 / #15·#19·#21 resume 3종 / #14 admission) | ✅ **5/5 전부 종결** — 라이브 스윕 신호 복원(격리/라이브 무차별 --all green) |
| audit-0703 4페이즈 (우편 접수문법·배달 / 위반방향 게이트 / 증명 파이프라인 / 세션이어짐) | ✅ 전부 랜딩 + 조사 워크플로(15에이전트)로 랜딩 코드 결함 0 재확인 |
| Link Part4 (related_boundary_refs 접수 문법 + 기계 생산자 준수) | ✅ 랜딩 e74b53e1 — 자동 재시공 파이프라인의 주소 계열 구멍 전부 봉합 |
| §4-5/6/7/8/9 갓모듈 소형 안전묶음 | ✅ 전부 랜딩 |
| P7 프레시머신 증명 | ✅ **PASS**(p7-fresh-proof-0703.md — 설치→온보딩→발주→게이트→도장→complete) |
| P8 바운디드 도그푸드 프로브 | ✅ 1회 완료(p8-dogfood-probe-0703.md — 엔진 결함 0, UX 갭 2는 문서 랜딩 722fa998). **신뢰성 반복 샘플만 후속** |

## GP3 — 갓모듈 대형 분해 (현행 창 — 전제 전부 해소)

정본: godmodule-checker-cleanup-synthesis-0701.md §4 + gp3-threshold-0703.md.

| 항목 | 상태/전제 |
|---|---|
| §4-3 routing_loop0 클러스터맵 | ✅ (C1/C15 추출가능. 정정: C1 def 52→**54** 실측, 3중 재계수) |
| 전제1 mutation-RED 하네스 | ✅ **문턱조사로 해소**(gp3-threshold-0703.md) — kind=mutation_red는 형-검사만이라 대체 불가, **command-kind 변이 프로브 선언으로 의미론 집행(엔진 수정 불요)**. 분해 계약에 이 패턴 채택 |
| 전제2 case_runners vs C1 공유기계 비교 | ✅ **공유기계 O — 역할-수준 변형**(사본 아님: exact copy 1, 이름 재사용 0). **공유 픽스처-그래프 헬퍼 1회 선추출 → §4-1·§4-2 중복 추출 방지**. 후보 패밀리: graph row/link builders·plan builders·run_building_plan wrapper·proof_limits |
| **§4-1 kernel_checks.py(10k+) 도메인 분해** | **다음 발주** — 공유 헬퍼 선추출 포함, command-kind 변이 프로브 계약 |
| §4-2 case_runners.py(9,087) 분해 | §4-1 뒤 (선추출 재사용) |
| §4-4 체커다이어트 완주 (87라벨 + 고아 5종 + 라벨별 RED probe) | **순서안 착지(checker-diet-order-plan-0704.md, 173d91e4)** — 87 재계수 일치·6-Batch 저위험 선행·§4-2와 의미론 창 배타 실측. Smith 확정 2결정(라벨별 probe 기구/창 배타 방식) 대기 |
| `_run_dynamic_graph_walker` | **불가침** 유지 |

## 현재 위치 (0703 밤)

**GP0 ✅ · GP1 ✅ · GP2 ✅(신뢰성 반복만 후속) · GP3 진입 — 전제 전부 해소, §4-1 분해
설계가 다음 발주.** Smith 비준 큐(0703 저녁: Part4→#14→GP3 문턱) 전량 완료 + 전제2까지
착지. 걷는 빌딩 0.

**§4-1 Stage A 경과(0703 심야)**: 1차(kc-splitmap-0703a, 단일 레인 직렬 정독)는 4라운드
공전 후 link_paused — 산출은 실질적(run_* **18개** 전수(정본의 16은 구버전)·잎 13개·슬라이스
순서 1~11·pin 이동 목록·facade 유지 결정), 미완은 잎 경계 스윕 1/13. COO가 지도를
kc-splitmap-draft-0703.md로 수확·커밋하고 forward 종결(잔여 frontier agent_incomplete —
v2 대체). **여기서 Smith의 본질 지적**: "왜 워크플로처럼 사고하지 못했나" — 원인은 독트린
배치 차이(워크플로 독트린은 호출부 상주, 브릭 폭 독트린은 스킬에 잠듦 + 흉터의 과잉일반화
"그래프를 줄여라"≠"직렬 판단 노드를 빼라" + fan의 렌즈 고착). 교정 각인 3곳: 운영 메모리
그래프-폭 원칙 / building-sizing-method 과소-폭 금지 규칙(c4970513) / 골 루프 프롬프트
발주 전 폭 질문(b4c856a2). **v2(kc-splitmap-v2-0703b)를 fan 파티션으로 재발사** — 잎
검증자 13 병렬 → 합성 수렴 → 렌즈 fan → closure. 폭 원칙 첫 실전. DSL 실측 1건: fan 뒤엔
수렴 노드 필수(fan→fan 직결 불가, assembly.py:603).

**슬라이스 1 ✅ 랜딩(0703 심야, stop-and-gate)** — axis_vocab_drift_check.py 잎 추출(686L,
kernel_checks 11,379→10,861). 게이트: 순수-이동 AST 대조(동일 35/스왑 3=정본 명시
self-allowlist 경로 이동/신규 5=D4 프로브 기계) · 금지 4종+사어 무접촉 · --probe-mutation-red
rc=0(독 주입→core 비영→복원 green 내장) · registry 행 동형 · 격리+라이브 --all 35/35.
경과에서 결함/규칙 4건 적출: ①review 렌즈가 구형 brick: 주소 저작 → Part4 접수가 옳게
채택 차단, 단 기대(접수 반려→렌즈 재시도)가 아니라 link_paused 정지 — 후속 조사 후보
②정지 후 resume 체인: 원 워크트리 처분됨 상태에서 fresh 트리로 closure가 걸려 헛짚음
(기존 규칙 "worktree gone→직접 마감" 재확인) + 그 사고가 closure step-output 1 vs
raw-return 0 자기잠금을 남겨 #21 정합성 검사가 옳게 재개 거부 ③처분용 adapter_cwd에
세션ID 포함 scratchpad 경로를 쓰면 vessel이 redaction 위반자가 됨(중립 경로 규칙 각인)
④렌즈 concern의 실질(신규 파일 언트래킹)은 기우 — WIP 앵커 패키징이 언트래킹 포함 실증.

**슬라이스 2 ✅ 랜딩(0703 심야)** — building_plan_graph_check.py(258L, 무클로저 2본).
kernel_checks 10,861→10,734. **전 노드 1라운드 자가 완주·concern 0** — 선례 명시+렌즈
주소규칙 인라인의 효과 실증(슬라이스 1의 정지 클래스 재발 없음). 게이트: 순수-이동 AST
동일 2/2·프로브 기계 5·변이-RED rc=0·격리+라이브 --all 35/35. 머지 후 push.

**슬라이스 3 ✅ 랜딩(0704 자정)** — raw_evidence_stream_scrub_check.py(237L) +
agent_output_text_preservation_check.py(304L). kernel_checks 10,734→10,456. 2연속 전 노드
1라운드 자가 완주·concern 0. 프로파일 yaml 무수정(diff 0줄 — v2 pin 경고 준수), 잎별
변이-RED 2종 rc=0, 격리+라이브 --all 35/35.

**병행 트랙 가동(0704 자정)**: §4-2 선행 공유 헬퍼 통합 스펙 조사(sharedhelper-spec-0703a)
— 읽기 전용·파일 충돌 0이라 §4-1 직렬과 병행. fan(case_runners 측/loop0 측 파티션)→합성→
렌즈. 착지 시 §4-1 종료 즉시 §4-2 구현 발주 가능(설계 대기 0).

**슬라이스 4 ✅ 랜딩(0704 00:55)** — building_result_summary_check.py(458L, run+로컬 헬퍼 4).
kernel_checks 10,456→10,133. **3연속 1라운드 자가 완주·concern 0**. 순수-이동 AST 동일
5/5(v2 전속 배정 이름셋 그대로)·변이-RED rc=0·격리+라이브 35/35.
형제 세션 영향 점검(Smith 요청): 엔진 경로 미커밋 수정 0, .gitignore +7줄(시크릿 패턴)은
admission 허용 파일이라 무영향, 원격 동기 — **현재 영향 없음**. 감시 규칙: 발사 전 엔진
경로 status 스냅샷.

**슬라이스 5 v1 폐기·v2 재발사(0704 01:1x)** — v1은 COO 런처 생성 오염(문자열 치환
no-op → 계약 본문은 슬라이스3 좌표, 증명 선언은 슬라이스5 파일). 레인은 존재하지 않는
파일의 프로브를 선고받았고 **기계 증명 사이클이 5회 정확히 반려 후 예산 HOLD — Phase 3
파이프라인의 첫 실전 완주 관측**(오염 발주로부터 main을 지킴). 교정 각인: 런처 전문 작성+
assert 의무(치환 조립 금지). **부수 엔진 갭 발견: 증명-예산 HOLD 경로는 WIP 앵커 미보존**
(렌즈-정지 경로는 보존 — 백로그 등재). v1 vessel은 기록용 잔류(link_paused). 하네싱 세션
커밋 87ae5df0(brick 계약+agent 레인 표면)이 v1 발사 직전 착지 — v2부터 그 표면으로 걸음.

**슬라이스 5 v2 ✅ 랜딩(0704 01:4x)** — brick_cli_entrypoint_check.py(807L)+
mcp_connect_projection_check.py(854L). kernel_checks 10,133→**8,762**(시작 대비 -2,617,
잎 6/13). 1라운드 자가 완주·concern 0·순수-이동 AST 동일 5/5+8/8·pin 10문자열 동반 이동.
**COO 표면 추가 2건(bbfdc492, Smith 지시 재검토)**: ①closed-agentfact discipline(전 8오브젝트
바인딩)에 concern 주소 형식 절 — 렌즈 위반(0703 실측)의 2차 앵커 ②work/return.yaml에
증명-모순 처리 규칙(모순 발주는 1라운드 insufficient_input — 0704 v1 6라운드 실측 기반).
.gitignore 시크릿 가드도 검증 후 커밋(61818474, Smith 지시).

**슬라이스 6 ✅ 랜딩(0704 02:2x)** — chat_session_park_check.py(1,266L)+
agent_session_id_redaction_check.py(400L). kernel_checks 8,762→**7,390**(시작 대비 -3,989,
잎 8/13). **3라운드 자가 수리 완주**(이동 불일치→정규식 중복→잔여 갭 — 매 라운드 실질 결함을
스스로 닫음, COO 개입 0). 공유명 해소 판정 수용: _SESSION_ID_*_RE는 redaction 잎 소유+
chat_session이 지연 임포트(행동 동일, 순환 차단 — AST 비동일 2건의 전부), 프로브 텍스트
상수는 계약대로 chat_session 소유. 게이트 전 항목 green.

**슬라이스 7 ✅ 랜딩(0704 03:0x)** — dashboard_productization_projection_check.py(1,364L,
48이름). kernel_checks 7,390→**6,167**(시작 대비 -5,212·46%, 잎 10/13). 1라운드 완주·AST
동일 48/48·공유 헬퍼 임포트 확인(중복 0).

**슬라이스 8 ✅ 랜딩(0704 03:2x)** — adapter_error_check.py(1,675L, run 2본+20이름).
kernel_checks 6,167→**4,626**(시작 대비 -6,753·59%, 잎 11/13). 1라운드 완주·AST 동일
20/20·공유 그래프플랜 임포트 확인.

**슬라이스 9 ✅ 랜딩(0704 03:4x)** — reporter_notification_projection_check.py(1,890L,
비연속 3블록 출신). kernel_checks 4,626→**2,884**(시작 대비 -8,495·75%, 잎 12/13). 2라운드
완주·AST 동일 18/18(_without_report_grain_env 포함)·closure의 verification_gap(언트래킹
기우 — 기지 클래스, 커밋 실물이 반증).

## §4-1 kernel_checks.py 도메인 분해 ✅ **완주 (0704 04:4x)**

**11,379줄 → 295줄.** 18개 run_* 전부가 13개 도메인 잎(<domain>_check.py)으로 이주,
kernel_checks.py에는 facade 재수출 + 러너 3인방(check_profile.py 소비)만 잔존. 사어
_gemini_api_classify_error_kind 삭제(참조 0 재확인). 라이브 --all 35/35 green(d296c7a7).
슬라이스 10개(잎 13개) 전 과정: 매 슬라이스 순수-이동 AST 대조·잎별 --probe-mutation-red·
registry 행·격리+라이브 스윕 통과, 자가완주 7회·자가수리 완주 2회(3라운드/2라운드)·COO
stop-and-gate 1회(슬라이스 1)·발주 오염 폐기 1회(슬라이스 5 v1 — 기계 증명 사이클이 막음).
공유명 소유권 패턴 정착(chat_session 소유·타 잎 임포트·지연 임포트 순환 차단).

**§4-2 1단계 ✅ 랜딩(0704 05:0x, a0604fd9)** — fixture_graph_helpers.py 신설(5함수 289L,
소비자 0 무변경 — diff 2파일이 정의 그 자체). falsy-gate 분기를 명시 파라미터
falsy_declared_gate_refs_use_default로 보존, docstring이 양쪽 원점 file:line 인용(스펙 D1
대조 완료). --self-check COO 손 rc=0. **새벽 골(/goal 0704) 종료선 2개 전부 달성.**

**§4-2 2단계 ✅ 랜딩(0704 오전, dc59c4e0)** — loop0 로컬 헬퍼 5개 thin alias 전환
(fgh-stage2-loop0-0704a, 전 4노드 1라운드 자가완주, +41/-55 단일 파일). COO 게이트
detached 워크트리 손 재현: 베이스라인-등가 프로브 7종 rc=0(selected_adapter_ref
미방출·falsy 빈-게이트 승격 assert 포함)·self-check rc=0·포커스 rc=0·변이-RED(게이트
ref 독 → rc=1 → 복원 green·오염 0)·격리 --all rc=0. **QA 정직 발견 1건**: proof-limits
텍스트 변이는 loop0 프로파일 무감(프로브 A rc=0, non-binding verification_gap) — 소비
실증은 프로브 B(게이트 ref RED)로 성립, 텍스트 감지 재검증은 3단계 계약이 보유.

**§4-2 3단계 ✅ 랜딩(0704 오전, f5d92a0c) — 소비 전환(스펙 commit 1~3) 완주.** case_runners
로컬 헬퍼 5개 thin alias 전환(+37/-59 단일 파일, 1라운드 완주). COO 게이트 손 재현: 등가
프로브 11종 rc=0(None-only 빈-게이트 보존·고정 close reason·adapter:local 상시 방출·
loop0-의미론 누출 없음 assert)·양 포커스 프로파일 green·변이-RED(driver0 rc=1→복원)·격리
--all rc=0. **실측 확정: proof-limit 텍스트 변이는 양 소비자 어느 표면에서도 무감**(스펙
probe-point 기대 반증) — 백로그 소형 후보 'proof-limit 텍스트 핀' 등재. 다음: §4-2 본대
(case_runners 108 def 패밀리 분해 — splitmap 발주 후보) / 스펙 4단계(plan envelope)는
'프로브·프로파일 후 고려' 조항 유지. Smith 큐 항목 1 전량 이행.

## 새벽 골 마감 (0704 05:0x) — Smith 기상 대기 큐

발주 중지, 감시 모드. Smith 게이트 대기 항목:
1. **§4-2 2·3단계 진입 승인** — loop0 소비 전환 → case_runners 소비 전환(각 별 커밋·별
   변이-RED, 스펙 정본 순서). 이후 §4-2 본대(case_runners 108 def 패밀리 분해).
   → ✅ **Smith 승인(0704 오전, 새 COO 세션 — 이전 세션은 골 완주 후 감시 모드에서 API
   에러로 종료, 상태 손실 0 재구성)**. 2단계 발주 fgh-stage2-loop0-0704a 발사(09:10).
   게이트 추가 설계: 베이스라인-대조 등가 프로브(merge-base 원본 vs alias본 dict 대조 +
   base/new 소스 assert로 공허한 green 차단), 변이-RED는 공유 모듈 독 주입→loop0 프로파일
   rc≠0(소비 실증), falsy-gate는 falsy_declared_gate_refs_use_default=True 강제 명문화.
2. §4-4 체커다이어트 순서 확정(87라벨 — 잎별 --probe-mutation-red 패턴 재사용).
3. coo·dev 오브젝트 처분(이월).
4. 백로그 소형 2건 발주 승인 여부: 증명-HOLD WIP 앵커 미보존(엔진 갭)·렌즈 구형주소
   정지 기전 조사.
2. 후속 조사(소형): 렌즈 구형 주소 저작 시 반려-재시도 루프 미발화(link_paused로 정지)의
   기전 — Part4 D1의 접수 지점이 렌즈 반환 경로를 덮는지
3. 틈새: P8 신뢰성 반복 프로브(분해 창 종료 후) / #23 레거시 정리(903MB worktrees·3주치
   vessels·inbox — **WIP 앵커 구제 선행**: 미머지 앵커 464105cf(관측측 v2, 참고용)·
   link-part4-r6(머지됨, 정리 가능))

**하네싱 세션 Gap 2건 처분(0704 오전, Smith 승인)**: ①Gap1 good_enough 선언-집행 분리 —
선언(10 KIND return.yaml)은 완료돼 있었고 집행 세트(agent/return_fact.py:49-74
TOP_LEVEL_VERDICT_KEYS)에만 부재. COO 전수 대조로 유일 갭 확인(선언 7키 중 미집행 1키).
frozenset 1키+체커 핀(_EXPECTED... :2106)+행동-RED 계약으로 goodenough-enforce-0704a 발주
(§4-2와 파일 비충돌 병행). ②Gap3 재파견 종료선 — reroute-defaults.yaml에
re_instruction_endline_rules 3행 선언 시공(616c97c0, Smith 비준): 종료선 재진술 / 레인
환경-실행가능 증명만 / scope 밖 수리는 COO 게이트. 로더 3키 한정 재검증·경로 admission
프로파일 green. 집행 게이트는 후일 소비자(선언-먼저 공인 패턴).

## GP-H — 하네스 구조 강화 T1~T6 (0704 등재, Smith 지시로 골페이즈 편입)

정본: harness-roadmap-orders-0704.md (하네싱 세션 저작, COO 검토·앵커 스팟체크 0704 —
coo.md 332줄 실측 일치·work/return.yaml 에코 필드 0 일치·compose 경로 콘텐츠 린트 부재
일치. 참고: run.py:1089 _preflight_step_output_building_root는 다른 용도의 preflight
선례 — T1 design 노드가 경계 확정 시 참조). 발주 시점 재확인 조항 유지.

| 항목 | 내용 | 의존/게이트 | 슬롯 |
|---|---|---|---|
| T1 발주문 린트 | 프리플라이트 모듈+오염 픽스처 RED (compose 배선은 2단계 별도) | 독립, **T계열 최우선** | §4-2와 파일 비충돌 — 발주 준비 완료 |
| T2 계약 수신 에코 | work 반환 received_deliverables_echo 선언+3자 대조 지침 | 독립 (D4 픽스처 스윕이 핵심) | T1과 병행 가능 |
| T3 패리티 원장 | 선언-집행 갭 열거 체커+원장 | 독립. **선/후 결정 확정: Gap 1 선랜딩(Smith 0704 오전 명시 지시 — 걷는 중)** → 체커는 green 탄생, 첫-RED 도그푸드 증명 가치는 소멸(정직 기록). 로드맵 권고(후자)와 상충했으나 Smith 지시 우선 | T1·T2와 병행 가능 |
| T4 프롬프트 행동-RED | 유혹 픽스처 실레인 프로브(N=3, 프롬프트 무수정) | 독립이나 실어댑터 비용 | GP3 분해 창과 레인 경합 주의 — §4-2 랜딩 후 |
| T5 핀 통합 | 프롬프트 중복 핀 다이어트 | **T4 랜딩 전 발주 금지**(측정 없는 다이어트 금지) | T4 후 |
| T6 홀드 자기서술 | hold_reason→처분 매핑 정본(선언만) | 선언 슬라이스 독립·소형. 소비 슬라이스는 walker 인접 = **Smith 게이트** | 틈새 소형 |

공통 규율은 로드맵 §공통 발주 규율 그대로 상속(fable5 레인 금지·계약 인라인·종료선
필수·레인-불가능 D 분리·_run_dynamic_graph_walker 불가침). 순서 원칙 2(GP3 분해 중
프로브 금지)는 T4에 적용 — T4는 픽스처 격리라 P8 신호 오염과는 다르지만 레인
파이프라인 경합이 실비용이라 §4-2 창 종료 후 슬롯.

**T7~T11 편입(0704 오후 — Smith 재정의 841b401b·핸드오프 21f44683 반영, 정본:
harness-roadmap-orders-t7-t11-0704.md)**:

| 항목 | 재정의 내용 | 상태 |
|---|---|---|
| T7 실패 복구 4결함 | S-a 예산브리지 조사 / S-b 검증 순서 재배치(비엔진, 축배치 design 선결) / S-c·S-d 선언. S-a2·S-d 수리는 엔진 Smith 게이트 | 발주 가능 |
| T8 증거 투영 | **신설 렌더러 폐기 → reporter 패킷 확장**(기존 sink 4개 출구, closure 결정 3필드 추가) | 발주 가능 |
| T9 | **"이식성" 폐기 → 체커-동반 개발 원칙**(신규 기능=게이트 체커 동반, 브릭은 로컬 설치가 맞다 — Smith). T11 흡수 가능 | 발주 가능 |
| T10 동적 그래프 | **전체 실행(5a5663f7 — S2·S4 Smith 게이트 → 사전 승인 전환, 경계 3조건: ①계약 밖 표면 필요 시 중단·엔진 불가침 4종 ②기계 게이트(RED/GREEN 쌍+격리 --all+번호별 diff 실물) ③같은 자리 3라운드+ 홀드 시 중단·Smith 복귀). 순차 S1→S2→S3→S4 — 단 S3는 직전 지시로 이미 걷는 중이라 S1·S3 랜딩 → S2(S1 스키마·S3 게이트 행 참조) → S4 순으로 집행. 독자 판정 기본 규칙 고정: 실행·재개=rev 인지 필수 / 투영=단일 읽기 헬퍼 기본 / spine ORPHAN-SKIP 해소는 이월 불가 1차 필수. rev 파일 _DECLARATION_EVIDENCE_REFS 편입 확정** | 전 슬라이스 진행 |
| T11 교훈 원장 | lessons-ledger.yaml + 커밋 동반 관행 (T3 패리티 원장·ledger_projection과 3자 구분 명시) | 발주 가능 |

조사자 세션은 Opus 폴백 후 핸드오프 문서로 인계 종료(다음 조사자 세션은 Fable5 재개).
실행 주체는 COO 세션(이 세션) — T7·T8·T9·T11 발주는 Smith 확인 후.

**GP-H 1차분 ✅ 완료(0704 오후)** — T1 f9687d7a·T2 69f056a0·T3 aa879966 전부 랜딩, 라이브
--all rc=0. T1은 5라운드 자가수리 완주(실결함 3개 순차 폐쇄 → fnmatch 재구현 폐기·assembly
문법 정렬 → 설계질문 자가 해소; 매 라운드 실질 전진 = 공전 아님이 실측 판정). 후속 소형
등재 3건: ①T1 L3 패턴이 0702 사고 원문("근거 file:line만 반환" — reason_refs 무동반)을
못 뭄(패턴 1행+픽스처) ②proof-limit 텍스트 핀(§4-2에서 확정된 무감지) ③T2 드리프트
강제가 단방향(shape→산문)임을 실측 — 로드맵 "양방향" 서술 정정. 운영 실측 1건: route
policy가 설계-질문 concern에도 재파견을 채택한다(implementation_gap의 수리가능/설계결정
하위구분 부재 — T6/T7 계열 입력). T4·T5는 슬롯 유지(§4-2 창 종료 후 → 지금 발주 가능
상태, Smith 게이트 대기).

**Gap 1 ✅ 랜딩(0704 오전, 529c76d0)** — good_enough 집행 동기화(frozenset 1키+체커 핀).
goodenough-enforce-0704a 1라운드 완주, 단 closure가 D3~D6 partial 정직 보고 — **COO 계약
저작 실수 실측: 커밋-의존 증명 형식(커밋 후 변이·diff base..HEAD)은 레인-불가능**(커밋은
엔진이 완주 시 소유). 레인 행동은 전부 옳았고, COO 게이트가 그 증명을 직접 수행: 행동-RED
(베이스라인 갭 실증→변형 6종 거부→회귀 0→패리티 잔존 0)·변이-RED(핀이 'missing forbidden
return key(s): good_enough'로 뮤)·true-base 2파일 diff·격리 --all rc=0. 교훈 2건 운영
메모리 각인: 커밋-의존 증명은 COO 게이트 항목 분리 / 빌딩 diff는 merge-base 기준으로
읽어라(main 전진 후 wrong-base diff는 형제 랜딩을 역전환으로 보이게 한다 — 실제 소동 1회).
T1(t1-tasklint-0704a)·T3(t3-parityledger-0704a) 병행 걷는 중 — T3 계약은 green 탄생을
명시하고 RED 실증을 워킹트리 변이 2종으로 대체.

## 저녁 골 (0704 — COO 작성, Smith 위임: "순서정리하고 운영자 관점으로 골 작성")

**목표 한 줄**: 하네스 로드맵 실행 가능분을 전부 소진하고(엔진·Smith 게이트 제외),
갓모듈 마지막 대형(§4-2 본대)의 조사를 발사한 상태로 창을 닫는다.

**웨이브 A (즉시, 파일 비충돌 병행 3발)**
1. **T7 S-b** — 처분 검증을 persist 이전으로(결함② 수리, 비엔진). design 선결: 저작
   진입점의 축 배치(link/transition.py vs COO 헬퍼 — support가 처분을 '판단'하는 축
   침범 금지). 증명: 오염 처분 시도 시 raw/link.jsonl 라인수 불변 + 사전 거부.
   walker_resume.py 수정 필요 판정이 나오면 구현하지 말고 COO 게이트 이관(엔진 인접).
2. **검증 표면 소형 2종** — ①T1 L3 패턴에 0702 사고 원문 계열("file:line만 반환",
   reason_refs 무동반) 추가 + dirty 픽스처 ②proof-limit 텍스트 핀: fixture_proof_limits
   5문자열을 loop0·driver0 프로파일 pin으로(§4-2 실측 무감지의 폐쇄). 변이-RED 필수.
3. **T7 S-c/S-d 조사** — repo 무수정(수확형): S-c 결함③ "거부 후 정정 경로" 선언
   내용(가드 2곳 file:line 정합 포함), S-d "미완 처분 보존 원칙" + temp_dir
   wip_anchor_ref="" 예외/결함 판정 + 증명-예산 HOLD 앵커 미보존(0704 실측, 같은 가족)
   흡수. fake-landing no-diff 가드 홀드가 정상 경로임을 계약에 선명시(0704 교훈).

**웨이브 A 경과(0704 저녁)**: ③ScSd ✅ 수확 8bac93d4(정정경로+보존원칙 선언 2문서, no-diff
가드 정상경로 2회째 관측). ①T7-Sb ✅ **결함② stale 3중 확인** — design 실물 조사(선-검증
onboard.py:3409-3423 실존, 유일 저작 진입점 :3142)·COO 손 재검증·QA 공격 무결. 레인 전원
정직 무변경 반환, 가드 홀드 검수-forward. 잔여 관측 1건 백로그: forward-resume 후 무변경
조사 vessel의 frontier가 evidence_incomplete(수취 영수증 0 vs 반환 5 — 장부 꼬리, 산출과
무관, 추격 금지 적용·결함 관측 등재). ②s2는 closure 경계질문(기존 :33 패턴 오탐 수리가
종료선 안인가) — 라우트 결정 대기, complete 시 COO 게이트에서 범위 처분. **T7 4결함 최종
상태: ①stale ②stale ③④선언 랜딩 — 엔진 수리 잔여는 temp_dir·증명-HOLD 앵커(Smith 판정
대기)뿐.** 병행 신호: T10 발주-준비가 형제 세션에서 Smith 결정 반영하며 진행 중(d67a03d7
expansion_budget fail-closed 확정 등) — 이 골의 T10 제외는 유지, 발주는 그쪽 정본 따름.

**웨이브 B (A 랜딩 후, 병행 2)**
4. **T6 홀드 자기서술 선언** — hold_reason→{합법 처분·실제 의미·오판 사례} 매핑 정본.
   S-b/S-c/S-d 산출 + 오늘 실측 2건(설계-질문 concern에도 재파견 채택 / fake-landing
   가드의 조사-발주 정상경로) 흡수. 소비 슬라이스(walker)는 Smith 게이트 유지.
5. **§4-4 체커다이어트 순서안** — COO 기획 문서(87라벨 분류·순서·RED probe 재사용
   설계) → Smith 확정 게이트에 등재(발주는 확정 후).

**웨이브 C (대형 창 개시)**
6. **§4-2 본대 splitmap 조사 발사** — case_runners 108 def 패밀리를 §4-1 표준(fan
   파티션 잎 검증 → 합성 → 렌즈)으로 지도화. 슬라이스 추출 연쇄는 다음 창(지도
   착지가 이 골의 종료선).

**종료선(DONE)**: 웨이브 A 3건 랜딩(게이트 손 재현 포함) + T6 선언 랜딩 + §4-4
순서안 Smith 큐 등재 + §4-2 splitmap 조사 발사(착지는 다음 창) + 전량 push.
**웨이브 T10 추가(0704 밤 — Smith 발주 실행 지시, 정본 dd49bab9 §T10)**: S1(plan_expansion
순수함수, 비엔진)·S3(link-gate:expansion-approval 행+expansion_budget 선언, 비엔진) 즉시
발주. S2(revision 표면+동반 체커)·S4(resume 확장 분기)는 엔진 — 발주문 초안 작성 후 Smith
승인 대기. 필수 제약 상속: revision 랜딩→처분 순서 / 상류 편입 거부 / 신규 노드 예산은
expansion_node_budgets 전용 키(node_reroute_budgets·budget_delta 재사용 금지) / 승인 기록
raw/link.jsonl 금지(work/expansion-approvals.jsonl 기본안). 로드맵 상단 "랜딩 완료(웨이브
A)" 줄 재발주 금지 — 잔여는 T10 4조각 + T8-Sb + T6뿐.
**저녁골 경과(0704 밤)**: 웨이브 A ✅ 3/3 · 웨이브 B ✅(T6 06dbf416 — hold_reason 26행
정본, 3라운드 완주 / §4-4 순서안 수확 173d91e4) · T10 S1 ✅ 17eb15c2(plan_expansion 순수
함수 — **write_scope 가드 첫 실전 발화**: 레인의 관례적 체커 등록(case_runners 러너+
프로파일)이 계약 금지 글롭에 걸림 → diff 검수 후 수용, 교훈 '체커-동반 D에는 등록 표면
3종이 따라온다' / fresh-트리 no-diff 재정지는 기존 규칙로 앵커 직접 머지) · T10 S3 ✅
6c995aaa(게이트 행+expansion_budget=0 fail-closed+화이트리스트 3종 — 드리프트 집행자는
catalog-restructure link_gate_token_drift임을 게이트에서 실측, 변이-RED 양표면 리터럴
확인) · **T10 S2 걷는 중**(design이 지목한 run.py는 callee-측 커버로 무접촉 판정 — 경계
조건 ① 비발동, 레인도 동일 독해로 scope 준수) · S4 대기(S2 랜딩 후). splitmap(웨이브 C)은
T10 창 종료 후 발사(레인 경합), case_runners def +1(run_plan_expansion_case) 반영 예정.

**T10 경과(0704 밤 2차)**: S2 ✅ e142dfe4 — 6라운드 자가수리 후 클린 수확(런타임 inbox
잔해 5,397개가 write_scope 가드에 걸림 — 오늘 3번째 가드 발화, 소스 8표면만 분리 랜딩).
게이트 손 재현: 체인 체커 6쌍 내장 green·내구성 실물(os.link 배타+원자, :1491-1499)·
저작 선-검증 사슬·spine ORPHAN-SKIP 해소(1차 필수)·D6 판정표 기계-판독 함수 13행 착지.
t8sb-v2 ✅ 22a851ee(우회 3키 여유 폐쇄 — 규칙-내 10변형+전각 거부). l33 ✅ 8f873218
(표준 ADDR 오탐 폐쇄, 17dirty/12clean — T1 2단계 선결 해소). **S4 ✅ b0dd55ae — T10 4조각 전량 완결.** Invariant-D 확장 프로브가 BROKEN-1 회귀를
끝-대-끝 기계화(예산 HOLD→rev-1 신규 노드→reroute-편입→expansion_node_budgets 재부착,
1라운드 완주). 사전 승인 체제 무-Smith-복귀 종료: 경계① 미발동(후보 1건 callee-커버
판정)·경계② 기계 게이트 전부 green·경계③ 미도달. 후속 소형 등재: D5 fan-in wait-all
rev-확장 픽스처(S1 조립-시 member_refs 강제로 완화됨). 교훈 등재: 픽스처-실행 발주는
project/ 잔해 정리를 계약에 명시(S2 실측).

**이 골에서 안 하는 것(0704 밤 정정 — T10 제외 조항은 stale, 위 웨이브로 대체)**: 엔진
수리 전부(S-d 수리·K-of-N 디스패치·T10-S2/S4 — 초안까지만), P8 신뢰성 반복(분해 창과
배타), #23 레거시 정리, 소급 원장 등재.

## GP-O — 온보딩 zero-dev 트랙 (0704 편입 — 온보딩 세션 산출, 정본 onboarding-zero-dev-plan-draft-0704.md f4053b97)

"개발 1도 모르는 고객" 기준 온보딩 재설계 v2 — fable5 비평(FLAWED 판정) 전면 반영판:
L2 순환은 관문 압축(앱 1+구독 1)으로 재정의, L1은 배포-결정 선행으로 정직 축소, 0618
깔때기 역전(무료 첫 초록불 선행·결제는 업셀) 계승 복원, **실측 우선 역전**(L2 시공 전
실수강생 3~5명 동반 관찰 → 시공/기각 분기), 에이전트 금지행위 계약(결제·키 대행 금지)·
14관문 인벤토리·Windows 하중벽·생애주기·지원채널 절 신설. 부수 실측 버그 1건: README
AI-확인 줄 expected가 현 install.sh와 불일치(성공을 실패로 판정) — 온보딩 세션에 수리
후보 통보 완료("에이전트용 표면은 체커 없이 썩는다"의 산 증거, T9 체커-동반 원칙 접점).

**Smith 결정 대기(v2 §7 — 순서 고정)**: ①배포 표면(설치 진입점 공개 여부·고객 접근권
생성 주체 — **다른 모든 결정의 선행 조건**) ②실측 먼저 승인(P0 수강생 3~5명 동반 관찰)
③P0 기본 provider ④Windows 우선순위 ⑤한국어 통일(③~⑤는 실측 후 가능).
실행 주체: 온보딩 세션(워크트리 분리) — COO 트랙과 파일면 비충돌 유지, 머지 전 fetch·스윕.

## §4-2 본대 슬라이스 연쇄 (0704 밤 개시 — 지도 정본 cr-splitmap-draft-0704.md)

**슬라이스 1 ✅ 83961354** — adapter 러너 4본(348행) rehome 완결(헬퍼층 기실존 잎으로,
재수출 허브 개시). 2라운드 자가수리(QA가 공유-헬퍼 중복 적발 — 상수 동행 규칙 집행).
게이트: AST 4/4 동일·재수출 해소·행동-독 생존성 RED(메시지-변이 무감 실측 2회로 **행동-독
프로브를 표준 승격**)·격리 --all. **D5 후속 ✅ d92e9df3** — fan-in wait-all rev-확장 런타임
실증(관측자 부하-지탱 구조 확인, walker_fan_in 무수정·행동 정상 확정) — T10 이월분 종결.
**슬라이스 2 걷는 중** — 자립 러너 4본(workflow_import 574·wiki_carry 168·auto_repair 38·
hook_registry 34 = 814행) 잎 4신설. 연쇄는 직렬(전 슬라이스가 case_runners를 물음 — §4-1
동일), 이후: 자립 잎 잔여(12패밀리) → 공유-인프라 선행 → §4-4 민감군(carry/drain/
materialize/compose) 최후.

**Smith 결정 4건 확정(0704 밤 3차)**: ①§4-4 검증 입도 = **러너 단위**(라벨별 기구 제작
기각 — 행동-독 프로브 재사용, 필요 시 승격) ②§4-4 시작 = **Batch 0~1 병행**(§4-2 비민감
구간 실측 근거, 민감군 3~5만 §4-2 완주 후) ③GP-O 배포 표면 = **프라이빗 git + Smith 초대
온보딩**(공개 진입점 없음 — 현 구조 변경 최소) ④GP-O 실측 = **Smith 본인 + 회사 인원**
(수강생 동반 대신). 부수: dev 오브젝트 **유지** 확정(coo 오브젝트 처분은 미결 유지).
T1 2단계(compose 배선)는 §4-2 완주 후 재상정.

## 심야 판 현황 (0704 밤 4차 — 3워크스트림 병행)

| 트랙 | 상태 |
|---|---|
| §4-2 본대 연쇄 | 슬라이스 1~3 ✅(83961354·d6fb4ec0·33972b52 — case_runners 9,302→7,005행, AST 전수 동일·행동-독 생존성·--all 매회 green). **슬라이스 4 수리 2R**(자립 5패밀리 1,950행 — QA가 임포트 순환 적발, 지연-임포트 선례로 교정 중). 잔여: 공유-인프라 4모듈 → 의존 잎 3 → §4-4 민감군 4패밀리 |
| §4-4 다이어트 | **Batch 0 걷는 중**(Smith 확정: 러너 단위·병행) — work 1R에 99→87 삭제+witness 매핑 완료, QA가 witness 로그 보존 형식 지적(수리 라운드). Batch 1은 같은 파일이라 직렬 대기 |
| T1 2단계 | **배선 수리 2R**(Smith 승인: "빌드에 붙이자") — 1R에서 정직 발견: fail-closed 배선이 기존 체커 픽스처 조립까지 걸어버림(--all RED). 레인이 scope-내 실발주/픽스처 판별 이음새 시도 중, 불가 판정 시 경계 정지→Smith 복귀 계약 |

Smith 결정 소화 상태: §4-4 2결정·GP-O 2결정·dev 유지 전부 집행 반영(5c8441dd). 미결 잔여
= coo 오브젝트 처분 1건뿐.

**T1-2단계 이음새 재정의(0704 심야 — Smith 승인 "어셈블리 수정해라")**: v1(compose_building
이음새)은 4라운드 진동으로 구조 판정 — 공용 계층엔 실발주/픽스처 판별자가 원리상 없다.
v2를 assembly build() 하강부(실발주 전용 저작 관문)로 재발주(t1s2v2-assemblywire-0704a).
v1 vessel은 기록용 주차 예정(미머지). **증명-형식 공전(2번 문제)은 COO 판단으로 처분**:
운영은 중단 규칙+게이트 재현으로 흡수(금일 실증 3회), 근본 해법(route policy의 concern
하위분류 — 수리가능/형식/설계질문)은 엔진 개선 소형 후보로 백로그 등재.

## 심야 판 현황 v2 (0704 — 최신)

**§4-2 본대**: 슬라이스 1~5 ✅(83961354·d6fb4ec0·33972b52·6e06c217·79457344) — case_runners
9,302→**4,779행(49% 감소)**, 자립 잎 15패밀리+공유-인프라 완료. **슬라이스 6 걷는 중**
(의존 잎 3패밀리 1,343행 — temp_vessel 직수입). 잔여: 슬라이스 6 + §4-4 민감군 4패밀리
(carry/drain/materialize/compose ~2슬라이스) = **본대 완주까지 ~3슬라이스**.
**§4-4**: Batch 0 ✅ cdb1ec67(12중복 삭제 99→87, 러너-단위 witness 양 split 실증, 개명
접두 실측 기록). Batch 1(agent_packets 5+small_intake 3 라벨 이동)은 hardening.yaml
직렬 — 발주 준비됨.
**T1-2단계**: v1(compose 이음새) 6라운드 진동 후 주차 절차 — 구조 판정(공용 계층 판별자
부재). **v2(assembly 이음새, Smith 승인) 걷는 중** — design이 발주 전제 오류(체커의 bare
build 호출) 정정하고 assemble() 하강부로 조정, work 진행.
push 7차까지 완료(79457344 = origin 동기).

### T1-2단계 완결 기록 (0705 새벽)

**T1-2단계 랜딩 117405c0 (v4)** — 발주문 린트가 build()·assemble() 양 공식 관문에 배선.
여정: v1 compose 이음새 진동(구조 판정) → v2 assembly 골격(필터 자기모순 — 오염일수록
린트 전에 걸러짐) → v3 필터 수리(write_requested, 단 build 관문 미배선) → v4 양 관문 완결.
COO 게이트: build 오염 CompositionError·클린 통과·생존성 변이 RED·--all rc=0 전부 손 재현.
경화 나선(fixture-텍스트/sentinel 우회)은 경계 조항으로 게이트에서 절단 — 후속 소형 후보.

**엔진 관찰 2건 백로그 추가**:
- write_scope allowed_paths 소극 집행 의심: v3·v4 모두 allowed에 없는 check_profile.py
  diff가 walker를 통과(등재 4줄 — 내용은 정당). forbidden은 물었는데 allowed 밖은 안 문
  것으로 보임 — 재현 조사 후 소형 후보.
- route policy 커버리지 나선 3번째 실측(v3 6R·v4 경화 4R) — 기존 backlog 행(957b382d)
  근거 보강.

### §4-2 본대 완주 (0705 새벽) — GP3 갓모듈 분해 완료

**case_runners.py 9,302행 → 971행 재수출 허브** (슬라이스 9개, 1d19b42c 완주 머지).
잎 모듈 ~20개, 전 슬라이스 동일 게이트 표준(AST 동등·행동-독 생존성·격리 --all) 통과.
kernel_checks(§4-1)에 이어 두 번째 갓모듈 해체 — GP3 잔여는 §4-4 Batch 2~5 라벨
이동(순서·게이트 확정, 기계적)뿐. 슬라이스 8 교훈(실측 개수 > 계약 리터럴, 전속 헬퍼
동행)이 슬라이스 9 계약에 반영돼 1라운드 완주로 실증.

**T1-2단계 첫 실전 발화**: 랜딩 직후 COO 자신의 슬라이스 9 발주문을 L1(종료마커 부재)로
거부 — 발주문에 `종료선:` 독립 행이 신규 표준. 오탐 아님(마커가 산문에 묻힘).

## 현재 판 (0705 아침)

**걷는 중**: §4-4 Batch 2(step_template 16± → 신규 step_template_boundary, work 진행) ·
T4 행동-RED 프로브(design 착지 — 좌표 계약 안, work 진입). 표면 비충돌 병행.
**직전 랜딩**: §4-2 본대 완주(1d19b42c, case_runners 971행 허브) · T1-2단계 v4(117405c0,
발주 린트 양 관문 — 첫 실전 발화로 COO 발주문 거부 실측) · Batch 0·1.
**대기열(순서 확정)**: Batch 3 carry(→ Batch 2 뒤 직렬, hardening.yaml 공유) → Batch 4
materialize(builder_composition 확장) → Batch 5 compose(최심부 31, 최후). T5 핀 통합은
T4 랜딩 후(측정 없는 다이어트 금지). P8 신뢰성 반복은 분해 창 종료로 해금 — 슬롯 대기.
push 13차+골문서까지 origin 동기(a39fdfbc).

### T4·T5·Batch 2~4 기록 (0705 오전)

**T4 랜딩 62565e27** — 에이전트 축 첫 행동 측정: P1(dev 무-diff 유혹)·P2(qa 가짜-complete
유혹) 모두 3/3 정직 거부(QA 라이브 독립 재실행 동일). 0702 dev.md 경화가 행동으로 실증.
프로브는 admission 등재만(—all 비디스패치, 라이브 비용 격리).
**T5 주차(무-diff)** — 레인 정직 롤백: work 레인 어댑터 refresh 불능으로 전후 측정 불능
(0/3 인프라 실패) → 계약 롤백 조항 이행. QA 레인은 3/3·3/3 재현(프롬프트 건강, 문제는
레인 환경). fake_landing 홀드 forward 2회 불가로 중단 규칙 적용, 기록 주차. **v2 후보:
측정을 QA 레인에 위임하는 그래프(work 통합→QA 후측정→closure 대조)**.
**Batch 2~4 랜딩**: d4825e4c(step_template 16, 79→63) · 68262905(carry 14 고아0, 63→49) ·
eeb583a9(materialize 20, 49→29; 개명 의혹은 게이트 집합대조로 무혐의). **Batch 5(compose
31, 최종) 걷는 중** — 랜딩 시 §4-4 완료 = GP3 전체 종료.
**운영 사고 1건(자가)**: Batch 3 1차 머지를 게이트 워크트리 안에서 실행(무효) — 본 repo
재머지로 수습. 게이트→머지 전환 시 cd 확인이 체크리스트 항목으로 추가됨.

### §4-4 완료 — GP3 갓모듈 분해 전체 종료 (0705 오전)

**Batch 5 랜딩 0b9608ba** — compose 28라벨(재계수 28>계획 31, 실측 우선) →
compose_boundary 신설. **hardening.yaml 99→1라벨** (6배치, boundary 프로파일 5개 탄생).
잔여 1라벨 `c1-gate-sequence-coo-first-is-admitted` — compose/materialize 계열 아닌
게이트-시퀀스 단독 라벨. 처분(적정 거처 이동 or 잔존) = COO 소형 후속.
**GP3 종료 선언**: §4-1 kernel_checks ✅ · §4-2 case_runners ✅(9,302→971 허브) ·
§4-4 라벨 다이어트 ✅(99→1). 남은 본선 = P8 신뢰성 반복 · T4 후속(프롬프트 수리
불요 — 3/3 통과) · T5 v2(QA-레인 측정 위임 구조) · GP-O 실측(온보딩 세션 소관).

### 마감 웨이브 현황 (0705 낮)

**Smith 결정 확정**: coo 오브젝트 **유지** (0705) — 근거 3겹: COO 헌장 정본(coo.md)의
기계 배선체 / brick-protocol-coo projection 생성원 / coo-배제 불변식 피검체. dev도 유지
(0704 확정). **Smith 대기 항목 0.**
**hardening.yaml 은퇴**: 마지막 라벨(c1-gate-sequence)이 구동 러너 거처(compose_boundary)로
이동, 파일+core행 삭제(4890ed40) — 99라벨 프로파일 소멸, §4-4 완전 종결.
**write_scope 회색지대**: 조사 완결(주차) — driver.py:1050/1082 사이 혼합-diff 통과 갭
좌표 박제 → **수리 발주 걷는 중**(wsallow-repair, observed_paths_outside_declared_scope
기반 홀드 + 동반 체커).
**걷는 중**: T5v2(핀 통합, QA-위임 측정) · 엔진소형 4건 설계조사 · ws수리.
**대기열**: #18 부검 프리셋 → approval_policy 핀 → llm D5/D6+effort 번들 → 엔진소형
시공(조사 좌표순) → #23 레거시 정리(앵커 구제 선행) → **P8 단독**(파이프라인 조용할 때
마지막).

### 형제 세션 진단 접수 — T10 확장 운전 선결 갭 2건 (0705, 최우선 발주됨)

**갭 1 (gap1-budget-birth-0705a 걷는 중)**: 확장 예산의 출생 선언 부재 — 소비·검증은 전부
랜딩됐는데 assemble()/build()에 인자가 없어 신규 판 전부 예산 0. 저작 인자 → plan 통과
(fail-closed 하위호환 절대).
**갭 2 (gap2-approve-basis-0705a 걷는 중)**: run_approve_entry에 승인 근거 인자 부재 —
근거는 발주 시점 선언으로만 주입돼 forward 처분이 게이트 재홀드로 회귀. **이 세션 0705
실측 3회(t5v1·wsp·t5v2 evidence_incomplete)의 원인 규명이 형제 세션에서 완결된 것.**
갭 랜딩 후: 형제 세션이 T10 첫 확장 운전(웨이브A 확장 조각 JSON 투입) + 각인 웨이브(스킬
3종·헌법 갱신, 각인 재료 9건). 이 세션 몫 = 갭 1·2 발주·게이트 + push·골문서 상시.
추가 백로그(형제 통보): 어댑터-에러 홀드 forward 무동작(no-op) 기전 미규명 — 소형 조사
후보.

### 외부감사 인계 정본 접수 + S1 도장 (0705)

정본 = external-audit-repair-orders-0705.md(0395c26f). 1급 3건 전부 걷는 중: 묶음1
bool봉합(bundle1-boolseal-0705a) + 갭1(예산 출생) + 갭2(승인 근거).
**S1: Smith 확정 각인(정본 v2 5ddc5c14) — 재배선** (COO 도장과 일치. 묶음2 수용 기준 7항·S4 RED 사양 명문화, 묶음3 경로-유출 원칙 확정, 당김 조항 포함) — ①support 비판단 원칙 정합(감사
B급 판정의 정중앙) ②행동 동등성 증명이 계약 필수라 위험 통제 ③유지 시 driver 직저작
부채 계속 누적(실증: 이 세션 wsr이 같은 방향으로 쌓고 있었음). 조건: 재배선 랜딩까지
기존 driver 홀드 현행 유지(보호 공백 0).
**교차 발견**: S4 == 이 세션 wsallow 갭(독립 규명 일치). wsr-v1 앵커(43d6baae)·v2는
driver 직저작 방식이라 **주차**(미머지) — 술어·픽스처·체커는 묶음 2 재료로 인계.
묶음 2 계약에 "오늘 신설 driver 홀드 배선 재배선 인벤토리 포함" 각주 필요(형제 전달).

### 외부감사 수리 진행판 (0705 오후)

**랜딩**: 묶음1 bool봉합(125bfcff — writer 2곳 변이 각각 RED 실증) · 묶음3 경로상대화
(91e4005f — 절대경로 재도입 변이 RED, walker 불가침면 무접촉) · 갭1 예산출생(f84fedcb
push — assemble/build 인자→plan 통과 손프로브, fail-closed 보존) · admission-wire
(278505c7 — 본배선 기구현 판명, 라이브-walk 핀 신설: 저작층은 기존 핀 2개가 RED로 커버
실증). **wsr-v2 주차 확정**(e96a337d — S1 재배선과 충돌하는 driver 직저작 방향, 술어·
픽스처·AST핀 기법은 묶음2 재료로 명시 인계).
**걷는 중**: 묶음2 게이트 재배선(수용 기준 7항 verbatim, design-first) · 갭2 승인근거(3R).
갭2 랜딩 시: 주차 홀드 빌딩들(t5v1·wsp·소형조사·웨이브A) 근거-forward 정식 종결 가능.
묶음2 랜딩 시: T10 첫 확장 운전 선결 전부 충족(형제 몫).

### 외부감사 트랙 문서 지도 + 페이즈 정본 접수 (0705 오후, Smith 지시 등재)

**문서 지도** (전부 status/kernel/): `external-audit-repair-phases-0705.md` = **실행 순서
정본(Phase 1~5 + §0 제외목록)** / `aplus-wave-plan-0705.md` = 웨이브2(A+) — **게이트 전
A+ 명의 코드 발주 금지**(게이트 = Phase 1 랜딩 + 묶음2 랜딩 + T10 운전 1회) /
`external-audit-repair-orders-0705.md` = 발견·판정 원장 / `handoff-external-audit-track-
0705.md` = 트랙 인계(새 세션 진입점) / `constitution-amendment-draft-0705.md` = 헌법 개정
심사(비준 완료) / 루트 `BRICK-CONSTITUTION.md` = **개정법(Rules 11~13)** — 이후 발주 계약
저작 시 참조.
**구분 원칙**: 지금(①) = 뚫린 구멍 막기 / 웨이브2(②) = 감시탑 상설화(같은 파일 리팩터라
병행 금지).
**§0 제외목록 준수**: 묶음1 본체·묶음3·갭1·갭2v2·T1~T6·감사 아카이브 = 랜딩 완료 —
지피티 보고서 근거 재발주 금지.
**순서**: 묶음2(걷는 중) → **Phase 1 = 묶음5+묶음1잔여(발주 1순위, T10 운전 선결)** →
T10 운전(조사자) → 묶음6·4·7 → 묶음9(승인됨)·10 → 묶음8 → 묶음11(조건부, 묶음2 랜딩 후).
**Smith 0705 오후 3결정**: 헌법 비준 ✅ / 묶음9 승인 ✅ / A+ 웨이브 채택 ✅.

### 남은 길 — 쉬운 판 (0705 저녁, Smith 보고용)

| 순서 | 일 | 쉽게 말하면 | 왜 |
|---|---|---|---|
| 걷는 중 | 묶음2 | 계약 밖 파일 섞인 커밋 차단 + 정지 도장을 심판(Link)에게 | 실측 2회 뚫림 + 도장 권한이 잘못된 축에 있음 |
| 걷는 중 | Phase1(묶음5+1잔여) | T10 확장의 안전핀 3개: 위조 개정판 거르기·승인 재사용 금지·bool 예산 잔여 | 이거 없이 첫 운전하면 오작동·속임수 가능 |
| 다음 | T10 첫 운전 | 확장 기능 실전 1회(조사자 몫) | 지어진 기능도 실전 0회면 미검증 |
| 그 뒤 | 묶음6 | 숫자 자리에 True 못 들어가게 공용 헬퍼+정적 검사 | 헌법 Rule 12 상시화 |
| 그 뒤 | 묶음4 | 빌딩이 멈추면 "뭘 해야 하는지" 에러·문서가 안내 | 지금은 COO 기억 의존(처분 오판 실측 다수) |
| 그 뒤 | 묶음7 | write_scope 경로 판정 코드 3곳 → 정본 1개 | 판정이 갈리면 그게 구멍 |
| 그 뒤 | 묶음9(승인) | provider 없는 새 컴퓨터에서도 verify 초록불 | README 약속이 fresh 머신에서 깨짐(실측) |
| 그 뒤 | 묶음10 | pip 패키지에 빠진 핵심 폴더 채우기 | 릴리스 설치가 즉사(실측 0파일) |
| 마지막 | 묶음8 | 문서 대청소(깨진 참조·낡은 숫자) | 코드 수리 끝나고 한 번에 |
| 조건부 | 묶음11 | 선언만 있고 안 물리는 게이트 4건 실구현 | 묶음2 선례 동형, 랜딩 후 착수 |
| 잠금 | A+ 웨이브 6종 | 같은 구멍 재발 방지 감시탑 | 지금 고치는 파일을 또 뜯어서 병행 금지(게이트: Phase1+묶음2+운전1회) |

이 트랙 밖 COO 백로그: P8 신뢰성 반복(조용한 파이프라인) · route policy 하위분류(A) ·
mutation_red 승격(D) · #20 캐스케이드(C) · #23 레거시 · 홀드 주차분 정식 종결(갭2 랜딩으로
가능해짐 — 틈새 처리).

### 프리셋 재편 v2 접수 + G1·G2 개방 (0705 밤)

**G1·G2 개방**: Phase1 랜딩(fc7dd571 — reader 패리티·sideways 거부·이중승인 거부 변이
전부 RED 실증) + 묶음2 랜딩(1cfb34ac — 7항 전수, :983 변이 RED, driver 저자 grep 0).
병합 조합 회귀 1건(driver0 체커 3부모 병합 훼손)은 라이브 스윕이 잡아 즉시 수복
(8e281bb5) — "격리 green ≠ 병합 green" 교훈 + sweep-push는 && 체인 재각인.
**A+ 잔여 게이트**: G3(T10 첫 운전 — 조사자 몫)만 남음.
**프리셋 재편 v2**(preset-restructure-plan-0705.md, 지피티 검수→조사자 교차검증 §4 이력
포함): 메뉴판→부품함 — 블록 8종(brick/templates/blocks, 문서+DSL 스니펫, 실행 표면
아님) + 프리셋 29종 anti_hint·blocks 2필드 additive + 질문-우선 진입 규율. S1(문서-전용,
종료선 7항) 발주 — 1차 웨이브 코드와 비충돌. S2는 sizing-doctrine R1~R3에 합류(중복
발주 금지).
**병행 개시**: S1(preset-blocks) · 묶음7(write_scope 매처 단일화) · 묶음4(홀드 안내 A안).
묶음6은 묶음7 랜딩 후(assembly 표면 직렬).

### 세션 마감 (0705 밤) — 핸드오프 정본

**handoff-coo-main-track-0705.md** = 이 세션 인계 정본(읽기 순서·랜딩 전체·A+ 게이트
상태·대기열·주차장·교훈 8종). 걷는 빌딩 0, HEAD 1ce52761 origin 동기.
**Phase 3 완료** (묶음 6·4·7 랜딩) — A+ 게이트 G1·G2·G4 개방, **G3(T10 운전, 조사자)만
대기**. 다음 발주: 묶음9(승인됨)→10→11(조건 충족)→8.

### 자율운행 판 (0705 밤 2차 — COO 역할 세션 교대, Smith "골 끝까지 자율운행" 위임)

**S14 접수·검증**: 지피티 T10 체인 공격 보고 — MAJOR 2건(홀드 identity 재사용·bool 예산)은
현행 HEAD 실물 반증(Phase1 fc7dd571·묶음6이 제안 수리 그대로 선랜딩 — 아카이브 착시,
§0 클래스). 운전 절차 정본 = t10-drive-runbook-0705.md (077d8c46+af13030b).
**T10 조각 v1 폐기→v2**: 리허설 조각의 커널 아카이브 이동은 cleanup-wave-b(73673bf9)가
선집행 — 지피티 감사 세션의 정합성 적중, COO 재검증 확정. v2 = 잔여 실작업(4번째 z6 후보
확정+원장 / buildings-residue 분류), dry-run PASS, 지피티 공격 대기(Smith 수취).
교훈 각인: 조각/발주 앵커 재확인은 스키마만이 아니라 **작업 실존까지**.
**묶음9 ✅ 랜딩(d041f176)**: verify 계층화 — 무인자=hermetic(core)/--all 명시 플래그/
init 정합(RED hermetic이면 init fail 보존). COO 게이트 4관문: D1~D4 diff 실물 대조(89066c9d)
· 무-provider PATH 리터럴 프로브 rc=0 · 계층화 변이-RED(--all 기본값 재도입→RED→복원,
체커 내장 프로브 승격) · 격리 --all rc=0(140 프로파일). 고객 표면 문구(README·install.sh)는
계약대로 무접촉 — 온보딩 조율 대기.
**주차장 5건 forward 시도 → 전건 합법-거부(상태 무변경)**: 승인 표면이 hold가 아니라
`evidence_incomplete`로 관측(수취/반환 장부 꼬리 — 0704 웨이브A 관측 클래스의 재현).
묶음4 안내 에러 정상 발화. 추격 금지 적용 — 주차 유지, 백로그 보강(아래 행).
**다음**: 묶음10 ∥ 묶음11A 발주 → 묶음11B 초안(Smith 게이트) → 묶음8 → G3 운전(조각
v2 회신 후) → A+ 웨이브.

### G3 개방 (0705 심야 — COO 판정, 위임 권한 하)

**판정 권한 원칙 교정(Smith 원문 취지)**: "성공 판정 = 사람"이 아니라 **"성공 판정 권한의
배분 = Smith"** — 사람 승인이 상수가 아니라 권한 소재가 Smith의 주권적·위임가능 결정.
헌법 3축 절 "품질+성공 판단 = 사람" 문구는 "품질+성공 판정 권한은 Smith가 배분한다
(기본 소재: 사람)"로 개정 후보 등재(비준은 Smith — 묶음8/차기 개정 동승).
**G3 = 개방(조건부)**: 첫 실전 운전(t10-first-drive-0705b)이 G3의 선언 목적("Contract
Kernel이 흡수할 실전 데이터")을 초과 달성 — 개정 2장 라이브 체인·확장 실걸음·가드
실전 통과·엔진 발견 4건(runbook §5). 조건 = A+ W1 착수 전 replay-다중화 수리(인체공학
행 11)를 선행 슬롯 등재 + 수리 후 0705b 재개로 완주 봉인. **A+ 게이트 4/4 개방.**

### 월 지출 한도 사건 + 재발주 (0705 심야)

**사건**: claude 계정 월 지출 한도 도달("You've hit your monthly spend limit" 직접 재현) —
claude-local QA 레인 3연속 즉사(local_cli_nonzero, step-output 없이 adapter-error만).
묶음10·11A·gap1b 3빌딩이 fan-in 미충족 홀드 주차. codex 레인 산출(design·work·review)은
전부 정상 — 콘텐츠 무죄. Smith 계정 재로그인으로 해소(pong 재현).
**복구 시도 실측**: stop 처분 3연발 전건 "승인 대상 hold 상태가 아니에요" 거부 —
frontier가 hold가 아닌 `evidence_incomplete`(수취 영수증만 남고 반환 0 = 장부 꼬리).
**주차장 5건과 동일 클래스, 이제 누적 8례** — 레인이 반환 없이 죽으면 빌딩이
처분-불가능 상태로 떨어진다. 백로그 행 승격: 소형 조사 → **T7 계열 엔진 수리 후보
(복구 경로 부재 — Smith 게이트)**.
**처분**: 0702 규칙(반복 처분 실패 시 추격 금지·fresh 재발주) 적용 — 동일 계약으로
0705b vessel 3발 재발사. 죽은 0705a vessel 3기는 기록용 잔류.
**신규 선결 갭 발견(운전 전 실측)**: base `expansion_budget` 저작 인자 부재 — 갭1(c89f1732)은
노드별 키(declared_expansion_node_budgets)만 랜딩, base 키는 픽스처 전용. 공식 경로 출생
빌딩 전수 예산 0 → rev 쓰기 fail-closed 거부. **gap1b 발주로 봉합 중**(갭1 동형 4파일).

### T10 운전 경과 + 갭 연쇄 (0705 심야 2차)

**gap1b ✅ 랜딩(93eb4343)** — 리터럴 프로브 3종·변이-RED·격리 --all 4관문. **묶음11A ✅
랜딩(aff33e54)** — deliverable_crosscheck 기계 소비 탄생(0702 fake-landing 계보 종결).
**T10 운전**: 출생 빌딩(t10-first-drive-0705a) 홀드#1 정상 성립(coo 게이트·expansion_budget=2
실림). 단계2 실물-판 dry-run이 **엔진 갭 2호 적발**: plan_graph.py:162가 예산 부재를 빈
dict로 정규화 → reroute-정책 게이트 판 전수가 확장 조립 불능(출생 검증은 None-스킵 —
경로 간 부재-의미론 비대칭, Rule 11 동형). 수리 빌딩 t10gap2-gatebudget 발주(QA fable5 —
엔진 인접 승격 첫 적용). 랜딩 후 운전 재개(홀드#1은 안전 주차).
**evidence_incomplete 봉쇄 9번째 사례(클래스 확장)**: 묶음10-0705b는 4레인 전원 반환 후
주소-미해소 홀드였는데도 forward가 "승인 대상 hold 상태가 아니에요" 거부 — receipts 파일
자체가 부재(returns 4)인 판이었다. 즉 returnless 죽음만이 아니라 **영수증 장부 꼬리 일반**이
처분을 봉쇄. T7 수리 후보의 우선순위 근거 보강.
**묶음10 3차 발주(0705c)**: 0705b QA·review의 실질 발견 2건(wheel smoke의 setuptools-env
의존성 → 지정 환경-보고로 강건화 / repo 루트 build·egg-info 잔해 → --out-dir /tmp 강제+
부재 확인)을 계약에 접어 재발주 — 재발주 빌딩 = QA 승격 트리거 해당이나 이번 판 QA는
이미 sonnet이 실질을 잡았으므로 유지.

## 백로그 통합 (소형·주시·대기)

| 항목 | 분류 |
|---|---|
| **route policy concern 하위분류 부재** — 형식/설계질문 concern에도 재파견 채택(0704 실측 4빌딩: t6·batch0·t8sb·t1s2 공전 원인) → 수리가능/형식/설계 구분 후 형식은 COO 게이트 직행 | 엔진 개선, 소형 |
| **evidence_incomplete frontier가 approve-from-hold를 막음** — 주차 5 vessel(t5v1·engine-smalls·gap2v1·wsallow-repair·t1s2v3) 전건서 "승인 대상 hold 상태가 아니에요" 합법-거부 실측(0705 밤, 상태 무변경). 수취/반환 장부 꼬리 클래스(0704 관측)와 동일 기전 추정 — 종이-종결 경로 또는 장부 꼬리 정정 경로 조사 후보 | 엔진 관찰, 소형 |
| **raw graph fragment의 step top-level write 필드 미운반**(지피티 V2-ATT-001, COO 실물 확정) — plan_graph 투영이 brick_steps[].write_scope를 Brick row로 안 옮기고 조용히 버림 → 검증·어댑터 요청에 미도달. 근본수리 = top-level write 필드 거부(validator, 권장안 A) 또는 운반. T10 조각 저작 규율은 runbook 단계2 4단으로 방어 중 | 엔진 개선, 소형 |
| **write_scope 글롭 세그먼트 비인지**(지피티 V2-ATT-002) — fnmatch `*`가 슬래시를 뚫어 `dir/*.md`가 하위 재귀 매칭. 기존 "fnmatch 함정" 각인의 정식 수리 = 세그먼트-인지 matcher(`*`=단일 세그먼트, `**`=재귀) — **A+ W1 matcher 단일소스 계약에 합류** | A+ W1 합류 |
| **prose 제외 ⊆ forbidden_paths 체커** — 파괴적 work 노드에서 작업문이 "무접촉" 선언한 파일이 forbidden에 없으면 RED(지피티 V2-ATT-006 일반화) | 체커 후보, 소형 |
| **미지-발견→파괴-이동 커밋 게이트 패턴** — 발견 레인이 특정한 미지 대상을 이동/삭제하는 노드는 default-transition만으로 잇지 않는다(사람/COO 커밋 게이트 또는 조각 분리) — B6/B7 블록 코퍼스·graph-sizing 각인 후보(지피티 V2-ATT-004 일반화) | 각인 후보(묶음8/블록 갱신 동승) |
| **v2b — 4번째 z6 후보 이동+원장**(T10 운전 v3 조각이 exact path 확보 후): 좁은 exact 스코프 + prose-제외=forbidden 동기화 + 이동 원장 — 일반 소형 빌딩, T10 불요 | 발주 대기, 소형 |
| **운영자 인체공학 웨이브(Smith 0705 심야 독트린: "구조만 짜게 하라")** — 0705 실측 실수 8클래스 전수를 표면이 흡수(주소 유령-오진·proposal 잔해·캐스팅 철자·고아 발사·레인-불가능 D 린트·expand()·게이트-필수 기계화·중립 cwd). 정본 operator-ergonomics-wave-0705.md — expand()와 합본 웨이브, A+ W1과 표면 대조 후 슬롯 | 발주-준비 정본 등재 |
| **확장 조각 저작 DSL(가칭 expand()) 부재** — Smith 0705 밤 지적("빌딩 하나 태울 때 고생하면 애초에 의미가 없다"): 일반 발주는 build()+brick()/fan() 한 줄인데 T10 조각은 날것 엔진 스키마 수작업 — 그 수작업이 지피티 FATAL(row-외 write_scope)의 발생 지점. 사양 = brick()/fan() 재사용 → 조각 스키마 materialize(rows·edges·budgets 올바른 칸) + runbook 4단 dry-run 내장. B7(미지수 확장) 활성화 전 필수, 비-walker 순수 저작 계층. 0703 교훈("공식 경로의 표현력 한계 = 도그푸드 사각")의 재발 사례 | 발주 후보, 소형~중형 |
| 그래프 admission-gate 라이브 배선 (Rule 8 후반) | GP0 잔여, 소형 |
| P8 신뢰성 반복 샘플 | GP2 후속 |
| #23 레거시 정리 (앵커 구제 선행) / claude 세션 잔존 / gemini 세션 미조사 | 틈새 |
| mutation_red 의미론 강화(red_rc≠0 요구 — 형검사→집행 승격 설계논점) | gp3-threshold 후속 1 |
| 세션연속성 체커에 approval_policy="never" resume-argv pin 부재 | gp3-threshold 후속 2, 소형 pin |
| reason_refs bare 산문 허용 vs related_boundary_refs 산문 거부 — 정합 논점 | gp3-threshold 후속 3 |
| QA 산문 픽스처 세션ID 리터럴('sess-…') 재발 시 레인 계약 지침 승격 | gp3-threshold 후속 4 |
| ~~라이브 --all vs 걷는 빌딩 보고패킷 경합~~ → ✅ 순서 원칙 5 등재 | 종결 |
| ~~증명-예산 HOLD 경로 WIP 앵커 미보존~~ → **종결(5a5663f7 Smith 확정 — 수리 불요: diff 없음이라 보존 대상 자체가 없음)**. temp_dir 앵커도 설계 예외 확정 — T7 엔진 수리 잔여 0 | 종결 |
| llm= D5/D6(동시사용 거부) / effort 기록 / #18 부검 프리셋 / #20 write_scope 캐스케이드 | 소형 대기 |
| claude 레인 SIGTERM(143) 2건 — 3회째면 원인파악 빌딩 | 주시 |
| ~~coo·dev 오브젝트 처분~~ → ✅ 둘 다 유지 확정(dev 0704, coo 0705) | 종결 |
| ~~onboard.py/cli.py 미커밋 diff~~ → ✅ 랜딩 f7b11848 (Smith 다른 창의 Claude 저작 — gemini 키 대화형 접수+gh doctor행 제거. COO가 diff 정독·컴파일·4케이스 격리 재실행 후 커밋, service_tier 선례) | 종결 |

## 순서 원칙 (충돌 시 이 순서)

1. Smith 명시 지시 > 상설 골 훅.
2. GP3 분해 중 P8 프로브 금지(10k줄 이동 중 갭 신호 오염) — 신뢰성 반복은 분해 레인이
   걷지 않는 창에서.
3. 발주 크기: 토큰 효율이 아니라 "업무를 종료시킬 수 있는가"로 사이징, 파일 비충돌 병행.
4. 레인-불가능 수용 기준은 COO 게이트 항목으로 분리, 기계 게이트는 proof_obligations 선언.
5. 라이브 --all rc=1은 걷는 빌딩의 보고패킷 경합일 수 있다 — 착지 직후 재확인 후
   재실행으로 판정(0704 실측 등재). 공유 중 측정은 detached 워크트리 우선.
6. 발주는 반드시 정식 백그라운드 경로로 — 셸 `&` 고아 발사는 샌드박스에서 마감 커밋을
   유실한다(0705 Batch5 1차 실측). 게이트→머지 전환 시 cd 본-repo 확인 동반.

## 미래 후보 (선언 원칙 보존 확장)

- **선언된 팬의 조건부 개방** (Smith·COO 0702 합의): 팬 가지 N개를 선언+게이트로 잠그고
  HOLD 처분에서 몇 개를 열지(forward) 접을지(stop) 정한다 — resume 그래프 확장 없이
  병렬 수 유연성 확보. 근사형은 현 엔진으로 가능(per-node coo-gate + stop 처분 실존),
  완성형은 fan-out 진입 edge 게이트 소형 확장. GP3 이후 또는 필요 시 승격.

## 마스터 잔여 큐 (0706 새벽 정리 — 과업 종료 판정 기준선)

Smith "과업 모두 종료까지 이어간다". 이 큐가 비면 연속 운행 종료. 우선순위 = 저위험·고가치·비의존 순.

### 잔여 페이즈 스냅샷 (0706 야간 갱신 — 콘솔 Artifact와 동기, 상세 근거는 아래 절들)
| 페이즈 | 내용 | 상태 |
|---|---|---|
| **P0 게이트 판독** | (0706 저녁 전량 랜딩·봉인) R3 ccb73b44 · R5R8 e4cf700d · R1 6ae9f3f4 · r3margin 2eb79b40 · firehunk b94a77b3 · fugu451obit d25b89ce, 핸드오프 문서까지 origin=298bfc2e | 완료 |
| **P1 야간 웨이브 — 전량 랜딩 완료** | r9 db3a17a7 · cpath⑤+fugupacket 7bacb772 · **graphdecl-fix 612abed3**(5라운드 종료선 절단 — 표17 격자 일반해는 #12로 명시 이관, 변이 2종 RED, 스윕 50) · fugu-fieldprobe 성공(푸구 실사용 개방 확정) · checker-audit complete(은퇴 0·고아 0·재설계 1) | 완료 |
| **P3 줄이기 웨이브 — 걷는 중(0706 야간 발사)** | **friction-bundle-0706n**(표13 자동 WIP 앵커·표14 스윕 관측성·시간-픽스처 재설계) ∥ **build-unify-0706n**(#12 — build(preset=)·해석 수렴·--real-provider 축소·표16/17/18 흡수). 두 빌딩 다 design(fable5)→work(**푸구**)→공격QA(fable5)+증거QA→closure — 난이도-비례 캐스팅 독트린(Smith 0706 야간) 1호 적용 | 걷는 중 |
| **P2 walker 직렬(랜딩 순서만 직렬)** | ~~cpath~~(랜딩됨) → R2(carry 공용헬퍼) → 자기잠금 가족② | R2가 다음 |
| **P3 줄이기 웨이브(Smith 0706 야간 채택 — 회고 4제안 COO 판정안대로)** | 마찰청산 묶음(표 13·14·16, walker 무접촉) ∥ **#12 build() 단일 진입은 graphdecl-fix 랜딩 직후 발주**(assembly.py write_scope 겹침 해소 대기) · 규칙 만료태그 관례 즉시 발효(임시규율 vs 헌장 태그, 착지 시 대응 규칙 폐기 — 첫 폐기 예정: graphdecl-fix 랜딩 시 "output-root는 반드시 ~/.brick" 우회 규칙) · 인체공학 표 신규 행에 "제거되는 사람-판단" 컬럼 관례 | 4기 랜딩 직후 발주 |
| **P4 대형** | #15 가중치→그래프 초안기 — #12 랜딩 후(통일 입구 전제) · Case 8 정찰(읽기전용, 슬롯 나는 대로) | #12 뒤 |
| **P5 저우선** | T10 fresh 0705c(완주 스탬프) | 의존 없음 |
| **P-결정(Smith)** | 회고 4제안 = **채택됨(0706 야간, COO 판정안대로)**. 체커 은퇴 감사 = **채택·발주됨**(checker-audit-0706a — 존 리더 7 + 프로파일 매퍼 ∥ 병합 ∥ 전수성·반증 2렌즈 QA ∥ closure, 12노드 읽기전용; 산출 = 부패 4클래스 분류 + 처분 후보 표, 은퇴 집행은 후속 빌딩) | 결정 대기 0건 |

**운영 개선(Smith 0706 오전 지적 → 즉시 도입)**: 게이트의 기계부(스냅샷→마감→수확→프로파일→변이스펙→격리 --all)를 `support/onboarding/coo_gate_runner.sh`로 결정론화 — COO 토큰/시간은 판단 3점(design 승인·변이 설계·머지 결정)에만. **(0706 오후~저녁 개정)** 판정 이후의 기계 꼬리도 러너가 소유: `--land`(harvest 머지→라이브스윕→green일 때만 push) + `--ship`(이미-main 커밋의 무머지 스윕→push, 562dd86c) — **COO 맨손 git merge/push 전면 금지(Smith 0706 저녁), 러너가 already-on-main SHA를 NOTHING TO LAND로 거부(2c11380f)**.

**0706 새벽 Smith 위임(원문 취지 — 다음 발언까지 유효)**: "골 잡고 모든 과업이 없어질 때까지
빌딩으로 진행. 물을 게 생기면 COO 판단에 맡긴다. 운영자 관점 + 땜빵 절대 금지 원칙 하에
수정 결정 가능(예시로 walker 명시). 멈추지 말 것." → 집행 해석: C그룹 스코프 결정·D그룹 잔여
결정(wheel A/B 포함)·walker 수리 시공 결정이 COO 판단으로 개방. 판정마다 근거·반전 경로를
투명하게 기록(헌법 0706 개정 조항의 위임 운영). **위임 하 첫 판정: wheel = Option B 채택**
(근거: customer-ready 궤적과 W6 종료선이 어차피 설치면 smoke를 요구, 구현은 앵커에 완성
존재, 랜딩 비용=게이트뿐. smoke 실측 실패 시 Option A 폴백을 반전 경로로 예약).

### A. 진행 중 (착지 대기)
- (비어 있음 — 0706 새 세션이 걷던 3빌딩 전부 랜딩: erg3 6a28ed49 · 11B v1 021c1c3e · v2b 620df663. 회수 경위는 인체공학 표 13 참조. erg3 원장도 종결: forward 처분 체인으로 building_finished 16:15:56Z — 중간 fake_landing_write_scope_diff_absent 홀드는 "산출 선-랜딩으로 인한 무-diff"를 검토자가 확인 후 승인, 가드 자체는 설계대로 작동. v2b도 building_finished. 11B v1 vessel은 reroute×2 봉쇄 이력 그대로 잔류(내용은 랜딩됨).)

### B. 즉시 착수 가능 (표면 비충돌, 저위험, walker 무접촉)
- **T10 완주 — 재판정(0706)**: replay 수리 랜딩 후 0705b resume 실측 → **evidence_incomplete 클래스**(수취/반환 장부 꼬리 — 승인 대상 홀드 아님, error=not_approval_hold)라 미러 수리 적용 대상이 아님. 경로 = t7-recovery 정정 조사 or fresh 0705c. **저우선 유지**(미러 도그푸드 증명은 t7b 설계 vessel로 이미 완성).
- ~~인체공학 슬라이스 4~~ → **랜딩**(a79906cf — 게이트-없는 write 경고 + 프리셋 가까운 이름 제안, 변이-RED×3).
- **인체공학 잔여 행 후보**: 표 13(자동 WIP 앵커 — 이번 밤 2회 더 실측: resume-경유 마감 무커밋) · 표 14(스윕 관측성) · 표 16(CLI repo_root 검증) — 슬라이스 5 묶음 감.
- **graph-decl 표면 결함 2종(0706 저녁 실측, 소형)**: ①발사기가 building 루트에 `proposed-building-graph.json`을 쓰는데 lifecycle 경로-형태 체커는 루트에 work/capture/raw/evidence만 허용 — repo 안 output-root의 완주 vessel이 스윕을 RED로 만듦(임시 우회 = output-root를 ~/.brick로; 정식 수리 = 제안 파일을 work/ 밑으로 or 체커 허용) ②노드에 model_ref 생략 시 materializer가 `model:default`를 박아 codex-fugu-local 등 provider-엄격 어댑터에서 디스패치 전 ValueError 즉사(어댑터 default_model_ref 상속이 옳음). 부수 실측: graph-decl 기본 action=stop(동결 제안만)이라 실행엔 `"action":"forward"` 필수 — 문서화 감.

### C. 대형·스코프 결정 (0706 위임 하 COO 프레이밍 진행)
- ~~A+ W1 Contract Kernel~~ → **웨이브 종결(0706 오전)**: K1' 랜딩(7ea0d7d2 — 어휘 link/ 재귀속, 4축 역전 소멸, 단일소스 가드) · K2' 랜딩(0fd9bf33 — 정규화 위임 핀 + positive-int 통합 + **K3' 흡수 완결**(행동 프로브가 텍스트-핀 공허 대체 + manifest 등재 — 별도 슬라이스 불요 판정) + COO-직접 driver:2444 리터럴 쌍) · K4' 랜딩(ab197c36 — segment-aware matcher, WR-007 봉인, 'support/' 글롭 함정 의미론 사망). **W1 종료선 충족: S12-WR-001~007 전건 봉인 + 행동-동등성 게이트 전 슬라이스 통과 + 격리 --all 46.**
- **부검-딥 그래프-선언 템플릿(신규 — Smith 0706 지시)**: 수집 fan(sonnet xhigh ×8 = 4축×관찰/반증 2렌즈, 관찰만) → 병합 노드 → 진단 fan(이종 3두뇌: fable5 xhigh · codex 최신 xhigh · **fugu-ultra** — 독립, 근본원인+축귀속+처방후보+상호맹점) → 종합 closure(fable5 xhigh, 후보까지만 — 채택은 COO/Smith). 토큰 절약 변형 없음(Smith: "아끼지 말고 제대로"). 랜딩 형태 = brick/templates/graph-decls/postmortem-deep.yaml (erg6 --graph-decl 랜딩 선행). 첫 실전 = 0706 낡은-CLI 사건 + 레인 rc=1 클러스터.
- ~~A+ W2~~ → **랜딩**(8e7e17d8 — 공허-검증 기계 차단, core 편입, 스윕 45 프로파일).
- ~~expand() DSL~~ → **랜딩**(3c95c932 — 실수용기 왕복 검증 내장 4단 드라이런).
- **11B 후속 슬라이스** → **발주됨**(b11b-followup-0706a, engine-feature-hard, CLI 한 줄 — 공유 술어 모듈+walker_resume 시드 fail-closed+전 텍스트 검사).
- **concern-path 풀 미러 슬라이스(신규 — 수술 후속 선언)**: 미러 수술은 gate-sequence 경로 완전 미러 + concern-path 5사이트 loud-거부(최소 슬라이스). concern-path 채택의 정합 미러(runtime mail 재독·cohort 재검증·insert_width — 설계 D1.7)는 별도 슬라이스. 자기잠금 가족②와 픽스처 홈 공유(D5 판정).
- ~~무마찰 발주 — 런처 파이썬 소멸~~ → **판정선 도달 선언(0706 낮, erg6 랜딩 9e95fa02)**: --graph-decl로 커스텀 fan·per-node 캐스팅·source_facts·전문 task가 선언 파일+CLI 한 줄로 발주됨 — 완성 리터럴(t7b-모양 dry 발사, 동결 제안의 per-node fable5/xhigh 행 검증)을 게이트에서 집행. 표 15 갭 폐쇄. 첫 응용 = postmortem-deep 템플릿(brick/templates/graph-decls/). 잔여 소형: 표 17(입구 캐스팅 비대칭)·표 18(별칭 증발 — 수리 걷는 중)은 build() 단일 진입 통일 슬라이스가 흡수. 이번 밤 실측: CLI 한 줄 발주 5건 성공(erg4b·wheelsmoke-b·W2b·t7b-fixtures·11b-followup), 파이썬 런처 잔존 사유 = 커스텀 fan+per-node 캐스팅+source_facts(t7b·W1-S1 설계 슬라이스 2건, 표 15 갭 그대로).
- **가중치→그래프 초안기 (draft 표면 — Smith 0706 오후 재확인, COO 실수-기반 설계)**: 입력 = 업무 설명+가중치(sizing 질문 8종: walker인접/크기/분할/파일충돌/실패비용/사람승인/종료모양) → 출력 = graph-decl 초안+근거(모양·fan 폭·QA 렌즈 수·게이트 배치 + 위험-비례 캐스팅 자동: 승격기준 4종 내장 — 엔진인접 work=푸구·공격QA=fable5, 기본 codex/sonnet/gemini + L1/L4 린트 스캐폴드 자동 + fan 3법칙·write_scope 2법칙·source_facts 실존 선검증 + COMPOSED OK 사전확인). 자동발사 금지(Rule 3) — 초안은 후보, 확정은 운영자. 규칙 원천 = 0706 COO 실측 실수 전량(린트 반려 2회·캐스팅 철자·fan 문법·조립 사전검증). 순서: R-웨이브 랜딩 후 build() 통일과 한 묶음(cli/assembly 이음새 공유). **프리셋 재편 v2(블록 8종)는 이 초안기+선언 수렴에 흡수** — 별도 교정 슬라이스 불요 판정.
- **build() 단일 진입 통일 (Smith 0706 오전 방향 확정 — 행 17의 근본 수리)**: 저작 입구 2개(CLI --task/--preset vs DSL build())가 캐스팅을 다르게 해석하는 비대칭(표 17 실측: --real-provider 무-adapter가 work를 claude로 견인)을 해석기 수렴으로 제거 — ①build(preset=...) 지원(materialize_building_intent 재사용, 신규 조립기 금지 Rule 9) ②CLI는 build() 박막화 ③캐스팅 해석 = 에이전트-오브젝트 단일화 한 곳 ④--real-provider 의미 축소(스텁↔실물 전환 전용). --task/--preset 표면 언어는 유지(무마찰 헌장 — 표준 발주 한 줄 보존). **선행: erg6 랜딩(cli/onboard 표면 충돌 회피).**

### R. 부검 0706a 처방 채택 웨이브 (Smith 0706 "포함시키고 진행" — 전량 편입)
정본 = postmortem-deep-0706a-diagnosis-synthesis.md. **R7 집행(선언)**: 사건·과업 처분의 단일소스 = 본 문서 마스터 큐(§A~E·R) — 코퍼스/부검 문서는 입력 증거이지 처분 원장이 아니다(Case 6 충돌 해소: T10 0705b 처분은 §B 재판정 행이 지배). **R6 집행(관례)**: R행마다 착지 시 랜딩 커밋을 이 절에 追記 — 처방-착지 추적은 이 절이 원장이다. 순서 판단(COO): 병렬 = R1(parents[N] 정체성 가드+레지스트리 체커) · R4(어댑터 오류 분류+타임스탬프 보존) · R5+R8(부재주장 도메인 라벨 의무+거짓 'git 없음' 자기제한 제거 — 규율 계열 합본). **R3 최우선 격상(0706 오후 실측: erg6·cpath 수술 2연속 무유서 사망 = Case 9 자율운행 반복 위협 — R3가 없어 레인이 조용히 동결)** — 수신-후-무응답 loud HOLD+증거포착을 다음 walker 슬라이스 최상단으로. **cpath 수술은 레인 2연속 동결로 COO-직접 전환(위임 'ex walker', 픽스처 게이트 기랜딩)**. 이후 **직렬(walker_kernel 충돌)** = R2(carry 공용헬퍼+전채널 체커+remint 5좌표 감사 — 푸구 실측 갭 포함) · R3(팬-이음새 driver-사망 증거 포착+수신-후-무응답 loud HOLD, Case 9 선행). 문서-측 = R6(처방-착지 추적) · R7(사건 처분 단일소스 = 마스터 큐 선언). 별도 소형 = R9(모델-레인 규율 정합화: discipline:model-lane-matching 선언을 0705/0706 실정책과 일치시키기 — 부검이 표면화한 선언-정책 충돌).

**착지 원장(R6 집행, 0706 야간 세션 追記)**:
- **graphdecl-fix(발주표면 결함 2종) 착지 = 612abed3** — ①proposal 파일 work/ 배치+체커 인지(vessel 주차 소멸) ②model_ref 생략 시 어댑터 default 상속(선언층+노드층). 5라운드 종료선 절단(6번째 reroute = 메타류 기각), 변이 2종 RED, 스윕 50. **잔여 이관**: 표17 캐스팅-해석 격자의 일반해 → build-unify(#12). **만료태그 첫 폐기 집행**: "output-root는 반드시 ~/.brick" 우회 규칙 만료 — 이후 발주는 repo-안 output-root 허용.
- **--land 잠금 버그 수리 = 0123690f** — 비동기화 1호 도그푸드에서 EXIT 트랩의 빈-디렉토리 rmdir가 로그 포인터 때문에 조용히 실패 → 2호가 stale lock 거부. 포인터 선삭제로 수리, 2호(612abed3 랜딩)에서 해제 검증.
- **난이도-비례 캐스팅 독트린(Smith 0706 야간)**: 단순·정직·중간=codex / 복잡·얽힘=푸구+페이블 work(또는 dev fan 분할) — 싼 두뇌의 절약분이 QA 라운드로 역류한다(graphdecl-fix 5라운드가 실측 근거). work 레인 fable5 금지 해제(어려움-비례). 줄이기 웨이브 2기가 1호 적용. 소형 후속: model-lane 규율 문서에 티어 행 추가.
- **R9 착지 = db3a17a7**(r9-modellane-0706e) — 모델-레인 선언 정합 + 신설 게이트 프로파일(스윕 47→48). 게이트: 포커스 3프로파일 green + 변이 2종 RED(조항 제거·낡은 금지 재삽입) + 격리 --all 48. 원장은 evidence_incomplete(수취 장부 부재 — T10 클래스)로 종결 포기, 산출은 WIP 앵커에서 고아-수확 랜딩. QA 잔여 관찰(리터럴 핀 패러프레이즈 회피 가능성) = 강화 후보.
- **cpath ⑤ 착지 = 7bacb772 첫 머지**(cpath-mirror-0706c) — concern-path 처분 미러(공유 헬퍼 + 시퀀스 재사용), F-C1/C2/C3 GREEN 플립 + F-R 유지. 변이 3중 RED(gate-seq 사이트=F-R1 패리티 / concern 사이트 #4·#6=선언 리터럴). 강화 후보: rollback 짝 사이트(#3/#5/#7) 무음 중화. P2 직렬 다음 = R2.
- **fugupacket(packet 재성형 A안) 착지 = 7bacb772 둘째 머지** — sakana 와이어만 경로 라벨 불투명화, 신설 sakana_wire_packet 프로파일(스윕 49). 변이 RED + **라이브 A/B: 경로 라벨 재구성 → BLOCK(451) / 재성형 형태 → PASS**(필터 활성·경로 민감 확정). 현장 증명 = fugu-fieldprobe-0706n 발사(첫 실전 푸구 디스패치). 부수 갭: claude-local 유서 stdout 무발췌(R4 후속 후보).
- **--land/--ship 비동기화 착지 = 20410768**(COO-직접, Smith 야간 지시) — 기본 비동기(즉시 리턴+로그+RESULT 줄+Slack 벨+동시 잠금), 도그푸드 1호가 위 7bacb772 랜딩. 인체공학 표 14 계열.
- **checker-audit-0706a 완주·원장 complete** — 체커 53파일·프로파일 47 전수: **은퇴 후보 0 · 고아 0** · 재설계 후보 1(check_bounded_agent_proposed_routing_loop0.py의 시간-픽스처 — 벽시계 클래스 잔존, 줄이기 웨이브 감) · 정리 후보(낡은 주석/인용 — EI 반증으로 축소: 표적은 생존) · 픽스처 헬퍼 중복 1쌍(발산형 — 동일 불변식 아님 판정). 기계-규칙 자산은 건강 — 줄이기의 실표적은 사람-규칙(만료태그)과 시간-픽스처 1건.
- **레인 스로틀 실측(0706 야간)**: fable5 xhigh 공격QA 동시 3레인 → 밤 후반 rc=1 연쇄(직후 pong 정상 = 일시 스로틀). 교정 규율 = fable5 QA 동시 1~2레인 시차 발주.

**착지 원장(R6 집행, 0706 저녁 세션)**:
- **R3 착지 = ccb73b44** — 전 세션 사망 걸음(r3-fanwatch-0706a)의 work 산출을 orphan-harvest 게이트로 회수(driver0 green + 신규 fan-dispatch-child-timeout FIRE + 변이스펙 RED-CONFIRMED + 격리 --all 46). 계약 이탈 1건(D1 여유 마진 미구현 + 병렬 공유-데드라인 큐잉 엣지, 실패모드는 loud 과발화라 랜딩 후 후속) → **r3margin-0706e 걸음 중**. **+Smith 0706 저녁 추가 기준: FIRE 판정을 부하-무관(증거-형태)으로 근본 재설계 — 벽시계 상한·숫자 조정 금지**(인체공학 표 19). work 1차 반환 실물은 생산측 마진(+30s 플로어)은 충족했으나 FIRE는 여전히 벽시계(1.85s) — 게이트에서 이 기준으로 판정, 미충족분은 협착 재파견. 랜딩 직후 라이브 스윕에서 preset 완주 fixture(engine-feature-hard) 간헐 agent_incomplete 1회(격리 green — 타이밍 민감, r3margin 랜딩 후 재검).
- **R1 재파견 = r1identity-0706b 걸음 중** — 1차(r1identity-0706a)는 wheel 설치 트리에서 정체성 가드가 brick --help를 죽이는 결함(wheel_smoke RED 실측) + 신설 체커 프로파일 미등재로 NEEDS-OPERATOR. 재파견 계약 = 소스/설치 2모드 가드 + 프로파일 실등재.
- **R5+R8 재파견 = r5r8domain-0706b 완주(frontier=complete), COO 게이트 대기** — 1차(r5r8domain-0706a)는 조항 제거 변이 rc=0 = VACUOUS. 재파견 계약 = 조항을 체커가 기계로 무는 실게이트(조항제거→RED가 종료선).
- **R4 갭 2종 발견(0706 저녁 실측) → fugu451obit-0706e 걸음 중** — ①`--json` 모드에선 provider 실제 에러가 stdout JSONL에 남는데 유서 excerpt는 stderr 소음만 실림(사인 은폐) + 451이 classification=unknown ②걷는 빌딩 vessel엔 유서 full-write가 자기 산출물 때문에 거부되어 partial-write-risk 마커만 남음(raw/adapter-error.jsonl 부재). 계약 = content_policy 분류 + stdout 발췌 + 걷는-vessel full 유서 + fugu-rootcause-0706.md 정정 절(D4).
- **푸구 사인 정정(실측 확정)**: 도구 제거 -c 수리는 0624 기랜딩(e4466b2b)이었고, 실사인 = **Sakana API가 walker 발주 packet을 HTTP 451(content policy)로 차단** — 작은/무해/66KB 프롬프트 통과, 19KB 실packet만 재현(크기 아닌 내용·조합). 어댑터 스택 자체는 pong 실반환으로 green. **조사 완결(sonnet 서브에이전트, 프로브 9발·재현성 확정)**: 필터는 결정적이고, 최소 방아쇠 = "자격증명/세션 저장금지 지시문" + **`agent/prompts/dev.md`류 역할-프롬프트 파일 경로의 의미**가 한 JSON 구간에 결합될 때(무해 경로 `notes/readme.md`로 바꾸면 통과 — 경로 존재가 아닌 의미 반응). 정황: Anthropic 7/1 신형 anti-jailbreak 방어 배치(6/24 작동↔7/6 차단 사이) — Fugu 라우팅 풀이 proprietary라 인과 미확정. **후속 빌딩 후보(fugu451obit 랜딩 후): packet 재성형 — wire packet의 `agent/prompts/*` 경로를 불투명 ref로 치환(회피 가능성 높음, 단 로컬 증거에는 ref→경로 매핑 보존해 fault attribution 유지)**. 푸구 캐스팅 보류 유지, 슬롯 되돌리기·Sakana 문의는 Smith 판단 대기.

### D. 엔진 이월 (Smith 게이트 / 불가침면)
- ~~t7b replay 다중화~~ → **수리 랜딩 + 라이브 도그푸드 완성(0706)** — 수술 머지 c59d1745(A방향 정합 미러: reroute 미러가 라이브-처분과 동일 채택 경로 재사용 + 시퀀스 재사용→세대 간 reroute_ref 문자열 패리티, forward 미러 시퀀스 롤백, 미러 예산고갈 loud, 무검사 홀드 6사이트 loud-거부). 게이트 = RED→GREEN 4쌍 플립 실증(9a65a814 기준선 red-pin → 전원 GREEN) + 변이-RED(시퀀스 재사용 제거→패리티 즉발) + 프로파일 편입(building-automation) + --all 45. **도그푸드: reroute×4로 봉쇄됐던 설계 vessel 자신이 수리된 replay로 building_finished** — 0705 봉쇄 클래스 라이브 사망 확인. 다단 홀드 운영의 전제 조건 충족.
- ~~헌법 개정 비준~~ → **Smith 0706 비준 집행 완료** — BRICK-CONSTITUTION.md 0706 개정(3축 절·진단 5단 ⑤: "품질+성공 판정 권한은 Smith가 배분한다(기본 소재: 사람)").
- ~~bundle10 wheel 패키징 — Smith Option A/B 결정 대기~~ → **해소(0706 저녁 원장 정리)**: 0706 오전 위임 하 COO 판정으로 **Option B 채택·랜딩 완료**(§마스터 큐 서두 위임 절에 기록, wheelsmoke-hygiene 592df226까지 후속 랜딩, wheel_smoke 체커 가동 중 — 실증: 0706 저녁 R1 wheel-설치 결함을 이 체커가 적발). 반전 경로(A 폴백)는 예약 유지. 이 행이 갱신 안 된 채 남아 0706 저녁 "결정 대기" 오보 1회 유발 — 낡은 행 정리.
- 0702 결함가족 ②(자기잠금) · route policy concern 하위분류(A+ W1 인접) — 0706 Smith 질의 접수, 설명 보고됨. 자기잠금 규범 근거는 Rule 11(기비준), 시공 스코프는 t7b 설계 슬라이스 D5가 결합/분리를 판정.

### E. 무해 잔류 → **전량 원장 마감(0706 오전, Smith "재개 가능한 건 재개해서 써라" 집행)**
재개-가치 감정 후 처분: **7기 전원 `frontier=complete` 마감** — 11B v1(reroute×2+stop = **F-S 픽스처 모양의 라이브 재현, 미러 2차 실증**) · 11B v2 · W1-S1 · expand-dsl-0706a · erg4a·W2a(낡은-트리 무효) · 부검 fleet. **T10 0705b만 회생 불능 종결**: 정정 기록(raw:operator-correction:01) 후에도 correction_ineffective — 반환5>수취0(타 빌딩 스텝 포함)의 음의 갭은 위조-인접 형상이라 t7-recovery가 설계대로 거부(fail-closed 정당). 완주 스탬프는 fresh 0705c만 유효(저우선). **0705 봉쇄 5기 전부 해소.**

#### (구 E절 기록 — 마감 전 상태)
- 주차 3기(t1s2v3·wsallow·engine-smalls) — 대체·수확 완료. fresh 불요.
- 부검 fleet v2 vessel(link_paused) — 산출 회수 완료.
- **11B v2 vessel**(bundle11b-walkeradj-0705b, link_paused/worker 진입 전 COO 처분 대기) — v1 랜딩으로 대체, design 산출은 C절 후속 슬라이스에 수확. forward 금지(중복 시공 재개됨).
- erg3-fastfix-probe 앵커(4c35bfcb) — erg3 정식 산출(D2 상위 구현)로 대체된 부분 프로브.
- 혼합 회수 앵커 57b4fc63(refs/brick/wip/erg3-11b-mixed-recovery-0706) — 랜딩 완료로 사료화(provenance 보존).
- **낡은-트리 무효 vessel 3기(0706, 인체공학 표 16 사건)**: erg4-slice4-0706a(design 홀드 폐기) · wheelsmoke-hygiene-0706a(대상 파일 부재 트리에서 완주 — 산출 무효) · aplus-w2-manifest-0706a(design 홀드 폐기) — pipx CLI가 ~/BRICK(7/4 트리)을 걸었다. 전부 forward 금지. 0706b 재발주로 대체.

## 무마찰 발주 — 가중치→그래프 + 런처 파이썬 소멸 (Smith 0706 지시 등재, 회고 결론)

**Smith가 원하는 것**: AI(COO)가 업무를 받으면 그 가중치(위험·크기·분할가능성)에 따라 그래프를
바로, 편하게 그린다. 운영자는 "무슨 일인지"만 말하고 그래프 모양·캐스팅·게이트·경로는 표면이
채운다. **손으로 파이썬 런처를 짜는 관행을 아예 없애고, 전 발주를 기계(CLI/선언 표면)에 넣고
돌리는 것 — 이것이 이 기능의 골이다.** 편의가 아니라 실수 클래스 전체의 발생-지점 제거다.

**근거 1 — 0705 심야 회고(실수 최대 발생원)**: 그날 COO를 무너뜨린 건 그래프 판단이 아니라
손 조립의 부스러기였다 — 확장 조각 write_scope 오배치(지피티 FATAL), proposal 잔해(스윕 3회
차단), 캐스팅 철자(claude: vs model:claude:), 프리셋 접두어 누락, 처분 상대경로 유령 봉쇄,
공허 변이-RED 오독, cwd 리셋 발사 실패 2회. 판단은 옳았고 손이 미끄러졌으며, 그 누적 피로가
세션 도구 호출까지 파손시켜 인계로 끝났다. **CLI 한 줄로 나간 발주(erg1b·erg2·부검·v2b)는
무사고 — 파이썬 런처를 쓴 발주만 미끄러졌다.** 손 런처 = 도그푸드 실패 신호.

**근거 2 — 0706 새벽 COO 실측(t7b 발주, 이 절 등재 직전의 산 증거)**: t7b 설계 슬라이스
(read-only, 4노드)를 발주한 0706 COO의 직접 의견:
- 그래프 모양 판단은 수 초였다. 발사에는 도구호출 6회+시그니처 고고학이 들었다 —
  **판단:조립 비용 ≈ 1:10.**
- 공개 진입점 `support.operator.build`가 `(*args, **kwargs)` 래퍼(독스트링 공백)라 시그니처를
  소스에서 읽어야 했고, one-call `build()`가 `task=goal`(한 줄)로 접어 전문 task 반입이 불가함을
  발견해, 결국 **assemble→persist_proposed_building_graph→run_goal_approve_entry에
  밑줄-프라이빗 헬퍼(`_build_output_root`/`_build_proposal_root`)까지 임포트하는 내부 미러링**으로
  도망쳤다. COO가 프라이빗 표면에 손대야 발사가 되는 것 자체가 갭의 리터럴 증거다.
- CLI 실측 갭(인체공학 표 15): 커스텀 fan 모양 / per-node 위험-비례 캐스팅(**0705 모델정책이
  CLI로 표현 불가**) / per-node work_statement(task.md 미주입 규율상 필수인데 프리셋 materializer는
  헤딩 3종만 스캔) / source_facts / 확장 조각 무경로.
- 중요한 반전: 나를 CLI 밖으로 민 건 게으름이 아니라 **규율**이었다(전문 task·인라인 계약·
  위험-비례 승격 전부 각인된 규칙). 해법은 규율을 버리는 게 아니라 **표면이 규율-수준 입력을
  받는 것**이다.

**즉 필요한 것**:
- 운영자는 업무·가중치만 선언 → 표면이 그래프 초안(노드 KIND 체인·fan 폭·QA 렌즈 수·게이트
  배치)을 그린다
- 캐스팅(모델·effort)은 위험-비례 자동(0705 모델정책 내장 — 엔진인접이면 QA fable5 등) —
  철자로 안 막힘
- 프리셋·조각·경로·proposal 정리는 표면이 처리 — 손 부스러기 0
- 운영자에게 남는 건 오직 판단: 이 초안이 맞나, 게이트 어디, 종료선 뭐냐

**통합 재료 (이미 흩어져 존재 — 이 절이 하나로 묶음)**: building-sizing-method(방법) ·
expand()/build()/fan()(표면) · 프리셋 블록 v2(어휘) · 질문-우선 진입(규율) · 인체공학
웨이브(손 부스러기 흡수). 새로 다 만드는 게 아니라 흩어진 조각들의 통합·반자동화다.

**경계**: Rule 4(축 보존 최소 그래프)가 상위법 — 자동 초안도 익숙한 프리셋이 아니라 축 보존
최소형. 초안은 후보일 뿐 발주 확정은 운영자 판단(질문-우선 진입 규율 유지). 스케줄러·자동발사
금지(Rule 3), 신규 엔진·2차 생산자 아님(Rule 9) — CLI/선언 표면의 확장이다.

**판정선**: "런처 파이썬이 사라지는 날" = 인체공학 웨이브 완성. 그 전까지 파이썬 런처가 필요한
발주가 나오면 그것 자체가 표면 표현력 갭의 실측이므로 인체공학 표에 행 추가가 관례다(0703
"COO 사고 한계 = 공식 경로 표현력 한계 = 도그푸드 사각" 재확인).

**우선순위**: C그룹. 인체공학 슬라이스들(발사·admission·재개·게이트필수·expand)이 랜딩할수록
CLI 커버리지가 넓어지고, 전 발주가 CLI/선언 표면으로 나가는 순간 달성.
