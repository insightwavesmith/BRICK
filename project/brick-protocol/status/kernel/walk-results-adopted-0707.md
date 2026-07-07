# 0707 완주 3빌딩 채택 정본 — 사고법 v2 합의 + Smith 판정 6건 + 후속 발주 근거

> 지위: 0706n 3빌딩(graph-thinking-design·compress-s1·onboard-seq-audit) 완주 산출의
> **채택된 부분**만 정리한 발주 근거 문서. 원문 전체는 각 빌딩 vessel의
> `work/step-outputs/*/step-output.json` (brick home `project/brick-protocol/buildings/` 하위).
> 이 문서는 support 증거이며 판정 권위가 아니다. 판정(채택)은 Smith 0707 확정.

## A. 사고법 v2 — 3인 이종 설계(fable5∥푸구∥codex, 상호 열람 금지) 합의

### A1. 3/3 만장일치 (전원 독립 도달)
1. **신규 프리미티브 불요** — 기존 build/fan/hold/expand/resume 프리미티브 안에서 해결. 신규 조립기·런타임 상태·Movement 리터럴·자동발사 없음.
2. **fan 폭은 발사 전 리터럴 확정 + 상한 3.** 폭 = min(신호 사다리, 비충돌 파티션 수, 겹침(κ) 하향, 3). 사다리는 천장이지 바닥이 아님. write-set 겹침 → 폭 1로 붕괴.
3. **2단 발주 표준형** = build1(설계 → 수렴 홀드) → 사람/COO 판독 → 2단은 새 선언(build/resume). `expand()`는 dry-run 증거 전용 — 발사·승인·걷기·Movement 선택 금지.
4. **partition_plan은 design/deep-design 반환 계약 필드** (런타임 숨은 상태 금지). 현 return 템플릿엔 아직 없음 — 이번 A 조각이 추가한다.
5. **채택 전 체커 동반 필수** — graph_draft/plan_expansion/return-shape drift/profile 기존 메커니즘으로 핀.

### A2. 채택된 partition_plan 스키마 (fable5 D3 원안 채택, deep-design 먼저)
`brick/templates/bricks/deep-design/return.yaml`에 사전 선언되는 신규 필드:
```
partition_plan:
  width_decision: {n: int(<=3), rationale_signals: [...], partition_count: int,
                   kappa_proxy: {overlapping_write_pairs: int, shared_contract_files: [...]}}
  branches: [{branch_id, concern_key, objective, output_format,
              write_set: {allowed: [...], forbidden: [...]}, returns_field,
              sibling_independent: bool,
              casting: {adapter, model, effort, timeout_seconds}}]
  done_line: str
  residual_owner: str
  qa_plan: {lenses: [...], second_verdict_path: str, max_concurrent_xhigh: int(기본2), stagger: bool}
  env_plan: {preflight_probe: bool, provider_risk: str}
  expansion: {attach_to_step_ref, budget_mode: 'per-node'|'aggregate' (XOR), budgets: {...}}
```
일반 design 확장은 실측 후(단계적 — Smith 판정 1). codex Q7 스키마와 실질 동형(필드명 차이만) — 충돌 시 위 원안이 정본.

### A3. 채택된 초안기/체커 규칙 증분 (D5, fable5·푸구 공통안)
draft-time 하드 RED: RED-1 폭>3 · RED-2 branch write-set 교차 · RED-3 deep-티어 캐스팅 timeout<10800s · RED-4 fan branch에 concern_key/objective 부재 · RED-5 2단 초안에 done_line/residual_owner 부재 · RED-6 expansion budget 혼합 모드.
소프트 WARN: WARN-1 xhigh급 QA 동시>2 · WARN-2 얽힘/walker-인접 표면+저티어 work.
각 규칙은 픽스처+변이 RED로 핀(변이가 규칙 삭제 시 프로브가 발화해야 함).

### A4. Smith 판정 (0707 확정)
1. partition_plan 홈 = **deep-design 먼저**(단계적). 2. 첫 조각 = **체커-우선**. 3. held-node 직접 확장 = **봉쇄 유지** + resume 근본 해결 트랙(아래 D절)이 검증기 포함 근본 수리 — 통과 전 2단은 항상 새 선언. 메타지시: 3다이얼(시간→공간→권위)은 COO 실사고 절차, sizing 스킬이 그릇.

## B. compress-S1 — 전제 충돌 실측 (무변경 정직 반환, 2라운드)

- census: `support/checkers/check_*.py` 56파일 중 **32파일**에 모듈-로드 부트스트랩 블록. P2형(ROOT+import_identity 삽입) 10파일, P1형(ROOT만) 7파일. **do-not-touch: `check_import_identity_modes.py`, `check_profile.py`.**
- 공유 헬퍼 좌표: `support/checkers/lib/yaml_subset.py:38-41`의 `_ensure_import_identity`는 repo 루트가 이미 sys.path에 있어야 import 가능 → **부트스트랩 블록을 그 헬퍼로 접는 것은 원천 불가**(닭·달걀). "신규 모듈 금지" 제약 하에서 S1 원안은 성립 안 함이 증명됨.
- baseline `--all` rc=1은 격리 스냅샷의 handoff 문서 UUID(이후 main에서 마스킹 완료) 기인으로 추정 — 라이브 재발 아님.
- **Smith 판정 4 = ⓐ 신규 부트스트랩 모듈 1개 허용**(제약 완화). 사다리 S2~S5 원안 유지. 후속: 신설 모듈은 각 체커 파일 잔여 부트스트랩이 2~3줄이 되도록(자기 위치 기준 sys.path 삽입 → 공유 모듈 import → 나머지 위임). 판단 로직·핀·프로파일 불변, 바이트 감소는 부트스트랩 블록에서만.

## C. onboard-seq-audit — S0~S5 검수 결과 (무변경, 검수표 완성)

- **확정 균열(S0)**: `README.md:45`·`support/docs/references/quickstart.md:107`은 성공 문구 `"5) 설치 점검 완료"`를 기대, `support/onboarding/install.sh`(161-186 영역) 실제 출력은 `"5) brick 진입점 설치 완료 ✅"` — `설치 점검 완료` 문자열은 미출력.
- README(41-73)의 축약 체크리스트 vs quickstart(98-164)의 S0~S5 전체 체크리스트 불일치 — 부분집합 명시 또는 정합 필요.
- README readiness 명령이 `onboard codex` vs `onboard doctor` 중 어느 쪽이 정본인지 미확정 — 구현 실물(`support/operator/cli.py:934-955,1536`) 기준으로 정합할 것.
- 발급 절차 갭 B-G1~G7 + 발급자 의무 8항목 초안은 work step-output에 실재.
- **Smith 판정 5 = 고객 배포는 본 repo 초대 경로**(별도 채널 없음), **발급자 = Smith**. **판정 6 = install.sh를 문서 의도에 정렬**: 설치 후 점검을 실제 수행하고 `"5) 설치 점검 완료"`를 출력하도록 스크립트를 고친다(문서를 스크립트에 맞추는 게 아님). 성공 문자열은 체커로 핀.

## D. resume 근본 해결 트랙 대상 4묶음 (Smith 판정 3 "근본 해결, 구조 잡아라")

1. **resume 엔진 결함 3종**(0702 실측, `resume-defect-mechanisms-0702.md` 정본): ①raise 예산 주입 행을 재개가 안 읽음(소비경로는 실존, 총량 반영 미확정) ②거부된 처분 시도가 원장에 남아 자기잠금(옳은 검증이 persist 이후 실행되는 순서 문제) ③step-output 즉시쓰기 vs raw-return 일괄쓰기 별개 트랜잭션 → 재개 자체 거부(가드는 실존, "거부 후 정정 경로" 선언 부재).
2. **수취 장부 꼬리(T10 클래스)**: agent-received.jsonl 부재 vs agent-return N행 → evidence_incomplete로 원장 종결 불가(fail-closed 자체는 정당). 원장 3+기 실측.
3. **홀드 체인 순환**: 처분 체인이 스텝별 홀드를 다회 통과해야 하는 구조(erg3: 4회 forward)의 근본 정리.
4. **held-node 직접 확장 검증기**: HELD 수렴 노드 위 expand→resume의 append-only 안전성(re-route 차단 여부) — 검증 실험 통과 시 2단 표준형을 직결형으로 단순화하는 반전 경로(사고법 v2 합의의 유일한 엔진 실측 의존점).

부수 대상(같은 가족, 설계 판단에 포함): 증명-예산 HOLD 경로의 WIP 앵커 부재 갭, fake_landing_write_scope_diff_absent의 다회 forward 인체공학.

## G. 0707 추가 판정 2건 (Smith)

1. **claude-측 QA 캐스팅 2티어**: QA 렌즈에 claude 투입 시 — 엔진쪽/매우 중요 = **fable5 xhigh**, 그 외 QA = **Opus 4.8 xhigh**(`model:claude:claude-opus-4-8`) 기본. 종전 sonnet-기본을 대체. 부수: fable5 동시 버스트 압력 완화. 적용 = 신규 발주의 QA branch model_ref 명시(즉시) + 초안기 캐스팅 상수 갱신은 #15 규칙표 증분(P8)에 동승 + model-lane 규율 문서 티어 행(기존 소형 묶음 행에 합류).
2. **온보딩 스플래시**: 무료 초기 배포 전제로 이즈쿠 블록아트 스플래시 채택(Smith — "팔 게 아니면 괜찮다" 리스크 수용 판정). 가드레일 2종 동반: ①에셋은 repo 트리 밖(install이 로컬 배치·출력, git 이력 영구 잔존 회피) ②만료태그 `[임시: 만료=판매/공개 배포 전 오리지널 마스코트 교체]` 등재. 집행 = D(onboard-s0-repair) 랜딩 후속으로 편입(P11).

## H. repo 청소 조사(F1) 채택 판정 (0707, 위임 하 COO 집행)

조사 실측: 추적 5,111파일 census — 로컬 잡동사니는 전부 미추적+ignored(고객 클론 무영향). `.github/workflows/release-gate.yaml`은 활성 CI + 체커 핀(install_release_export_lint_check.py:601-609가 존재 요구) → **유지**(삭제 시 --all RED — Smith 지목 표적이 load-bearing으로 판명). `release_export.sh` 실존: 공개 배포 경로는 이미 project/ 제외 — repo-초대 노출만 남음(향후 노출 축소 레버 = 초대를 export 미러로 전환, 사업 판단이라 Smith 자리, 관찰만 기록). 픽스처류·spec/reviews 역사 문서 = 체커/런타임이 물고 있어 유지-보수적. **채택 집행 2건**: ①support/docs/references/current-origin-dogfood-onebrick-20260630.md — 참조 0건 grep 증명 + 절대 로컬 경로 포함 → status/kernel/archive로 이관 ②.gitignore에 export 거부목록 대비 명시 누락 5행 추가(.gemini/ .mcp.json .ssh/ tokens/ sessions/). 반전 경로: 이관은 git mv라 이력 보존 — 언제든 복귀 가능. 시공 = repo-cleanup-apply-0707a(소형 1샷).

## I. 0707 새벽 집행 원장 (착지·사건·처분 — 추기)

**착지(origin)**: F2 청소(27b23f0f) → D 온보딩 수리(7562a1fb) → C2 접기+등재 + 스플래시 에셋 반입(21cec775/48a62764) → B2 수취 writer(9fee4231) → E 스플래시 배선(c9f03ab08). P11 완전 집행.

**claude-local 스로틀 창 실측(이 새벽, 레인 사망 4건)**: A1 공격QA(fable5)·A2-dd(fable5, 출생 즉사·유서 무기록=R4 갭)·E EI(opus 동시 2중 1)·B1 R2 공격QA(fable5). **교훈: 이 창에선 모델 불문 claude-local 동시 2도 위험 — 동시 1 안전선, 신규 발주는 codex/gemini 렌즈로 회피**(G2·G3·H1 적용). 회수: E·B1 = attach-QA(재시공 0, 독트린 6 실전 2·3호), A = 승계 재발주 A2r(deep-design 생략 표준).

**처분 기록**: A1 미완주 → fail-open 5종(QA 관찰 전량 채택)을 D2로 박은 A2r 재발주. B1 = D1·D2 완결+524줄 AST 단일소스 핀 실존 → 선착지 판정, 우회형 3종(별칭 인라인·budget_increment 조항·잔여 가드)은 후속 브릭. B2 DL-4 후속 = receipt-writer-dl4-0707a 발사. 반복 관찰 3회: "완주 증거 /tmp 로그 미지속" 클래스(C1 D3·B1 D4·G2 D3) — 증거-지속 표준(vessel-로컬 로그 사본)을 발주 계약 관례로 승격 후보.

**땜빵-아님 확인**: 착지 전건 격리 --all green + 변이 RED 게이트 통과. 스로틀 창 중 랜딩 실수 1건(착지 창 스테이징 충돌)은 ship 재정합으로 수습 — 교훈 등재됨.

**새벽 마감 집계(추기 2차)**: 발주 11기 전량 origin 착지 완결 — F2·D·C2·반입·B2·E·B1(f74bf1c8)·G2(2aeedd74)·H1(3fbc8f95)·A2r(27bf2235)·G3(199ed29e). 격리 스윕 52→55 프로파일 성장. 스로틀 창 최종 집계: claude-local 레인 사망 4(fable5 ×3·opus ×1), attach-QA 회수 3(E·B1·A2r), 승계 재발주 1(A2r). **변이-설계 교훈(2회 실측)**: 변이는 발화 경로(행동)를 끊어라 — 메시지 문자열 드리프트는 부분문자열로 살아남아 NOT-RED 오판을 만든다(D 게이트 M1·A2r 게이트 M1). P8(graph-draft-proposal-side: 9번째 답+폭 min() 계산+fan 자동 제안+계약 산문) 발사 — 사고법 v2 집행 꼬리의 마지막 조각. **held-node 직결화 결정 재료 완비**: 검증기가 픽스처 수준 안전 기준 3종+변이 4RED green — 개방 여부(픽스처 증명만으로 vs 라이브 1회 감시 통과 후)는 판정 3의 개정이라 Smith 몫.

## J. 발주 서류 결정지 13항목 — Smith 확정 (0707)

사람 몫 4항목만 남긴다: **⑦task(무엇을) ⑪source_facts(뭘 읽힐지) ⑫gates(어디서 멈출지) ⑬write_scope(범위 확인 — 초안기 제안+운영자 확인)**. 나머지 9항목은 디폴트·자동·해석층으로: building_id/declared_by/author_ref/timeout=자동, action=서류에서 제거(행 22 --forward), expansion_budget=디폴트 5(기판정), nodes/work_statement=초안기, 캐스팅=티어만(행 23). 직결 트랙(주차, Smith 동행)과 소형 수리 묶음(COO 자율 발주)도 함께 확정.

**+앵커링 방어 규율(Smith 0707 통찰: "판단 후 수정 개념 자체가 손실회피편향을 준다")**: 초안 검토자는 구조적으로 수용 쪽으로 기운다(자동화 편향) — 의지 아닌 구조로 방어: ①선-답(9답은 초안 이전) ②근거표 행 단위 감사 ③갈림(뒤집기) 기록 — 비율 0 수렴 = 사고 정지 카나리아 ④블라인드 듀얼 관례(대형 발주는 초안기 전에 운영자 예상 모양을 원장에 선기록 후 diff). 잔여 위험 = "통과하는 평범한 모양"(하류 검증이 더 나은 대안을 측정 못 함) — ③④가 유일 방어. 부수: 행 22(재초안 인자)는 수정 비용을 낮춰 손실회피 압력 자체를 감소.

**+역할 프레임 교정(Smith 원문 취지)**: "편함 추구가 아니다 — 운영자 본령은 지도를 짜고 장수를 고르는 것." 초안기는 '잘하는 부하'가 아니라 **서기(書記)** — 판단은 9답(전장 평가)과 검산(지휘)에 있고, 표는 반복-검증된 판단의 재생일 뿐. 경계할 습관 = 답만 찍고 검산을 건성으로 하는 역할 역전. 자동발사 금지·후보-채택 구조가 이 역전의 기계적 방벽.

## K. 캐스팅 대개편 — codex 개발 제외 (Smith 0707 판정)

**"개발에서 코덱스는 이제 제외한다. 오푸스 4.8 xhigh + fugu 둘로 가자. 코덱스는 쉬운 것도 못 한다. 지금 빌딩까지만 굴린다."** 적용: 신규 발주의 시공(work)·수리 레인 = **opus-4.8 xhigh(단순~중간) / fugu(복잡·얽힘·엔진급)** 2트랙. codex는 현재 걷는 빌딩을 끝으로 **시공(work)·수리 레인에서만** 퇴역. **QA 렌즈·closure는 codex 유지(Smith 0707 2차 명확화: "QA·closure의 codex 렌즈는 쓴다 — 개발만 제외")**. 초안기의 work-레인 codex 상수만 티어-해석 이관(행 23) 전까지 발주 시 재캐스팅으로 무력화.

## L. 앵커링 방어 자문(X2, fugu∥fable5→opus 종합) 채택 — COO 판정 (위임 하, 0707)

합의: §J 4중 방어 의미론 전원 일치 + "카나리아=조언(판정 아님)" + "블라인드는 파일 증거로 증명 불가(mtime 위조 가능)" 한계 명시까지 양측 독립 도달. 갈림 = 기계-구조(fable5) vs 규율-우선(fugu).

**채택 = 병합, 무게는 기계 쪽** (근거: 0707 새벽 X1 사고 — 규율은 운영자 자신이 2회 어겼음이 실측, "습관이 아니라 구조" 논지가 발제 취지이자 당일 데이터와 정합):
① draft-diff 신설 verb + 뒤집기 원장(모양-갈림/캐스팅-갈림 분리, §K 오염 방지) — fable5안
② 블라인드 듀얼 사전등록 파일 + 기계 diff + prereg-first 증거 — fable5안
③ 답-지문(sha+시각)은 신규 원장 없이 기존 rationale 파일에 — fugu 절제 채택
④ 감사표 파일 자동생성 보류(마찰 과대) — 감사 품질은 ①이 결과로 측정
⑤ 채택분 전부 체커-핀(픽스처+변이 RED) + 서기-프레임 독트린 유지
카나리아 창 N=10 = 미실측 기본값 태그. 정본 D1~D5 번호는 본 절이 확정.

**§L 보강 — 원장 의미론 확정 (0707, X3 3차 산출 도착 전 선기록 — 앵커링 방어 선-답 실천)**: ①갈림 원장(flip-ledger)은 **운영자-수준 전역**이 정본(카나리아는 운영자 사고를 재는 것) — 단 **모든 행에 building_id 기록** 의무, 창 집계는 draft-사건 단위. ②원장 경로는 **brick_home 고정, 오버라이드 불수용**(repo-내 경로는 loud 거부). 근거: X3 1~2차 QA 실측(구조/캐스팅 오분류·공유 원장 창 의미론·repo-내 경로 수용). 3차 산출이 이와 다르면 추격 없이 이 문면을 계약에 박은 보강 재발주. 시공 = S22(--forward) 착지 후 발주(표면 겹침: cli·graph_draft), work=fugu(§K 계약-인접).

## E. 초안기 제안측 부재 — 실측 (0707, #15 규칙표 증분 후속 발주의 갭 증거)

resume-rootfix-design-0707a 발주에서 `brick draft`에 준 8답과 초안기 반응 실측 원문:

- 8답: walker_adjacent=yes · size=large · **splittable=yes · file_conflict=no** · failure_cost=high · human_approval=no · termination_shape=doc · difficulty=entangled — 폭 신호가 최대치로 켜진 조합.
- 초안기 산출 모양: **단일 work**(+deep-design 자동 삽입) → QA fan → closure. 병렬 팬은 제안하지 않음.
- rationale 원문 행(그대로 인용): `note-split-candidate | graph shape unchanged (single work node) | 분할 후보: 별도 빌딩 발주 검토 — operator Movement-adjacent`
- 운영자 조치: 선언 파일의 nodes를 fan[design fable5 ∥ 푸구 ∥ codex] → closure(codex)로 수동 교체 후 발사(0707, 정상 개시).

## F. resume 근본 트랙 — Smith 판독 판정 3건 (0707) + C 게이트 실측

**판정 ④(0707 새벽 추가, Smith): held-node 직결화 = 라이브 1회 감시 통과 후 개방** — 다음 실전 2단 발주(1순위 후보 = P10 압축 사다리, 방아쇠 = P8 랜딩)의 2단째를 직결형(held 수렴 노드 위 expand→resume)으로 시도하되 check_heldnode_expansion_verifier 감시 + 실패 시 새-선언 폴백(반전 경로). green이면 2단 표준형을 직결형으로 개정(판정 3의 예정된 반전 경로 집행). 그 전까지 봉쇄 유지.

**판정**: ① 푸구 시공 순서 채택(공유 헬퍼+단일소스 핀 먼저) — 승인, resume-admission-unify-0707a 발사. ② 수취 writer = **fable5 원천 봉합 채택**(Smith: "근본수정이 페이블이지? 페이블로 간다. 엔진을 손대는 건 괜찮다") — receipt-writer-join-0707a 발사(기록계 packet 조립부 확장, 커널 무접촉, 미래 걸음 전용). 정정-도장 검증(operator_correction 커버리지)은 과거 꼬리 전담으로 강등·후순위 유지. ③ 체커 신설 = 프로파일-프로브 우선, 표현 불가 실측 시 신설 1개+사유(계약에 반영).

**compress-s1b 1차 게이트 실측(0707)**: VERDICT NEEDS-OPERATOR — ①격리 --all rc=1: `import_identity_modes parents[N] registry mismatch` — 접기가 29파일에 심은 `parents[2]` 신규 사이트가 바인딩 레지스트리(check_import_identity_modes.py 내 하드코딩 dict) 미등재. **원인 = 발주 계약이 그 레지스트리 파일을 do-not-touch로 봉인(레인-불가능 D 배정 클래스, 0703 #14 동족)** — 접기류 수리는 바인딩 레지스트리 등재까지가 한 몸이다. ②QA의 "--all rc=0" 자기보고를 격리 게이트가 반증(codex green 불신 규율 재실증). ③COO 변이 M1(module_registry 행 제거→admission RED 기대)도 NOT RED — 실 지킴이 식별을 C2의 D3로 이관. M2 관찰: ensure_checker_imports no-op에 표본 3체커 무플립(belt-and-suspenders). 처분 = 수리 재발주 compress-s1b-fix-0707a(승계: 앵커 87719e15 diff 적용 + 레지스트리 등재, 재발주 승격 캐스팅). 1차 앵커는 C2 랜딩 시 대체.

판독: 현행 초안기는 분할 가능성을 **감지**(note-split-candidate)하되 **제안하지 않는다** — 폭 계산(min 규칙)·병렬 설계/시공 팬·2단 표준형 1단 그래프의 자동 제안이 전부 부재(제안측 갭). 거부측(안티패턴 RED-2~6·WARN-1~2)은 gt-checker-slice-0707a 계약분. 수리처 = #15 규칙표 증분 후속 발주(방아쇠 = gt-checker-slice 랜딩): 폭 신호용 9번째 답 + min() 폭 계산 + fan 자동 제안 행. 인체공학 표 등재 = operator-ergonomics-wave-0705.md 행 20.

## M. 캐스팅 개정 — fable5 기획 전용 (Smith 0707 오후 판정, §G1 대체)

**판정(Smith 원문)**: "지금 페이블로 QA 따는 건 중지하고 오푸스 4.8 xhigh로 변경한다. 페이블은 디자인에만 사용한다."

의미론:
1. **claude-측 QA = 전부 opus-4.8 xhigh** (`model:claude:claude-opus-4-8`), 엔진급 여부 불문 — §G1 2티어(엔진쪽=fable5) 폐지.
2. **fable5 유일 사용처 = 기획 레인**(deep-design/design-lead, xhigh). 0704 "fable5 렌즈 예외 선례"(Smith 지시 시 QA 투입 허용)도 닫힘.
3. 복잡 work 상위-두뇌 승격 = **푸구 단독** (0706 야간 "푸구+페이블" 중 페이블 축 재봉쇄).
4. 코드 잔여: 초안기 §G1 상수(graph_draft.py:80 캐스팅 규칙표 + rule ⑨ fable5-burst)가 폐지된 2티어를 조언함 — 소형 증분 빌딩 필요(X3 착지 후 발주, 같은 파일 충돌 회피). 그 전까지 초안기 캐스팅 조언 중 fable5-QA 행은 발주 시 COO 재캐스팅으로 무력화.
5. 부수 효과: fable5 스로틀 버스트 클래스(0706 야간 레인 사망 4건) 자연 소멸 — QA 풀이 opus 단일화.

**§M 보강(Smith 재확인, 같은 날)**: "워크도 마찬가지로 오푸스 4.8 xhigh를 쓴다. 푸구, 클로드 2개를 사용" — 시공(work) 풀 = **opus-4.8 xhigh(기본) + 푸구(복잡·얽힘·엔진급)** 2하네스로 확정, work에도 fable5 부재. 전 레인 최종형: 기획=fable5 / work·QA=opus-4.8 xhigh(+복잡 work만 푸구) / code QA·closure=codex 렌즈 유지 / review=gemini.

## N. 고객 배포 경계 결함 (Smith 라이브 설치 실측, 0707 오후) — 등재

**증상(Smith 원문)**: "프로젝트-브릭프로토콜이 있으니까 애초에 이거 이어서 작업하려고 하더라. 고객 측면에서 이런 거 매우 많이 덜어내야 할 듯" — 신선한 고객 머신의 에이전트가 클론에 동승한 우리 내부 작업사(project/brick-protocol/)를 보고 **자기 일로 착각해 이어서 작업 시도**.

**실측**: 추적 파일 5,130 중 project/ = 4,598(90%), 242MB — 원장·빌딩 증거·인계문서·inbox 이벤트 전부 고객 클론에 동승. install.sh = clone-first(전체 클론). 과거 릴리즈 정리 흔적 존재(0613 release-v010-clean-repo 이벤트들, .github/workflows/release-gate.yaml)하나 현행 설치 경로와 미연결.

**판정 방향(Smith)**: 고객 측 대량 덜어내기. 경계는 구조적이어야 함(파일 부재) — 조언성 경계(README "무시해라")는 에이전트 착각을 못 막는다(라이브 실증).

**처분**: 설계-우선 클래스(P3, 배포 아키텍처 갈림: 클린 배포 repo/export vs 설치측 sparse-checkout vs 내부작업 별도 repo 이관) — deep-design 발주(fable5 xhigh, §M 캐스팅), 착지 열차 소진 후. 조사 함대(폴더 신뢰·프리셋 하드코딩)와 같은 "고객-측 결함" 가족 — 설계 입력에 스카웃 결과 동봉.

## O. 고객-측 결함 2건 정찰 결과 채택 (스카웃 2 + 교차검증 1, 0707 오후) — COO 처분 (위임 하)

**P2 프리셋 하드코딩 = CONFIRMED (결정적, 코드로 완결 증명)**:
- 근본원인 2중: ①캐스팅 해석 사다리의 스텝-명시 rung은 fail-closed 헌법("support는 어댑터를 대신 정하지 않는다", composition_intent)에 따라 registry 무참조 통과 — 그런데 플릿 프리셋 8종이 그 슬롯에 우리 환경의 codex/gemini 리터럴 49행을 데이터로 박아 배포됨 → 고객 등록(providers.yaml)이 반영될 해석 경로 자체가 없음. ②brick init 기본 host=codex 고정(cli.py:1538) + install.sh가 --host 없이 non-interactive 호출 → claude-only 머신은 providers.yaml이 비어 비-플릿 프리셋조차 codex-preferred 레인에서 local_cli_missing HOLD.
- 증상: 등록을 다 마쳐도 플릿 프리셋은 1번 노드에서 매번 HOLD 사망, resume 동일 재발.
- **처분 (2단 분리)**: (a) 소형 즉시 — init 기본 host를 first-ready 자동감지로(기존 REAL_PROVIDER_SELECTION_ORDER 재사용) + pre-walk fail-fast(발사 전 전 스텝 어댑터 가용성 대조, not-ready 시 발사 거부+교체 안내) = preset-host-autodetect 빌딩. (b) 엔진급 설계 — 프리셋 리터럴 49행 제거+티어 어휘(행 23 처방의 프리셋 적용, fail-closed 헌법 경계 검토 포함) = deep-design(fable5, §M 캐스팅).

**P1 claude 폴더 신뢰 = PARTIAL (구조 공백 실증, 차단 발화 조건은 미재현)**:
- 실증된 것: claude 어댑터에 신뢰 처리 전무(gemini는 --skip-trust+env로 명시 우회하는 것과 비대칭), 온보딩 전 표면에 claude 핸드셰이크 0, 신뢰는 ~/.claude.json 경로-단위 저장 + 레인은 stdin=DEVNULL 헤드리스(응답 불가), 미신뢰 경로 기동이 trust=False 엔트리 생성.
- 반박된 것(교차검증): "무인 레인이 막힌다"는 웜 머신 프로브 3종 전부 green이라 미재현 — 미신뢰 워크스페이스의 실증 효과는 **권한 드롭**(project-scoped 권한 축소)이며, 하드 차단 조건(신선 글로벌 상태/버전)은 프레시-상태 실측 1건이 선행 게이트.
- **처분**: 2단 빌딩(recon 실측 → 수리) — recon: HOME 격리로 신선 상태 재현, 헤드리스 차단 여부 + 부모경로(~/.brick/worktrees 루트) 신뢰 상속 여부 실측 → 수리 옵션 갈림(경로별 기입 vs 부모 1회 승인 vs 온보딩 대화형 스텝+preflight_claude). P2 먼저(온보딩 3파일 공유 표면은 순서로 해소, 교차검증 판정).

**발주 대기열(착지 열차 소진 후)**: ① graph_draft §M 캐스팅 상수 증분(소형) ② P2-(a) preset-host-autodetect(소형) ③ P1 recon→수리 2단 ④ §N 배포 경계 deep-design(fable5) ⑤ P2-(b) 티어 어휘 deep-design(fable5) — ④⑤ fable5 설계는 시차 발사(스로틀 안전선).

**§N 판정(Smith, 0707 오후)**: 배포 경계 = **클린배포 repo 채택** ("1. 클린배포") — 릴리즈 시점에 제품 파일만 별도 repo/브랜치로 export, install.sh는 클린 repo를 클론. 우리 작업 repo는 그대로. deep-design 입력에 방향 고정: 설계 범위 = 제품 파일 매니페스트(in/out 경계), export 메커니즘(0613 release-v010-clean-repo 흔적·release-gate.yaml 재활용 검토), 버전·고객 업데이트 경로, 온보딩 문서의 클론 대상 전환.

**§O-P1 재분류(Smith 실측 답변)**: 고객 설치서 뜬 팝업 = **macOS 시스템 창(TCC 폴더 접근권한)** — claude CLI 신뢰 다이얼로그가 아니었다. 재분류: ①주 결함 = 설치/첫 빌딩 흐름 중 TCC-보호 경로 접근(어느 단계·어느 경로인지 recon 필요 — tccutil reset으로 우리 머신 재현 가능) → 수리 = 선검사에 설치 경로 지침(보호 폴더 회피) + "권한 창 뜨면 허용" 온보딩 문구 + 보호-경로 접근 제거. TCC는 프로그램 우회 불가(OS 설계)이므로 회피+안내가 정공법. ②부 결함 = claude 미신뢰 워크스페이스 권한 드롭(구조 공백 실증분) — 소형 위생 수리로 별도 유지(온보딩 신뢰 스텝), 우선순위 강등. P1 recon의 질문 교체: "claude가 언제 막히나" → "TCC를 누가 언제 건드리나".

**§O-P1 recon 결과 채택(워크플로 3인, 0707 저녁) — COO 처분**: TCC 창은 "책임 앱×보호 폴더 조합당 최초 1회" — 창이 떴다는 것 자체가 그 순간 그 폴더 최초 실접근이라는 뜻. 원인 후보 순위: ①보호 폴더(Downloads/Desktop) 체크아웃에서 install.sh 실행(배너 전 발화) ②brick init의 `claude mcp add`가 고객 cwd 상속(onboard.py:1211 subprocess.run cwd 무지정 + connect.py --scope 미지정=local) — **부수 기능버그 동시 발견**: 고객이 서 있던 엉뚱한 프로젝트에 local 스코프 MCP 등록됨 ③첫 발사의 git rev-parse cwd 탐색(cli.py:187) ④BRICK_HOME 보호 경로 지정 ⑤키체인 창 오인. 증폭기: iTerm2 등 비-Terminal 앱은 승인 미이전(앱 단위 어트리뷰션). 수리 5종 채택(우선순위 ②1줄 cwd 고정 > ①preflight 보호구역 경고 > ④TCC 진단 처방 > ③발사 전 cwd 프로브 가드 > ⑤문서 지침, 합계 ~50줄) — 범인 미확정과 무관하게 전부 심층방어로 유효, 확정은 다음 리허설 체크리스트(창 문구 3요소·직전 배너·상태 4종)로. **발주 순서 조정: P1-fix는 P2a와 같은 파일(cli.py·install.sh)을 만지므로 P2a 착지 후 발주**(병행 금지). not_proven 8항 정직 반환 — 실제 범인, mcp add의 cwd 내용 실접근 여부 등은 리허설/신규 계정 실험으로.

## P. 클린배포 설계 완결 (cleanrepo-design-0707b, fable5∥푸구 2인 이종, 0707 저녁) — Smith 판독 대기

**핵심 실측**: `support/onboarding/release_export.sh`(7/1작, 7,573B)가 **이미 존재** — project/·egg-info를 뺀 클린 트리를 만들 줄 알고, in/out 필터(EXCLUDE project/, DENY 12패턴)와 "첫 onboard가 project/를 로컬 생성" 설계까지 있다. **그러나 install.sh는 release_export를 0회 참조** — 도구는 있는데 배선이 안 됨. §N 결함의 정확한 정체 = "export 존재하나 미연결".

**두 설계 합의(narrowly_proven)**: 클린 배포 repo/export 경계, 내부 project/ 무변경, release_export.sh를 producer로 유지, 자동 발행 금지, 체커 동반 커버리지 — 방향 전원 일치.

**갈림 5점(Smith 판독)**:
1. **매니페스트 중심성**: 신규 `release_product_manifest.json`(제품 파일 화이트리스트)을 도입할까(푸구: 명시 매니페스트 선호) vs release_export.sh의 기존 EXCLUDE/DENY 필터 확장으로 충분(fable5: 기존 자산 재활용). — 화이트리스트=미래 파일 안전(누출 기본거부), 블랙리스트=현행 유지 저비용.
2. **클론 대상 문구**: 공개 클린 repo 슬러그 확정 vs 플레이스홀더 정책.
3. **release_export.sh 책임 폭**: export만 vs export+검증+배선까지.
4. **누출 스캔 범위**: project/ 경로만 vs 원장 어휘·세션ID·절대경로까지.
5. **AGENTS.md 처리**: v1은 그대로 두기 vs 고객-안전 재작성 슬라이스 후속.

**COO 소견(위임 하 집행 준비)**: 갈림 1이 유일한 실제 아키텍처 판단 — 나머지 4는 1이 정해지면 따라온다. 매니페스트(화이트리스트) 방식을 권한다: "미래에 새로 만든 파일이 자동으로 고객에게 새어나가지 않음"이 §N 결함의 재발 방지 본질이고, 블랙리스트는 새 내부 디렉토리가 생길 때마다 DENY 추가를 잊으면 뚫린다(§N이 딱 그 사고). partition_plan 양측 확보 — 채택 방향만 서면 시공 발주 가능.

**§P 판정(Smith, 0707 저녁)**: 갈림 1 = **화이트리스트(매니페스트) 채택**. 신규 release_product_manifest.json에 제품 파일 명시, 목록에 없으면 기본 제외 — 미래 파일 누출 기본거부(§N 재발 구조 차단). 따라오는 세부 결정: 갈림 2=슬러그는 플레이스홀더 정책(공개 repo명 미확정 시 {OWNER}/BRICK-dist 자리표시), 갈림 3=release_export.sh 책임 폭 = export+매니페스트 검증(배선은 install.sh 몫으로 분리), 갈림 4=누출 스캔 = 매니페스트 위반(화이트리스트 밖 파일 export 시도) + project/ 경로 + 세션ID/절대경로 어휘까지(누출 기본거부와 정합), 갈림 5=AGENTS.md는 v1 그대로(고객-안전 재작성은 후속 슬라이스). 시공 = 푸구 설계의 매니페스트-중심 partition_plan 기반 발주(cleanrepo 시공 빌딩), 방아쇠 = 현행 착지 열차(M7r·P2a) 소진 후.

## Q. 프리셋 티어 어휘 설계 완결 (preset-tier-design-0707b, fable5∥푸구, 0707 저녁) — Smith 판독 대기

**두 설계 합의(narrowly_proven)**: ①프리셋이 우리 머신의 어댑터/모델 리터럴(49행)을 그만 싣고 provider-중립 **캐스팅 티어**(`casting_tier_ref: casting-tier:{plan|deep|standard|light}`)를 발화 ②티어는 **1회만** 해석 — 기존 preset-step→row 복사 이음새(composition_graph_emit 캐스팅 복사 + plan_rendering CASTING_FIELDS emit)에서 provider_registry.py 신규 resolver가 fail-closed 사다리로 실 어댑터 확정 ③기존 리터럴 selected_* 선언은 **하위호환 그대로 유효**(registry 우회 = 오늘과 동일, fail-closed 헌법 무손상) ④신규 티어-프리셋은 codex/gemini/fable/fugu 리터럴 명명 금지.

**핵심 성과**: 헌법 충돌 회피 논증 성공 — "선언을 support가 바꾼다"가 아니라 "티어 선언 자체가 해석 위임을 명시 선언"이라 fail-closed와 양립. §M 정책(기획=fable5, 시공·QA=opus-4.8, 복잡 work=푸구)을 티어→모델 매핑으로 표현 가능.

**갈림 3점(Smith 판독)**:
1. **렌즈 의도 표현**: 렌즈(code-attack/axis/evidence/review)를 authoring 행에 **명시**할까(푸구: lens+tier 요청쌍) vs 티어+다양성 메타(`casting_diversity_key`)로 **함축**할까(fable5). — 명시=교차검증 의도가 선언에 남아 감사 쉬움, 함축=행 간결.
2. **시공 슬라이스 범위**: 이번 시공이 graph_draft/draft_diff를 지금 건드릴까 vs 별도 선언 빌딩으로 분리.
3. **헌법 주석**: composition_intent 법-주석에 티어 위임 노트를 이 슬라이스에서 달까.

**COO 소견(위임 하)**: 갈림 1 = **명시(푸구안) 권장** — 플릿의 설계 의도가 "이종 렌즈 교차검증"인데 그게 선언에 안 남으면(함축) 미래에 왜 이 캐스팅인지 추적 불가, §Q의 감사성이 §L 앵커링 방어 철학(차이를 장부에 남긴다)과 한 가족. 갈림 2 = **분리**(graph_draft는 M7r가 방금 만진 파일 — 충돌·범위 폭발 회피). 갈림 3 = 이 슬라이스에서 주석만(코드 무변경). 시공 방아쇠 = 착지 열차 소진 후. cleanrepo 시공과 파일 비충돌(이쪽=provider_registry/presets, 저쪽=release_export/install) → 병행 가능.

**§Q 판정(Smith, 0707 저녁)**: 갈림 1 = **명시(푸구안, lens+tier 요청쌍) 채택** — 렌즈 의도가 authoring 행에 남아 감사성 확보(§L 앵커링 방어 철학과 정합). 따라오는 세부: 갈림 2=시공 슬라이스는 graph_draft/draft_diff **미접촉**(별도 선언 빌딩 — M7r가 방금 만진 파일 충돌 회피), 갈림 3=composition_intent 법-주석에 티어 위임 노트만(코드 무변경). 시공 = 푸구의 lens+tier partition_plan 기반 발주(preset-tier 시공 빌딩), cleanrepo 시공과 파일 비충돌(provider_registry/presets ↔ release_export/install)이라 병행 가능, 방아쇠 = 착지 열차(M7r·P2a) 소진 후.

## R. import 이중 신원 근본 해결 판정 (Smith 0707 심야, GPT 검수 교차확인 후) — 수준3 채택

**Smith 판정 원문**: "땜빵 하지 말자. import가 문제면 나중에 또 문제가 된다." → 앨리어싱(수준1 땜빵) 거부, **물리구조=패키지구조 통일(수준3)** 채택.

**실측 재현(이 세션)**: `import link.movement` vs `import brick_protocol.link.movement` — 같은 파일(True)이나 같은 모듈(False) = 이중 신원 확정. 다른 세션 GPT-5.5 검수와 교차확인된 5건(이중신원·brick→agent private import·Agent 어휘 support 상주·Rule13 체커 부재·no_axis_judgment 협소커버) + support materialization 클러스터(native_dispatch:284·plan_rendering:217-218·composition_route_policy).

**정당화 조건 충족**: Smith "이제 다른 고객들이 써야 하거든" + "리포 클론으로 우선 쓰게 된다" → 수준3의 정당화 조건(외부 소비·클론 배포)이 이미 성립. 클론 고객은 이중신원 환경을 통째 물려받음.

**수준3 = 개헌급**: 축 폴더(brick/agent/link)를 실제 brick_protocol/ 루트 밑으로 이동 → 재매핑·셔임(import_identity)·editable finder·이중 sys.path 전면 철거. 모든 import·경로기반 체커·AGENTS.md 물리루트 조항·헌법 물리루트 선언까지 이동. **가장 큰 위험 = 마이그레이션 자체가 "for now" 다리를 또 낳는 것**(이 리포 4세대 이사 연혁이 증거) → 설계-우선 필수, 단발 시공 금지.

**처분(설계-우선)**: deep-design(fable5) 발주로 마이그레이션 설계 먼저 — 경계 매니페스트(뭐가 brick_protocol/ 밑으로), 철거 순서(셔임·finder·allowlist·bootstrap 어느 것부터), 경로 체커 26,800 검사 이동, 헌법·AGENTS 개정안, 롤백 안전선, partition_plan. 이전 세션이 잡은 Phase 0(게이트 .DS_Store 수리·Rule13 체커) 등 소형 필수는 이 개헌과 **분리**해 선행 가능(별건). Smith 동행 안건(개헌은 헌법 개정 권한 사항).

**미해결 꼬리**: preset-tier-single 착지 스윕 RED(gemini/.DS_Store 환경모드 추정, 이중신원 무관 — provider_preflight 등 개별 프로파일은 passed) → 재착지 부검 필요(별건).
