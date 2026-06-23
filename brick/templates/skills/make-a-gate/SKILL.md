---
name: make-a-gate
description: BRICK 새 게이트(link-gate) 만들기. Link 게이트 어휘를 1개 추가할 때 — link/spec.py GATE_REGISTRY에 행 APPEND + 병렬 표면 동기화. 끝에 레지스트리 로드 + 카탈로그 크로스체크 green = placement 가능 증명. 단일소스 가드(check_gate_registry_single_source) 준수.
---

# 새 게이트 만들기 (single-source APPEND → sync → 사용 가능 확인)

법: 게이트 어휘는 **`link/spec.py` `GATE_REGISTRY` 한 곳**이 단일소스(STRUCT-SURGERY ② landed).
모든 파생(`link/gate.py`의 `DECLARED_GATE_REFS`, HUMAN/AUTO 분할, `_GATE_REQUIRED_RETURN_FIELDS`,
placement)이 이 행에서 자동 유도된다. 케이던스: per-step compileall, 끝에 `--all` 1회. 핀 완화 금지.

## ⚠ 행 순서가 load-bearing — 끝에 APPEND, 중간 삽입 금지

`DECLARED_GATE_REFS`는 **positional**이고 `building_operation_common.py`가 인덱스 `[0..N]`로 읽는다.
새 행은 **반드시 리스트 끝에 APPEND**한다. 중간 삽입은 모든 후속 인덱스를 어긋나게 한다.

오늘 레지스트리(실측, 4행):
```
[0] link-gate:default-transition  (concept_token=None,            placement="none",             disposition="auto")
[1] link-gate:strict              (concept_token="strict-evidence", placement="qa",              disposition="plain")
[2] link-gate:human               (concept_token="human-review",  placement="final_transition", disposition="human")
[3] link-gate:coo                 (concept_token="coo-review",    placement="final_transition", disposition="coo")
```

## 1단계 — APPEND 1행 (`link/spec.py` `GATE_REGISTRY`)

```python
GateRegistryRow(
    ref="link-gate:<name>",
    concept_token="<token>",            # None이면 프리셋서 못 부름(default-transition류)
    required_return_fields=("<…>", "…"),# 이 게이트가 요구하는 반환 필드(없으면 빈 튜플)
    placement="qa",                     # "qa" | "final_transition" | "none"
    placement_order=<int>,              # 같은 placement 내 정렬(기존 값과 안 겹치게)
    disposition="auto",                 # "auto" | "plain" | "human" | "coo"
),
```
이것만으로 `link/gate.py`의 `DECLARED_GATE_REFS`/HUMAN·AUTO 분할/`_GATE_REQUIRED_RETURN_FIELDS`,
concept token, `gate_placement_for_row`가 전부 자동 유도된다.

## 2단계 — register (병렬 표면 동기화 — drift 크로스체크가 비교함)

5행째를 더하면 다음을 **반드시** 같이 갱신(안 하면 RED):

1. **`support/operator/building_operation_common.py`** — `COMPACT_LINK_GATE_TOKENS`는
   `DECLARED_GATE_REFS`를 **위치 `[0..3]`**로 인덱싱. 체커는 인덱스 집합 == `range(len(GATE_REGISTRY))`을
   **정확히** 요구 → **`[4]` 항목을 추가**해야 한다 (concept_token 있는 게이트면).
   ```python
   COMPACT_LINK_GATE_TOKENS = {
       "strict": _DECLARED_GATE_REFS[1],
       "human":  _DECLARED_GATE_REFS[2],
       "coo":    _DECLARED_GATE_REFS[3],
       "<token>": _DECLARED_GATE_REFS[4],   # ← 새 행
   }
   ```
2. **`link/gate.yaml` `declared_gate_refs`** — `{gate_ref: link-gate:<name>, meaning: …}` 추가
   (레지스트리와 drift나면 RED).
3. **프리셋서 부를 수 있게 하려면** `link/gate.yaml` `post_d_base_gate_matrix.concepts`에
   `{concept_ref: <token>, live_surface: link-gate:<name>, meaning, must_not: […]}` 추가 —
   프리셋 `gate_concept_profile` 어휘가 여기서 SOURCED. 안 올리면 프리셋의 그 토큰이
   `invalid_chain_gate_concept_profile`로 RED.
4. **`AGENTS.md`** — 게이트 ref가 정규식 `link-gate:[a-z-]+`로 스크랩됨 → 새 ref를 언급.

## 단일소스 가드 (위반 금지)

`check_gate_registry_single_source`:
- **RULE 1** — `link/spec.py` 밖에서 `link-gate:` 문자열 **2개 이상**을 담은 리터럴 금지(어휘
  재-열거 금지). 단일 비교(`x == "link-gate:human"`)나 1-원소 값은 OK.
- **RULE 2** — support materializer서 placement 규칙을 **다시 짓지 마라** — `gate_placement_for_row`에
  위임. (스킬 콘텐츠인 이 .md는 agent/brick/link/support 트리 밖이라 RULE 영향 없음.)

## 3단계 — 사용 가능 확인 (in-repo, 실행으로만)

레지스트리를 로드해 새 ref가 파생을 관통하는지 확인:
```bash
PYTHONPATH=support/import_identity uv run python3 -c "
import brick_protocol.link.spec as L
import brick_protocol.link.gate as G
assert 'link-gate:<name>' in L.DECLARED_GATE_REFS, 'spec missing'
assert 'link-gate:<name>' in G.DECLARED_GATE_REFS, 'derivation missing'
print('GATE-WIRED')
"
```
그 다음 단일소스 + 카탈로그 크로스체크 프로파일 green == 게이트가 **placement 가능**:
```bash
HOME=$(mktemp -d) PYTHONPATH=support/import_identity uv run python3 \
  support/checkers/check_profile.py --profile gate_registry_single_source
HOME=$(mktemp -d) PYTHONPATH=support/import_identity uv run python3 \
  support/checkers/check_brick_template_catalog_restructure.py    # link_gate_token_drift 통과
```
마지막에 한 번 `check_profile.py --all` exit 0으로 reconcile.

## 알아둘 것
- support 코드 편집은 **#2의 positional 인덱스 동기화 1줄**뿐 — 그 외 placement/어휘 로직을
  support에 손배선하면 단일소스 가드 RED.
- 추가형 유지. 기존 게이트 행 수정·재배치는 positional 인덱스 전부에 파급 — APPEND만.
