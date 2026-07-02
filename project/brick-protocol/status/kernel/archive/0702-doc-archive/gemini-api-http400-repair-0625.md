# gemini-api-http400-repair-0625

## changed files

- `support/connection/adapter_constants.py`
- `support/connection/agent_adapter.py`
- `support/connection/adapter_gemini_http.py`
- `support/connection/adapter_local_cli.py`
- `support/checkers/lib/kernel_checks.py`
- `project/brick-protocol/status/kernel/gemini-api-http400-repair-0625.md`

## commands

- `git diff --check` -> exit 0.
- `uv run python3 support/checkers/check_profile.py --profile agent_axis_behavioral` -> exit 0; profile passed with 217 declarative rule observations and 9558 kernel targets inspected.
- `uv run python3 support/checkers/check_profile.py --profile core` -> exit 0; profile passed with 101 declarative rule observations and 5449 kernel targets inspected.
- `rg -n "gemini-2\.5-flash" support/connection support/checkers/lib/kernel_checks.py project/brick-protocol/status/kernel || true` -> no matches.

## narrowly_proven

- `adapter:gemini-api` model-ref default, API fallback, HTTP text seam default, and checker expected endpoint/model literals now align on `gemini-3.5-flash`.
- The local Gemini CLI fallback on the declared Gemini path now aligns on `gemini-3.5-flash`.
- The `gemini_api_adapter` kernel check observed the mocked request endpoint at `v1beta/models/gemini-3.5-flash:generateContent` and returned `api_model_name` as `gemini-3.5-flash`.
- The scoped grep found no remaining `gemini-2.5-flash` on the declared adapter/checker/status surface.

## not_proven

- Live Gemini API provider availability.
- Credential validity.
- Provider semantic compatibility beyond local adapter/checker literals.
- Provider request/response bodies, because this repair must not store live provider bodies.

## remaining_delta

- A post-repair four-LLM Gemini lane proof should be rerun after targeted checks pass, because this repair changes the Gemini API model route literal.
