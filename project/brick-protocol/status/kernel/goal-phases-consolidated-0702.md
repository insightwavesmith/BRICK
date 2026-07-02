# 운영 골 페이즈 통합 (0702 정본 — Smith·COO 합의 프레임)

Status: support evidence only. 운영 순서의 정본. 골 오브 레코드 자체는
customer-ready-goal-phases-0629.md(+GOAL/)가 소유 — 이 문서는 그걸 향해 가는
워크스트림들의 통합 순서표다. 상태값은 0702 기준 실측.

## 최상위 (불변)

**골 오브 레코드 = P8 도그푸드**: 고객이 설치 → LLM 연결 → `make X` → 공식 build 경로가
Brick/Agent/Link로 일을 선언·수행 → 아티팩트+증거 반환. 최종 증명은 그 고객 경로로
브릭이 제 일을 하는 것. 아래 GP0~GP3은 전부 이걸 향한 순서다.

## GP0 — 엔진 신뢰 기반: "빌딩이 안 죽는 엔진" (진행 중, 최우선)

오늘(0702) 도그푸딩이 실측으로 캐낸 엔진 결함 수리 묶음. 죽는 엔진 위에선 어떤 페이즈도 못 달린다.

| 항목 | 상태 |
|---|---|
| reroute 기록자 (raw manifest 등록 누락) | ✅ 랜딩 `17d6702` (3중 게이트) |
| 슬랙 벨(goal-runs 루트) + 구조도 fan 렌더링 | ✅ 랜딩 `fe6ccb5` (3중 게이트) — 벨 라이브 실증은 진행 중 빌딩으로 |
| **워크트리 reaper liveness + 미완처분 보존 + 픽스처 루트 격리** | 🔄 빌딩 진행 중 — **이것 전까지 병행 발사·체커 실행 전면 금지** |
| one-call build() 인자 통과 (output_root/write_scope/gates) | ⏸ reaper에 블록 (2회 사망·작업물 유실) — 랜딩 시 "정식 원콜=벨 기본" 완성 |
| 그래프 admission-gate 라이브 배선 (Rule 8 후반) | 대기 (follow-on 4번째 항목, 0701 처분) |

완료 기준: 발사→완주→벨→작업물 회수 전 과정이 병행 상황에서도 안전.

## GP1 — 운영면 정비: 스킬·문서·헌법 (배치 1~6 골, Smith 0702 비준)

| 배치 | 내용 | 상태 |
|---|---|---|
| 1 | 스킬 거짓말 핫픽스 + 발사부채 문서화 | ✅ `d29a1ac` |
| 2 | one-call 인자 통과 | ⏸ GP0 reaper에 블록 (동일 항목) |
| 3 | 사본 드리프트 + live 스킬 sync + APPLY-LIST 재작성 | ✅ `c7d7710` — **Smith 터미널 삭제 6줄 대기** |
| 4 | 헌법 한 화면 추출 (BRICK-CONSTITUTION.md) | 초안 `13730f4` — **Smith 비준 대기** |
| 5 | 스킬 리사이즈 본편 (2,237→~1,590줄, pin맵 59 준수) | 대기 — GP0 랜딩 후 착수 |
| 6 | status/kernel 문서 ~108개 아카이브 | 대기 — 배치5 뒤 |

측정 기반: skill-doc-resize-audit-0702.md (24레인 감사). 부속 완료: inspector 레인
기본 claude·sonnet·xhigh 재선언(`b956a17`, pin 동반 갱신).

## GP2 — 도그푸딩 크리티컬 패스 (골 오브 레코드 본대)

| 항목 | 상태 |
|---|---|
| 온보딩 Phase 0~1 (provider registry/add, sink add, Slack·Dashboard) | ✅ 랜딩 (소넷세션, `dab4acb`/`60863f8`) |
| **발사 인체공학 3종** — 결과 요약 패킷 / `llm=` 별칭 / `returns=` 계약 주입 (Smith 0702 채택) | 대기 — 배치6 뒤 최우선 |
| 온보딩 잔여 Phase 2~3 (대화형 등록/모델선택) | 대기 |
| 갓모듈 소형 안전묶음 §4-5(registry phantom)/§4-8(게이트 6스텝)/§4-9(프로브 안전화) | ✅ 랜딩 (소넷세션 작업 B/C/D) |
| §4-6 anti-toothless 가드 구현 (서베이로 리스크 소멸 — 걸릴 프로파일 1개) | 대기 (소형) |
| §4-7 fixture vessel 비재진입 격리 | 대기 (소형, pin-aware) |
| P7 프레시머신 증명 → P8 바운디드 도그푸드 프로브 | 대기 — PASS 기준 문서 존재(0629), 프로브는 갭 추출기 |

## GP3 — 아키텍처 청소: 갓모듈 대형 분해 (P8 프로브 후 윈도우)

정본: godmodule-checker-cleanup-synthesis-0701.md §4. off-critical-path 비준(0629) 유지.

| 항목 | 상태/전제 |
|---|---|
| §4-3 routing_loop0 클러스터맵 | ✅ 완료 (routing-loop0-clustermap-0702.md — C1/C15 추출가능, C2-C14는 check() 캐빙 문제) |
| 전제 하네스: mutation-RED 프레임워크 | 미구축 (§3 확인) — 대형 스플릿 전 필수 |
| 전제 조사: case_runners vs C1 공유기계 비교 1레인 | 대기 (클러스터맵 not_proven 해소, 항목2 설계 입력) |
| §4-1 kernel_checks.py(10,141) 도메인 분해 | 대기 |
| §4-2 case_runners.py(8,512) 분해 | 대기 (공유기계 비교 뒤) |
| §4-4 체커다이어트 완주 (87라벨 + 고아 5종 + 라벨별 RED probe) | 대기 |
| `_run_dynamic_graph_walker` | **불가침** (P4 resume-preservation 증명 전까지 HOLD) |

## 순서 원칙 (충돌 시 이 순서)

1. **GP0 > 전부** — 죽는 엔진 위에 아무것도 못 짓는다.
2. GP1 배치5·6은 GP2와 병행 가능 (파일 비충돌) — 단 빌딩·체커 직렬 규칙은 GP0 랜딩까지 유지.
3. **GP3은 P8 프로브 뒤** — 10k줄 이동 중 프로브를 돌리면 갭 추출 신호가 오염된다.
4. Smith 게이트 3건: 헌법 비준 / live 삭제 6줄 / P8 프로브 진입 결정.

## 현재 위치 (0702)

GP0 reaper 빌딩 진행 중(침묵 유지) → 랜딩·검증·머지 → batch-2 재발사(GP0 마감) →
GP1 배치5 → 배치6 → GP2 온보딩 잔여+소형 2건 → P7/P8 → GP3.

## 미래 후보 (선언 원칙 보존 확장)

- **선언된 팬의 조건부 개방** (Smith·COO 0702 합의): 팬 가지 N개를 선언+게이트로 잠그고
  HOLD 처분에서 몇 개를 열지(forward) 접을지(stop) 정한다 — resume 그래프 확장 없이
  병렬 수 유연성 확보. 근사형은 현 엔진으로 가능(per-node coo-gate + stop 처분 실존),
  완성형은 fan-out 진입 edge 게이트 소형 확장. GP3 이후 또는 필요 시 승격.
