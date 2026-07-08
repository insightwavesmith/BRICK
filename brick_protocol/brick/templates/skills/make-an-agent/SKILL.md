---
name: make-an-agent
description: BRICK 새 에이전트 OBJECT(레인) 만들기. 새 lane(역할 야물)을 추가할 때 — brick_protocol/agent/objects/<name>.yaml 작성 + hook 바인딩 등록, 끝에 resolve_agent_object green = dispatch 가능 증명. 키셋은 brick_protocol/agent/spec.AGENT_OBJECT_SCHEMA 단일소스가 봉인.
---

# 새 에이전트 OBJECT(레인) 만들기 (scaffold → register → 사용 가능 확인)

법 (Smith 0612): **선언 = COO 직접 제작 가능, 문지기는 체커.** OBJECT는 **자동 발견**된다
(`list_agent_object_refs`가 `brick_protocol/agent/objects/*.yaml` glob) — 코드/스키마 안 고친다. 키셋은
`brick_protocol/agent/spec.AGENT_OBJECT_SCHEMA`(단일소스)가 봉인. 케이던스: per-step compileall, 끝에 `--all` 1회.

## 1단계 — scaffold (`brick_protocol/agent/objects/<name>.yaml`)

기존 레인(예: `brick_protocol/agent/objects/qa.yaml`, `dev.yaml`)을 본떠 닫힌 키셋을 유지한다.

```yaml
{
  "object_ref": "agent-object:<name>",   # 정확히 이 형태
  "name": "<name>",                       # 디렉터리 슬러그와 동일
  "lane": "<lane>",                       # leader/worker/reviewer/monitor/report/external/native-dispatch-performance-mode
  "callable_performer_refs": ["callable:local:agent-invoke0-smoke"],
  "prompt_refs": ["prompt:<…>"],          # brick_protocol/agent/prompts/<…>.md 실재해야
  "skill_refs": ["skill:<…>"],            # brick_protocol/agent/skills/<…>/ 실재해야
  "hook_refs": [ ... ],                    # 아래 권위 규칙 + bindings.yaml과 정확히 일치
  "tool_policy_refs": [ ... ],
  "discipline_refs": ["discipline:closed-agentfact", "discipline:proof-limits"],
  "adapter_refs": ["adapter:local","adapter:codex-local","adapter:gemini-local","adapter:claude-local"],  # 능력 선언
  "preferred_adapter_ref": "adapter:<…>", # ★ 반드시 위 adapter_refs의 멤버(fail-closed)
  "preferred_model_ref": "model:<provider>:<…>"  # 선택. adapter의 provider와 일치해야
}
```

**키셋(허용/금지)은 `AGENT_OBJECT_SCHEMA`가 봉인** — head keys + `CASTING_FIELDS`서 파생된
casting 다이얼(`preferred_adapter_ref`/`preferred_model_ref`/`preferred_reasoning_effort_ref`) +
ref_fields(prompt/skill/hook/tool_policy/discipline/adapter). **금지**:
provider_connector_refs / credential_body / session_id / success / failure / quality /
movement_choice / default_gatefact (provider 결합·판정 권위는 Agent 레코드가 절대 못 듦).

## 권위 규칙 (전부 하드, `_validate_agent_authority`)

- 모든 OBJECT는 `hook:instruction-chain-read` + `hook:resource-ref-redaction`를 **반드시** 가짐.
- `preferred_adapter_ref` ∈ 자기 `adapter_refs` (fail-closed 다이얼; 안 맞으면 거부).
- write-tier 정책(`tool-policy:read-write-scoped` **또는** `tool-policy:probe-write-scoped`) ⇒
  lane ∈ {worker, leader, reviewer} **그리고** observed-write 어댑터 보유(`_OBSERVED_WRITE_ADAPTER_REFS`:
  codex-local/codex-fugu-local/claude-local/gemini-local). 둘은 semantic_capability_classes로 갈린다 —
  `read-write-scoped`는 `read`+`probe_write`+`verification_write`+`source_write`+`artifact_write`(구현자용,
  실소스 변경 가능), `probe-write-scoped`는 `read`+`probe_write`+`verification_write`만(`source_write`/
  `artifact_write` 금지, 리뷰어 W1 워크트리 프로브/검증 전용).
- `lane==leader` ⇒ `hook:leader-write-need-gate` + `tool-policy:leader-coordination`.
- `lane==reviewer` ⇒ `hook:reviewer-no-mutation` (+ `tool-policy:probe-write-scoped` 없으면
  `tool-policy:reviewer-readonly` 필수). 오늘 실제로는 `qa`/`inspector`/`qa-lead`가 `probe-write-scoped`를
  들고, `reviewer-readonly`는 정의만 되고 어떤 OBJECT도 안 듦(unbound fallback).
- `tool-policy:web-capable` ⇒ pm-lead / design-lead 만.

## 2단계 — register (hook 바인딩, 순서 정확히)

`brick_protocol/agent/hooks/bindings.yaml`의 `bindings`에 항목을 추가한다. 로더는 바인딩 항목을 **요구**하고
OBJECT의 `hook_refs`와 **정확히 같은 순서로 같은 집합**이어야 한다(agent_resources `binding mismatch`).

```yaml
"agent-object:<name>": [ <hook_refs 그대로, 같은 순서> ]
```
각 hook은 `brick_protocol/agent/hooks/registry.yaml`에 `execution_opened: false`로 실재해야 한다.
`prompt_refs`/`skill_refs`는 `brick_protocol/agent/prompts/*` / `brick_protocol/agent/skills/*`로 해석돼야 한다.

## 3단계 — 사용 가능 확인 (in-repo, 실행으로만)

OBJECT를 **로드**하면 `validate_agent_object_keys` + `_validate_agent_authority`가 둘 다 돈다.
로드가 green이면 그 레인은 **dispatch 가능**:

```bash
PYTHONPATH=brick_protocol/support/import_identity uv run python3 -c "
from brick_protocol.support.connection.agent_resources import resolve_agent_object
r = resolve_agent_object('agent-object:<name>')
print('role=', r['role'], '| object_ref=', r['agent_object']['object_ref'])
print('AGENT-OBJECT-LOADABLE')
"
```
그 다음 agent-object 프로파일 + 마지막 `check_profile.py --all` exit 0으로 reconcile:
```bash
HOME=$(mktemp -d) PYTHONPATH=brick_protocol/support/import_identity uv run python3 \
  brick_protocol/support/checkers/check_profile.py --profile agent_object_schema_single_source
```

## 알아둘 것
- 스키마/`AGENT_OBJECT_SCHEMA`/체커를 **고치지 않는다** — OBJECT 추가는 글로브로 자동 발견.
  `check_agent_object_schema_single_source`는 스키마 key-set을 `brick_protocol/agent/spec.py` 밖에서 **재-열거**할
  때만 RED(by-name read `obj.get("adapter_refs")`는 clean).
- `preferred_model_ref`는 `preferred_adapter_ref`의 provider와 일치해야(model 다이얼이 adapter
  source에 coupling). codex 어댑터엔 `model:codex:*`, gemini엔 `model:gemini:*`, claude엔
  `model:claude:*`.
- 추가형 유지. 기존 레인 수정은 그 레인을 쓰는 KIND·프리셋 영향 먼저 grep.
