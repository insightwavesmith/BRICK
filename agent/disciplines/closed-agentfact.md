# Closed AgentFact Discipline

Return work evidence that can be recorded as:

```text
AgentFact(received_work, returned)
```

Do not add status, verdict, score, credential body, provider session, route, or
Link decision fields to the returned payload.

## Transition-concern address forms (intake rejects everything else)

When authoring `transition_concern_evidence`:

- `reason_refs`: step-output ledger addresses (`work/step-outputs/...`) or
  opaque tokens (`observation:...`) only. No `#fragment`, no bare `file:line`,
  no document paths.
- `related_boundary_refs`: bare `brick-...` node refs or the
  `building-boundary:` sentinel only. The legacy `brick:` / `brick-instance:` /
  `brick-boundary:` prefixes, file paths, `file:line` citations, and prose are
  rejected at Agent-return intake (0703 measured: a review lens authored a
  `brick:` ref and parked the whole walk).

## Absence-claim domain labels

When making an absence claim in `transition_concern_evidence.not_proven` or
`transition_concern_evidence.proof_limits`, name the searched domain in the
claim text using a path glob, tool, or scope label. Do not write open-ended
claims such as "not found anywhere" without the searched domain.
