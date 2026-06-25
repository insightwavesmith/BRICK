# Gemini API HTTP 400 repair design
Read-only diagnosis/design Building for the P12 blocker found in `gemini-api-four-llm-lane-proof-0625`.

Observed blocker:
- `project/brick-protocol/buildings/gemini-api-four-llm-lane-proof-0625/work/step-outputs/gemini-api-four-llm-lane-proof-0625-gemini-broad-review-attempt-1/adapter-error.json`
- adapter_ref: `adapter:gemini-api`
- selected_model_ref: `model:gemini:default`
- exception_type: `ValueError`
- message_excerpt: `gemini-api HTTP error status 400`

Current local surfaces to inspect:
- `support/connection/adapter_gemini_http.py`
- `support/connection/agent_adapter.py`
- `support/connection/adapter_constants.py`
- `support/connection/adapter_model_casting.py`
- `support/checkers/lib/kernel_checks.py` gemini_api_adapter checker
- `support/checkers/profiles/agent_axis_behavioral.yaml`
- `brick/templates/presets/four-llm-standard-graph.md`

Official doc evidence supplied by COO from Google AI docs crawled 2026-06-25:
- Current Gemini generateContent REST example uses `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent`, header `x-goog-api-key`, and body `contents -> parts -> text`.
- Current repo uses `MODEL_REF_GEMINI_FLASH = model:gemini:gemini-2.5-flash` and `_GEMINI_API_MODEL_FALLBACK = gemini-2.5-flash`, while local Gemini CLI path uses 3.5 flash.

Required analyses:
1. Determine the strongest local-code root-cause candidates for HTTP 400 without reading/storing provider body or credentials.
2. Decide whether the minimal repair should update Gemini API default/fallback model to `gemini-3.5-flash`, improve safe HTTPError classification, both, or neither.
3. Specify exact write scope for the repair Building and exact files/checkers to update.
4. Specify verification: deterministic mocked checker, no-key path, request URL/header/body capture, and a live four-LLM lane proof expectation (clean adapter-error is acceptable if provider/key/location fails, but model/request-shape drift should be fixed).
5. Define proof limits and not_proven. Do not edit files. Do not choose Movement or judge quality/success.
Return a precise repair plan, stop conditions, changed-file candidates, checker plan, and next write Building contract.
