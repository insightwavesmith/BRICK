# 가이드 2/3 — 축분석본 (Link/Brick/Agent 각 축 심층분석)

**출처**: 0702 15:52~0703 10:12 밤샘 빌딩 39개 → 3축(Brick/Agent/Link) 독립 렌즈 판정(117콜) → 유형분류(sonnet 3콜) → 증류(sonnet 1콜, 상위 3개 선별) → 깊은추론(fable5, 3콜)
**원문(가공 없는 fable5 텍스트)**: `guide-1-원문-raw.md`
**전체요약**: `guide-3-전체요약본.md`
**증류에서 빠진 것**: write_scope 너무 좁음(5개 빌딩, returns-persistence 계열 — 반대방향 버전, 낮은 우선순위), 형제 빌딩 write_scope 충돌(2개 빌딩, 표본 부족)

---

## 1위 — Link축: 재시도 메커니즘이 실전에서 거의 발동을 안 함
**영향: 17개 빌딩**

### 근본원인
SILENT 20건은 "한 가지 병"이 아니라 **각기 다른 지점에서 죽은 직렬 AND게이트**였다.
- 12개: 애초에 반려가 한 번도 안 남(1차 통과) — 이 중 `d2-ledger-cleanliness-0703b`는 QA가 rc=143 인프라 크래시로 죽어서 재시도 자체가 안 발동
- 3개: `verification_gap` 종류 반려만 나옴 — 설계상 재시도 대상이 아님(사람 검토용)
- 2개: 진짜 재시도 대상(`implementation_gap`)이 게이트에서 채택됐는데 **둘 다 사람 승인 대기(HOLD)에서 멈춤** — 밤새 방치돼서 재시도가 안 굴러감
  - `dispose-preserve-0702c`: reroute 예산 맵이 빈 상태로 선언돼서 멈춤(중간에 커밋 735d1dd3로 기본예산5 배선 고쳐짐)
  - `llm-alias-0702f`: QA가 반려사유 인용을 파일경로 문법이 아니라 `file:line+산문`으로 써서, 배달기(mail)가 그 형식을 거부 → 사람HOLD로 떨어짐
- 1개(`default-route-0702a`): 빌딩 통째로 반려(COO가 병합 단계에서 거부) — attempt 단위 렌즈로는 아예 안 보이는 급

**실제로 자동재시도가 완주한 사례는 정확히 1건**(`postmortem-default-route-0702b`) — 그 외엔 전부 위 4가지 이유 중 하나로 멈췄다.

### 이미 있는 것
- 기본 예산5 배선(`reroute-defaults.yaml` + `735d1dd3`) — 이미 랜딩, 0702의 예산 관련 HOLD 7건은 이걸로 해결됨
- 반려사유 주소문법 규칙 — `ca141522`(0703 09:51)로 이미 prose+체커pin까지 배선됨
- 처분(disposition)/재개 기계 전체 — `re_instruction` 필드까지 다 배선됨

### 남은 것 (진짜 갭)
`validate_transition_concern_evidence`(agent/return_fact.py:128-157)가 반려사유(`reason_refs`)를 **비어있지 않은지만** 체크하고, 문법(경로 형식)은 안 봄 — 그래서 잘못된 형식이 3단계 뒤(배달 시점)에서야 걸려서 사람HOLD로 튄다.

### 처방
1. `agent/return_fact.py`의 `validate_transition_concern_evidence`에 문법 검사 추가 — `/`가 들어간 참조는 `work/step-outputs/...` 경로여야 하고 `#fragment` 금지, 위반시 즉시 ValueError(잘못한 주체가 바로 알 수 있게)
2. `walker_runtime_mail.py`의 `_runtime_concern_handoff_from_ledger`에서, 반려문서 자체 주소(`concern_doc_ref`)는 **항상** 보장해서 배달 — 개별 인용 참조가 깨져도 전체 재시도를 HOLD시키지 말고 그 인용만 별도 필드로 빼기
3. `check_bounded_agent_proposed_routing_loop0.py`의 기존 mail-8 pin 확장

### 규모
Part1은 **작고 국소적**(순수 함수 1개, import 없음). Part2는 보안이 강하게 걸린 공유 표면(`walker_runtime_mail.py` — 과거 경로traversal 공격 대응 계보)이라 변이-RED 픽스처+독립 공격리뷰 필요.

### 검증 안 된 것
반려HOLD가 실제로 슬랙 알림까지 가는지 끝까지 안 쫓아봄 / intake ValueError가 에이전트한테 즉시 재수정 기회를 주는지 미검증 / 12개 "무반려" 빌딩이 진짜 깨끗한지(다른 렌즈에선 일부 DEFECTIVE로 나옴 — 재검토 필요할 수 있음)

### 후속 추가 (Smith 대화에서 도출, 0703 — fable5 처방 위에 얹는 구체 조각)

**발견의 배경**: fable5 처방은 "반려사유 주소(reason_refs/concern_doc_ref)가 항상 유효하게 배달되게" 하는 것까지만 다뤘다. 여기서 한 겹 더 파보니, 애초에 **반려 시 반환되는 두 종류의 서류(같은 return 안에 있는 두 필드)** 중 하나만 배달되고 있었다:
- **종이1** = `transition_concern_evidence` (concern_ref/concern_kind/reason_refs/related_boundary_refs/binding — 주소·이름표뿐, 자유문장 칸 없음. `transition-concern-return.yaml`에 공통양식으로 정의)
- **종이2** = `observed_evidence`/`negative_probe_observations`/`failing_or_missing_probes` 등 (에이전트가 이미 압축해서 쓴 실제 내용 — 원본 전체가 아니라 몇 문단짜리 요약)

**실측 확인**: `_handoff_address_refs`(support/operator/run.py)는 "Addresses are the text items of `*_refs` list fields... **Bodies never ride, so nothing else is collected**"라고 코드에 명시. 즉 종이1(주소)만 다음 시도로 가고, 같은 return 안에 이미 존재하는 종이2(내용)는 안 감. 새로 뭘 써야 하는 게 아니라 이미 있는 걸 안 옮기고 있었을 뿐.

**왜 지금까지 이렇게 안 됐나 (구조적 이유, 확인됨)**:
1. `source_facts`(진짜 본문을 실을 수 있는 유일한 통로)는 `walker_carry.py::_brick_source_facts`가 조립(composition) 시점에 고정된 정적 목록만 읽음 — 재시도 시점에 "직전 반려 서류를 여기 추가하라"는 코드 자체가 없음(grep 전수 확인).
2. `walker_carry.py` 코드 주석(ζ7): *"support delivers recorded addresses and records; it authors no route, Movement, success, or quality"* — "배관은 판단하지 말고 주소만 날라라"는 의도된 원칙. 내용을 옮기는 것 자체가 "이게 중요하다"는 판단처럼 보일 수 있어서 경계한 것으로 추정(단, 이 의도를 직접 설명한 역사적 문서/커밋은 못 찾음 — Smith의 기억: "예전에 원문 전체를 넘기다 토큰폭발이 나서 주소만 넘기게 바꿨다"와 겹치는 것으로 보임).

**추가 처방 (기존 Link Part1/2 위에 얹는 Part3)**:
- 종이1(`transition_concern_evidence`)의 좁고 딱딱한 스키마는 **그대로 유지** — 합치면 "관찰→판정"이 한 문장 안에서 흐려질 위험(성공 물타기)이 생기므로 병합 금지.
- 대신 **배달 시점에 종이1과 함께 종이2(이미 압축된 요약 필드들)도 같이 넘기도록** `_runtime_concern_handoff_from_ledger`/`_handoff_address_refs` 배선에 한 단계 추가. 종이2는 이미 작으므로(에이전트가 압축해서 쓴 것, 원본 전체 아님) 예전 토큰폭발 문제 재발 안 함.
- 이렇게 하면 다음 시도(work-attempt N+1)가 "왜 반려됐는지" 구체적 내용을 프롬프트에서 바로 볼 수 있음 — 지금은 라벨만 보고 그 라벨이 가리키는 서랍을 직접 찾아가 읽어야 하는데, 그걸 아무도 안 함.

### 추가로 필요한 것: 같은 빌딩 내 세션이어짐 (Smith 판단, 0703)

**문제**: 같은 빌딩 안에서 attempt N → N+1로 넘어갈 때, 지금은 완전히 새 세션(새 대화)이 뜬다. 그래서 종이1+종이2를 아무리 잘 배달해도, 결국 "낯선 사람이 쪽지 읽고 새로 파악"하는 구조다. **원래 작업하던 사람(같은 세션)이 그대로 이어서 하는 게 훨씬 낫다** — 자기가 뭘 했는지, 왜 반려됐는지 이미 자기 기억(대화 맥락)에 있으니까.

**실측 (이 대화에서 이미 확인한 것)**:
- `session_continuity_mode` 필드가 4개 값으로 선언돼 있음: `none`(기본값) / `continue_if_available` / `start_or_continue` / `fork_from_available` — 근데 실제 배선(`adapter_local_cli.py`)엔 `none`일 때 `--no-session-persistence` 플래그 붙이는 것 딱 한 줄뿐. 나머지 3개는 **선언만 되고 배선 자체가 없음**.
- CLI 자체(codex, claude)는 세션 재개를 실제로 지원함 — `codex resume`("Resume a previous session by id or pick the most recent"), `claude -c/--continue`, `--resume`, `--fork-session` 전부 확인됨. **CLI가 못 하는 게 아니라 BRICK이 그 기능을 안 쓰고 있을 뿐.**
- 워크트리는 이미 `building_id` 단위로 재사용됨(`_worktree_path_for`) — 코드/파일은 이미 이어짐. 세션(대화 기억)만 안 이어짐.
- codex 세션 영속화가 기본적으로 꺼져있는 이유(코드 주석 확인): 비-ephemeral 세션은 공유 `~/.codex` SQLite에 저장되는데, 동시에 여러 codex 빌딩이 돌면 두 번째가 락 대기하다 데드락 — 그래서 `--ephemeral`이 기본값. **즉 안 켜둔 데는 실제 이유(동시성)가 있고, 그냥 스위치만 켠다고 되는 게 아니라 이 동시성 문제를 같이 풀어야 함.**

**처방 방향**: 같은 빌딩 내 attempt 재시도(다른 빌딩으로의 재발주는 제외 — 그건 원래 새로 시작하는 게 맞음)에 한해, `continue_if_available` 모드를 실제로 배선. codex 쪽은 동시성 문제(공유 SQLite 락) 해결이 선행 조건 — 빌딩별로 격리된 세션 저장 경로를 쓰거나, 같은 빌딩 내 attempt는 순차 실행이 보장되니 락 문제가 없다는 걸 먼저 증명해야 함.

**이게 종이1/2 배달 처방과의 관계**: 세션이어짐이 되면 종이1/2를 명시적으로 프롬프트에 다시 박아 넣을 필요가 줄어든다(같은 세션이 이미 다 기억하니까) — 그래서 두 처방은 경쟁이 아니라 **서로 다른 상황을 커버하는 보완 관계**다. 세션이어짐이 안 되는 동안(또는 안 되는 케이스)엔 종이1/2 배달이 안전망 역할을 한다.

**중요(0703 정정)**: 이 항목은 "부가/후속"이 아니라 아래 3위(Agent축)까지 포함한 **전체 4개 항목과 동급으로 중요**하다 — 목록 순서는 발주하기 쉬운 순서일 뿐, 중요도 순서가 아니다. 아래 "4위" 섹션에서 독립 항목으로 다시 정리한다.

---

## 2위 — Brick축: 산문(prose)으로만 막아놨지 기계가 안 물어줌
**영향: 12개 빌딩**

### 근본원인
필드는 있고 배선도 있는데 **위반시 실패하는 게이트(bite)가 없다** — 3개가 맞물림:
1. `driver.py`의 유일한 write_scope 게이트(`_write_need_complete_without_scoped_diff_for_plan`)가 "허용범위 밖 diff가 아예 없음" 방향만 체크. 헬퍼(`_path_allowed_by_write_scope`)는 금지경로도 이미 판정할 수 있는데, 소비하는 쪽이 `return not any(...)`라서 **정상 편집 하나만 있어도 금지경로 편집이 무제한으로 같이 묻어갈 수 있음**. 체커 자신도 이걸 "후속과제로 미룸"이라고 주석에 써놨음.
2. 정책 피드백 루프: `node_write_scope`가 `assemble()` 시점에 고정되고 design 단계의 세부 검토가 역전파가 안 되니까, `brick-task-author` SKILL.md가 **공식적으로** "넓게 선언하고 산문+QA검사로 억제하라"고 가르침 — 이게 산문 펜스를 대량생산하는 진짜 기계였음.
3. 같은 모양이 재시도 지점에도 있음: `re_instruction`(사람이 재시도에 교정문구 다는 필드)은 끝까지 배선돼있지만 **선택사항**이라 아무것도 강제 안 함 — 실측: 8개 빌딩 전부 100% 비어있음.

### 이미 있는 것
- `forbidden_paths` 스키마 필드, 3계층 검증 로직 다 있음, 12개 빌딩 전부에 실제로 채워져 있음
- 경로 매처(`_path_allowed_by_write_scope`)도 이미 있고 정상 동작(라이브 검증됨)
- diff-vs-scope 런타임 게이트 자체는 있음(단, 방향이 하나뿐)
- `re_instruction`은 끝단까지 완전 배선(단, 필수 아님)

### 처방
1. **런타임**: `driver.py`에 반대방향 게이트(`_write_need_complete_with_forbidden_diff`) 신설 — 기존 fake-landing 패턴 그대로 복제, 금지경로 위반이 있으면 정상편집이 섞여있어도 HOLD
2. **작성규칙**: SKILL.md를 "넓게 선언+산문 자제"에서 "넓게 선언하되 산문으로 적은 불가침은 반드시 forbidden_paths에도 그대로 미러링" 으로 뒤집기
3. **재시도 지점**: `run_approve_entry`에서 `action=reroute`일 때 `re_instruction` 필수화(forward/stop/raise는 그대로 선택)

### 규모
런타임 게이트는 **기존 fake-landing 패턴 복제**(100~150줄, 변이-RED 픽스처 포함) — 단 `driver.py`/`check_building_operator_driver0.py`는 MERGE-RULE로 보호된 엔진 핵심이라 체커pin과 한 빌딩에서 같이 랜딩해야 함. 문서 수정은 두 SKILL.md 사본 동기화 필요.

### 검증 안 된 것
12개 빌딩에서 실제로 에이전트가 산문 펜스를 위반한 사례가 있었는지는 미확인(가능성만 확인, 실제 위반 재현은 안 함) / QA/probe 단계가 샌드박스 안에 남기는 부산물이 새 게이트에서 오탐을 낼지 미검증 / 모든 reroute에 `re_instruction` 강제가 Smith가 원하는 마찰 수준인지는 정책 판단 필요

---

## 3위 — Agent축: "증명(Proof required)"이 산문일 뿐 아무도 실행 확인을 안 함
**영향: 9개 빌딩**

### 근본원인
Smith의 3층 규율(법/주입/강제) 중 **③강제가 빠짐**. task.md의 "증명" 섹션은 프롬프트 안 산문일 뿐이고, 그 아래 어떤 기계도 "정확히 어떤 커맨드를 요구했는지" 모름:
- `BrickComparisonFact`는 `commands_run` **키가 있는지만** 확인
- `link/gate.py`는 필드 존재 여부만 확인
- 어댑터는 자기보고 그대로 아무 검증 없이 통과시킴

그래서 압박받은 에이전트가 요구된 것 대신 **인접하거나 좁은 커맨드**로 대체해도(`--all` 대신 `assembly_equivalence`만, 실제 되돌리기→rc=1→복원→rc=0 사이클 대신 서사적 "RED였다" 주장) 모든 게이트를 통과한다. 부수적으로: `made_changes=true`인데 실제 변경파일은 `[]`인 모순(재시도가 헛돎)도 **이미 측정은 되는데**(`write_observation.py`가 자기보고를 실측으로 덮어씀) 아무 게이트도 그 사실을 소비 안 함.

이 문제는 이미 **WRITE(파일쓰기)**에 대해서는 정확히 이 파이프라인(선언→측정→비교→게이트)이 존재한다 — PROOF(증명커맨드)에 대해서만 그 대응물을 안 만들었을 뿐.

### 이미 있는 것
- WRITE용 선언→측정→비교→게이트 4단 전체 파이프라인
- task.md의 "증명" 관행 자체(산문으로)
- `commands_run`/`observed_evidence` 필수 반환필드
- closure의 `deliverable_crosscheck` — 단, 코드 주석 자체가 "**미래에 Link쪽 완결게이트가 이 필드를 소비할 예정**"이라고 명시(아직 소비 안 됨)
- `make-a-gate` 스킬(게이트 레지스트리 추가용 정규경로)

### 처방
WRITE용 파이프라인을 그대로 거울처럼 복제:
1. **선언**: `brick()`에 `proof_obligations`(커맨드+기대rc 리스트) 필드 신설, task.md 증명 섹션을 그대로 옮겨적음
2. **측정**: `proof_observation.py`(신규, `write_observation.py` 거울) — 어댑터 반환 후 선언된 커맨드를 실제로 실행해서 rc/로그를 기록. 자기보고와 무관하게 실측
3. **비교**: `brick/comparison.py`에 `compare_proof_runs_to_declared_obligations` 신설 + `made_changes_claim_without_observed_change` 버킷(이미 있는 데이터로 바로 뽑아낼 수 있음)
4. **게이트**: `GATE_REGISTRY`에 `link-gate:proof` 행 1개 추가 — 실패시 QA단계 두 스텝 뒤가 아니라 work 스텝 자체에서 바로 판정
5. **핀**: 변이-RED 픽스처(선언된 증명커맨드가 rc=1이면 반드시 걸림)

### 처방 정정 2가지 (0703, Smith 대화로 확정)

**정정1 — 범위는 work뿐 아니라 모든 브릭 종류**: fable5 원문이 "an agent"라고 썼듯, 자기가 뭘 실행했는지 스스로 보고하는 건 work만이 아니라 QA/codeqa/closure 등 **모든 브릭 종류**가 다 함. 실제로 checker-infra-smalls의 codeqa가 `--probe-mutation-red` 돌렸다고 자기보고한 사례도 있었음. `proof_obligations`는 work-row뿐 아니라 필요한 모든 brick-kind row에 선언 가능해야 함.

**정정2 — 게이트 결과는 HOLD가 아니라 reroute**: 원래 설계(4번 처방)는 "HOLD"였는데, 이러면 오늘 1위(Link축)에서 잡은 바로 그 문제(사람HOLD가 밤새 방치돼서 재시도가 안 굴러감, 17개 빌딩 영향)를 이 새 게이트가 그대로 재현한다. **HOLD 대신 정식 반려(implementation_gap, reroute-eligible)를 만들어서 오늘 고친 Link 파이프라인(Part1+2+3)을 그대로 타게 해야 한다.** HOLD는 재시도 예산을 다 쓰고도 안 될 때만 최후수단으로.

**재시도 대상 판정 원리**: 자기보고와 실측이 어긋나면, 그 어긋난 claim을 낸 브릭 자신이 재시도 대상이다(work의 코드 주장이 틀리면 work로, QA의 실행 주장이 틀리면 QA로). 이건 브릭이 "내 탓이오"하고 자기 자신을 지목하는 게 아니다 — 스키마의 "본인이 본인 반려대상 지정 금지" 규칙은 **에이전트가 자기 손으로 종이1을 쓰는 경우**에만 적용되고, 여기선 게이트(Link)가 실측된 사실만 보고 독립적으로 결정하는 것이라 그 규칙과 무관하다.

**구체 사례 (전체 흐름 그림)**:
```
브릭(선언) → 링크(발사) → 에이전트(실행) → 링크게이트(실측·대조)
                                                │
                    ┌───────────────────────────┴───────────────────────────┐
                    ▼ 반려: 주소+요약 실어 재시도                            ▼ 충분: 진행
              브릭(같은 노드, 재처리)                                    브릭(기록)
                    │                                                       │
                    └──(링크 발사 → 에이전트 재실행)                        ▼
                                                                        링크(다음으로) → ...
```
세 "링크" 상자가 같은 색인 이유: 서로 다른 기능이 아니라 **같은 링크 역할이 매 이동마다 다시 등장**하는 것(모든 노드=브릭, 모든 이동=엣지=링크, 예외 없음). `process_one_node`가 매 attempt마다 브릭 선언부터 다시 읽는 것으로 코드 확인됨(재시도가 "에이전트만 다시 도는 것"이 아니라 "브릭부터 다시 거쳐가는 것").

### 규모
**기존 패턴을 따라가는 append**라 각 조각은 작음(필드1개+함수1개+게이트행1개). 단 두 곳이 공유/위험 표면: `run.py`의 어댑터 브래킷(모든 빌딩의 핫패스, present-only 주입으로 무영향 보장 필요)과 재진입성(체크 픽스처 vessel이 비-재진입성이라 실행 중 충돌 위험 — 0702 워크트리 리프 사고 전례 있음, 라이브 프로브 필수).

### 검증 안 된 것
새 필드가 실제로 `assembly.py`의 어느 지점에서 스탬프되는지 라인단위로는 미추적(주석 기반 추정) / 증명커맨드를 빌딩 워크트리 안에서 실행하는 게 재진입-안전한지 미검증(라이브 프로브 필요) / GATE_REGISTRY의 현재 placement 어휘(none/qa/final_transition)로 work-row에 hold를 걸 수 있는지 — 새 placement kind가 필요할 수 있음

---

## 4위 — 세션이어짐: 같은 빌딩 내 attempt 연속성
**영향: 같은 빌딩 안 모든 재시도** (다른 3개 항목과 동급 — 순서는 발주 편의상일 뿐)

### 근본원인
attempt N→N+1이 완전히 새 세션(새 대화)으로 뜬다. 워크트리(코드)는 이미 `building_id` 단위로 재사용돼서 이어지는데, 세션(대화 기억)만 매번 초기화된다.

### 이미 있는 것
- `session_continuity_mode` 필드 4개 값 선언(`none`/`continue_if_available`/`start_or_continue`/`fork_from_available`)
- CLI 자체(codex, claude) 세션 재개 기능 — `codex resume`, `claude -c/--continue/--resume/--fork-session` 전부 확인됨
- 워크트리 재사용(`_worktree_path_for`, building_id 단위)

### 남은 것 (진짜 갭)
`adapter_local_cli.py`의 실제 배선은 `none`일 때 플래그 하나 붙이는 것뿐(4개 중 1개만). CLI는 이미 지원하는 기능을 BRICK이 안 쓰고 있을 뿐.

### 처방
같은 빌딩 내 attempt 재시도(다른 빌딩 재발주는 제외, 그건 새로 시작하는 게 맞음)에 한해 `continue_if_available` 모드 실제 배선. **선결 조건**: codex는 공유 `~/.codex` SQLite 단일-writer 락 때문에 세션영속화를 기본으로 꺼둠(동시빌딩 데드락 방지) — 빌딩별 격리된 세션 저장 경로를 쓰거나, 같은 빌딩 내 attempt는 순차실행 보장되므로 락 문제가 없다는 걸 먼저 증명해야 함.

### 다른 항목과의 관계
Link Part1~3(주소+요약 배달)과 경쟁이 아니라 보완 관계 — 세션이 이어지면 프롬프트에 다시 박을 필요가 줄어들지만, 세션이 안 이어지는 동안(또는 코덱스처럼 못 켜는 경우)엔 Link의 배달 처방이 안전망 역할.

### 규모
중간 — 배선 자체는 기존 4개 값 중 1개를 더 배선하는 정도로 작지만, codex 동시성 문제 해결이 선행돼야 해서 별도 빌딩으로 분리 추천.

---

## 공통 패턴 (4개 다 관통하는 것)

네 처방 전부 "새로 발명"이 아니라 **이미 있는 유사 장치를 거울처럼 복제/확장하거나, 이미 있는 통로를 그냥 연결**하는 형태다. 즉 BRICK 자체가 "선언은 하는데 강제(bite)는 나중" 또는 "통로는 있는데 안 이어짐"이라는 습관을 Link/Brick/Agent/세션연속성 네 곳 모두에서 반복하고 있었다 — Smith의 3층 규율(법/주입/강제) 중 **③강제(체커/게이트)가 항상 제일 늦게, 혹은 아직도 안 옴**이라는 하나의 근본 패턴으로 수렴한다.

## 다음 스텝
발주하기 쉬운 순서(=중요도 순서 아님): Link Part1+2+3 → Brick Fix A/B/C → Agent 증명 파이프라인(범위: 전체 브릭종류, 결과: reroute) → 세션이어짐(별도 빌딩, 동시성 선결). 네 항목 모두 동등하게 중요하다.
