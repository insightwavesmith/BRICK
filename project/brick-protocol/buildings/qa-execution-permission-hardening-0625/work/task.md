P0 repair: fix or precisely classify Claude QA execution-permission gap.

Trigger evidence:
Multiple code-attack-qa Bricks using adapter:claude-local reported that python/checker execution was blocked with 'requires approval' even though the QA Brick had write_scope and tool-policy:read-write-scoped. The COO/main environment could run the same commands successfully:
- git diff --check
- python/json validation
- uv run python3 -m py_compile ...
- uv run python3 support/checkers/check_profile.py --profile building_automation (EXIT 0)

Problem statement:
QA without execution verification is not acceptable for code-attack-qa. Determine whether this is:
1. Claude adapter invocation/config issue (permission-mode, tools, settings, sandbox, setting-sources, cwd/env),
2. Agent YAML/tool-policy mismatch,
3. Brick write_scope projection issue,
4. support adapter bug,
5. or expected provider limitation that must route QA execution to codex/gemini/fugu instead of Claude.

Required work:
1. Inspect Claude local adapter invocation construction and compare with codex-local observed-write path.
2. Find why QA Claude can Read/Grep but reports Bash/python requires approval in non-interactive run despite `--permission-mode acceptEdits` and declared write_scope.
3. Implement the smallest safe fix if the root cause is in BRICK adapter/config/projection. If it is a provider limitation, document and enforce routing policy so execution-QA uses an execution-capable adapter and Claude is read-only review only.
4. Add targeted checker/probe proving the intended behavior or explicit limitation:
   - QA adapter with write_scope can run a harmless command/checker, OR
   - plans/presets do not assign execution-QA to claude-local and instead use an execution-capable adapter.
5. Preserve BRICK law: adapter = capability connection, YAML/Brick/Link controls authority; support does not judge success/quality/Movement; no credentials/session bodies; no AGENTS.md mutation.
6. Run targeted verification, git diff --check, compile/import smoke. Avoid broad --all unless needed.

Grounding files to inspect:
- support/connection/adapter_local_cli.py
- support/connection/adapter_subprocess.py
- support/connection/agent_adapter.py
- support/connection/adapter_grant_policy.py
- support/operator/run.py
- support/operator/walker_kernel.py
- agent/objects/qa.yaml, qa-lead.yaml, dev.yaml
- agent/tool_policies/*.yaml
- brick/templates/bricks/code-attack-qa/brick.md
- brick/templates/presets/fast-fix.md and graph presets using code-attack-qa
- recent Building step outputs where QA reports python execution blocked: adapter-timeout-frontier-lifecycle-hardening-0625-reroute4 and building-map-evidence-red-cleanup-0625.

Return shape:
made_changes, changed_files, observed_evidence, commands_run, blocked_or_missing_evidence, handoff_refs, not_proven.
