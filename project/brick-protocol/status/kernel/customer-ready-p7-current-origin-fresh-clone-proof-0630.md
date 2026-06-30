# Customer-Ready P7 Current-Origin Fresh-Clone Proof — 0630

Status: SUPPORT-EVIDENCE PASS for the current-origin minimal real-provider fresh-clone route.
Not source truth, not success judgment, not quality judgment, and not Link Movement authority.

## Result

The P7 minimal real-provider fresh-clone route was re-run after `origin/main` was updated to the
current product line.

```text
building_id = p7-current-origin-codex-realrun-20260630T003019Z
origin/main cloned HEAD = 75e32c2879d8bd4d0de3a111f0b024f4a50631b0
local main at proof time = 75e32c2879d8bd4d0de3a111f0b024f4a50631b0
fresh clone repo = /tmp/p7-current-origin-codex-realrun-20260630T003019Z/BRICK
fresh HOME = /tmp/p7-current-origin-codex-realrun-20260630T003019Z/home
BRICK_HOME = /tmp/p7-current-origin-codex-realrun-20260630T003019Z/home/.brick
official route = uv run python3 -m brick_protocol.support.operator.cli build --graph <packet>
frontier_kind = complete
customer_visible_frontier_state = frontier_complete
sandbox commit = 87f85d5e1012004c39ec5d2e68e801d44c0f64b0
evidence_root = /tmp/p7-current-origin-codex-realrun-20260630T003019Z/home/.brick/project/brick-protocol/buildings/p7-current-origin-codex-realrun-20260630T003019Z
```

This supersedes the earlier stale-origin proof whose clone was `ebf5930`.

## Shape used

Composition-first minimal P7 proof shape:

```text
work(adapter:codex-local, write_scope one status file)
  -> closure(adapter:codex-local)
  -> building-boundary:closed
```

Why this shape: P7 is the fresh-clone route proof, not the full P8 QA/reliability proof. The minimal graph
keeps the signal on clone/install/onboard/provider/official-route/evidence/frontier instead of mixing in
heavy QA provider flakiness.

## Observed steps

```text
1. Network clone from GitHub origin/main succeeded; cloned HEAD == origin/main == 75e32c2.
2. Fresh HOME/BRICK_HOME were set under /tmp; `brick status` reported default_builds_root_exists=false before the run.
3. `uv sync` succeeded in the fresh clone.
4. `brick auth login` support evidence reported codex CLI installed/ready and preserved proof limits.
5. `onboard codex --no-example` succeeded and rendered the repo-local MCP config instructions.
6. The official in-repo CLI graph route ran with `adapter:codex-local` for work and closure.
7. The run reached `frontier_kind=complete` and returned `customer_visible_frontier_state=frontier_complete`.
8. The sandbox commit contains exactly one artifact file: `project/brick-protocol/status/kernel/p7-current-origin-codex-realrun-20260630T003019Z.md`.
```

Artifact content from sandbox commit `87f85d5`:

```text
- cloned HEAD 75e32c2879d8bd4d0de3a111f0b024f4a50631b0
- fresh HOME /tmp/p7-current-origin-codex-realrun-20260630T003019Z/home
- official route uv run python3 -m brick_protocol.support.operator.cli build --graph
```

## Evidence checks

```text
Frontier event: evidence/spine/events/0024-Frontier.json
frontier_kind: complete
observed_counts.adapter_error_records: 0
observed_counts.agent_return_records: 2
observed_counts.building_map_link_edges: 2
raw/agent-return.jsonl: 2 returned AgentFact rows
raw/adapter-usage.jsonl: 2 codex-local usage rows
raw/link.jsonl: forward work -> closure; forward closure -> boundary; dynamic walker forward observations
step-output work: made_changes / changed_files recorded
step-output closure: transition_concern_evidence = null
```

The final evidence directory contains capture, raw, work, evidence manifest, claim_trace, and spine files.
The closure Agent's own not_proven list included an observation that claim_trace/capture were not seen during
its inspection; the final operator inspection found those files present after evidence finalization.

## Caveats / proof limits

```text
- GitHub clone used the host's already-authenticated gh session as the documented private-repo prerequisite.
- The fresh HOME was populated with the user's existing Codex credential file classes to simulate the documented `codex login` result; credential bodies were not printed or recorded.
- A first attempt without those Codex credential files reached agent_incomplete with adapter_error local_cli_nonzero / codex websocket connection failure.
- A second attempt with `auth` in the Building id/path was rejected by write_scope admission; the successful run avoided credential/auth wording in writable paths.
- This is a minimal current-origin P7 route proof, not a broad reliability proof or customer-comprehension proof.
- Provider process liveness after the run, future provider reliability, semantic quality of Agent returns, production runtime behavior, and P8 repeated reliability remain not_proven.
```

## Three-axis attribution

```text
Brick evidence: declared graph packet, work/closure Brick rows, write_scope-limited artifact contract.
Agent evidence: codex-local Agent returns for work and closure, plus adapter usage rows.
Link evidence: declared forward Movement rows, final Frontier event frontier_kind=complete.
Support evidence: CLI status/auth/onboard/build JSON, raw/evidence/spine files, sandbox commit. Support does not judge success/quality/Movement.
```

Rejected shortcut:

```text
Do not treat `brick build` exit 0 as P7 PASS. The proof rests on the final Frontier event, raw Agent returns,
adapter usage, Link rows, and operator-readable evidence root.
```

## Next target candidates

```text
1. Update goal/status docs to replace stale-origin P7 wording with this current-origin proof.
2. Treat P8 first proof as already done but reliability still not_proven; next product work remains customer release pruning + FINAL architecture cleanup.
3. If Smith requires a stricter P7-human-auth proof, run a manual-human login transcript separately; do not fold it into this minimal provider route proof.
```
