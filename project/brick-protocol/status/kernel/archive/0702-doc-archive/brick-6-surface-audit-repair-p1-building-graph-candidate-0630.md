# BRICK 6-Surface Audit Repair - P1 Building Graph Candidate - 2026-06-30

## Status

```yaml
candidate_ref: building-graph-candidate:brick-6-surface-p1-raw-evidence-scrub-0630
phase_ref: phase:P1
status: candidate_not_declared_not_run
source_goal_ref: goal:brick-6-surface-audit-repair-0630
operator_role: COO/operator candidate declaration only
```

This document is a manual graph candidate for the P1 repair Building. It is not
an active Building Plan, not a run result, not Movement authority, and not a
success/quality judgment. The actual implementation must run later through the
official `build()` / `brick build` route after Smith/COO goal activation.

## Source Audit Documents

Open these before declaration or repair:

- `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-goal-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-p1-raw-evidence-stream-scrub-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md` (`C15`)
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s4-support-machine-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s5-checker-system-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s6-product-surface-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-coverage-matrix-0630.md`

## P1 Work Contract Candidate

Repair raw evidence stream persistence so credential/secret/PII-looking payloads
cannot silently enter raw BRICK JSONL streams. Add checker-first negative probes
covering the active raw stream writer seams for at least:

- `raw/brick-work.jsonl`
- `raw/agent-received.jsonl`
- `raw/agent-return.jsonl`
- `raw/adapter-error.jsonl` or its active writer/diagnostic equivalent

Preserve Brick/Agent/Link authority boundaries: this is Support/evidence
integrity only. It must not create source truth, success judgment, quality
judgment, Movement authority, scheduler/queue/retry behavior, or a new axis.

## Must Preserve

1. Raw evidence remains useful enough for replay/audit; redaction/blocking must
   preserve evidence refs, proof limits, and explicit `not_proven` when body
   detail is removed.
2. Secret/credential/session-body-looking fixture data must not persist silently
   in raw JSONL as original text.
3. Do not make checker green by skipping raw stream writing entirely unless the
   Brick/Agent/Link evidence contract still has an admitted replacement.
4. Do not recursively ban ordinary nested words such as `status` or `result` in
   non-secret evidence bodies; this phase is about secret/PII-like payloads, not
   AgentFact top-level authority keys (that is phase:P4).
5. If the design cannot choose block vs redact without losing replay truth, HOLD
   and return the policy question instead of patching around it.

## Manual Graph Candidate

```text
p1-design-evidence-surfaces
  -> p1-work-guard-redaction
  -> fan([
       p1-code-attack-qa,
       p1-axis-attack-qa,
       p1-evidence-integrity
     ])
  -> p1-closure
```

### Node: p1-design-evidence-surfaces

```yaml
brick_kind: design
agent_hint: design-lead
write_need: false
movement: forward
target: p1-work-guard-redaction
required_return_focus:
  - observed raw writer surfaces
  - design choice: block vs redact vs mark
  - reading_scope_map
  - checker/verifier plan
```

Design must inspect current raw writer call chain before naming a repair
surface. Minimum reading scope candidate:

- `support/recording/raw_claim_trace.py`
- `support/recording/*`
- `support/operator/*evidence*`
- `support/operator/run.py`
- `support/operator/reporter.py` only if raw/report body crossing is relevant
- `support/checkers/lib/kernel_checks.py`
- `support/checkers/lib/case_runners.py`
- `support/checkers/profiles/*` relevant to evidence/read-side projection

### Node: p1-work-guard-redaction

```yaml
brick_kind: work
agent_hint: dev
write_need: true
movement: forward
target: fan:p1-qa
write_scope_candidate:
  - support/recording/**
  - support/operator/** only if the active writer seam is there
  - support/checkers/**
  - project/brick-protocol/status/kernel/** only for proof/status record if needed
```

Work must implement the smallest evidence-integrity seam that makes the negative
probes meaningful. Prefer an admitted shared guard/redaction helper over
copy-pasted checks. Do not touch product release export/dashboard hardening in
this phase unless a raw-stream test requires a local fixture helper.

### Node: p1-code-attack-qa

```yaml
brick_kind: code-attack-qa
agent_hint: qa
write_need: probe_write
movement: forward
target: p1-closure
```

Attack the implementation with synthetic raw payload fixtures. At minimum test
secret-like classes:

- API key/token-looking string
- private-key-like block
- provider/session-body-like string
- credential-looking env assignment

The QA proof must drive a real writer/checker surface, not only search source
text.

### Node: p1-axis-attack-qa

```yaml
brick_kind: axis-attack-qa
agent_hint: inspector
write_need: probe_write
movement: forward
target: p1-closure
```

Verify the repair remains Support/evidence integrity and does not let Support
own Brick work truth, Agent return truth, Link Movement, success, or quality.

### Node: p1-evidence-integrity

```yaml
brick_kind: evidence-integrity
agent_hint: inspector
write_need: probe_write
movement: forward
target: p1-closure
```

Verify persisted raw/claim/evidence outputs still carry proof limits and useful
refs after block/redaction/mark behavior. Confirm the negative probe cannot pass
by simply dropping required raw evidence.

### Node: p1-closure

```yaml
brick_kind: closure
agent_hint: coo
write_need: false
movement: forward
required_return_focus:
  - observed_evidence
  - narrowly_proven
  - not_proven
  - next Movement candidate
  - deferred Smith/COO policy questions, if any
```

Closure must state whether P1 is narrowly proven, or whether policy choices
(block vs redact, replay reproducibility, false-positive threshold) remain
`not_proven` / HOLD material.

## Operator Questions If The Building Hits Conflict

- Is the leaking body a Brick work statement/source fact, an Agent returned body,
  a Link carry/handoff row, or Support raw/projection serialization?
- Does blocking the payload break required replay/evidence, or can redaction with
  stable refs preserve accountability?
- Is this actually phase:P4 AgentFact top-level authority-key closure, or phase:P1
  secret/PII scrub?
- Is this actually phase:P7 release/export/dashboard ship hardening rather than
  raw ledger persistence?
- Which exact raw writer would still persist the fixture if this repair is wrong?

## Done Evidence Required Before P1 Closure

- Direct observed writer-chain evidence for the raw streams in scope.
- Negative probe(s) that fail on unguarded secret/PII raw persistence.
- Positive evidence that allowed non-secret evidence still persists with proof
  limits and refs.
- Focused checker/profile evidence covering the new guard.
- `git diff --check` green.
- `check_profile.py --all` green or a narrowly explained HOLD with current
  evidence and next Movement candidate.

## Proof Limits

- This is a graph candidate only; it has not run.
- It is support/operator planning evidence only.
- It does not prove the repair, select Movement, judge quality, or close P1.
