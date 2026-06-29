# Customer-Ready P5 First Run Official Route Plan - 0628

Status: support evidence only.

This record is not source truth, success judgment, quality judgment, Movement
authority, or credential proof. It records the operator plan for P5 after
three-axis reconciliation with the P3 official-route plan.

## Phase

P5 - onboarding and customer first run.

## Operator Read

P5 is the customer first-run truth surface. It must match P3: first run enters
the official Building route and returns honest readiness/frontier evidence.

P5 is not a provider-auth proof and not a hidden default to whichever model
worked in the operator session.

## Current Measurement

Existing support records show focused P5 repairs:

```text
customer-ready-p5-cli-onboard-first-run-0627.md
customer-ready-p5-gemini-readiness-honesty-0627.md
support/operator/cli.py
support/operator/onboard.py
support/connection/adapter_subprocess.py
support/checkers/profiles/brick_cli_entrypoint.yaml
support/checkers/profiles/building_operator_driver0.yaml
```

Measured direction:

```text
brick init / doctor / onboard expose Codex and Gemini-local readiness.
real-provider task path carries Brick write_scope when work needs write.
doctor separates Gemini API-key presence from credential_validity.
Gemini-local is CLI plus GEMINI_API_KEY or GOOGLE_API_KEY.
Gemini-api remains outside active write/probe-write path.
```

Remaining gaps / current prep evidence:

```text
P5 #6 fresh-machine prep has a fresh-HOME read-side-projection-boundary
profile measurement for the former empty-HOME intake_evidence_projection_case
hazard (operator transcript note: customer-ready-p5-b4-fresh-home-measurement-0630.md); do not carry that hazard as an active unmeasured blocker.
actual origin/main fresh clone -> install -> init/doctor/auth/onboard ->
brick build/fire -> evidence/frontier inspection is still not proven.
README/quickstart/launch-guide currently still point to Python internals or
direct run_building_intake in some places; customer docs are stale.
first-use adapter population needs proof across Claude/Codex/Gemini candidates.
Gemini credential validity remains not_proven without live call.
doctor rows do not yet expose the full requested readiness schema.
FIRST_USE now preserves structured doctor readiness fields for Gemini key
presence and credential_validity=not_proven; Agent YAML auto-population remains
explicitly deferred/not_proven unless a later Agent-owned admission chooses it.
P5-B3 aligns the first-run frontier story: `brick build` exit 0 only means the
CLI returned support evidence; customer-visible Building closure is
`frontier_kind=complete`; every other frontier is `not_ready` and points the
operator/customer to inspect `evidence_root`.
Slack/customer notification reliability is not proven.
```

## Attack Review Delta

Two independent attack reviews found P5 is HOLD as written:

```text
HIGH:
- P5 depends on unclosed P3 official-route gaps.
- customer docs still bypass the planned brick build path with direct
  run_building_intake examples.
- doctor/readiness rows do not yet distinguish every requested field:
  installed, env key present, credential_validity, live-provider-not-run, and
  adapter write/probe/source capability shape.

MEDIUM:
- live CLI provider selection may prefer Claude when all providers are ready,
  while weekend casting keeps Claude outside the active weekend performer pool.
- first-use adapter population is under-specified: current code selects at CLI
  intent time, while Agent Objects remain static.
- provider_preflight is not a standalone profile; it is a kernel check inside
  agent_axis_behavioral.
```

## Three-Axis Attribution

Brick:

```text
owns the first task and its write_scope.
The first customer task must materialize a declared Building Plan, not call a
provider directly.
```

Agent:

```text
owns available performer candidates and selected adapter refs.
First-use provider registration may populate compatible Agent available/
preferred refs, but it is not smart role assignment.
```

Link:

```text
owns frontier, gate sufficiency, Movement, and reroute/hold evidence for the
first run.
```

Support:

```text
install/init/doctor/onboard/CLI/reporting render readiness and route the first
task. They do not prove credential validity or quality.
```

## Implementation Plan

1. First-use adapter population.

```text
When a user logs in/registers Claude, Codex, or Gemini-local, add the provider
to compatible Agent available candidates and preferred_adapter_ref where no
user override exists.
Do not auto-decide that Gemini should plan or that Codex should close because
of registration alone.
Keep user override simple through Agent config/conversation.
This slice needs an explicit owning surface and checker. FIRST_USE readiness
evidence preservation is narrowed and covered separately; Agent YAML
auto-population is NOT_PROVEN and must not blindly mutate Agent YAML.
```

2. Customer default route.

```text
Default customer first run should be Claude/Codex centered when available.
Gemini-local remains an honest optional CLI+API-key lane.
No hidden Claude dependency when Claude is unavailable.
No active gemini-api path.
Weekend casting may still prefer Codex while Claude tokens are unavailable.
Any Claude-first default must be a deliberate post-weekend/default-customer
policy, not an accidental support ordering leak.
```

3. Doctor/readiness honesty.

```text
Doctor rows distinguish:
installed
env key present
credential_validity = proven | not_proven | invalid
live provider not run
adapter write/probe/source capability shape
```

4. Official route seal.

```text
First task must enter the same official route as P3:
brick build -> cli -> driver -> materializer -> run.py -> evidence/frontier.
Do not document direct Python run_building_intake as the customer path.
```

5. Fresh user artifacts.

```text
FIRST_USE file, generated local example, onboarding instructions, and doctor
output must all use the same provider and route story. FIRST_USE preserves
structured Gemini key-presence and credential_validity=not_proven evidence when
Gemini appears in readiness rows.
```

## Exit Checks

```text
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile brick_cli_entrypoint
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile building_operator_driver0
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile agent_axis_behavioral
python3 -m compileall -q support/connection support/operator support/checkers
git diff --check
```

`provider_preflight` is a kernel check, not a standalone profile name. If a
dedicated provider-preflight profile is added later, this command can be
replaced by that admitted profile.

P5 closure also needs focused checks for:

```text
README / quickstart / launch-guide customer route seal
FIRST_USE structured Gemini readiness evidence
FIRST_USE / docs / checker wording for frontier_kind=complete versus not_ready
doctor full readiness schema
first-use adapter population or explicit deferral
Claude/Codex/Gemini default ordering matching the active policy
```

Fresh-machine proof is a later P7 gate. P5-B4 has only prepared it by measuring
the former empty-HOME profile hazard; P7 still requires:

```text
origin/main fresh clone
install
brick init / doctor / auth / onboard
brick build/fire through documented public route
evidence/frontier inspection
```

## Movement

Recommendation:

```text
FORWARD only to docs/doctor/FIRST_USE/default-ordering consistency work.
HOLD P5 closure until P3 route gaps, customer doc drift, doctor schema,
FIRST_USE Gemini evidence, and first-use adapter population scope are resolved.
```

## Not Proven

```text
valid Gemini credential
P3 official-route closure
P5-B4 fresh-HOME profile measurement is support evidence only, not P7 PASS
actual origin/main fresh clone/install/init/doctor/auth/onboard/build/fire/verify
README / quickstart / launch-guide route consistency beyond the narrowed P5-B3
frontier-story wording alignment
doctor full readiness schema
FIRST_USE structured Gemini credential evidence beyond readiness presence and
credential_validity=not_proven
first-use adapter population across Claude/Codex/Gemini, except for the
explicitly narrowed FIRST_USE readiness evidence preservation
Slack delivery reliability
live provider first-run completion
customer comprehension of setup output
P7/P8 final customer-ready claim
```
