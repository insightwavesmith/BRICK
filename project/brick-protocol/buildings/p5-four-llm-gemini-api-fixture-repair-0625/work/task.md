# P5 four-LLM Gemini API fixture repair and revalidation

Implement the checker/fixture repair needed after commit 036d92d changed four-llm-standard-graph's Gemini lane from adapter:gemini-local to adapter:gemini-api.

Goal:
Keep strict completion semantics. Do NOT allow agent_incomplete as success. Repair the deterministic preset/profile path so gemini-api is handled as an HTTP API adapter, not a local CLI fixture.

Required work:
1. Inspect why `building_skill_preset_agent_tool_hardening` reports agent_incomplete for `building-chain-preset:four-llm-standard-graph` after Gemini API transition.
2. Implement the minimal fixture/profile/checker repair in support/checkers/** so deterministic preset completion can walk gemini-api without spawning a real Gemini local CLI and without needing live provider credentials.
3. Preserve existing gemini-api adapter semantics: no local CLI, no subprocess, clean no-key/HTTP error behavior in the adapter path.
4. Run and record:
   - git diff --check
   - uv run python3 -m py_compile for touched Python files
   - uv run python3 support/checkers/check_profile.py --profile building_skill_preset_agent_tool_hardening
   - uv run python3 support/checkers/check_profile.py --profile agent_axis_behavioral
5. If possible, run a four-llm validation smoke using current preset and record whether frontier reaches complete or adapter-error; if live Gemini credentials are absent, record not_proven rather than weakening fixture semantics.
6. Write a concise report to project/brick-protocol/status/kernel/p5-four-llm-gemini-api-fixture-repair-0625.md.

Allowed writes:
- support/checkers/**
- project/brick-protocol/status/kernel/p5-four-llm-gemini-api-fixture-repair-0625.md

Forbidden:
- Do not edit AGENTS.md, agent/, link/, support/connection/, or provider credential config.
- Do not relax `expected_frontier_kind: complete` to accept agent_incomplete.
- Do not store credentials or provider response bodies.

Treat all checker output as support evidence only, not source truth, success judgment, quality judgment, or Movement authority.
