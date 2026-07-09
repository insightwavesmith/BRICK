# BRICK 아키텍처 감사 보고서

| 항목 | 값 |
| --- | --- |
| 대상 | `/Users/smith/projects/BRICK` (Brick Protocol, namespace `brick_protocol`) |
| 역할 | 아키텍처 감사관 (헌법·축 경계·모듈 응집·문서-실물 정합) |
| 기준일 | 2026-07-09 |
| HEAD | `main` @ `cd3419034` — GOAL: approve route walker implementation building |
| 성격 | **읽기 전용 감사**. 코드 변경·수리 없음. support evidence only — 성공/품질/Movement 판정 아님 |
| 법 정본 | `BRICK-CONSTITUTION.md` (0702 비준 · 0705/0706/0708 개정) |
| 운영 정본 | `AGENTS.md` (헌법과 충돌 시 헌법 우선) |

---

## 1. Context — 왜 이 감사인가

Brick Protocol은 **3축 의미 모델**(Brick=WHAT, Agent=WHO/HOW, Link=MOVEMENT)과 **support=사실 기록만**을 헌법으로 고정한 프로토콜 제품이다. 공개 실행 표면은 `brick build` 하나이고, 선언된 Building Plan을 walker가 걷고 증거를 남긴다.

감사 목적:

1. 헌법이 말하는 축 경계가 **물리 루트·코드·체커**와 실제로 맞는지
2. support가 **제4축/2차 엔진/판정 권위**로 팽창하고 있지 않은지
3. 모듈 질량·단일소스·문서 드리프트가 다음 발주(발주/route 아키텍처 v2 등)를 위협하는지
4. 이중 트리·이중 어휘 위험이 있는지

**의도된 비결함(감사 노이즈 금지):**

- 스케줄러·큐·재시도 권위·2차 엔진 부재 → 헌법 Rule 3
- support 무판단 → 설계
- 로컬 CLI 도구 성격 → 이식성 부족은 결함 아님
- 동적 무한 팬 없음(홀드+승인 경유 확장) → 의도

---

## 2. 시스템 스냅샷 (실측)

### 2.1 물리 루트 (헌법 Active Physical Roots — 0708)

| 경로 | 역할 | 실측 크기(대략) |
| --- | --- | --- |
| `brick_protocol/brick/` | Brick 축 | 712K · py 5개 · 축 LOC 합 ~4.6k(전 축) |
| `brick_protocol/agent/` | Agent 축 | 464K · py 5개 · objects 9 |
| `brick_protocol/link/` | Link 축 | 196K · py 7개 · `spec.py` 928줄 |
| `brick_protocol/support/` | support only | 17M · py ~251 |
| `project/` | 프로젝트 증거/상태 목적지 | 58M |

### 2.2 support/operator 핫스팟 (줄 수)

| 모듈 | LOC | 가족 |
| --- | --- | --- |
| `onboard.py` | 4583 | 설치/온보딩 |
| `walker_kernel.py` | 3053 | 엔진(워커) |
| `assembly.py` | 2662 | DSL 조립 |
| `run.py` | 2532 | 공개 run facade |
| `driver.py` | 2485 | intake/portfolio |
| `reporter.py` | 2472 | 읽기 투영 |
| `plan_validation.py` | 2220 | 사전 검증 |
| `cli.py` | 1806 | 공개 CLI |
| `walker_resume.py` | 1793 | HOLD 재개 |
| operator 합계 | **~55k** | 77개 `.py` |

### 2.3 거버넌스 표면 규모

- 체커: `check_*.py` 63개 · 프로파일 YAML 60개
- Agent objects 9 · presets 30
- 모듈 census: `module_registry.yaml` (append-only, G4 양방향)
- 판정 홈: `judgment_home.yaml` + `check_support_no_axis_judgment.py`
- 공개 진입점: `brick = brick_protocol.support.operator.cli:main` (`pyproject.toml`)

### 2.4 공식 실행 흐름 (문서+코드 정합)

```text
brick build --task/--preset | assemble()/build()/fan() DSL
        → materialize / compose_building (declared plan)
        → run_building_plan (run.py)
        → walker_kernel + walker_* (declared steps walk)
        → recording/* (evidence under project/<id>/buildings/)
        → reporter / frontier / coo projections (facts only)
```

헌법 Rule 9: **`compose_building()`이 엔진이며 영구 정본** — 2차 생산자 금지.

---

## 3. 아키텍처 강점 (유지할 것)

### S1. 헌법-축-물리 루트 정렬이 명확하다

- 헌법·`AGENTS.md`·축 README 3종이 동일 모델을 반복한다: Brick/Agent/Link + support 비축.
- C2 이후 package root = `brick_protocol/` 한 트리. 레거시 루트 `brick/agent/link/support` 비활성.
- 축 의미는 YAML+`spec.py` 단일소스, support는 소비·기록·투영.

### S2. 판정 이전(relocation) 가드가 실재한다

- `judgment_home.yaml`이 J6(frontier→Link), J10(grounding→Brick) 등 판정 홈을 등록.
- `check_support_no_axis_judgment.py`가 support AST 재인라인 회귀를 RED.
- `WriteScope` 등이 `brick/spec.py`로 이전된 흔적(E2 주석)이 축 누수 교정 역사를 증명.

### S3. 단일소스·admission 기계가 강하다

- 게이트: `link/spec.GATE_REGISTRY` → `gate.py` 파생 (리터럴 재서술 금지 패턴).
- 경로: `check_package_path_admission.py` (forbidden roots + seed admission 마찰).
- 모듈: `module_registry.yaml` G4 양방향 census.
- 금지 소유: movement_author / target_selector / success_judge / quality_judge / route_invent.

### S4. 공개 표면 절제

- 고객 언어: `brick build` / `assemble`·`build`·`fan` DSL.
- 손작성 `graph_packet` CLI retired (Rule 10).
- docs/CLI 출력은 support evidence — `frontier_kind=complete`만이 고객 가시 closure 후보.

### S5. 증거/품질 이층 분리

- 반환 어휘: `observed_evidence` / `narrowly_proven` / `not_proven` / next Movement candidate.
- PROGRESS.md는 기계 투영이며 성공 판정 금지 문구를 스스로 박음.

---

## 4. 발견사항

심각도: **FATAL** = 헌법/축 붕괴 가능 · **MAJOR** = 구조 부채·이중 권위·고위험 발주 면 · **MINOR** = 드리프트·가독성·운영 마찰  
신뢰: **CONFIRMED** = file/실측 · **PLAUSIBLE** = 교차 정황 · **UNKNOWN** = 미측정

### F1 · MAJOR · CONFIRMED — support 질량이 축 질량을 압도한다 (제4축 압력)

**주장:** 의미 축 코드는 얇고(축 py ~17, 축 `spec.py` 합 ~2.5k), support/operator만 ~55k LOC·77 모듈이다. 헌법상 support는 “기록자”이지만, 변경 비용·인지 부하·버그 표면은 **사실상 support 중심 제품**이다.

**증거:**

- `wc -l`: operator 핫스팟 표 (위 §2.2)
- 축: `brick/*.py` 5 · `agent/*.py` 5 · `link/*.py` 7 vs `support/**/*.py` ~251
- architecture-map은 operator를 `builder` / **`engine`** / `operator surface` 가족으로 분류 (2026-06-24)

**반증:** 축 의미는 YAML·registry에 있고 코드 줄 수 ≠ 권위. 체커·judgment_home이 권위 침범을 막는다 → **권위 붕괴는 아님**. 다만 **운영 현실의 중심 질량**은 support.

**최소 처분 방향:** walker/onboard/assembly “천장”을 module_registry decomposition 목표로 재등록하고, 신규 기능을 축 YAML·기존 seam 확장으로 강제 (신규 god 모듈 금지).

---

### F2 · MAJOR · CONFIRMED — walker 핵심이 고결합 핫스팟이다

**주장:** `walker_kernel.py`(3053) + `walker_resume.py`(1793)는 route/HOLD 변경 시 최고 폭발 반경. 0708 발주 피드백도 Phase 7을 최고위험으로 명시.

**증거:**

- LOC 실측 위 표
- `order-architecture-feedback-0708.md` L91: “walker_kernel.py 3053줄 / 26개 모듈 의존 + walker_resume … high-impact … MAG-0/human 게이트”
- architecture-map engine 가족이 walker_* 다수 파일로 이미 분할됐으나 kernel 본체는 여전히 거대

**반증:** 분할 facade(`run.py`, `dynamic_walker.py` thin) 존재. 그러나 **로직 본체**는 kernel에 잔류.

**최소 처분 방향:** route v2 / HOLD 변경은 kernel 직접 수정 전에 seam( `route_materialization`, `walker_transition_concern`, Link gate registry) 확장 가능한지 먼저 증명. 개헌 없이 kernel 대형 리팩터 금지.

---

### F3 · MAJOR · CONFIRMED — 발주/route 설계 문서가 기존 봉인과 평행 재발명 위험이 있다

**주장:** 0708 발주 아키텍처 기획은 방향은 맞으나, 실재 봉인·메커니즘을 인용하지 않고 재명명/재구현하면 **이중 어휘·이중 잠금**이 된다.

**증거 (`order-architecture-feedback-0708.md` 교차검증 가능 앵커):**

| 문서 신규 | 기존 실물 |
| --- | --- |
| concern_kind 변형 목록 | `agent/return_fact.py` TRANSITION_CONCERN_KINDS 8종 + 3중 봉인 |
| Plan Lock | `declared-building-plan` revision chain + `check_plan_revision_chain.py` |
| route_scope 신규 | `route_materialization.py` + `link/route_policies/basic_qa_repair.yaml` |
| Blind Pack(주장 은닉) | `code-attack-qa`의 fake-landing 대조 임무와 충돌 |

**반증:** 기획이 아직 문서 단계면 코드 결함은 아님. **채택·시공 시 FATAL로 승격 가능**.

**최소 처분 방향:** 피드백 필수 해소 4건 통과 전 시공 금지. 원칙: “새로 만든다” → “기존 X(file:line)를 확장한다”.

---

### F4 · MAJOR · CONFIRMED — 문서 정본 드리프트 (Rules 1–10 vs 1–13)

**주장:** 운영 입구 문서가 헌법 개정(Rules 11–13, 0705)을 반영하지 않는다.

**증거:**

- `AGENTS.md` L7–9: “Rules **1-10**; ratified by Smith 0702”
- `BRICK-CONSTITUTION.md` L35: “Rules **1–13**, 현행 상태” + Rule 11 writer=reader 검증 공유, Rule 12 positive int budget, Rule 13 durable path hygiene
- `architecture-map.md` Date: **2026-06-24** (C2 package 이주는 0708 헌법에 등재)

**반증:** AGENTS는 “헌법이 이긴다”고 명시 → 법적 우선순위는 보존. 그러나 **기여자 첫 읽기 표면**이 구법.

**최소 처분 방향:** AGENTS L8을 Rules 1–13 / 0708로 1줄 수정. architecture-map 날짜·engine 어휘·공개 표면을 0708 헌법에 맞게 refresh (또는 “stale after 0624” 배너).

---

### F5 · MAJOR · CONFIRMED — 이중 작업 트리 (`BRICK` vs `brick-protocol`)

**주장:** 동일 계열 두 트리가 공존한다.

| 경로 | 레이아웃 | 비고 |
| --- | --- | --- |
| `/Users/smith/projects/BRICK` | `brick_protocol/{brick,agent,link,support}` | **현행 정본 후보** (헌법 C2, HEAD 최근) |
| `/Users/smith/projects/brick-protocol` | 루트 `brick/ agent/ link/ support/` | 레거시 레이아웃, package root 없음 |

**증거:** `find`/`ls` 실측. 헌법: legacy top-level roots are not active import roots.

**위험:** 에이전트/스킬/문서가 구 경로를 편집하면 침묵 분기. MCP `brick-protocol` 서버 handshake 실패와도 별개로, 인간 워크스페이스 혼선.

**최소 처분 방향:** 레거시 트리에 `ARCHIVED.md` 또는 read-only 표시; 모든 발주·감사 경로를 `projects/BRICK`으로 고정.

---

### F6 · MINOR · CONFIRMED — “engine” 명명 긴장이 남는다

**주장:** 헌법은 “2차 엔진 금지·Brick Protocol is not a runtime engine”인데, architecture-map·PROGRESS 방향성 문구는 “engine”을 일상 명사로 쓴다.

**증거:**

- architecture-map L39: `engine — walk the declared plan`
- PROGRESS.md L9: “증거 기반으로 만드는 **엔진**을 제품화”
- README L109–111: “not a runtime engine”

**반증:** support README는 “스케줄러·2차 엔진이 아니다 — 기록자”로 명시. 의미상 워커=기록자.

**최소 처분 방향:** 대외/헌법 인접 문서에서 `walker`/`recorder`로 통일. 내부 가족명 `engine`은 주석으로 “declared-plan walker, not authority”.

---

### F7 · MINOR · CONFIRMED — 스킬 3면 동기화 비용

**주장:** `agent/skills/` · `brick/templates/skills/` · 운영자 설치본 동기화는 의도이나, 드리프트 면적이 크다.

**증거:** 축 README가 “의도된 3면 동기화” + `APPLY-LIST.md` 명시. 스킬 리사이즈 감사(0702) 이력 존재.

**최소 처분 방향:** 신규 스킬은 APPLY-LIST 절차 없이 금지. 단일 생성 스크립트/체커 green 필수.

---

### F8 · MINOR · PLAUSIBLE — project 증거 질량 vs 클린 배포

**주장:** `project/` 58M + buildings 다수 파일. 제품은 `BRICK-dist` 클린 배포를 전제로 하나, 개발 홈 클론 비용·실수 커밋 위험이 상존.

**증거:** `du -sh project/`; README 클린 배포 경로 설명.

**최소 처분 방향:** `.gitignore`/release export 경로 재확인 (이미 release_export 존재 — 회귀 측정만).

---

### F9 · MINOR · CONFIRMED — dashboard는 package 밖 표면

**주장:** `support/dashboard/`(React)는 pyproject packages 목록에 없고 Node 별도 제품 표면.

**증거:** `pyproject.toml` packages = operator/connection/checkers/recording 중심; dashboard `package.json` 존재.

**반증:** 의도된 읽기 투영 분리. 아키텍처상 “support 하위이지만 Python 패키지 밖” — 문서에 명시만 필요.

---

## 5. 축별 경계 판정

| 축 | 소유(헌법) | 실물 홈 | 경계 건강 |
| --- | --- | --- | --- |
| Brick | 작업계약·플랜·반환형·비교 | `brick/{work,building,comparison,spec,templates}` | **양호** — WriteScope 등 축 회귀 완료 |
| Agent | 수행자·영수증·AgentFact | `agent/{objects,prompts,skills,return_fact,spec}` | **양호** — provider-neutral object, 금지키 |
| Link | transfer/carry/gate/Movement | `link/{gate,movement,carry,transfer,transition,spec}` | **양호** — GATE_REGISTRY 단일소스; Movement 권위 명시 |
| support | 사실 기록·walk·투영 | `support/{operator,recording,connection,checkers,...}` | **압력 큼** — 질량·god-hotspot; 권위 가드는 작동 중 |
| project | 증거 목적지 | `project/brick-protocol/` | **양호(역할)** / 질량 큼 |

**종합:** 의미 경계(누가 무엇을 소유하는가)는 **헌법적으로 건강**하다. 위험은 권위 붕괴보다 **support 실행 표면의 복잡도 부채**와 **신규 설계의 평행 재발명**.

---

## 6. 의존·흐름 다이어그램 (현재 정본)

```text
                    BRICK-CONSTITUTION.md
                              |
              +---------------+---------------+
              v               v               v
           Brick            Agent            Link
        (templates/       (objects/       (GATE_REGISTRY
         spec/work)        return_fact)    movement/gate)
              \               |               /
               \              |              /
                v             v             v
                 support/operator (walk+record)
                   composition_* → compose_building
                   run.py → walker_kernel → recording
                   gate_sequence / route_materialization
                              |
                              v
                    project/*/buildings/*  (evidence)
                              |
                              v
              reporter / ledger / dashboard / PROGRESS
                    (facts only; no judgment)
```

**금지 화살표(헌법):**

- support → Movement 선택 / 품질·성공 판정 / 미선언 라우트 발명
- Agent → 자기 성공 분류
- Brick → 수행자·라우트 선택

---

## 7. 권고 (우선순위)

### P0 — 시공 게이트 (코드 변경 전)

1. **발주/route v2 시공 금지 조건:** 0708 피드백 필수 해소 4건(concern_kind 봉인, Blind Pack↔fake-landing, Plan Lock↔revision chain, route_scope↔route_materialization) 문서 반영 후.
2. **정본 트리 고정:** 모든 감사·발주·구현 경로 = `/Users/smith/projects/BRICK`. 레거시 `projects/brick-protocol` 쓰기 금지.
3. **walker_kernel / walker_resume 직접 개편**은 MAG-0/human + 기존 seam 확장 불가능성 증명 후에만.

### P1 — 드리프트 1줄 수리 (저위험)

4. `AGENTS.md` Rules 1-10 → **1–13** + 0705/0708 개정 언급.
5. `architecture-map.md` 날짜·가족 설명·공개 표면을 현 HEAD에 맞게 갱신 (support record 배너 유지).
6. 대외 문구 “engine” → walker/recorder 정렬 패스.

### P2 — 구조 부채 관리 (중기)

7. operator 핫스팟(onboard, walker_kernel, assembly, run, driver)에 **decomposition ceiling** 또는 변경 예산 재도입 검토.
8. 신규 기능 기본 경로: **축 YAML / registry row / 기존 materializer seam** — 새 대형 operator 파일 신설 시 path admission + module_registry + 경계 감사 필수.
9. 스킬 3면 동기: APPLY-LIST 자동화 또는 checker 강제.

### P3 — 관측 (지속)

10. `check_profile.py --all` / `brick verify`는 **support green**일 뿐 PASS 4항목(헌법 성공 판정)과 혼동 금지 — 운영 교육 유지.
11. 외부 감사 트랙(0705)의 WR/writer-reader 계열 회귀가 현 HEAD에 남았는지는 **별도 교차검증 배치** 필요 (본 감사 범위 밖 — UNKNOWN).

---

## 8. 심각도 집계

| 심각도 | 건수 | ID |
| --- | --- | --- |
| FATAL | 0 | — |
| MAJOR | 5 | F1 support 질량, F2 walker 핫스팟, F3 발주 재발명, F4 문서 드리프트, F5 이중 트리 |
| MINOR | 4 | F6 engine 명명, F7 스킬 3면, F8 project 질량, F9 dashboard 패키지 밖 |

**한 줄 결론:**  
Brick Protocol의 **3축 의미 아키텍처는 건강하고 기계적으로 방어된다.** 위기는 “축이 무너짐”이 아니라 **support 실행 평면의 거대 질량 + 신규 발주 문서의 평행 재발명 + 문서/이중트리 드리프트**다. 다음 제품 움직임(발주·route v2)은 **기존 봉인 확장**으로만 허용해야 한다.

---

## 9. 이 감사가 못 본 곳 (자백)

- 런타임 e2e `brick build` / `brick verify --all` **미실행** (plan mode 읽기 전용; green 미측정)
- 0705 외부감사 WR-001/WR-006 등 **수리 랜딩 여부** 전수 미추적
- `walker_kernel` 내부 상태기계 전 분기·HOLD 신원 이중소비 **라인 단위 재감사 미실시**
- connection 어댑터 보안(redaction) 심층 침투 테스트 없음
- dashboard SSE/서버 아키텍처 상세 없음
- `brick-conductor` / 학습 트랙은 범위 외
- MCP `brick-protocol` 서버 handshake 실패 원인 미진단

---

## 10. 산출물·후속 (실행 승인 시)

이 보고서는 **감사 완료 산출물**이다. 코드 변경이 필요하면 별도 발주로:

| 후속 | 성격 |
| --- | --- |
| AGENTS Rules 1–13 패치 | MINOR 문서 1줄 |
| architecture-map refresh | support doc |
| 레거시 트리 ARCHIVED 표시 | 워크스페이스 운영 |
| 발주 기획서 v2 재검증 | 설계 게이트 (0708 피드백 대조) |
| walker 변경 빌딩 | 고위험 — seam-first 증명 후 |

**실행 단계(승인 후):** 사용자가 “보고서 파일로 저장” 또는 “P1 패치 실행”을 지정하면 해당 범위만 시공. 기본은 보고 종결.
