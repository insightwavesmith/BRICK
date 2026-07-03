# 운영 골 페이즈 통합 (0702 정본 — Smith·COO 합의 프레임)

Status: support evidence only. 운영 순서의 정본. 골 오브 레코드 자체는
customer-ready-goal-phases-0629.md(+GOAL/)가 소유 — 이 문서는 그걸 향해 가는
워크스트림들의 통합 순서표다. 상태값은 0702 기준 실측.

## 최상위 (불변)

**골 오브 레코드 = P8 도그푸드**: 고객이 설치 → LLM 연결 → `make X` → 공식 build 경로가
Brick/Agent/Link로 일을 선언·수행 → 아티팩트+증거 반환. 최종 증명은 그 고객 경로로
브릭이 제 일을 하는 것. 아래 GP0~GP3은 전부 이걸 향한 순서다.

## GP0 — 엔진 신뢰 기반: "빌딩이 안 죽는 엔진" (진행 중, 최우선)

오늘(0702) 도그푸딩이 실측으로 캐낸 엔진 결함 수리 묶음. **admission-gate 배선 제외 전부 랜딩 — GP0 실질 완성.**

| 항목 | 상태 |
|---|---|
| reroute 기록자 (raw manifest 등록 누락) | ✅ 랜딩 `17d6702` (3중 게이트) |
| 슬랙 벨(goal-runs 루트) + 구조도 fan 렌더링 | ✅ 랜딩 `fe6ccb5` (3중 게이트) — 벨 라이브 실증은 진행 중 빌딩으로 |
| **워크트리 reaper liveness + 미완처분 보존 + 픽스처 루트 격리** | ✅ 랜딩 `bec5b16`/`58d1ac0` (w1-stale-liveness 행동변이 게이트) — 병행 금지 임시규칙 해제 |
| one-call build() 인자 통과 (output_root/write_scope/gates) | ✅ 랜딩 `01d8262`/`fdc2308` — vessel 발사=벨 표준 가동 (배치5 빌딩으로 라이브 실증, 슬랙 17행) |
| 그래프 admission-gate 라이브 배선 (Rule 8 후반) | 대기 (follow-on 4번째 항목, 0701 처분) |

완료 기준: 발사→완주→벨→작업물 회수 전 과정이 병행 상황에서도 안전.

## GP1 — 운영면 정비: 스킬·문서·헌법 (배치 1~6 골, Smith 0702 비준)

| 배치 | 내용 | 상태 |
|---|---|---|
| 1 | 스킬 거짓말 핫픽스 + 발사부채 문서화 | ✅ `d29a1ac` |
| 2 | one-call 인자 통과 | ✅ (GP0에서 랜딩) |
| 3 | 사본 드리프트 + live 스킬 sync + APPLY-LIST 재작성 | ✅ `c7d7710` + 삭제 6건 집행 `e63426c` |
| 4 | 헌법 한 화면 추출 (BRICK-CONSTITUTION.md) | ✅ **Smith 비준** `2d292fd` (단일출처·불변규칙만) |
| 5 | 스킬 리사이즈 본편 | ✅ 1부 빌딩 `8c60b82` + 2부 COO `7be307c` (2,237→2,125 — pin 보존 우선, 잔여 감량은 pin 이동 비용상 종료) |
| 6 | status/kernel 문서 아카이브 | ✅ `9fc9ebc` — 133건 archive/, 잔류 28, WIP 앵커 첫 실전 회수 |

측정 기반: skill-doc-resize-audit-0702.md (24레인 감사). 부속 완료: inspector 레인
기본 claude·sonnet·xhigh 재선언(`b956a17`) + 전 레인 모델 재선언(Smith 0702, `cf0fb03`/`dd445cc` — design/pm=opus·xhigh, qa=sonnet·xhigh, qa-lead/cto=codex·xhigh, pin 3사이트 동반).

## GP2 — 도그푸딩 크리티컬 패스 (골 오브 레코드 본대)

| 항목 | 상태 |
|---|---|
| 온보딩 Phase 0~1 (provider registry/add, sink add, Slack·Dashboard) | ✅ 랜딩 (소넷세션, `dab4acb`/`60863f8`) |
| **발사 인체공학 3종** — 결과 요약 패킷 / `llm=` 별칭 / `returns=` 계약 주입 | `returns=`✅랜딩 · `llm=`✅랜딩 `9eb30ad9`(v9 확정 4조각, 0703 새벽 — D5/D6 동시사용·심화는 후속 소형, 현재 동시사용은 llm= 우선 silent-override) · **결과 요약 패킷 ✅랜딩 `6afb1c0d`**(`summarize_building_result()` — 오늘 밤 첫 frontier=complete 완주, 갭 2건 v3 진행) — **인체공학 3종 완결** |
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
2. GP1 배치5·6은 GP2와 병행 가능 (파일 비충돌). 병행 직렬 규칙은 reaper 랜딩으로 해제됨.
3. **GP3은 P8 프로브 뒤** — 10k줄 이동 중 프로브를 돌리면 갭 추출 신호가 오염된다.
4. Smith 게이트 잔여 2건: P8 프로브 진입 결정 / coo·dev 오브젝트 처분(엔진 바인딩 이의 제기됨).

## 0702 심야 갱신 (COO 실측 — push ee5e3061 기준, 21개 태스크 중 12 완료)

**저녁 랜딩(GP0/GP1 마무리 + GP2 인체공학 완결)**
- AGENTS.md 리사이즈+법급 문구 복원, gemini 등록 완결(라이브 실증), 인체공학 llm=
  기반+returns 계약 스탬핑 부분 랜딩, compact DSL 기본예산(5) 스탬프(가짜 랜딩 1회
  반려 후 v2로 랜딩) — 전부 이전 갱신에 기록됨.
- **route-complete 부분 랜딩**(`bfbcad85`): 재진입 스텝 증거·yaml 부재 명시에러·정책
  provenance pin. 합성 무선언 e2e 픽스처만 잔여(→ #15).
- **부검 완결**(`f26e57bc`): 3축 판정 Link>Agent>Brick, 처방 후보 3, 첫 자동 수리
  재진입 실측. Smith 판정("축 분리가 브릭의 최대 장점") §6-0에 기록.
- **3축 개선 배치**(`f38d0074`/`4625e81f`): Brick축(closure 반환 계약에
  `deliverable_crosscheck` 필드 신설 — 엔진은 나르기만)·Agent축(qa.md/coo.md 표준
  공격 항목)·Link축(#17로 차후+조건부 설계 확정) 전부 자기 선언 표면에 배치.
- **returns-persistence 랜딩**(`dfc11ee0`): CLI 원문 전체 보존(`raw/agent-output-text.jsonl`)
  — 1차는 write_scope 조사 누락(COO 실수)으로 5라운드 허비, 새 8항목 템플릿으로 v2b 정공.
- **task.md 템플릿 8항목 확정**(`073a26fa`): Required Sources + Brick/Agent/Link
  Boundary 신설(오늘 두 사고 직접 겨냥) — write_scope 누락·해석 모호함 재발 방지.
- **PHASE 3 표준 진단 체크리스트 신설**(`5b69f872`): 홀드 마주치면 처분 전에 3축+엔진
  4갈래 질문 — 전부 0702 실제 사고 인용. 이후 홀드 2건에서 즉시 실전 적용 확인.
- **읽기 방법론 정정**(`ee5e3061`): `output_excerpt`는 의도적 600자 미리보기, 구조화
  필드(`observed_evidence` 등)는 원래 안 잘림 — "returns 절단" 진단 일부는 COO의
  읽기 오류였음을 정정(부검 §7).

**진행 중이던 빌딩 2 — 둘 다 착지 (0702 심야 정정)**
- `llm-alias-completion-0702a`: 착지. llm= 본편은 이후 main 기준 미랜딩으로 재확인되어
  v9(llm-alias-0702h)로 확정 4조각 재발주(0702 심야, 진행 중).
- `resume-corrupt-investigation-0702b`: **착지 — 기전 규명 완료.** step-output
  즉시쓰기 vs raw-return 걸음종료 일괄쓰기(별개 트랜잭션). 기전 정본(커밋됨):
  resume-defect-mechanisms-0702.md. 1차(-0702a)는 트리거 확정.

**오늘 발견한 엔진 결함 5종 (전부 태스크 등록, 처방 대기)**
1. **가짜 complete 무저지** — ✅ **랜딩 `00fcaa59`(0703, diff-reality-gate-0703b)**:
   write 필요 플랜 + complete + write_scope 내 diff 부재 → human_review_waiting
   (사유 fake_landing_write_scope_diff_absent), 커밋 없음, WIP 앵커 보존. read-only 면제.
   zero-supply 픽스처는 COO 1건 승인으로 새 의미론 이행. 명시 후속 2건: 노드별
   형제-가림 blind spot(빌딩 수준 판정이 v1 범위) / gitignored 쓰기 경로 엣지.
2. **resume 예산 미소비**(#15) — raise가 쓴 예산 주입 행을 재개 걸음이 안 읽음.
3. **처분 자기잠금**(#19) — 잘못된 종류 처분 시도가 거부되고도 원장에 남아 정정도
   재개도 막음. llm-alias에서 실측.
4. **resume 원장 불일치**(#21) — 트리거 확정(1차) + **기전 규명 완료(2차 착지, 0702 심야)**:
   step-output은 스텝종료 즉시쓰기, raw-return은 걸음종료 후 일괄쓰기 — 별개 트랜잭션.
   기전 정본(커밋됨, 레인 가독): resume-defect-mechanisms-0702.md. #15와 다른 코드 경로.
5. (소음) admission 체커 중첩 vessel 레이아웃 미인지(#14) — push 무영향, 백로그.

**엔진 개선 후보(설계만, 미착수)**
- write_scope 캐스케이드(#20): design의 candidate_file_changes를 work의 실제
  write_scope로 역산 — 오늘 예산 캐스케이드와 같은 모양. GP2 이후 순번.

## 0703 새벽 갱신 (COO 실측)

- **llm= v9 랜딩** `9eb30ad9`: 확정 4조각(D1 팩토리 kwarg / D2 bare만 / D3 정확히 ValueError /
  D4 단일출처 provider_registry.py:43). 빌딩 내 수리 루프 4라운드 — 1라운드에서 QA 2렌즈가
  D4 개명·금지된 D5 구현·pin 부재·kwarg 삼킴 버그를 적중(렌즈 아키텍처 첫 실전 검증),
  자동 재파견이 전부 수리. 최종 모양: llm=은 brick() 전용(agent()는 TypeError로 거부 —
  삼킴 버그 원천 제거). 5게이트 전 통과(변이-RED는 계약-살해 변이로 rc=1 실측;
  bare-약화 변이는 등가 변이로 판정 — QA의 "rc=1" 자기보고는 재현 안 됨, 불신 원칙 재확인).
  잔여 홀드(5라운드 재파견 제안)는 맹목-design 잔재로 판정, 의도적 방치.
- **레인 문서 전달 계약 각인** `9f69b064`/`bc0426d2`: 격리 워크트리에 untracked vessel이
  안 보여 design 2건이 봉쇄/발명(0702 심야 실측). 교정: 계약은 work_statement 인라인 +
  참고문서는 `source_facts=`(본문 프롬프트 탑재, 못 읽는 ref 조용히 스킵 주의) 또는 커밋된
  트리 경로. 스킬 양 사본+골 루프 프롬프트+기전 정본(resume-defect-mechanisms-0702.md) 반영.
- **resume 3결함 수리 랜딩** `2a085b90`: v1은 design 소스 봉쇄로 COO 정지→교정 재발주,
  v2가 2라운드로 착지. **D1/#15 완결**(raise 예산 브리지 — QA 행동 프로브 base+2 소비 실증
  + COO 변이-RED rc=1), **D3/#21 완결**(pre-resume 정합성 대조 `_require_return_frontier_consistency`,
  replay 채택 전 명시 거부 + claim_trace 실존 검사 — 처방 ② 그대로), **D2/#19 개선-부분**
  (리더 측 홀드-스코핑 랜딩; 잔여 갭 = 저작 경로 persist-before-validate — 무예산 타깃 raise가
  행을 남긴 뒤 에러, QA 실측). 게이트: 변이-RED 2종 COO 직접(rc=1/rc=1/복원 rc=0), 격리 --all 33/33.
- **D2/#19 완결** `42ad54b3`(d2-ledger-cleanliness-0703b): 공유 `resume_budget_recovery_decision()`
  추출(walker_resume.py:428)로 resume 걸음과 승인 저작이 **동일 판정 집합** — v1의 브리지-거부
  회귀가 구조적으로 소멸. 사전검사가 append 전 실행, 거부 시 `resume_budget_precheck_refused`+
  원장 무기록(byte-equality pin). **#15/#19/#21 resume 결함 3종 전부 종결.**
  빌딩 사건 2건 기록: ①v1에서 COO가 reroute-제안 홀드에 forward 오판 — forward는 제안 채택이
  아니라 선언경로 계속(빌딩이 그대로 닫힘, 무피해, 메모리 각인) ②v2 code-attack-qa 레인
  SIGTERM(143)으로 agent_incomplete — COO가 그 렌즈를 손으로 대행 후 게이트 통과.
- **#17 diff-실물 게이트 랜딩** `00fcaa59`(위 결함 1 참조) — 부검 처방 1이 기계가 됐다.
  d2·#17 병합(onboard.py 자동병합)의 통합 스윕 33/33 격리 확인 후 push.
- **주시 패턴**: claude 레인 SIGTERM(143) 2연속(d2 v2 code-qa, #17 v2 axis-qa — 둘 다 fan
  안 claude-local 렌즈, 3600s 타임아웃 추정). 3회째면 원인파악 빌딩 발주.

## 0703 오전 갱신 (COO 실측 — 골 루프 계속)

- **reroute 채택 홀드 기전 규명**(reroute-adoption-invest-0703a, 읽기 전용 조사):
  runtime mail은 reason_refs의 슬래시 포함 주소를 빌딩 work/step-outputs 밑 실존 파일로
  요구(fail-closed, 의도) — 오늘 홀드 전부가 레인의 불량 주소 3형(#fragment/bare file:line/
  문서경로) 때문. 판정: 엔진 결함 아님, 레인 산출 습관+COO 발주 문구가 원인. 처방 빌딩
  (reason-refs-address-shape-0703a) 진행 중. 사례 정본: reroute-adoption-hold-cases-0703.md.
- **#17 게이트 오발 수리 랜딩** `0882ca7b`: capability class 도입 — probe_write(QA 변이
  프로브)/read는 write-need에서 제외, product-write만 무diff 게이트 대상. 게이트 홀드가
  원장에 실기록돼 재관측과 일치. 오발은 랜딩 2시간 만에 도그푸드(읽기 전용 조사 빌딩)가 검출.
- **결과 요약 패킷 완결** `6afb1c0d`+`516204ed`(v2+v3): `summarize_building_result()` —
  COO 손 판독의 자동화. **발사 인체공학 3종 전부 완결.**
- **§4-6 이빨 가드 + §4-7 픽스처 재진입 격리 랜딩** `ed0e9139`(v2): 4중 구조적 삭제 증명
  (temp repo 동일성/temp 하위/실 project 무겹침/sentinel nonce+PID). v1의 env-flag 신뢰
  위험은 QA가 실삭제 재현으로 반려. 선언 갭: 가드 무력화 부정 pin(v3 진행 중).
- **crosscheck 오보고 3건 실측**(llm QA rc=1 주장 / 요약패킷 FIX2 / 체커인프라 FIX2 pin) —
  COO 5게이트가 전부 적발. "빌딩 자기보고 불신 — 게이트는 내 손으로" 원칙의 실증 축적.
- **쉬운 설명판 진행 기록**: goal-loop-progress-0702night-0703am.md (항목별 문제→해결→증거).
- **reason_refs 주소 계약 랜딩** `f73db797`: 5개 verdict/QA kind 계약+transition-concern에
  주소 규칙 각인 + mail-8 pin(불량 3형, 실존파일 셋업으로 형식-기반 거부 증명). 해석기 무접촉.
  **자동 재시공 루프 복구 완료.** 6라운드 진단(Smith 직감 적중): 본체는 ~3라운드에 완료,
  이후는 ①review 렌즈가 temp 없는 샌드박스에서 "--all green"을 구조적으로 증명 불가(매 라운드
  소음) ②QA의 메타-검증 요구 상승. 교훈: **계약에 명시적 종료선 + 렌즈별 환경-가능 증명 분담.**
- **세션ID 각인 사고 1건**(COO 문서 커밋 99dfaa64): 스코어보드 경로에 세션 UUID를 박아
  redaction 체커에 적발 — glob으로 교정(219bc7c3). 문서-only 커밋도 스윕 대상에 포함.
- **§4-7 부정 pin 랜딩** `47d412eb`: 가드 통째 무력화→self-test rc=1(COO 직접 변이) — v2의
  unpinned-safety 갭 봉합. 4라운드 same-family 루프는 COO stop-and-gate로 종결(repo-identity
  서브케이스 개별 격리는 종료선 밖 nit로 기록·수용).
- **온보딩 Phase 2-3 랜딩** `22a9080e`: 대화형 provider/모델 수집(TTY 게이트 호출부 소유,
  prompt_func 주입식) + llm= 별칭 단일출처 정합 + pin 5종. **종료선 계약 첫 적용 — 2라운드
  자가 완주(frontier=complete, 개입 0)**: 계약에 명시적 DONE-라인을 넣자 루프가 스스로 닫혔다.
  D3(MCP 기본값)은 반증 분기로 착지: 영구 등록의 실소비자는 고객 자신의 대화형 CLI 세션
  (조사 실측이 안 다룬 제3 소비자, idempotent+불훼손+--skip-plugin) — COO 초기 opt-in 기판정
  철회. **제품 기본값 논점은 Smith P8 전후 확인 항목으로 기록.** 별칭-폴백 분기 미pin은 nit.
- **P7 프레시머신 재증명 진행(0703 오전)**: ①빌딩 경유 1차 — 레인 샌드박스 외부 네트워크 차단 실측(DNS 불가 — fresh-clone 증명은 레인으로 구조적 불가, 0630 선례처럼 운영자 프로브가 정답) ②COO 운영자 프로브 2차 — clone(진짜 origin/main 0fc74a02)·uv sync·대화형 수집기+등록 전부 green, init은 정직 doctor 진단(gh auth 캐비앗), 공식 build 걸음 완주(work+closure). **실갭 1건 적중**: #17 게이트 홀드가 원장 기록까진 되는데 공식 처분 경로가 홀드 정체 미기록으로 fail-closed(onboard.py:3366) — 사람이 처분할 수단이 없어 고객이 갇힌다(P8 차단급). 수리 빌딩(gate-hold-disposal-fix-0703a) 걷는 중. P7 PASS 판정은 수리 후 재프로브에서.
- **밤샘 감사(39빌딩 3축 117콜, 별도 세션) 처방 채택안(0703 오후, Smith 검토 반영)**:
  공통 병 = "필드·배선은 있는데 어기면 실패하는 강제(bite)가 없다". 채택 순서 —
  P8 전: ①Link Part1(reason_refs 주소 문법을 접수 시점 검사 — agent/return_fact.py 순수함수.
  옛 원장 replay carve-out 결정 명시) ②Brick FixA/B(forbidden_paths 위반방향 게이트 +
  스킬 교정: 산문 불가침은 forbidden_paths 미러 의무화). P8 후: ③Link Part2(우편 보장주소
  concern_doc_ref — 보안표면, 공격리뷰 동반) ④Agent 증명 파이프라인(proof_obligations
  선언→support 실측→비교→게이트 — WRITE 파이프라인 복제).
  **Smith 확정 세부 2건**: (a) 증명 게이트는 별도 부착식이 아니라 기본 걸음의 선언-조건부
  (#17 모양 — 선언 없으면 무반응) (b) rc=1은 사람 HOLD가 아니라 예산 내 자동 재시공 우선,
  HOLD는 예산 소진 후. **(c) Link Part1.5 추가(Smith 지적, 코드 실측 확인)**: 재시공 우편이
  concern 문서를 이미 읽고도(walker_runtime_mail.py:190) 주소만 부친다("ADDRESSES ONLY" :180)
  — QA 기 저작 요약을 기록-원장-파생+safe_source_fact_body 플로어+참고용 표기 3조건으로
  인라인(정본은 주소 유지). Smith 정책 대기: reroute 처분 re_instruction 필수화(FixC).
- **게이트 홀드 처분 사슬 완성(0703 오후)** — P7이 캔 갭의 수리 3부작 종결:
  v1 `09fa10c4`(홀드에 처분 정체 탑재) → v2(관측측 접근 — COO 라이브 프로브 실패로 미머지 반려,
  앵커 464105cf. 기전: forward→재걸음→무diff 그대로→게이트 재발화 무한) → **v3 `ca3b34c0`
  (설계 교정: 게이트 자신이 처분을 소비 — 재발화 억제)**. COO 라이브 프로브: P7 vessel이
  기존 처분 소비로 complete 판정+재관측 안정. 변이 rc=1 pin(w1-fake-no-diff-forward)·스윕 34/34.
  고객 사이클(무diff 완공→HOLD→사람 도장→완주)이 통째로 성립.
- **P7 PASS(0703 14:13)** — 프레시 clone(3f45fd35) 전 사이클: 설치→대화형 온보딩→공식 발주→
  걸음 완주→게이트 HOLD(설계 발화)→사람 forward→**frontier=complete**. 정본: p7-fresh-proof-0703.md
  (캐비앗: codex 자격 복사·gh auth transcript 미증명·레인 샌드박스 네트워크 차단 실측).
- **audit-0703 4페이즈 실행(Smith 승인, 0703 오후)** — 문제정의 정본: status/kernel/audit-0703/.
  Phase 0 ✅(가이드 정본화 9c5930b6 + FixB 스킬 교정 b81e5265 — COO 직접).
  **Phase 1 ✅ 랜딩** `06468178`(link-delivery-0703a, 다이어트 그래프 2라운드 자가완주):
  접수 문법(불량3형 즉시 반려)+보장주소(concern_doc_ref)+깨진 인용 검역(undelivered_citation_refs)
  +종이2 동봉(라우팅은 종이1만, 엔진 무선별, 스키마 무변경). 세션이어짐 선결 조사도 COO 프로브로
  완결(session-continuity-mechanism-0703.md — 직접 기전은 락이 아니라 디스패치-스코프 임시 홈 수명).
  걷는 중 3트랙: Phase 2(Brick A/C — FixB 제외) ∥ Phase 3(증명 파이프라인 — design 유지,
  재진입 프로브 선결) ∥ Phase 4(세션 배선 — connection 전용). 상호 불가침 파일 명시.
- **Phase 2 랜딩** `add2873b`(위반방향 게이트+사람-reroute re_instruction 필수). Phase 3·4는
  각 v1이 골격을 세우고 렌즈가 핵심 이탈을 적발 → stop-and-gate → 정밀 vN 재발주 반복 중.
- **신규 규명(0703 오후) — Link Part4 후보 등재**: `no_resolving_reroute_address` 홀드 2회
  재발(Phase3 v1·v2)의 기전 = concern의 **related_boundary_refs(재파견 대상 주소)**가 선언
  브릭으로 해석 불가한 저작 형식(walker_kernel.py:1945-1961 분류기). Phase 1이 고친
  reason_refs의 쌍둥이 갭 — 레인 저작 일반엔 접수 문법 미러(Part4)가 필요. Phase 3 v3의
  기계-저작 반려는 형식 보장으로 우회.
- **codex 우선처리 티어 기본화** `0efd9e7f`: 형제 세션 저작·라이브 실측(service_tier
  None→priority), COO가 diff 정독+컴파일 후 커밋. opt-out=BRICK_CODEX_SERVICE_TIER=0.
- **audit-0703 4페이즈 전부 랜딩(0703 저녁)** — 조합 통합 스윕 35/35:
  Phase 1 `06468178`(Link 배달: 접수문법·보장주소·검역·종이2) / Phase 2 `add2873b`(위반방향
  게이트+사람-reroute re_instruction) / Phase 3 `f8aa7451`(증명 파이프라인: 선언→support 실측
  →비교→기계-저작 정식 반려→재파견 — F4 사이클 pin이 재파견 실물까지 검증) / Phase 4
  `94676e44`(세션이어짐: building-스코프 codex 홈+resume --last, claude --resume, 폴백·정리 —
  COO 라이브 프로브로 기억 이어받기 실증. 마감 1줄은 Smith 지시로 COO 직접).
  진행 방식 확립: v1 골격→렌즈 적발→stop-and-gate→정밀 vN, 소량 잔여는 COO 직접 마감(Smith
  선례). 후속 후보 등재: Link Part4(related_boundary_refs 접수 문법) · claude 세션 잔존 정리
  (#23 계열) · gemini 세션(미조사).
- **P8 프로브 1회 완료(0703 저녁, Smith 진입 승인)** — 현행 공식 DSL 경로의 첫 P8 증거.
  정본: p8-dogfood-probe-0703.md. 주문 3건: 필수형상(HOLD→고객 forward→complete) /
  write 실무(complete+아티팩트 커밋) / 증명 사이클(기계 반려→재파견×5→예산 HOLD — 오늘
  랜딩분 라이브 완전 검증). **엔진 결함 0, UX 갭 2**(G-1 읽기 전용 주문 kind 안내,
  G-2 예산 HOLD 처분 안내 — 둘 다 문서/표면, 엔진 수정 불요). 신뢰성 반복은 후속.
- **GP2 잔여 = P8 신뢰성 반복 샘플(후속) — GP3 창이 열림.**
- **후속 큐(Smith 0703 저녁 비준 — 이 순서가 현행 골)**: ①Link Part4(related_boundary_refs
  접수 문법 — 재시도 파이프라인 마지막 구멍) ②#14 admission 소음(결함 원장 5/5 종결)
  ③GP3 문턱 조사(mutation-RED 하네스 전제를 증명 파이프라인이 대체하는지 확정) →
  전제2(case_runners vs C1 비교) → §4-1 분해부터. 틈새: P8 신뢰성 반복·#23 레거시 정리
  (WIP 앵커 구제 선행). G-1/G-2 문서는 랜딩됨(722fa998).
  0703 오후 정리 시점: 걷는 빌딩 0, 미머지 반려 앵커 2(464105cf 관측측/참고용, r6 잔재),
  프로브 잔해 /tmp/brick-p7-coo-proof-*(v2 vessel은 랜딩 증거 인용처 — 보존).
- **큐 ② #14 admission ✅ 랜딩(0703 밤)** — package_path_admission이 선언된 vessel
  레이아웃(buildings/<slug>/task-statement-*-node/<폐쇄 레코드셋>)을 인지. 블랭킷 buildings/**
  허용 아님 — vessel 내부 stray.txt·비정형 노드명 여전히 거부(자기-프로브 9케이스 내장).
  게이트(COO 손): 신코드×라이브트리 결정 프로브 rc=0(14,222경로) · 가짜 스트레이 심기 rc=1 ·
  변이-RED(인지 함수 무력화→rc=1, 자기-프로브 발화) · 격리+라이브 본선 --all 35/35 rc=0.
  **등록 결함 5/5 전부 종결, 라이브 스윕 신호 복원**(격리/라이브 무차별 green). 랜딩 중 부수
  발견: QA 산문의 픽스처 세션ID 리터럴('sess-…')이 잔해 vessel을 redaction 위반자로 만듦 —
  실누출 아님, 언트래킹 잔해 4파일 5라인 COO 직접 마스킹(레인은 언트래킹 불가시라 빌딩 수리
  불가 구조). 후속 후보: 레인 계약 지침에 '세션ID형 리터럴 인용 금지' 추가 검토(재발 시 승격).
- **큐 ① Link Part4 ✅ 랜딩(0703 밤, stop-and-gate)** — related_boundary_refs 엄격 접수
  문법(bare brick-·building-boundary:만, 콜론접미/구접두/산문/경로 거부) + **진짜 생산자
  수리**(walker_transition_concern.py:304 — 기계 proof-obligation concern이 brick:꼴을
  방출하던 것을 준수형으로; 분류기 무수정=replay 관용 유지). 경과: QA 5라운드 전부
  implementation_gap 동일 계열 — 원인은 계약이 operator/**를 불가침으로 묶은 채 생산자
  결함을 레인에 맡긴 것(레인은 접수에 정규화 심을 팠고 QA가 심의 우회 구멍을 라운드마다
  적발 — 옳은 QA). COO stop-and-gate: 심 제거+생산자 수리+반-심 pin. 게이트: 포커스 pin
  rc=0(거부 10형+정상 2형+기계왕복+반-심+우회 6형) · 변이-RED 양방향(접수 무력화 rc=1,
  생산자 역행 rc=1 — 생산자 행동 pin 실증) · 분류기/mail diff 0줄 · 격리+라이브 --all
  35/35. 머지 e74b53e1, 앵커 refs/brick/wip/link-part4-0703a-r6 보존. **레인-불가능 D-항목
  분리 원칙이 스킬에 각인됨(26cab276)** — 이 사건이 그 원칙의 2번째 실증.
- **큐 ③ GP3 문턱 조사 ✅(0703 밤)** — 정본 gp3-threshold-0703.md: kind=mutation_red는
  형-검사만(집행 아님, red_rc=0도 통과)이라 그대로는 대체 불가 / **command-kind로 변이
  프로브 스크립트를 선언하면 의미론 집행 가능(엔진 수정 불요)** — §4-1 분해 계약에 이
  패턴 채택. 다음: 전제2 case_runners vs C1 비교 1레인 → §4-1 분해. 후속 후보 5건 등재
  (문서 참조).
- **전제2 case_runners vs C1 공유기계 비교 ✅(0703 밤, caserunners-c1-0703a)** — 결론:
  **공유기계 O, 단 사본이 아니라 역할-수준 변형** — exact copy는 proof_limits 1개뿐,
  함수명 재사용 0. 그러나 graph row/link builder·plan fixture builder·run_building_plan
  래퍼 패밀리가 양쪽에 역할 동형으로 존재 → **공유 픽스처-그래프 헬퍼 모듈을 1회
  선추출하면 §4-1·§4-2 분해가 같은 추출을 두 번 하지 않는다**(후보 패밀리:
  graph_brick_step/brick_row/agent_row·graph_link_edge·proof_limits·plan builders·
  run_building_plan wrapper). 실측 정정: 클러스터맵의 C1 'def 52개'는 실제 54개
  (work·QA·COO 3중 독립 AST 재계수 일치; case_runners 최상위 def 108개). 게이트:
  읽기 전용이라 diff 없음이 정상 — #17이 G-1 클래스(read-only 주문)로 홀드,
  COO 실질 검토(3개 핵심 주장 직접 재계수 일치) 후 forward 처분 → complete.
  처분 절차 실측 2건: 주소는 절대경로 필요(goal-runs 오해석), resume은 격리
  adapter_cwd 요구(라이브 보호 fail-closed — 임시 워크트리로 해소).

## 현재 위치 (0702 심야)

GP0 ✅(admission-gate + 중첩 레이아웃 잔여만) · **GP1 ✅ 종료** · **GP2 인체공학
3종 사실상 완료**(llm= 잔여 조각만) · GP2 본대는:
진행 빌딩 2 착지 → resume 계열 결함 3종(#15/#19/#21) 한 빌딩으로 정리 → diff-실물
게이트(#17) → D1 결과 요약 패킷(#8 마지막 조각) → 온보딩 Phase2-3 → §4-6/§4-7 →
P7/P8(Smith 게이트) → GP3.

## 미래 후보 (선언 원칙 보존 확장)

- **선언된 팬의 조건부 개방** (Smith·COO 0702 합의): 팬 가지 N개를 선언+게이트로 잠그고
  HOLD 처분에서 몇 개를 열지(forward) 접을지(stop) 정한다 — resume 그래프 확장 없이
  병렬 수 유연성 확보. 근사형은 현 엔진으로 가능(per-node coo-gate + stop 처분 실존),
  완성형은 fan-out 진입 edge 게이트 소형 확장. GP3 이후 또는 필요 시 승격.
