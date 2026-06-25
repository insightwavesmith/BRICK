# P10 Agent YAML permission matrix reroute

Reroute from the prior P10 HOLD. The prior read-only Building correctly found a design/verification gap: the plan misclassified `adapter:codex-fugu-local` as a persona/step-role only. Current source shows it is an admitted adapter with read+write capability and observed-write support.

Goal:
Write a corrected permission matrix report that explicitly treats `adapter:codex-fugu-local` as a real adapter, while preserving the BRICK permission law.

Output file:
project/brick-protocol/status/kernel/p10-agent-yaml-permission-matrix-reroute-0625.md

Required content:
1. Corrected matrix for Codex Local, Claude Local, Gemini API, Fugu/codex-fugu-local, and COO.
2. Explain effective_write formula:
   Brick write_scope exists AND Agent has tool-policy:read-write-scoped AND adapter supports observed write.
3. Explain that adapter:codex-fugu-local is admitted and write-capable as technical capability, but read-only Brick lanes remain read-only when no Brick write_scope exists.
4. Preserve COO as coordination/read-only: no read-write-scoped policy.
5. Verify with compact source reads/commands:
   - git status --porcelain
   - rg/nl evidence from support/connection/adapter_constants.py for ADAPTER_CODEX_FUGU_LOCAL, ALLOWED_ADAPTER_REFS, _OBSERVED_WRITE_ADAPTER_REFS, _ADAPTER_CAPABILITIES
   - agent/objects/dev.yaml, qa.yaml, qa-lead.yaml, inspector.yaml, coo.yaml relevant tool_policy_refs/adapter_refs
   - support/connection/agent_adapter.py effective_write formula
   - brick/templates/bricks/work/brick.md requires_brick_write_scope
6. Run `git diff --check -- project/brick-protocol/status/kernel/p10-agent-yaml-permission-matrix-reroute-0625.md`.
7. Record observed evidence, narrowly_proven, not_proven, and next movement candidate.

Allowed writes:
- project/brick-protocol/status/kernel/p10-agent-yaml-permission-matrix-reroute-0625.md

Forbidden:
- Do not edit code, checkers, docs, AGENTS.md, brick/, agent/, link/, support/.
- Do not claim success, quality, source truth, or Movement authority.
