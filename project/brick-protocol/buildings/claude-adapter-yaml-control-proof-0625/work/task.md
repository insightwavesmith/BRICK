BRICK COO declared P3 read-only proof Building: Claude adapter / YAML control proof.

Goal of the objective: prove the principle "adapter = full-power connector, Agent YAML / tool_policy / Brick write_scope = control" and determine WHY Claude currently behaves read-only.

Required read-only investigation (NO file edits, NO git mutation, do NOT invoke a live Claude run):
1. Read support/connection/agent_adapter.py + support/connection/agent_resources.py for adapter:claude-local capability and sandbox/tool projection. Determine whether the adapter itself caps Claude to read-only, or exposes full capability gated by NEED.
2. Read agent/objects/*.yaml + agent/tool_policies/*.yaml to see which lanes carry tool-policy:read-write-scoped vs reviewer-readonly, and how effective_write is computed (Brick write_scope NEED AND tool-policy AND observed-write adapter).
3. Identify the exact seat of Claude read-only behavior among: (a) adapter capability, (b) provider sandbox/env isolation, (c) Agent YAML/tool_policy, (d) Brick write_scope NEED absence. Cite file:line evidence for each candidate and classify each as confirmed / not_proven.
4. Produce a findings report: for a read-only Brick, projected Claude tools should be read-only; for a write-scope Brick with a write-capable lane + adapter capability aligned, write should be admissible. State which of these is proven by code structure vs not_proven without a live run.
5. Keep Brick/Agent/Link/support boundaries explicit; checker green and code reading are support evidence only, not source truth/quality/success/Movement authority. No credential/session bodies.

Return exact observed_evidence (file:line), narrowly_proven, not_proven, and next Movement candidate. Avoid --all and any long live-provider run.
