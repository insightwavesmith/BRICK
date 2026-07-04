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
(표준 ADDR 오탐 폐쇄, 17dirty/12clean — T1 2단계 선결 해소). **S4 걷는 중(최종 조각)** —
S2 실물 좌표·잔해 방지 조항 반영 계약. 교훈 등재: 픽스처-실행 발주는 project/ 잔해
정리를 계약에 명시(S2 실측).

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

## 백로그 통합 (소형·주시·대기)

| 항목 | 분류 |
|---|---|
| 그래프 admission-gate 라이브 배선 (Rule 8 후반) | GP0 잔여, 소형 |
| P8 신뢰성 반복 샘플 | GP2 후속 |
| #23 레거시 정리 (앵커 구제 선행) / claude 세션 잔존 / gemini 세션 미조사 | 틈새 |
| mutation_red 의미론 강화(red_rc≠0 요구 — 형검사→집행 승격 설계논점) | gp3-threshold 후속 1 |
| 세션연속성 체커에 approval_policy="never" resume-argv pin 부재 | gp3-threshold 후속 2, 소형 pin |
| reason_refs bare 산문 허용 vs related_boundary_refs 산문 거부 — 정합 논점 | gp3-threshold 후속 3 |
| QA 산문 픽스처 세션ID 리터럴('sess-…') 재발 시 레인 계약 지침 승격 | gp3-threshold 후속 4 |
| 라이브 --all vs 걷는 빌딩 보고패킷 경합(rc=1이면 착지 직후 확인 후 재실행) | 운영 규칙 등재 |
| ~~증명-예산 HOLD 경로 WIP 앵커 미보존~~ → **종결(5a5663f7 Smith 확정 — 수리 불요: diff 없음이라 보존 대상 자체가 없음)**. temp_dir 앵커도 설계 예외 확정 — T7 엔진 수리 잔여 0 | 종결 |
| llm= D5/D6(동시사용 거부) / effort 기록 / #18 부검 프리셋 / #20 write_scope 캐스케이드 | 소형 대기 |
| claude 레인 SIGTERM(143) 2건 — 3회째면 원인파악 빌딩 | 주시 |
| **Smith 게이트**: coo·dev 오브젝트 처분(이월) | Smith 대기 |
| ~~onboard.py/cli.py 미커밋 diff~~ → ✅ 랜딩 f7b11848 (Smith 다른 창의 Claude 저작 — gemini 키 대화형 접수+gh doctor행 제거. COO가 diff 정독·컴파일·4케이스 격리 재실행 후 커밋, service_tier 선례) | 종결 |

## 순서 원칙 (충돌 시 이 순서)

1. Smith 명시 지시 > 상설 골 훅.
2. GP3 분해 중 P8 프로브 금지(10k줄 이동 중 갭 신호 오염) — 신뢰성 반복은 분해 레인이
   걷지 않는 창에서.
3. 발주 크기: 토큰 효율이 아니라 "업무를 종료시킬 수 있는가"로 사이징, 파일 비충돌 병행.
4. 레인-불가능 수용 기준은 COO 게이트 항목으로 분리, 기계 게이트는 proof_obligations 선언.

## 미래 후보 (선언 원칙 보존 확장)

- **선언된 팬의 조건부 개방** (Smith·COO 0702 합의): 팬 가지 N개를 선언+게이트로 잠그고
  HOLD 처분에서 몇 개를 열지(forward) 접을지(stop) 정한다 — resume 그래프 확장 없이
  병렬 수 유연성 확보. 근사형은 현 엔진으로 가능(per-node coo-gate + stop 처분 실존),
  완성형은 fan-out 진입 edge 게이트 소형 확장. GP3 이후 또는 필요 시 승격.
