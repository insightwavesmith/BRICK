# P5 four-LLM Gemini API fixture repair

## Scope

Repair support-checker deterministic preset completion after
`building-chain-preset:four-llm-standard-graph` moved the Gemini broad-review
lane to `adapter:gemini-api`.

## Changes

- `support/checkers/lib/case_runners.py`
  - Added a checker-local `adapter:gemini-api` preset-completion fixture.
  - The fixture patches the Gemini API adapter dispatch seam in-process during
    `preset_building_completion_case` only.
  - It returns the same structured HTTP-adapter shape used by the real Gemini
    API path, without a subprocess, live provider credentials, or URL/body
    response capture.

## Observed Evidence

- `building_skill_preset_agent_tool_hardening` now keeps
  `expected_frontier_kind: complete` and passes for the full current preset set,
  including `building-chain-preset:four-llm-standard-graph`.
- `agent_axis_behavioral` still passes its `gemini_api_adapter` kernel check:
  no-key remains a clean `local_cli_missing` typed adapter error, Gemini API is
  not a local CLI spec, the mocked HTTP request shape is pinned, and HTTP error /
  timeout / malformed response paths raise clean `ValueError`s.
- The optional live four-LLM smoke did not reach provider execution. Attempts
  with a temp `output_root` first exposed declaration-shape guards, then stopped
  at the expected admission guard: `write_scope is required for write-needed
  Brick building-step-template:work`. I did not open a live write-capable
  provider run for this fixture repair.

## Commands Run

- `uv run python3 support/checkers/check_profile.py --profile building_skill_preset_agent_tool_hardening`
  - first run before the second patch still observed `agent_incomplete`
  - final run passed
- `uv run python3 support/checkers/check_profile.py --profile agent_axis_behavioral`
  - passed
- `uv run python3 -m py_compile support/checkers/lib/case_runners.py`
  - passed
- `git diff --check`
  - passed
- Optional smoke attempts:
  - `run_building_intake` with both `project_ref` and explicit temp
    `output_root` rejected before execution
  - `run_building_intake` with colon-form `declared_by` rejected before
    execution
  - `run_building_intake` with documented hyphen-form `declared_by` rejected
    before execution because no Brick write scope was declared

## Not Proven

- Live Gemini credential validity.
- Live four-LLM provider reliability.
- Semantic quality of provider output.
- Success or quality judgment.
- Source truth.
- Movement authority.
