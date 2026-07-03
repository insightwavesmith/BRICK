# 운영 골 페이즈 통합 (0702 정본 — Smith·COO 합의 프레임, 0703 밤 정리)

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
| §4-4 체커다이어트 완주 (87라벨 + 고아 5종 + 라벨별 RED probe) | 대기 |
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

다음 순서:
1. **슬라이스 5 v2(brick_cli + mcp_connect) 걷는 중** — 이후 6~9 직렬(chat_session+redaction
   → dashboard → adapter_error → agent_adapter)
2. 후속 조사(소형): 렌즈 구형 주소 저작 시 반려-재시도 루프 미발화(link_paused로 정지)의
   기전 — Part4 D1의 접수 지점이 렌즈 반환 경로를 덮는지
3. 틈새: P8 신뢰성 반복 프로브(분해 창 종료 후) / #23 레거시 정리(903MB worktrees·3주치
   vessels·inbox — **WIP 앵커 구제 선행**: 미머지 앵커 464105cf(관측측 v2, 참고용)·
   link-part4-r6(머지됨, 정리 가능))

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
| **증명-예산 HOLD 경로 WIP 앵커 미보존**(0704 실측 — 렌즈-정지는 보존) — 미완 처분 보존 원칙 위반 | 엔진 갭, 소형 |
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
