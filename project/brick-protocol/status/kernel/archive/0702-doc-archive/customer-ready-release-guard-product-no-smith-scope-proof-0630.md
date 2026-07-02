# Customer release guard — product_no_smith_residue widened to skill surfaces (0630)

Status: IMPLEMENTED / support evidence only. Not source truth, not success or
quality judgment, not Movement authority.

## Why this slice existed

Release pruning found a real Smith-local residue leak in customer-facing skill
surfaces (`agent/skills/*` and `brick/templates/skills/*`). The old
`product_no_smith_residue` checker only described/scanned README.md,
`support/docs/spec`, `agent/prompts`, and `support/onboarding/install.sh`, so the
surface that leaked was not durably guarded.

## Building route

- graph packet: `project/brick-protocol/status/kernel/GOAL/release-guard-product-no-smith-scope-0630a.json`
- building_id: `release-guard-product-no-smith-scope-0630a`
- route: `python3 -m brick_protocol.support.operator.cli build --json --non-interactive --graph <packet> --timeout 900`
- shape: Codex `work` -> Codex `code-attack-qa` + Gemini `axis-attack-qa` fan-in -> Codex `closure`
- base_sha: `78eb14cb968dd5f503665fa247fe08770c007510`
- Building sandbox commit: `e2bd76ed19c720be8b1f6a24275bde086a5bf017`
- landed main commit: `065727f` (`BRICK building output: release-guard-product-no-smith-scope-0630a`)
- frontier_kind: `complete`
- evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/release-guard-product-no-smith-scope-0630a`

## Landed change

One-file checker hardening only:

```text
support/checkers/lib/kernel_checks.py | 21 insertions, 4 deletions
```

Changes:

- `_NO_SMITH_RESIDUE_SURFACES` now includes `agent/skills` and `brick/templates/skills`.
- `_no_smith_residue_fire_probe` now injects `/Users/smith` into:
  - `agent/skills/scoped-implementation/SKILL.md`
  - `brick/templates/skills/make-a-brick/SKILL.md`
- Existing README working-example allowance for `insightwavesmith/BRICK` is preserved.
- Checker docstring/output now names the widened skill surfaces.

## Operator verification after landing on main

Commands:

```text
git diff --check
python3 -m compileall -q support/checkers/lib/kernel_checks.py
PYTHONPATH=support/import_identity:. python3 - <<'PY' ... run_product_no_smith_residue(Path('.')) ... PY
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/read_side_projection_boundary.yaml
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
```

Observed:

```text
git diff --check: green
compileall: green
run_product_no_smith_residue: check_id=product_no_smith_residue, inspected=39
read_side_projection_boundary profile: rc=0
check_profile.py --all: exit 0, 28 profiles passed, no real failure lines
```

Direct checker output includes:

```text
product no-Smith-residue scan passed: README.md, support/docs/spec, agent/prompts,
agent/skills, brick/templates/skills, and support/onboarding/install.sh carry no
/Users/smith literal and no hardcoded insightwavesmith org outside the README
working-example allowance; temp-copy FIRE probes for both forbidden families and
both skill surfaces fired RED.
```

## Narrowly proven

- The release-pruning leak surfaces (`agent/skills`, `brick/templates/skills`) are now inside the durable checker scope.
- The live tree has no `/Users/smith` literal in the declared product surfaces.
- `insightwavesmith` remains allowed only for the README working-example line.
- FIRE probes prove the checker goes RED when `/Users/smith` is inserted into each new skill surface.
- The work ran through official `brick build --graph` with code and axis QA fan-in, then landed on main with full profile green.

## Not proven / caveats

- This is a residue-scan guard, not customer comprehension proof.
- It does not run release export or push/tag publication.
- It does not prove future provider reliability, future Building correctness, source truth, success judgment, quality judgment, or Movement authority.

## Next target candidate

- Push main when Smith explicitly OKs external publication.
- Continue FINAL architecture cleanup with the next conservation-ledger-first leaf, or run a release export/fresh-clone validation once origin/main is updated.
