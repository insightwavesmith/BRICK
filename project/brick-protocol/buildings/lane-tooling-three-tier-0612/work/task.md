# Lane tool-policy three-tier repair — give non-write lanes read-only teeth (F6, full-lane sweep)

## Objective
Replace the binary tool rule in the adapter instruction rendering with a three-tier model so reviewer/leader/design lanes can actually READ the artifact they are reviewing, and require review returns to be grounded in inspected artifacts. Today every non-write step renders "Do not use tools or hooks." — so attack-QA, inspector, coo, and even design steps work paperwork-only and honestly return "everything not_proven", which the shape-sufficiency gate then forwards. Real defects were caught only by out-of-band review. This building removes that structural blindness.

## Evidence (operator-audited, cite-checked)
- The binary lives in `support/connection/agent_adapter.py` (~line 1085-1097): `if agent_request_effective_write(request): <file-tool rules> else: rules.append("Do not use tools or hooks.")` — no middle tier.
- Lane audit (agent/objects/*.yaml): qa + inspector = reviewer-readonly (ALWAYS tool-less today); coo = leader-coordination (always tool-less); the four leads carry read-write-scoped but render tool-less on their NO-write steps (design!).
- Building adapter-30-s1-park-2's three QA returns each list "S1 implementation exists." under not_proven — reviewers could not see the code at all. The design return likewise: "Live repository file shapes were not inspected."

## Required shape — three tiers
1. **write tier** (unchanged): effective write (Brick write_scope + read-write tool policy + adapter write capability) → current scoped file-edit rules. Do NOT touch this logic.
2. **read tier** (NEW): a non-write step whose agent's tool policy admits review/coordination (reviewer-readonly, leader-coordination — decide the exact admitting set from the policy vocabulary and say which) → rules allow READ-ONLY repository inspection: reading files, diffs, searching, and running the checker command — explicitly NO file edits, NO git mutations, NO hooks/SDKs, NO network beyond the provider itself.
   - Per-adapter mapping: codex-local already runs sandbox read-only — update the RULES text + system prompt to permit read-only tool use; claude-local: permission-mode plan with a read tool list (Read, Grep, Glob); gemini-local: leave as-is (no-tools) if its policy file cannot express read-only — say so explicitly as a documented limit.
3. **none tier**: anything else (and any ambiguity) → today's "Do not use tools or hooks." Fail closed to none, never to read.

## Artifact-grounding requirement (the second tooth)
- Update the QA/review brick specs (brick/templates/bricks/code-attack-qa, axis-attack-qa, evidence-integrity, review — and design) so the REQUIRED return evidence must cite inspected repo artifacts (file paths / diff hunks actually read). A review return whose evidence_used contains NO repository artifact references must be insufficient at the Brick comparison (comparison_rule), so the gate sees missing required facts instead of an honest empty pass.
- Do not weaken the existing closed AgentFact discipline; this ADDS a required grounding fact, it does not add judgment vocabulary.

## Checker pins + FIRE (each demonstrated RED on a mutated copy)
1. Packet-rendering pin: a reviewer-readonly non-write request renders the read-tier rules (mutating the renderer back to the binary → RED).
2. Tier safety pin: the read tier NEVER renders edit/write permissions (a mutated renderer granting Edit/Write to a non-write step → RED).
3. Grounding pin: a QA return without repository-artifact references in its evidence fails its comparison (fixture with packet-only return → insufficient → RED path proven).
4. Existing chat_session_park_seam and all 12 profiles stay green: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all → exit 0.

## Hard constraints
- No write capability may leak into the read tier (this is the one catastrophic failure mode — fail closed to none).
- No scheduler/queue/retry/timer; no link/ edits; no new Link vocabulary; no judgment keys.
- Closed sets stay closed: if the tool-policy vocabulary needs a new admitted token, prefer reusing existing tokens; if truly unavoidable, declare it once with a pin and say so loudly in the return.
- Append-only: nothing under project/ may change.
- Honesty bar: claim only executed proof; partial deliverables stated plainly.

## Desired Output
Three-tier rendering live for all 8 lanes per the audit table, artifact-grounding required on review/design returns, the four FIRE pins demonstrated, and check_profile.py --all exit 0 — each claim from actual execution.
