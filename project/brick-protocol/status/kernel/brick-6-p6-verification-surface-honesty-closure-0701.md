# BRICK 6 P6 Verification surface honesty closure evidence - 2026-07-01

## Scope

- Phase: P6 - Verification surface honesty.
- Repo: `/Users/smith/projects/BRICK`.
- Base before P6 sequence: `94f4696`.
- Current adopted HEAD after P6 sequence: `40ea12d`.
- P6 evidence root:
  - `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p6-verification-surface-honesty-0701a`.

## Adopted commits

```text
dd6e407 P6: declare verification surface honesty graph
40ea12d P6: correct verification surface honesty
```

## Observed evidence

- P6a official `brick build --graph` ran the declared graph and produced design, work, code-QA, axis-QA, and work-reroute evidence.
- P6a frontier ended `link_paused`, not complete. The pause was caused by QA concerns that the P6 sandbox `check_profile.py --all` run returned rc 1 in `read_side_projection_boundary/intake_evidence_projection_case` with `frontier='agent_incomplete'`.
- Current main without the P6 implementation diff was remeasured and `check_profile.py --all` returned rc 0, indicating the P6a sandbox all-profile mismatch was not a standing main baseline failure.
- The P6 implementation diff was materialized narrowly on current main from the P6a work evidence:
  - removed the misleading `[tool.pytest.ini_options] testpaths = ["support/checkers"]` declaration from `pyproject.toml`;
  - added `brick_cli_entrypoint` profile `text_absent` guards against reintroducing the pytest/support-checkers declaration;
  - updated `support/docs/references/setup.md` to measure the profile count instead of pinning `24 profiles`;
  - updated `support/docs/references/checker-profile-map.md` so profile/preset/kernel-check counts are measured checkout facts, not constants; current observations: profiles=29, presets=28, distinct kernel checks=64.

## Verification commands after materialization on main

```text
python3 direct pyproject probe: PASS (`[tool.pytest.ini_options]` absent)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/brick_cli_entrypoint.yaml: PASS
negative temp-copy probe reintroducing `[tool.pytest.ini_options]` + `testpaths = ["support/checkers"]`: RED as expected (`text_absent rejected pyproject.toml`)
git diff --check: PASS
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all: PASS (`RC=0`)
```

## Narrowly proven

- `pyproject.toml` no longer advertises `support/checkers` as a pytest suite.
- Reintroducing the misleading pytest declaration drives the focused `brick_cli_entrypoint` profile RED.
- The active setup/checker-map docs no longer present stale fixed `24`/`28` profile counts as active truth; profile and kernel-check counts are measured from the checkout.
- Focused profile and `check_profile.py --all` agree on current main after the P6 materialization.
- Checker/profile green is explicitly preserved as support evidence only, not source truth, success judgment, quality judgment, or Movement authority.

## Not proven / proof limits

- P6a did not close as a frontier-complete Building; it ended `link_paused`. The final materialization was verified on current main using P6a evidence, not adopted as a completed P6a sandbox commit.
- P6 does not prove P7 product route, P8 ship safety, P9 dynamic proof, provider reliability, release/dashboard hardening, fresh-machine install, or customer comprehension.
- CI/branch-protection release-gate proof remains not proven.
- Checker/profile green is support evidence only.

## Next Movement candidate

Proceed to P7: product route / P3 Easy Building surface, unless Smith requires a separate rerun that closes P6 as a frontier-complete Building with the same implementation.
