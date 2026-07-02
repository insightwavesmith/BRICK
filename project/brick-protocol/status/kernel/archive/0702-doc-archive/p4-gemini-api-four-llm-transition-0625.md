# P4 Gemini API Four-LLM Transition - 2026-06-25

## Observed Evidence

- `brick/templates/presets/four-llm-standard-graph.md` now declares the
  `gemini-broad-review` inspect lane with `selected_adapter_ref: adapter:gemini-api`.
- Nearby preset prose now says the inspector admits `gemini-api` for the Gemini
  read-only inspect lens. No Agent Object or Agent resource file was changed.
- `support/operator/report_sinks.py` now distinguishes Slack lane labels for:
  `adapter:gemini-api` -> `Gemini API`, `adapter:gemini-local` -> `Gemini Local`,
  `adapter:claude-local` -> `Claude Local`, `adapter:codex-local` -> `Codex Local`,
  and `adapter:codex-fugu-local` or `model:sakana:fugu` -> `Fugu`.
- Existing intervention-required Slack owner text remains caller/COO-oriented.

## Commands Run

- `git diff --check -- brick/templates/presets/four-llm-standard-graph.md support/operator/report_sinks.py`
  - observed exit code: 0
- `uv run python3 -m py_compile support/operator/report_sinks.py`
  - observed exit code: 0
- `uv run python3 - <<'PY' ... _slack_lane_label mapping smoke ... PY`
  - observed exit code: 0
  - observed output: `slack lane label mapping smoke passed`
- `uv run python3 support/checkers/check_profile.py --profile agent_axis_behavioral`
  - observed exit code: 0
  - observed summary: `profile passed: agent-axis-behavioral`
- `uv run python3 support/checkers/check_profile.py --profile read_side_projection_boundary`
  - observed exit code: 0
  - observed summary: `profile passed: read-side-projection-boundary`
- `uv run python3 support/checkers/check_profile.py --profile building_skill_preset_agent_tool_hardening`
  - observed exit code: 1
  - observed blocker: `preset_building_completion_case` expected `complete` for
    `building-chain-preset:four-llm-standard-graph`, observed `agent_incomplete`.

## Narrowly Proven

- The edited Python file compiles.
- The Slack lane-label helper maps the declared adapter/model cases to the requested labels.
- The required Agent-axis and read-side projection profiles completed without reported violations.
- The four-LLM preset now selects `adapter:gemini-api` for the Gemini broad review lane.

## Blocked Or Missing Evidence

- The optional `building_skill_preset_agent_tool_hardening` profile did not pass after the preset
  moved to `adapter:gemini-api`. Read-only inspection observed that `agent/objects/inspector.yaml`
  already admits `adapter:gemini-api`; the failing profile path uses a preset-completion fixture
  command runner that mocks CLI-style invocations, while the Gemini API adapter is not a local CLI
  adapter. Repairing that fixture would require editing `support/checkers/**`, outside this Brick's
  declared write scope.

## Not Proven

- Live Gemini API provider execution.
- Real Slack delivery behavior.
- Semantic quality of future four-LLM review output.
- That the optional preset hardening fixture is updated for direct Gemini API adapter walks.
- Source truth, success judgment, quality judgment, or Movement authority.

## Next Movement Candidate

- Candidate: `forward`, subject to Link gate and caller/COO disposition. This status row is support
  evidence only and does not choose Movement.
