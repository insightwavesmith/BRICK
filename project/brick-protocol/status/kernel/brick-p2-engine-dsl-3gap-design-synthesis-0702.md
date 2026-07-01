## P2 완료 (0702)

3개 갭 전부 push 완료: 갭1+2(`c03719f`, 2회 QA에서 실결함 2건 발견+수정), 갭3
(`b087b4a`, QA에서 strict-evidence 오버랩 결함 발견+수정). `--graph` CLI 실제
폐기(`aaf2975`, 문서 10곳 동기화, `run_customer_graph_building_in_sandbox`는
`fire()`용으로 정확히 보존). 매 단계 워크트리 독립 30/30 체커검증 후 merge.
신규발견 2건은 Follow-On으로 별도 추적(task #24: 그래프레벨 `..` 탈출검증
사전결함; Smith claim2 관련 gate_sequence_policy 소재는 본문에서 이미 해소).

# P2 엔진 DSL 3갭 설계 종합 (0702)

Status: COO 종합, brick-p2-engine-dsl-3way-design-0702a (Codex design + Claude
design + Gemini axis-attack-qa fan-out -> closure synthesis) 결과. Source
truth/성공판단/품질판단/Movement 권한 아님 — 설계안일 뿐, 구현 전 이 문서는
확정이 아니다.

## 갭 재확인 (착수 전 COO가 직접 코드로 재검증, 3개 다 그대로)

1. `GroupSpec`(support/operator/assembly.py:129~)는 `role`/`members` 두 필드뿐 —
   `sibling_independence` 없음.
2. `brick()`은 `write_scope`를 `_FORBIDDEN_BRICK_KWARGS`(brick/spec.py:534~550)에
   넣어 항상 거부 — per-node 좁히기 불가.
3. `assemble()`의 `gates=`(`stamp_profile_gates()`, assembly.py:876~918)는
   `final_transition`(target이 `building-boundary:`로 시작)일 때만 스탬프 —
   중간 노드 게이트 선언 경로 없음. 단, 하위 엔진 walker(`_gate_disposition_for_step()`,
   walker_step_fixture.py:165~198)는 이미 `declared_gate_refs`를 노드별로 범용
   읽음 — DSL이 노출만 안 할 뿐.

## 3-way 합의 설계안 (Codex+Claude 합치, Gemini 공격검토 반영)

**갭1 (최저위험) — sibling_independence**
- `GroupSpec.sibling_independence: tuple[str, ...] = ()` 필드 추가
- `fan_in(..., sibling_independence=())` / `fan(..., sibling_independence=())` 파라미터 추가
- `_lower_groups()`에서 fan_in group dict에만 그대로 lowering
- 흐름: `fan_in()/fan()/build()` → `GroupSpec.sibling_independence` → `_lower_groups()` →
  `plan['groups']` → 기존 `walker_fan_in`의 vouch 해석 그대로 소비
- 위험: 캐스팅된 alias/중복 kind 이름이 caller가 준 ref를 못 찾을 수 있음 —
  구현 시 ref 해석 형식을 명확히 정의하고 테스트해야 함

**갭2 (중위험) — per-node write_scope**
- `write_scope`는 여전히 forbidden(그대로 유지) — 대신 새 필드
  `BrickSpec.node_write_scope: Mapping[str, Any] | None = None`,
  `brick(..., node_write_scope=None)` 파라미터 신설(이름 분리로 "derived vs declarable" 불변식 안 건드림)
- 흐름: `brick(node_write_scope=..., write=True)` → `BrickSpec.node_write_scope` →
  `_lower_node()`가 `_validated_write_scope`/`WriteScope`로 검증 후 `node['write_scope']` +
  `requires_brick_write_scope`(템플릿이 write_need일 때만) 스탬프 → `compose_building`
- 검증규칙: write=False면 거부 / write_need 없는 템플릿이면 거부 / 형식 불량 거부 /
  **graph-level `assemble(write_scope=...)`이 있으면 그 부분집합이 아니면 거부**(subset-required,
  실패시 fail-closed — Gemini 공격검토가 짚은 containment 위험 반영) / 생략시 기존 동작과 byte-identical

**갭3 (최고위험) — mid-graph gate**
- `EdgeSpec.gates: tuple[Gate|str, ...] = ()`(선택적 `edge(...)` 헬�퍼) +
  `BrickSpec.gates: tuple[Gate|str, ...] = ()`, `brick(..., gates=())`
- 흐름: 그래프의 엣지가 확정된 후 해석 — 노드에 나가는 completion edge가 정확히
  1개면 그 edge의 `declared_gate_refs`에 병합(`link-gate:default-transition` 먼저,
  그 뒤 번역된 gate ref); **나가는 edge가 2개 이상이면 명시적 edge-level gates를
  요구하며 거부**(모호성 방지)
- 검증: Gate enum 또는 승인된 gate concept 문자열만 허용 → `link-gate:human`/
  `link-gate:coo`/`link-gate:strict`로 번역; profile gates와 병합(덮어쓰지 않음);
  `link-gate:human` 있으면 human-gate hold 정책 부착
- 위험: fan-out 소스 모호성, 중복 edge/node 선언, profile-gate 병합 순서,
  **Link 배치법(`link/spec.py`) 문구 변경 여부**

## 구현 Building 구조 제안 (closure의 next_target_candidates)

병렬 3레인 아님 — **3개 모두 같은 파일(brick/spec.py, assembly.py,
check_assembly_equivalence.py)에 부딪혀서 순차 1레인 또는 3개 순서있는 커밋으로
한 work 레인 안에서** 처리 권고. 순서: 체커먼저 확장(assembly_equivalence.yaml에
3개 갭의 omitted-option byte-identity + 각 갭 probe 추가) → 갭1 구현+포커스체커
→ 갭2 구현+subset-rejection negative probe → 갭3 구현+walker_step_fixture pause
probe. 이후 QA fan-out: code-attack-qa(API/edge case) + axis-attack-qa(Brick/Link
권한경계) + evidence-integrity(체커/증거 주장 검증) → closure.

## Not Proven (closure 자체가 명시)

구현 자체(이 closure는 설계만, 소스변경 없음). sibling_independence의 실제
node_id/brick ref 해석은 compose/walker fan-in replay 통합발사로 증명 필요.
mid-graph gate의 end-to-end pause는 조립된 그래프/walker probe로 증명 필요.
임의 gate 토폴로지의 데드락 감지는 증명 안 됨(구현은 "선언된 pause만 증명"
+ "모호한 edge 배치는 거부"만 목표로 함). 문서/스킬 업데이트는 구현 뒤 후속.

## Smith 결정 후보 3건 (closure가 명시적으로 COO/Smith 검토용으로 플래그)

1. 이름: `node_write_scope`(Claude안, 채택 추천) vs `write_scope`를 brick()에
   재개방(Codex안). **COO는 이미 narrowly_proven으로 node_write_scope 채택**
   (derived-vs-declarable 불변식 안 건드리는 이유가 명확해서) — 재론 불필요 판단.
2. subset-required 강제: node_write_scope는 항상 graph-level write_scope의
   부분집합이어야 함(fail-closed). **COO는 이미 채택**(Smith가 직접 짚은
   containment 위험 반영, 안전방향이라 재론 불필요 판단).
3. **미결 — Link 배치법 변경 여부**: closure 설계는 "link/spec.py의 gate
   placement 메타(현재 human/coo profile gate는 final_transition에만 배치)는
   안 건드리고, targeted gate는 edge-level 명시선언으로만 처리"를 기본안으로
   제안. 이건 Link 축의 배치 LAW를 건드리느냐 마느냐의 구조판단이라 Smith
   확인이 필요.

## Smith 이의제기 검증 (0702, 2회 독립조사)

Smith가 B안(Link 배치법 자체 개정)을 지지하며 제기한 2가지 주장을 코드/문서로
직접 검증(Explore 에이전트 1회 + COO 직접 grep 1회, 둘 다 동일 결론):

- **주장1(런타임 미구현 이유=헌법적 이유) — 확인됨.** `link/spec.py`(42-88,
  122-136행)의 gate 레지스트리 자체가 `placement` 필드를 갖고, human/coo
  게이트가 명시적으로 `placement="final_transition"`으로 선언되어 있다. 즉
  이 제약은 assemble()의 편의계층이 우연히 놓친 게 아니라 **Link 축 정본
  레지스트리에 박힌 값**이다. `research-0626/build-fluency-roadmap-0626.md`
  C7(line 18)이 "per-node gate=" 확장을 이미 미래과제로 적어뒀다 — 의도적
  보류였음이 방증된다. 단, "왜 final_transition으로만 뒀는지"의 명시적 서술
  텍스트는 못 찾음(사실은 있으나 근거문서는 없음).
- **주장2(게이트 2개 붙이면 자동 인간검수, 이미 구현됨) — 못 찾음(2회 독립
  탐색 모두 동일).** `link/gate.py`, `walker_step_fixture.py`,
  `gate_sequence.py` 전수 검색 — 게이트 개수 기반 인간검수 강제 로직 없음.
  유일하게 발견된 "multi_candidate" 메커니즘은 `driver.py:1375`의
  `multi_candidate_requires_declared_policy`인데, 이건 **게이트가 아니라
  portfolio 레벨 reroute 후보(D2-mode 여러 Building boundary)가 여러 개일
  때의 정책 문제**로, 게이트 개수와는 다른 축이다. Smith가 어느 기능을
  가리키는지 재확인 필요 — 이름이 다를 수 있음.

결론: 방향은 B안(Link 배치법 개정)으로 확정(주장1이 실제로 뒷받침). 갭3(중간
게이트) 구현은 이 미결(주장2 소재 확인)까지 보류. 갭1(sibling_independence)+
갭2(node_write_scope)는 이견 없이 합의된 상태라 먼저 구현 진행.

## 갭3 재설계 (0702 후속) — 주장2 소재 확인됨, A/B안 둘 다 폐기

Smith가 "이거 있었거든"이라 말한 정확한 메커니즘을 찾았다: `support/operator/
gate_sequence.py`의 `run_gate_sequence_policy()` — Link row에 선언된 **순서있는
게이트 시퀀스**(`gate_sequence_policy`)를 읽어, 각 게이트가 불충분하면
`on_missing_required_facts`(hold/reroute/forward 중 선택), 충분하면
`on_sufficient`(주로 `next`=다음 게이트 검사, 또는 `forward`)를 실행하는 이미
완성된 엔진 메커니즘이다.

**실전 증거**: `brick/templates/presets/brick-protocol-engine-feature-hard.md`
(27-58행)이 정확히 이 패턴을 이미 프로덕션에서 쓰고 있다 — design→work
사이(최종전이 아닌 명백한 **중간지점**)에 `gate_sequence_policy`를 선언해
`link-gate:default-transition`(불충분시 reroute, 충분시 next) →
`link-gate:coo`(불충분시 HOLD+`required_disposition_owner: coo`, 충분시
forward) 순서로 검사한다. `composition_gate_translation.py:102-106`의 주석이
이걸 명시적으로 인정: "does NOT replace or claim exclusivity over pre-existing
AUTHOR-declared gate_sequence_policy holds (e.g. brick-protocol-engine-feature-
hard's design->work coo HOLD)".

**결론 — link/spec.py의 `placement="final_transition"` 필드는 전혀 안 건드려도
된다.** 그 필드는 `stamp_profile_gates()`의 **프로필 토큰 자동스탬프 경로**만
제약하는 좁은 규칙이고(gate_concept_profile 문자열 → 자동번역), `gate_sequence_
policy`라는 더 일반적인 **직접선언 경로**는 이미 프리셋 YAML에서 임의 edge
(step_template_ref 매칭)에 자유롭게 쓰이며 엔진이 이를 완전히 지원한다.
`composition_graph_validate.py`의 `_composition_edge_records_with_gate_sequence_
policy`가 이 매칭/부착을 수행한다.

**갭3의 새 스코프**: A안도 B안도 아니고, **"이미 증명된 gate_sequence_policy
직접선언 경로를 assemble()/brick() DSL에서도 쓸 수 있게 노출"**로 재정의.
`brick()`에 `gate_sequence_policy=` (또는 더 단순한 `gates=` 편의 파라미터가
내부적으로 표준 hold-policy를 조립해 이 필드로 lowering) 파라미터를 추가하고,
`_lower_node()`/`_lower_edge()`가 이를 그대로 `node`/`edge` dict의
`gate_sequence_policy` 키로 통과시키면 된다 — link/spec.py 무변경, 순수 추가.
이건 A안보다도 안전하다(이미 프로덕션에서 검증된 동일 메커니즘 재사용, 새
검증로직 발명 없음). Smith의 두 주장 모두 실질적으로 맞았던 것으로 확인됨.

**Smith 확정 요구 (0702) — API는 "매우 편하게" 선언 가능해야 한다.** raw
`gate_sequence_policy`(declared_link_gate/on_missing_required_facts/on_sufficient
중첩 dict)를 캐스터가 직접 조립하게 하면 안 됨. 기존 `assemble(gates=("human-
review",))`가 이미 쓰는 **단순 문자열 토큰 어휘**를 그대로 노드 레벨에도
재사용하는 게 목표 API:

```python
brick("design", "...", alias="design")
brick("work", "...", write=True, gates=("coo-review",))  # <- 이 노드로 들어오는
                                                            #    edge에 중간 HOLD
```

## 갭1+2 구현 결과 (0702)

1차 구현 Building(`brick-p2-gap1-gap2-impl-0702a`)에서 QA fan-out이 실제 결함
2건을 잡음(merge 보류, WIP브랜치 보존): (1) `build()`의 `_auto_fan_branch_returns`
재작성 단계가 `Fan(...)`을 인자 1개로 재구성해 `sibling_independence`를 조용히
버림 — 체커 fixture가 `fan_in()`을 직접호출해 이 경로를 우회했던 게 원인.
(2) `node_write_scope`의 subset검증이 그래프레벨 `write_scope`가 없으면 통째로
스킵됨. 2차 fix Building(`brick-p2-gap1-gap2-fix-0702a`)이 둘 다 고침: (1)
`Fan(tuple(...), node.sibling_independence)`로 보존 + `build()`의 실제 공개
진입점을 통과하는 새 체커 fixture 추가. (2) `graph_scope`를 항상
`_validated_write_scope(write_scope)`(생략시 기존 `derived_worktree_write_scope()`
재사용)로 먼저 구해 무조건 subset검증 + `_normalized_write_path()`에 절대경로/`..`
탈출 거부 추가. 30/30 체커 green, 재검증 QA(code-attack/evidence-integrity)
클린. **신규 발견(스코프 밖, 별도 기록)**: axis-attack QA가 `assemble()`의
**그래프레벨** `write_scope=` 자체(`_validated_write_scope()`)는 `_normalized_
write_path()`를 안 거쳐서 `..` 탈출 검증이 아예 없다는 걸 찾음 — 오늘 갭1/2
작업이 만든 결함이 아니라 그 이전(P8/P9 graph-write-scope-default 작업)부터
있던 사전존재 결함. Follow-On으로 별도 추적, 오늘 fix 채택은 막지 않음.

## 갭3 API 설계 스펙

내부적으로 `brick(gates=...)`는 `_materializer_human_gate_hold_policy()`류
헬퍼(coo/human 버전)를 그대로 재사용해 표준 hold-policy를 조립하고, 해당
노드의 들어오는 edge(들어오는 edge가 1개일 때만 — 모호하면 거부)에
`gate_sequence_policy`로 lowering한다. 그래프 레벨 `gates=`와 완전히 같은
토큰(`"human-review"`/`"coo-review"`) 어휘를 재사용해 배우는 새 문법이 없게
한다. 목적: 지금까지 이 세션이 써온 "디자인 Building 따로 → Smith 수동검토 →
별도 구현 Building 재발사" 2단계 수작업 패턴을, 구현 뒤에는 **하나의 Building
안에서 design→(HOLD, Smith 검토+승인)→work가 자동 이어지는** 단일 그래프로
대체한다.

