Fresh smoke after commit ec43f0b: verify the Claude QA execution-permission fix is applied in a new Building process.

Context:
Commit ec43f0b changed Claude local invocation to emit --allowedTools alongside --tools for write-effective/read-tier requests. The prior failure mode was Claude code-attack-qa reporting python/checker execution as approval-gated despite write_scope and Bash in --tools.

Brick objective:
Run a new official Building after ec43f0b and verify whether the QA lane using adapter:claude-local can execute harmless commands/checkers without approval blocking.

Required work:
1. Work step should create a small support record under project/brick-protocol/status/kernel/claude-qa-execution-fresh-smoke-0625.md summarizing what is being smoked and the expected evidence.
2. QA step must independently drive at least these harmless commands from its sandbox/cwd if permitted:
   - python3 -c 'print(42)'
   - git diff --check
   - optionally uv run python3 -m py_compile support/connection/adapter_local_cli.py
3. QA must report whether execution succeeded or was still approval-gated. If still gated, return non-binding transition_concern_evidence against the adapter invocation boundary.
4. Closure must preserve proof limits: this is support evidence only, not provider quality/success/source truth.

Write scope:
- project/brick-protocol/status/kernel/claude-qa-execution-fresh-smoke-0625.md

Return shape:
made_changes, changed_files, observed_evidence, commands_run, blocked_or_missing_evidence, handoff_refs, not_proven.
