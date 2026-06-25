# Customer Entry Readiness Reconciliation (0625)

Status: SUPPORT RECORD. This document records customer-entry readiness count
reconciliation evidence. It is not source truth, not a success judgment, not a
quality judgment, and not Movement authority.

## Scope

This record reconciles the customer-entry/readiness documentation count drift
observed in `support/docs/references/setup.md` against the current checkout.
It does not mutate `AGENTS.md`, Brick / Agent / Link contracts, checker
behavior, runtime behavior, gates, routes, Movement, or provider surfaces.

## Current Counts

| Surface | Current measured count | Measurement |
| --- | ---: | --- |
| Checker profiles | 24 | `find support/checkers/profiles -maxdepth 1 -type f -name '*.yaml' \| wc -l` |
| Presets | 28 | `find brick/templates/presets -maxdepth 1 -type f -name '*.md' \| wc -l` |

`support/docs/references/setup.md` now says 24 checker profiles live under
`support/checkers/profiles/`.

## AGENTS.md Count Drift

`AGENTS.md` still contains historical 13-profile count wording. That drift is
intentionally not edited in this repair because AGENTS mutation is high-impact
constitutional work and needs explicit Smith/human disposition before closure.

## Historical Evidence Note

`project/brick-protocol/status/kernel/checker-split-map-0611.md` is historical
support evidence for the repo-split era. It is useful context, but it is not
the current measured profile count and does not replace current checkout
measurement.

## Remaining Readiness Blockers For P12

1. Capture a fresh-machine or release-export transcript:
   clone -> install -> `brick init` -> `FIRST_USE.md` -> `brick verify`.
2. Measure provider-backed customer path behavior after provider-native auth,
   including missing/unauthed/ready states where applicable.
3. Observe whether a new customer distinguishes this active checkout or release
   export from the HISTORY repository without human correction.
4. Observe one customer sandbox `--real-provider` task with live tree untouched
   and the evidence root reported clearly.
5. Keep Slack optional unless a later Building admits a customer Slack setup
   flow with separate delivery evidence.

## Observed Evidence

- `support/docs/references/setup.md` was updated from 13 profiles to 24
  profiles.
- Current measured counts are profiles=24 and presets=28.
- `AGENTS.md` was not edited.
- `checker-split-map-0611.md` remains historical evidence, not current count
  authority.

## Proof Limits

- This record is support evidence only.
- This record does not prove source truth, success, quality, Movement
  authority, provider behavior, Slack delivery, release export parity, customer
  comprehension, or future Building correctness.
