---
name: make-a-brick
description: BRICK 새 브릭 KIND 만들기 (scaffold-then-register). 새 종류의 브릭(예: 새 검증/설계/구현 변형)을 추가할 때. scaffold_brick_kind 헬퍼가 brick.md+return.yaml 작성 + 카탈로그 등록까지 하고, 끝에 체커 green = Builder가 해석 가능 증명.
---

# 새 브릭 KIND 만들기 (scaffold → register → 사용 가능 확인)

법 (Smith 0612): **선언 = COO가 빌딩 밖에서 직접 제작 가능.** 문지기는 빌딩이 아니라 **체커**다.
KIND는 **데이터**다 — `brick_protocol/brick/spec.BrickSpec` 코드를 안 고친다. 새 casting 다이얼은 `CASTING_FIELDS`로
자동 흘러든다. 케이던스: **스텝마다 compileall만, 끝에 `--all` 한 번.** 핀 완화 금지. 주장은 실행 결과만.

## 1단계 — scaffold (헬퍼가 2파일 + 카탈로그 등록)

`support.operator.brick_kind_scaffold.scaffold_brick_kind`가 다 한다:
`brick_protocol/brick/templates/bricks/<kind>/brick.md` + `return.yaml` 작성 + 카탈로그 `active` 등록.

```python
# cd /path/to/BRICK && uv run python3 -c "exec(open('/tmp/mk.py').read())"
from brick_protocol.support.operator.brick_kind_scaffold import scaffold_brick_kind
rec = scaffold_brick_kind(
    "<kind-slug>",                         # 디렉터리 슬러그 = brick_kind. [-a-z0-9], 첫 글자 [a-z0-9]
    brick_word="<짧은 명칭>",
    performer_word="<수행자 단어>",         # 예: dev / qa / coo
    requires_brick_write_scope=False,       # write 필요한 KIND면 True
    performer_lane_need="<lane>",           # worker/leader/reviewer/monitor/...
    link_movement_literal="forward",
    brick_contract="<이 KIND가 무엇인지 한 문장>",
    required_return_shape=["observed_evidence", "<…>", "not_proven"],  # 비어있지 않게
    body_paragraph="<## 본문에 들어갈 지시 한 문단>",
    agent_object_hint_ref="agent-object:<slug>",  # 선택. brick_protocol/agent/objects/<slug>.yaml 실재해야
    carries_forward_fields=["<shape의 부분집합>"], # 선택. 다운스트림에 운반할 필드
)
print(rec)  # kind / brick_md_path / return_yaml_path / primary_return_ref /
            # catalog_registered / admission_registered / admission_registration_required
```

헬퍼가 보장하는 불변식:
- **brick_kind == 디렉터리 슬러그** (안 맞으면 체커 RED).
- **primary required_return_template_refs[0] == `brick_protocol/brick/templates/bricks/<kind>/return.yaml`** (정확히).
  entry[1]은 관례상 `…/transition-concern-return.yaml`(헬퍼가 자동 추가).
- **본문↔return 불변식**: `required_return_shape`의 **모든 필드**가 `##` 본문에 word-boundary
  토큰으로 등장(헬퍼가 "Return: … `field`, …" 줄을 자동으로 박아 by construction 통과).
- **금지 반환 키 명시**(success/failure/approved/quality/movement_choice/route_target).
- 은퇴 철자(write_need/role_need/agent_word/return_template/default_link/default_agent) 안 씀.

## 2단계 — (필수) 새 KIND를 커널 admission 게이트에 등록

KIND는 데이터지만, 새 KIND **디렉터리**는 커널 보안 게이트(`check_package_path_admission`)의
**닫힌 허용목록**(`TEMPLATE0_BRICK_KINDS`)에 슬러그가 없으면 `core`·`structure_template_integrity`
프로파일(=`--all`)이 `bricks/<kind>` 경로를 **unadmitted로 거부**한다. (이 허용목록은 디스크에서
자동 유도하지 않는다 — 자동 유도하면 게이트가 무의미해지므로. 그래서 헬퍼가 대신 못 고치고,
**리뷰된 한 줄 등록**으로 사람이 추가한다.)

scaffold 직후 `rec["admission_registered"]`가 `False`면 `rec["admission_registration_required"]`가
정확한 위치를 알려준다. `brick_protocol/support/checkers/check_package_path_admission.py`의 `TEMPLATE0_BRICK_KINDS`
세트(알파벳 순)에 슬러그 한 줄을 추가한다:
```python
TEMPLATE0_BRICK_KINDS = {
    "axis-attack-qa",
    "<kind-slug>",   # ← 새 KIND. 슬러그 == brick.md의 brick_kind == 디렉터리명.
    "closure",
    ...
}
```
이건 게이트 완화가 아니라 **새 KIND를 명시적으로 admit하는 등록**이다(카탈로그 active 등록과 동급).
추가 후 `check_package_path_admission.py`는 코드가 바뀌었으니 **compileall** 한 번.

## 3단계 — (선택) KIND를 NEEDED로 만들기

scaffold만으로는 KIND가 로드 가능·고아 아님이지만 **아직 어느 프리셋도 안 쓴다.** 빌딩이 실제로
쓰게 하려면 프리셋에 스텝을 추가한다 (`brick_protocol/brick/templates/presets/<name>.md`):
```yaml
steps:
  - step_template_ref: building-step-template:<kind>
    brick_spec_ref: brick_protocol/brick/templates/bricks/<kind>/brick.md
    target_word: <…>
```
active step-template 레지스트리는 `bricks/<kind>/brick.md`에서 SOURCED(별도 step-templates.yaml
없음). 체커는 모든 프리셋 ref가 active KIND로 해석되는지 검증한다.

## 4단계 — 사용 가능 확인 (in-repo, 실행으로만)

⚠️ 체커 **스크립트를 직접** 돌리면(`python3 brick_protocol/support/checkers/check_bricks_spec_completeness.py`)
admission 게이트를 **건너뛰어** false-green이 난다(스크립트는 "resolvable"이라 하지만 `--all`은
미등록 KIND 경로를 거부). 그러니 **프로파일 러너**로 돌린다 — 프로파일이 admission을 함께 건다:

```bash
# core: bricks-spec U2 in-process 회귀(진짜 Builder 경로로 registry 빌드 →
#   resolved agent_object_ref == 선언 hint, registry shape == primary template shape)
#   + package_path_admission 게이트.
PYTHONPATH=brick_protocol/support/import_identity uv run python3 \
  brick_protocol/support/checkers/check_profile.py --profile core                       # exit 0
# structure_template_integrity: 카탈로그 orphan_physical_template 없음 + admission.
PYTHONPATH=brick_protocol/support/import_identity uv run python3 \
  brick_protocol/support/checkers/check_profile.py --profile structure_template_integrity   # exit 0
```
**이 두 프로파일 green == KIND가 Builder가 해석 가능 AND admit됨** (= 다음 발사에서 로드됨).
2단계 admission 등록을 빠뜨리면 `core`가 "not listed in current seed admission set"로 거부한다 —
이게 바로 직접-스크립트 경로가 못 잡는 갭이다. 마지막에 한 번 `check_profile.py --all` exit 0 reconcile.

## 알아둘 것
- KIND는 데이터 — `brick_protocol/brick/spec.py` 안 고친다. `BRICK_ROW_ALLOWED_KEYS`는 새 brick-ROW *키*를
  더할 때만 바뀐다(보통 안 바뀜).
- `carries_forward_fields`는 반드시 `required_return_shape`의 부분집합(헬퍼가 강제).
- scaffold는 **추가형**. 기존 KIND 수정은 그 KIND를 쓰는 프리셋·체커 영향을 먼저 grep.
