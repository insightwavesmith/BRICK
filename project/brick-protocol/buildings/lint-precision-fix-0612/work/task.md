# Checker lint false positive: 'sk-' substring marker trips on 'task-source:*' refs

## Objective
Fix a reproduced false positive in `support/checkers/check_building_lifecycle_path_shape.py` `has_sensitive_text()`: the marker tuple `("sk-", "bearer ", "api_key", "api-key")` does a plain SUBSTRING match, so the legitimate sentinel ref `task-source:inline-statement` matches via "ta**sk-s**ource". An honest, engine-written adapter-error capsule carrying `task_source_ref: task-source:inline-statement` is therefore rejected with "adapter-error must not contain credential-like text", turning the whole yard RED.

Reproduction (already verified by the operator — trust but re-run):
- `'sk-' in 'task-source:inline-statement'.lower()` → True
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all` → exit 1, rejecting
  `project/brick-protocol/buildings/adapter-30-s1-park/work/step-outputs/adapter-30-s1-park-work-attempt-1/adapter-error.json`.

## Required fix shape
- Tighten ONLY the `sk-` marker in `has_sensitive_text` so it no longer matches inside ordinary hyphenated words like "task-source", WITHOUT weakening true-positive coverage: a real key-looking token (e.g. `sk-` followed by a long key tail, in the spirit of the `has_credential_text` regex `\bsk-[A-Za-z0-9._~+/=-]{12,}\b`) must STILL be rejected. A word-boundary/regex form for the `sk-` marker is the expected shape. Leave the `"bearer "`, `"api_key"`, `"api-key"` markers as they are.
- Do NOT delete the check. Do NOT relax `has_credential_text`. Do NOT special-case a file path. Do NOT add a "task-source" allowlist/exemption — the fix is matcher PRECISION, not an exemption.

## Proof required (run these and report results honestly in your return)
1. Python probe: `has_sensitive_text` on a value containing `task-source:inline-statement` → False. True-positive probes: build the key-looking tokens AT RUNTIME by string concatenation — e.g. `"sk" + "-" + "A" * 16` and `"bearer" + " " + "x" * 16` — and assert each still → True. NEVER write a credential-shaped literal into any file (the intake guard `_RAW_SECRET_PATTERNS` in `support/operator/primitives.py` rejects such literals — and that guard's word-boundary + 12-char-tail regex style is exactly the precision precedent your fix should follow).
2. Full gate with the existing yard evidence in place:
   `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all` → exit 0
   (the previously rejected capsule must now pass).
3. If any profile fixture pins the OLD substring behavior, update only that pinned expectation and say so explicitly in your return.

## Constraints
- Write scope: support/checkers/ only.
- Append-only history: do not touch anything under project/.
- This is a checker PRECISION fix; if the only way you find is deleting coverage, stop and report instead.

## Desired Output
The tightened marker, the probe results, and the full-gate exit code — claimed only from actual execution.
