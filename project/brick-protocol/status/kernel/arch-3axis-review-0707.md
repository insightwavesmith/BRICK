# BRICK 3축 아키텍처 검수 보고 (0707) — 3축 + 코덱스 병렬 검수 병합 최종

- 대상: `/Users/smith/projects/BRICK` @ main `25516d390` (2026-07-07, 워킹트리 dirty: M 2건 / untracked 2940건)
- 검수원 4계열:
  - [A] 3축 경계 (inspector 레인) / [B] 모듈·의존·단일소스 (cto-lead 레인) / [C] 선언 대 실행 증거 (qa 레인) — 라이브 리포 실측
  - [X] 코덱스 병렬 검수 — **tarball 추출본 기준**(BRICK-audit-v2-fragment, .git 없음·README 없음·체커 49종·support 214모듈). 라이브와 스냅샷 스큐 존재. [X] 관찰은 라이브 재앵커링 여부를 명기.
- 캐스팅 일탈 명기: A/B/C 3기 모두 Fable 5로 실행(agent-object 선언 및 0707 캐스팅 기준과 다름 — COO 세션 임의 실행). [X]는 코덱스 계열 별도 실행.
- 원칙: 아래는 전부 **관찰**. 판정은 COO 소관.

---

## 0. 4계열 교차 종합

**서로 다른 환경에서 독립 실행된 두 검수(3축 라이브 vs 코덱스 tarball)가 동일 지점에 수렴했다:**

1. 이중 import 신원 분열 — 양쪽 모두 실행으로 재현 (`module_same=False`). 라이브는 상시 발동+세션 상태 분열까지, 코덱스는 import-time 분열까지 확보.
2. brick→agent 프라이빗 심볼 import (`brick/spec.py:71`) — 동일 증거 독립 확보.
3. Agent provider/모델 어휘의 물리적 원본이 support에 존재 — 동일 결론.
4. Rule 13(절대경로·세션 식별자 금지) 커버 체커 부재 — 양쪽 독립 확인.
5. `check_support_no_axis_judgment`의 커버 범위 협소(등록 verdict J6/J10만) — 양쪽 독립 확인.
6. `check_profile.py --all` red — 단 **원인이 환경마다 다름**(라이브: .DS_Store 크래시 / tarball: gemini-local CLI 부재) → --all이 환경 민감 실패 모드를 최소 2개 보유.

메타 패턴(3축 기보고 유지): 가드는 촘촘하고 대부분 green이나, 발견된 위반은 전부 가드 탐지 형태 바로 밖.

**코덱스 병합이 3축 보고를 교정한 지점 1건**: 축 C claims_matrix의 "support는 사실만 기록, 판단 안 함 → green체커" 행은 **과대 판정이었음**. check_support_no_axis_judgment green이 커버하는 것은 등록된 verdict 필드 재판정(협의)뿐이고, AGENTS.md:68-72의 광의 주장(Movement 선택·route target 발명·GateFact 생성·성공/실패 분류 금지)은 **체커없음** — support에 관찰 후보 실재(§1-9). 해당 행을 "green체커(협의) / 체커없음(광의)"로 정정한다.

---

## 1. 구조적 관찰

### 1-1. 패키징 이중 신원 — 두 환경에서 독립 재현 [B, X 교차확인]

- [B, 라이브] `brick.spec` vs `brick_protocol.brick.spec` 이중 실행: GATE_REGISTRY 객체 분열, MovementFact 클래스 분열, isinstance False. **상시 발동**(캐노니컬 진입만으로 connection 11모듈 이중 로드, 유입점 `coo_operating_chain.py:15-19`), 세션 상태 dict 분열(`adapter_local_cli.py:164`). 5중 합작 원인. 셔임 allowlist가 체커의 캐노니컬 신원을 차단(실행 확인).
- [X, tarball] 독립 재현: BrickSpec/AgentSpec/CASTING_FIELDS `module_same=False attr_same=False`. 뉘앙스: GATE_REGISTRY는 `attr_equal=True`(객체는 갈라져도 값은 동등).
- [C] check_import_identity_modes green — 가드 green과 분열 실증 공존 = 가드 임계 밖.
- [X not_proven 유지] 라이브 오퍼레이터 프로세스에서의 실전 split은 코덱스 미관찰 — [B]가 라이브에서 상시 이중 로드+상태 분열까지 확보했으므로 병합 기준으로는 실증 완료. 단 실 디스패치 중 isinstance 예외 발생 여부는 여전히 not_proven.

### 1-2. 정본 게이트 `--all` RED — 환경별 이중 실패 모드 [C, X 교차확인]

- [C, 라이브] 55프로파일 중 44 pass → 45번째에서 `.DS_Store` 2개(UnicodeDecodeError) 크래시, 이후 10개 미실행. 단독 재현 확정. 원인: `dashboard_productization_projection_check.py:210,220,47`.
- [X, tarball] .DS_Store 제외 추출이라 크래시 미발생, 대신 **`adapter:gemini-local` CLI 부재로 exit 1** — 두 번째 실패 모드.
- 라이브 재확인: Smith 머신에는 `/opt/homebrew/bin/gemini` 실재 → 로컬에서 .DS_Store 수리 후 gemini 게이트는 막히지 않을 것으로 관찰(단 gemini 없는 환경(CI 등)에선 두 번째 모드 발동). 헌법 성공판정 ①은 두 모드 모두에서 미충족.
- [X 제안 수용] 프로파일 러너가 "환경 결핍(blocked)"과 "소스 red"를 구분 기록하지 않음 — 둘 다 같은 exit 1.

### 1-3. 게이트 커버리지 침묵 부분화 [C] — 기보고 유지 (크래시가 이후 10개 lane을 무실행 처리)

### 1-4. support의 Link/Agent 형상 materialization 클러스터 [X 신규, 라이브 재앵커 완료]

코덱스가 발굴하고 본 세션이 라이브 커밋에서 재앵커링한 support/operator 내 관찰 후보군:

- `native_dispatch.py:284` — `NATIVE_DISPATCH_MOVEMENT_AUTHORIZED_REFS = frozenset({"agent-object:coo"})`: Agent 권한자 리터럴이 support에 하드코딩 (라이브 :284,647,652 확인).
- `plan_rendering.py:217-218` — "development / cto / forward must resolve to agent-object:cto-lead" 강제 + `:88,120,244` adapter:local/model:default 기본값 + provider fallback 사다리: Agent Object 선택·기본값 로직이 support에 존재 (라이브 확인).
- `composition_route_policy.py:24,34-57` — reroute 예산 materialization + target_ref 생성 (라이브 확인).
- `composition_gate_translation.py:91,113,279` — human gate hold policy(action: hold/forward) 생성 (라이브 확인).
- `route_materialization.py` — link_row(movement/target_ref) materialize ([A]가 라이브에서 기관찰, [X]가 tarball에서 독립 확인).

각 파일 주석은 "support helper, not Movement authority"류 선언을 동반 — 선언은 있으나, §0의 정정대로 이 광의 경계를 커버하는 체커는 없음.

**스냅샷 스큐 발견 (이미 수리된 이음새)**: tarball에서는 `ADMITTED_POLICY_ACTIONS`가 support/operator/gate_sequence.py에 자체 정의(:23-27)였으나, **라이브에서는 `link/gate.py:21`에 정의**되고 gate_sequence.py는 link에서 import 소비(`evaluate_declared_movement_gate` 포함). 이 어휘 이음새는 스냅샷과 라이브 사이에 이미 link 소유로 이관됨. 코덱스 A-2-2 관찰은 라이브 기준 부분 스테일.

### 1-5. 캐스팅 정책이 support에 살며 값 재작성 [A] — 기보고 유지 (`_contain_fable5`, graph_draft.py:532-605; 체커 탐지 형태 밖)

### 1-6. 경계 선언 이원화 [A] — 기보고 유지 ("읽기전용 지원 증거" vs "TRANSPORT+DERIVE only"). [X]의 provider 어휘 관찰(adapter_constants.py:14-100, provider_registry.py:43-60, agent/spec.py:24-32 "still physically lives in support ... for now" 자인 주석)이 같은 델타에 합류.

### 1-7. 순환 import [B] — 기보고 유지 (agent.spec↔adapter_model_casting, support 내 13모듈 SCC). [X]는 축 파일 한정 스캔에서 cycles=[] — 스캔 범위 차이로 상충 아님(축 내부는 양쪽 다 무순환).

### 1-8. reroute 자격 파티션 축 소속 미선언 [A] — 기보고 유지

### 1-9. brick→agent 프라이빗 심볼 결합 [A, B, X 삼중 확인] — `brick/spec.py:71-75` (+ [X]가 TYPE_CHECKING AgentSpec import :77-82 추가 관찰)

---

## 2. 국소적 관찰 (기보고 유지 + 병합 추가)

- Link 어휘 리터럴 산재 [A+B]: movement 문자열 8곳 + link-gate 단일 리터럴 6곳 — 체커 임계 밖.
- 가드 체커 문서-구현 격차 [A]: 'keyword binding' 미구현, J3/J5 미등록, checkers/ 스캔 제외. [X] 독립 확인: 등록 verdict는 J6/J10뿐.
- AGENTS.md:97 스테일 rebase 선언 [C]: building-evidence/ 부재 — 개헌급 human gate 대상.
- yaml-only 무가드 어휘 [B]: return_fact.yaml content_kinds. / 주석 스테일 [B]: link/gate.py "4 refs" vs 5행. / build/lib 스테일 [B]. / onboard.py:2286 부분집합 재기술 [B]. / 워킹트리 dirty [C]. / 출력 규약 이탈 [C]: 0바이트 성공 출력 — [X]도 동일 관찰(no stdout).

---

## 3. 청정 지역 (위반 부재 — 4계열 교차)

- 개별 체커: [C 라이브] 61/61 실행 60 green / [X tarball] 49종 44 green (red 3건·timeout 2건은 전부 tarball 환경 아티팩트 — §4 참조).
- py↔yaml 11쌍: [B] 필드셋 드리프트 0 + [X] 필드 비교 스크립트 전쌍 `equal=True` — 이중 확인.
- link/ 크로스축 import 0건 [A, X 교차]. brick/ 3파일 provider/모델 리터럴 무인지 [A, X 교차].
- 헌법·AGENTS 주장: [C] 29건 중 24건 green체커 (§0 정정 1건 반영 시 23건), [X] 11건 대조 중 GATE_REGISTRY 단일소스·AgentFact 단일홈·writer/reader 패리티 등 핵심 green 교차 확인.
- wheel 스모크 green, brick verify --self-test green [C].

---

## 4. 코덱스 tarball 환경 아티팩트 — 라이브 이슈 아님 (병합 시 기각)

| 코덱스 관찰 | 라이브 실측 | 판별 근거 |
|---|---|---|
| brick/agent/link README.md 부재 | 3개 모두 실재, [C]가 대조 green | tarball 누락 |
| check_building_map_graph exit 1 | 라이브 green | tarball에 project/ 없음 |
| check_assembly_equivalence exit 1 (not-a-git-work-tree) | 라이브 green | tarball에 .git 없음 |
| 체커 2종 timeout 124 | 라이브 둘 다 exit 0 | 샌드박스 60s 제한 |
| --all의 gemini-local 실패 | 라이브 머신에 gemini 실재 | 단, gemini 없는 환경의 2차 실패 모드로 §1-2에 병합 |
| 체커 49종/214모듈 | 라이브 61종/239모듈 | 스냅샷 스큐 (구버전 fragment) |
| gate_sequence의 ADMITTED_POLICY_ACTIONS 자체 정의 | 라이브는 link/gate.py:21 소유로 이관됨 | 이미 수리된 이음새 |

---

## 5. not_proven (병합 후 잔여)

- Rule 13 기계 강제 — 커버 체커 부재 [C, X 이중 확인].
- AGENTS.md:68-72 광의 support 무권한 주장 — 커버 체커 부재 (§0 정정) [X].
- --all abort로 미실행된 10개 프로파일 lane의 green [C].
- 클린 체크아웃/CI에서의 --all green (gemini 부재 환경 포함) [C+X].
- 혼합 신원 isinstance 이음새의 라이브 디스패치 실발화 [B, X 공히 미관찰].
- wheel 설치 모드 셔임 경로 산정 / hook execution_opened 핀 체커 / provider 실동작(probe_prompt_behavior_red 미실행 — [C], [X] 공히 스킵) / coo_operating_chain 최상위 신원·J3/J5 미등록의 의도 여부.
- compose_building() 단일정본의 전용 커버: [C]는 profile 핀 green으로 관찰, [X]는 체커 특정 실패(tarball에서 해당 profile lane 미도달) — 라이브 증거 우선하되 전용 체커 명명은 미확정.

---

## 6. proposed_delta (병합 — 증거로서만, 소스 무변이)

1. `.DS_Store`/비UTF-8 격리 + --all 프로파일 단위 예외 격리 — 게이트 red 해소 + 침묵 부분화 제거. [C]
2. 프로파일 러너에 "환경 결핍(blocked)" vs "소스 red" 증거 상태 구분 추가. [X]
3. 혼합 신원 37행 단일화 또는 셔임 sys.modules 앨리어싱. [B] + top-level 축 import 차단/앨리어스 [X 동일 제안 수렴] + **import-identity 분열 자체를 거부하는 전용 체커 신설**(`module_same=False`면 reject). [X 신규]
4. support 측 Movement/action/target materialization을 커버하는 체커 확장 또는 신설 — 광의 AGENTS.md:68-72 주장에 checker-companion 부여. [X 신규, §0 정정의 수리형]
5. Agent provider/모델 어휘(adapter_constants, provider_registry)의 single-source home 명시 선언 또는 agent/ 이관 — "for now" 주석의 봉합. [A+X 수렴]
6. movement/link-gate 하드코딩 리터럴의 link 상수 소비 치환. [A+B]
7. check_support_no_axis_judgment의 ast.keyword 처리(또는 주장 삭제) + J3/J5 등록(또는 사유 명기). [A]
8. reroute 자격 파티션 축 소속 명시 / graph_draft 캐스팅 정책 vs brick/spec.py:66-70 봉합. [A]
9. Rule 13 gap의 공식 명명 또는 체커 신설. [C+X]
10. AGENTS.md:97 rebase 문구 갱신(개헌급, human gate). [C]
11. link/gate.py:30 주석 갱신, content_kinds 처분, 단일-리터럴 인벤토리 체커 검토. [A+B]

---

## 7. 통합 리스크 순위 (병합 갱신)

1. 이중 import 신원 이음새 — 두 환경 독립 재현, 가드 green 공존 [B+X]
2. support materialization 클러스터의 무체커 상태 — 광의 경계 주장이 체커 공백 위에 서 있음 [X+A]
3. 정본 게이트의 크래시-abort 구조 + 환경별 이중 실패 모드 [C+X]
4. agent/spec ↔ support/connection 양방향 결합 + brick의 agent 프라이빗 의존 [B+A+X]
5. support/operator 13모듈 SCC / GATE_REGISTRY 산재 리터럴 / in-tree 물리 3사본 [B]

---

## 8. review_needed — COO 판단 대기 (병합 갱신)

1. **이중 신원 처분**: 캐노니컬 단일화 vs 셔임 앨리어싱 (+ 전용 분열 거부 체커 신설 여부). [B+X]
2. **게이트 red 수리 발주**: .DS_Store 격리 + 예외 격리 + blocked/red 구분 → 수리 후 --all 재실행으로 10개 lane 증거 확보. [C+X]
3. **support materialization 클러스터**: AGENTS.md:68-72 광의 주장에 체커를 세울지, 선언을 좁힐지. [X]
4. **provider 어휘 home**: "for now" 상태의 공식 처분(agent/ 이관 vs support 잔류 선언). [A+X]
5. **AGENTS.md:97 개헌 문구** (human gate). [C]
6. **Rule 13 gap**: 체커 신설 vs gap 명명. [C+X]

---

## 커버리지 요약

- [A] inspector: 파일 10종 발췌, import 전수, 체커 1종 실행. / [B] cto-lead: 파일 40여 종, AST 그래프 실측, 실행 프로브 5회, diff 3종. / [C] qa: 체커 61/61 + --all + 재현 + wheel 스모크 + self-test, 주장 29건 대조. 1차 일괄 실행 GNU timeout 부재로 실패 후 재실행 확정.
- [X] 코덱스: tarball clean extraction 기준 — AST 축 스캔, 이중 신원 재현, 체커 49종 실행(44 green), 주장 11건 대조, route/gate/plan materialization 클러스터 발굴. 원문: 세션 외부 스크래치패드 `BRICK-경계검수-보고서.md`.
- 병합 재앵커링 (본 세션, 라이브 커밋): gate_sequence.py(ADMITTED_POLICY_ACTIONS는 link/gate.py:21 소유로 이관 확인), native_dispatch.py:284, composition_route_policy.py:24-57, plan_rendering.py:88-244, composition_gate_translation.py:91-279, `which gemini` → /opt/homebrew/bin/gemini 실재.
- 검수 프롬프트 전문: 세션 스크래치패드 `brick-arch-review-prompts.md`.
