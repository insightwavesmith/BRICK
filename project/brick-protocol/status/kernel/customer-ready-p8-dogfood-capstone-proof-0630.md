# Customer-Ready P8 Dogfood Capstone Proof — 0630

Status: support evidence only. Not source truth / success / quality / Movement authority.

## Probe result

P8 required-shape dogfood capstone reached `frontier_kind=complete` through the official customer graph route.

- graph packet: `/tmp/p8-dogfood-required-shape-20260629T182113Z.json`
- building id: `p8-dogfood-required-shape-20260629T182113Z`
- official route: `uv run python3 -m brick_protocol.support.operator.cli build --json --non-interactive --graph <packet> --timeout 300`
- evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/p8-dogfood-required-shape-20260629T182113Z`
- frontier: `complete`
- sandbox commit: `89d72b54e20c645c4ea18a4c129784f3a710cc5c`
- artifact path: `support/docs/references/p8-dogfood-capstone-20260629T182113Z.md`

## Declared shape

The run used the P8 criteria's required current casting:

```text
Codex work
  -> Codex code-attack QA
  -> Gemini axis-attack QA
  -> Codex closure
  -> building-boundary:closed
```

The graph was not the fixed `fast-fix` preset. It was a declared, task-sized graph for one real customer-facing documentation artifact.

## Real artifact

Sandbox commit `89d72b54e20c645c4ea18a4c129784f3a710cc5c` contains exactly one file change:

```text
support/docs/references/p8-dogfood-capstone-20260629T182113Z.md | 7 +++++++
```

Artifact content:

```text
Brick build exit 0 is support evidence only.
Customer-visible closure is recorded as `frontier_kind=complete`.
A non-complete frontier is `not_ready`.
When the frontier is `not_ready`, inspect `evidence_root` before treating the work as closed.
Evidence can show what was observed and recorded.
Evidence is not source truth.
Evidence is not a quality judgment.
```

## Operator verification after the run

- `raw/adapter-usage.jsonl` records codex-local usage for `p8-work`, `p8-code-qa`, and `p8-closure`.
- `work/step-outputs/p8-axis-qa-attempt-1/step-output.json` records `adapter_ref=adapter:gemini-local`, `selected_model_ref=model:gemini:default`, and `transition_concern_evidence=null`.
- `raw/agent-return.jsonl` contains returns for all four nodes: work, code QA, axis QA, closure.
- `raw/link.jsonl` records only `forward` movements to code QA, axis QA, closure, and `building-boundary:closed`.
- `evidence/spine/spine.json` contains 41 events and ends with `Frontier`.
- Operator hash-chain check over `evidence/spine/spine.json` passed: each event's `prev_hash` matches the previous event `content_hash` from genesis to Frontier.
- Operator scan found no forbidden top-level Agent return keys from the checked set: `success`, `failure`, `approved`, `quality`, `movement_choice`, `route_target`, `status`, `verdict`, `score`, `result`.

## Narrowly proven

- BRICK ran one small, meaningful, customer-facing documentation task through the official customer graph entrypoint.
- The run used the declared P8 multi-lane shape including Gemini axis QA.
- The Building reached `frontier_kind=complete`.
- The artifact is real, operator-readable, and present in the sandbox commit.
- Raw records and spine are present and internally consistent under operator verification.

## Not proven / caveats

- This is a first dogfood proof, not reliability proof.
- The sandbox artifact is not merged into `main` by this proof record; it remains real artifact evidence via sandbox commit `89d72b54e20c645c4ea18a4c129784f3a710cc5c`.
- Closure's own Agent return says `capture/` and `evidence/claim_trace` were absent at its inspection time; final operator verification after the run found the final evidence/spine files present. Treat closure-time evidence visibility as a timing/projection caveat, not as final absence.
- Code QA noted `check_profile.py --all` could not complete inside that QA lane because no usable temporary directory was available; the P8 proof therefore relies on post-run operator raw/spine checks for P8's evidence consistency requirement, not on that lane's full checker sweep.
- Gemini axis QA returned successfully in this run, but provider reliability and future Gemini credential behavior remain not proven.
- Source truth, success judgment, quality judgment, Movement authority, and future Building correctness remain not proven by support evidence.

## Next target candidate

P8 dogfood capstone is satisfied as the goal proof slice. The next critical path candidate is customer release pruning: decide what belongs in the customer-facing repository/export and exclude/archive stale internal evidence, status, dated goal cruft, and Smith-local traces before final architecture cleanup.
