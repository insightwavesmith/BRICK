# Customer-Ready P3 Brick Provider Env Precedence - 0627

Status: support evidence only.

This record is not source truth, success judgment, quality judgment, or Movement
authority. It records a support repair for the Gemini-local provider-key path.

## Scope

Focused repair:

- The current app/process environment carried a `GEMINI_API_KEY` that live Google
  Generative Language API rejected.
- `~/.brick/report.env` carried a different `GEMINI_API_KEY`.
- The Brick env-file key passed a live Google models endpoint check and a
  Gemini CLI smoke call.
- The Building engine env seam now lets Brick-file provider keys replace stale
  inherited provider keys before the Gemini adapter runs.

## Evidence

Observed before repair:

- Process `GEMINI_API_KEY`: present.
- `~/.brick/report.env` `GEMINI_API_KEY`: present and different from process env.
- Process key live models endpoint: HTTP 400, `API_KEY_INVALID`.
- Brick env-file key live models endpoint: HTTP 200.
- Gemini CLI smoke after loading Brick env file: `OK`.

No credential value is recorded here.

## Three-Axis Attribution

Evidence first:

- P3 C6 reached the Gemini Building Agent step and paused on
  `adapter:gemini-local` `local_cli_nonzero`.
- The rematerialized C6 plan had correct Codex/Gemini casting.
- A valid Brick env-file provider key existed, but the inherited app/process key
  won precedence before this repair.

Brick candidate:

- The C6 Building plan and Brick work composition were not the root defect for
  this finding.

Agent candidate:

- The Gemini Agent step and adapter selection were correct. The support
  brain-connection surface received the wrong provider key from process env.

Link candidate:

- Link correctly held at the Gemini Agent frontier. No Movement, target, route,
  or gate semantics changed in this repair.

Support surface:

- `support/operator/runtime_env.py`
- `support/checkers/check_report_env_autoload.py`
- `support/checkers/profiles/report_env_autoload.yaml`

Rejected one-axis shortcut:

- This was not treated as a new adapter authority problem or a Gemini capability
  problem. The support env seam was using stale inherited provider credentials
  ahead of the Brick operator env-file credential.

Chosen repair surface:

- Keep the generic loader's env precedence behavior.
- Narrowly change the Building engine seam so report keys remain threaded and
  provider keys from the Brick env file replace stale inherited provider keys.

## Verification

Commands run:

```text
python3 - <<'PY'
...call Google models endpoint using ~/.brick/report.env GEMINI_API_KEY...
PY

PYTHONPATH=support/import_identity python3 - <<'PY'
...load_report_env_into_process and compare redacted key fingerprints...
PY

PYTHONPATH=support/import_identity python3 - <<'PY'
...Gemini CLI smoke with Brick env-file key...
PY

PYTHONPATH=support/import_identity python3 support/checkers/check_report_env_autoload.py
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile report_env_autoload
python3 -m py_compile support/operator/runtime_env.py support/checkers/check_report_env_autoload.py
python3 -m compileall -q support/operator support/checkers
git diff --check
```

Observed focused evidence:

- `load_report_env_into_process()` replaced the inherited process provider key
  with the Brick env-file provider key.
- `check_report_env_autoload.py` passed.
- `check_profile.py --profile report_env_autoload` passed.
- Python compile checks passed.
- `git diff --check` passed.

## Narrowly Proven

- `~/.brick/report.env` contains a Gemini provider key that live Google API
  accepts.
- The inherited process key and the Brick env-file key were different.
- The engine seam now gives Brick-file provider keys precedence over stale
  inherited provider keys.
- Report keys are still returned for threading and are not newly injected into
  the global process env by this repair.

## Not Proven

- P3 C6 closure.
- Full customer-ready proof.
- Full `check_profile.py --all`.
- Future provider availability.

## Movement

P3 provider-env repair: FORWARD as support evidence.

Global customer-ready goal: still not closed until the rematerialized C6 Building
is rerun and produces Gemini Building QA plus Codex closure evidence.
