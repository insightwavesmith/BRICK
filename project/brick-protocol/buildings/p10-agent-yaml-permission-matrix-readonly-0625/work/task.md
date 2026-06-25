# P10 Agent YAML permission matrix read-only verification

Read-only verification of the permission model across Codex, Claude, Gemini API, and Fugu after the current commits.

Goal:
Confirm the current declared permission model and list gaps. Do not modify files.

Verify:
1. Brick write need / write_scope surfaces: work brick requires_brick_write_scope and plan validation behavior.
2. Agent YAML capability: tool_policy_refs and adapter_refs for dev, qa, qa-lead, inspector, coo.
3. Adapter capability: codex-local, claude-local, gemini-api, codex-fugu-local; distinguish local/API where relevant.
4. Effective write formula: Brick write_scope + Agent read-write-scoped + observed-write adapter; no single axis grants write alone.
5. Read-only lanes: QA/Inspector may carry write-capable policy but stay read-only when Brick has no write_scope; COO stays coordination/read-only.
6. Existing evidence from ec43f0b/ac73c86 and ff80f23/036d92d as support evidence only.
7. not_proven and next repair candidates.

Expected output:
A concise matrix in returned evidence; no files changed.

Suggested compact checks:
- read agent/objects/*.yaml
- read brick/templates/bricks/work/brick.md
- inspect support/connection/agent_adapter.py effective_write formula
- inspect support/connection/adapter_local_cli.py Claude --allowedTools path
- inspect support/checkers/lib/kernel_checks.py relevant probes

Do not run broad profile checks unless necessary. Treat all observations as support evidence only, not source truth, success judgment, quality judgment, or Movement authority.
