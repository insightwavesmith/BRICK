# Slack LLM Assignee Minimal Validation 0625

## Observed Evidence

- HEAD observed with `git log --oneline -1`: `ff80f23 BRICK reporter: show LLM assignee in Slack updates`.
- Worktree status observed with `git status --porcelain`: one pre-existing untracked file, `?? project/brick-protocol/status/kernel/p2-four-llm-standard-graph-validation-0625.md`.
- `support/operator/reporter.py` carries `current_agent_object_ref`, `current_adapter_ref`, and `current_model_ref` into Building event report packets at packet construction sites observed by `rg`.
- `support/operator/report_sinks.py` renders Slack assignee labels from adapter/model refs before falling back to lane labels: `adapter:codex-local` -> `Codex`, `adapter:claude-local` -> `Claude`, `adapter:gemini-local` -> `Gemini`, and `adapter:codex-fugu-local` or `model:sakana:fugu` -> `Fugu`.
- Direct Python smoke with `PYTHONPATH=support/import_identity python3 - <<'PY' ... PY` printed and asserted:
  - `label adapter:codex-local <none>: Codex`
  - `label adapter:claude-local <none>: Claude`
  - `label adapter:gemini-local <none>: Gemini`
  - `label adapter:codex-fugu-local model:sakana:fugu: Fugu`
  - Existing Building packet over `project/brick-protocol/buildings/claude-adapter-yaml-control-proof-0625` resolved `packet adapter: adapter:claude-local`, `packet model: model:claude:inherit`, and rendered `① 마감 시작했어요. (담당: Claude) (09:00)`.
- Intervention-required Slack text remains disposition-owner oriented. Observed code paths use `required_disposition_owner` and `disposition_owners` label lookup for `intervention_required`, not adapter/model labels. The profile specimen also printed `잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)`.
- `git diff --check -- support/operator/reporter.py support/operator/report_sinks.py` exited 0.
- `uv run python3 -m py_compile support/operator/reporter.py support/operator/report_sinks.py` exited 0.
- `uv run python3 support/checkers/check_profile.py --profile read_side_projection_boundary` exited 0 and printed `profile passed: read-side-projection-boundary (343 declarative rule observation(s), 3918 kernel target(s) inspected)`.

## Narrowly Proven

- Current HEAD contains packet fields for current Agent object, adapter, and model refs on the inspected reporter packet paths.
- The inspected Slack sink logic uses adapter/model-derived labels for ordinary brick received/returned thread replies and preserves caller/COO-oriented owner text for intervention-required messages.
- A shell-level smoke in this checkout proved the requested four adapter/model label mappings and proved `render_building_event_report_packet` over an existing Claude-lane Building can feed Slack rendering that includes `(담당: Claude)`.
- The two inspected Python files compile, have no diff-check whitespace errors, and remain covered by the `read_side_projection_boundary` profile as support evidence.

## Not Proven

- Provider behavior, credential validity, Slack delivery reliability, or any live external Slack delivery.
- Source truth, success judgment, quality judgment, or Link Movement authority.
- Complete semantic correctness of every possible Slack event packet; this was the declared minimal smoke plus the named profile.
- The unrelated untracked file in `project/brick-protocol/status/kernel/p2-four-llm-standard-graph-validation-0625.md` was not inspected or changed.

## Next Phase Recommendation

Carry this as support evidence for the minimal Slack LLM-assignee update. If further confidence is needed, the next phase should be a declared notification/reporting smoke that records a dry-run packet fixture per brick-grain event, still without treating Slack/checker output as source truth or quality judgment.
