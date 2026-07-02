# P10 Agent YAML Permission Matrix Reroute

## Scope

This report corrects the prior P10 HOLD classification gap: `adapter:codex-fugu-local`
is an admitted provider-neutral adapter row with read+write technical capability and
observed-write support. Adapter capability still does not grant write authority by
itself.

## Corrected Matrix

| Surface | Source rows | Adapter capability | Agent policy | Effective write posture |
| --- | --- | --- | --- | --- |
| Codex Local (`adapter:codex-local`) | `support/connection/adapter_constants.py:15`, `:75-77`, `:79-95` | read+write; observed-write adapter | Effective only for Agents carrying `tool-policy:read-write-scoped` | Write opens only when the Brick declares `write_scope`; otherwise read-only request posture. |
| Claude Local (`adapter:claude-local`) | `support/connection/adapter_constants.py:22`, `:75-77`, `:96-98` | read+write+web; observed-write adapter | Effective only for Agents carrying `tool-policy:read-write-scoped` | Write opens only when the Brick declares `write_scope`; otherwise read-only request posture. |
| Gemini API (`adapter:gemini-api`) | `support/connection/adapter_constants.py:24`, `:102-105`; `agent/objects/inspector.yaml:35` | read+review, not write; not in observed-write adapter set | Even if an Agent has read-write-scoped policy, this adapter lacks observed-write support | No effective write under the current formula. |
| Fugu (`adapter:codex-fugu-local`) | `support/connection/adapter_constants.py:21`, `:64`, `:75-83`, `:93-95` | read+write; observed-write adapter; Sakana provider route through the Codex executable path | Effective only for Agents carrying `tool-policy:read-write-scoped` | Write opens only when the Brick declares `write_scope`; read-only Brick lanes remain read-only without one. |
| COO (`agent-object:coo`) | `agent/objects/coo.yaml:29-40` | Lists local/codex/fugu/claude adapters | Has only `tool-policy:leader-coordination`; no `tool-policy:read-write-scoped` | Coordination/read-only posture. No effective write because the Agent policy term is false. |

## Effective Write Formula

Observed source formula:

```text
effective_write =
  bool(request.write_scope)
  AND "tool-policy:read-write-scoped" in request.tool_policy_refs
  AND adapter_ref in _OBSERVED_WRITE_ADAPTER_REFS
```

Source: `support/connection/agent_adapter.py:868-877`.

The raw request observation exposes the same three inputs as data:
`write_scope_present`, `tool_policy_has_read_write`, and
`adapter_supports_observed_write` (`support/connection/agent_adapter.py:1105-1132`).

`brick/templates/bricks/work/brick.md:1-12` declares `work` as requiring
`requires_brick_write_scope: yes`. That Brick contract is the Brick-side term in
the formula; adapter identity alone is not a write grant.

## Fugu Correction

`adapter:codex-fugu-local` is not merely a persona or step-role label. Current
source admits it as:

- a constant: `ADAPTER_CODEX_FUGU_LOCAL = "adapter:codex-fugu-local"`
  (`support/connection/adapter_constants.py:21`);
- an allowed adapter ref (`support/connection/adapter_constants.py:79-88`);
- an observed-write adapter alongside Codex Local and Claude Local
  (`support/connection/adapter_constants.py:75-77`);
- a read+write capability row (`support/connection/adapter_constants.py:90-95`);
- a Sakana provider route for model selection (`support/connection/adapter_constants.py:62-65`).

The permission law is unchanged: Fugu's technical read+write capability is
insufficient without a Brick-declared `write_scope` and an Agent Object carrying
`tool-policy:read-write-scoped`.

## Agent Object Observations

- `agent/objects/dev.yaml:20-34` carries `tool-policy:read-write-scoped` and lists
  `adapter:codex-fugu-local`.
- `agent/objects/qa.yaml:21-35` carries `tool-policy:read-write-scoped` and lists
  `adapter:codex-fugu-local`; reviewer lane does not itself grant authority.
- `agent/objects/qa-lead.yaml:22-36` carries both `tool-policy:leader-coordination`
  and `tool-policy:read-write-scoped`, and lists `adapter:codex-fugu-local`.
- `agent/objects/inspector.yaml:22-37` carries `tool-policy:read-write-scoped` and
  lists both `adapter:codex-fugu-local` and `adapter:gemini-api`.
- `agent/objects/coo.yaml:29-42` carries `tool-policy:leader-coordination` only,
  while listing `adapter:codex-fugu-local`; COO remains coordination/read-only for
  this matrix.

## Commands Run

```text
git status --porcelain
sed -n '1,220p' agent/skills/scoped-implementation/SKILL.md
sed -n '1,220p' agent/skills/protocol-boundary-watch/SKILL.md
nl -ba support/connection/adapter_constants.py | sed -n '1,220p'
rg -n "ADAPTER_CODEX_FUGU_LOCAL|ALLOWED_ADAPTER_REFS|_OBSERVED_WRITE_ADAPTER_REFS|_ADAPTER_CAPABILITIES" support/connection/adapter_constants.py
rg -n "effective_write|write_effective|observed_write|write_scope|tool-policy:read-write-scoped" support/connection/agent_adapter.py
nl -ba support/connection/agent_adapter.py | sed -n '846,884p'
nl -ba support/connection/agent_adapter.py | sed -n '1100,1138p'
nl -ba brick/templates/bricks/work/brick.md | sed -n '1,140p'
nl -ba agent/objects/dev.yaml | sed -n '1,120p'
nl -ba agent/objects/qa.yaml | sed -n '1,120p'
nl -ba agent/objects/qa-lead.yaml | sed -n '1,140p'
nl -ba agent/objects/inspector.yaml | sed -n '1,140p'
nl -ba agent/objects/coo.yaml | sed -n '1,140p'
rg -n "tool-policy:read-write-scoped|tool-policy:leader-coordination|adapter:codex-fugu-local|adapter:gemini-api|adapter:claude-local|adapter:codex-local|adapter:local|preferred_adapter_ref|lane" agent/objects/dev.yaml agent/objects/qa.yaml agent/objects/qa-lead.yaml agent/objects/inspector.yaml agent/objects/coo.yaml
```

`git status --porcelain` showed unrelated untracked Building/status evidence
already present under `project/brick-protocol/buildings/` and
`project/brick-protocol/status/inbox/`. This report did not modify those paths.

## Observed Evidence

- `adapter:codex-fugu-local` is admitted in `ALLOWED_ADAPTER_REFS`.
- `adapter:codex-fugu-local` is included in `_OBSERVED_WRITE_ADAPTER_REFS`.
- `_ADAPTER_CAPABILITIES` gives `adapter:codex-fugu-local` read+write capability.
- `agent_request_effective_write()` requires all three inputs: write scope,
  read-write-scoped Agent tool policy, and observed-write adapter support.
- `work` Brick frontmatter declares `requires_brick_write_scope: yes`.
- COO lacks `tool-policy:read-write-scoped`.

## Narrowly Proven

- The prior classification of `adapter:codex-fugu-local` as persona/step-role only
  does not match current source.
- The corrected matrix preserves the BRICK permission law: adapter write capability
  is technical capability, not authority.
- COO remains coordination/read-only under the effective-write formula because the
  Agent policy term is absent.

## Not Proven

- Provider availability or runtime execution behavior for Codex, Claude, Gemini, or
  Sakana/Fugu.
- Quality, success, or approval of any future Building.
- Movement sufficiency or final route choice.
- Semantic correctness beyond the cited current source rows.

## Next Movement Candidate

Candidate only, not Agent authority: return this corrected support evidence to the
declared Link gate for sufficiency review.
