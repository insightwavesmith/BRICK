# Customer-Ready P3 Gemini-Local HOLD - 0627

This record is support evidence only. It is not source truth, success judgment,
quality judgment, or Movement authority.

## Phase

P3 - C6 One-Call Launch Close.

## Live Checkout

- Worktree: `/Users/smith/.brick/worktrees/struct-surgery-0623`
- HEAD: `137f0e8e62e7d7fc5ff0255cc00b0ba68e724929`
- Prior committed scope: P1 adapter authority repair and P2 Codex/Gemini
  recast.

## Building Evidence

- Building id: `c6-one-call-launch-0627-weekend-recast-2`
- Evidence root:
  `project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-2`
- Launch surface: `run_customer_building_in_sandbox`
- Plan shape: graph
- Walker mode: dynamic
- Isolation mode: worktree
- Worktree disposed after incomplete frontier: true

## Observed Fan Shape

The rematerialized plan used the weekend casting required by the goal:

- Codex work: `adapter:codex-local`
- Codex structure QA: `adapter:codex-local`
- Gemini broad review: `adapter:gemini-local`
- Codex closure: `adapter:codex-local`

Raw plan adapter counts:

- `adapter:codex-local`: 4
- `adapter:gemini-local`: 1
- active Claude occurrences: 0

## Frontier

- Frontier kind: `agent_incomplete`
- Frontier reason: adapter error evidence exists after Agent receipt and before
  returned AgentFact.
- Incomplete step:
  `c6-one-call-launch-0627-weekend-recast-2-gemini-broad-review`

## Adapter Error Evidence

Building raw adapter error:

- Raw file:
  `project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-2/raw/adapter-error.jsonl`
- Adapter: `adapter:gemini-local`
- Agent object: `agent-object:inspector`
- Selected model: `model:gemini:default`
- Error kind: `local_cli_nonzero`
- Exception type: `ValueError`
- Return code: 144

Operator diagnostic evidence, not QA or closure evidence:

- Direct Gemini HTTP diagnostic through `invoke_gemini_text` returned
  `ValueError: gemini-api HTTP error status 400`.
- The Gemini CLI client error file reported Google API status
  `INVALID_ARGUMENT` with reason `API_KEY_INVALID`.

## Three-Axis Attribution

Problem definition:

The C6 weekend recast Building reached the declared Gemini QA Agent step, but
the Gemini brain connection failed before AgentFact.returned.

Brick candidate:

The Building Plan did declare the required fan shape and included the Gemini
review step. No active Claude selection was observed in the rematerialized plan.

Agent candidate:

The Agent row selected `agent-object:inspector` with `adapter:gemini-local`.
The Agent receipt exists. The Agent return is missing only for the Gemini review
step because the adapter failed before returned evidence could be recorded.

Link candidate:

Link did not choose a new Movement. The observed lifecycle paused at the Gemini
review boundary with a frontier requiring caller/COO disposition.

Support surface:

`support/connection/adapter_local_cli.py` successfully projected the
Gemini-local CLI path with API-key auth, temp HOME, admin policy, and
`--skip-trust`. The live provider/auth call rejected the key.

Rejected one-axis shortcut:

This is not proven to be a Brick plan, Agent YAML, Link Movement, Slack, Claude,
or P1/P2 recast defect. It is currently evidenced as a Gemini provider/auth
blocker on the support brain-connection surface.

Chosen repair surface:

No code repair is selected from this evidence. The next repair is either an
external Gemini API key/client fix or an explicitly declared casting reroute by
caller/COO.

Verification before movement:

After Gemini credentials/client are fixed or a declared casting reroute is
authorized, re-run a rematerialized C6 Building and require Gemini QA evidence
inside the Building root before closure is accepted.

Movement:

P3 = HOLD. The blocker is non-Claude and exact: live `adapter:gemini-local`
provider/auth call is rejected with `API_KEY_INVALID`/HTTP 400.

## Not Proven

- C6 one-call launch closure.
- Gemini Building QA return.
- Codex closure after Gemini QA.
- Customer-ready proof.
- Fresh-machine proof.
- That the current Gemini API key is valid for
  `generativelanguage.googleapis.com`.

## Next Admissible Movement

- If Gemini auth/client is fixed: REROUTE by re-running rematerialized C6 with
  Codex work, Codex QA, Gemini QA as a Building Agent step, and Codex closure.
- If Gemini-local remains unavailable: caller/COO must explicitly decide whether
  to HOLD, use a read-only `adapter:gemini-api` QA reroute, or defer Gemini QA
  until credentials are repaired.
