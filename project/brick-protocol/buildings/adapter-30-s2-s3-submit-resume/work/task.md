# Chat-session adapter S2 SUBMIT + S3 RESUME — the remaining engine seams (adapter #30, seams 2-3 of 3)

## Objective
Complete the chat-session adapter's engine surface. S1 (park) is DONE and committed: a chat-session step records a closed work envelope (work/step-outputs/<step>/work-envelope.json) + a distinct park record (parked.json) + raw/chat-session-park.jsonl + an addressable hold row, observes chat_session_parked, and stops fails-closed. This building adds: S2 — a live session CLAIMS the parked envelope atomically and SUBMITS its work as a passive file; S3 — the engine RESUMES a parked building when (and only when) a valid claim + submission exist, replays completed steps from record, consumes the submission as the step's return through uncompromising door validation, and walks on with gates computed at re-entry. After this building, a real chat session can be a formal performer end-to-end (dogfood-ready).

## Context you need (all real, verify in repo)
- S1 surfaces: support/connection/agent_adapter.py (adapter:chat-session, typed park), support/recording/chat_session_park.py + adapter_error_frontier.py (park evidence writers), walker_kernel/walker_frontier (dynamic park), run.py (linear park + parked-resume early reject: 'parked building resume is the S2/S3 submit/claim surface'). That early reject is the exact seam S3 replaces with a real admission branch.
- Resume machinery: support/operator/walker_resume.py (_read_disposition_row, hold identity matching, replay from recorded step outputs).
- Session-leak law: UUID/ULID-shaped text is rejected before evidence writes (adapter_error_frontier._reject_session_like_text, lifecycle checker session-identifier scans). Claude session ids are UUIDs — they must never enter the ledger.
- RETURNED_FORBIDDEN_KEYS discipline: the workflow importer's envelope-tolerant boundary is HARNESS-TRANSPORT-ONLY; a session's direct submission gets NO tolerance — forbidden keys are rejected verbatim, never laundered/stripped.

## S2 deliverables — claim and submit
1. **Atomic exclusive claim**: a claim verb/surface (operator-callable function, no CLI/server) that claims a parked step's envelope using an ATOMIC filesystem primitive (O_EXCL create or atomic rename). Second claimant -> loud reject naming the existing claim. The claim writes a ledger-visible fact: "lane claimed envelope with token T".
2. **Word-form claim token**: the claim mints a token made of WORDS (e.g. hyphenated word tuples) — explicitly NOT UUID/ULID-shaped (the leak guards must never fire on our own tokens). The token is the submission's admission key.
3. **Submission = passive file write**: the session writes its returned payload + the claim token into the claimed slot (a declared path shape next to the envelope). Submitting triggers NO engine action — no walking, no gate computation, nothing. (Gate-forgery impossibility is structural: computation happens only at S3 re-entry.)
4. **Claim release = human disposition only**: no timers, no expiry. An operator/COO disposition can invalidate a claim loudly (recorded), freeing the slot.

## S3 deliverables — resume
5. **New resume admission branch for parked buildings**: resume authority = (claimed envelope + submission carrying the MATCHING token). Replace the current early reject with this branch; a parked building WITHOUT a valid claim+submission still fails closed with the current explicit reason.
6. **Door validation at re-entry, before any evidence write**: the submission must satisfy the closed return discipline — RETURNED_FORBIDDEN_KEYS verbatim reject (no tolerance, no laundering), UUID/ULID-shaped token reject, required return shape of the parked Brick honored, claim-token match. Any violation -> loud reject, building stays parked, nothing written to evidence except (optionally) a support observation of the rejected attempt.
7. **Full replay walk**: completed steps replay from recorded step outputs (never re-invoke providers); the parked step consumes the validated submission as its agent return; the walk continues LIVE from the next step with gates computed through the existing completion seams.
8. **Graph-plan law**: a plan containing a chat-session step MUST be a graph plan — enforce fail-closed at plan admission/validation (a linear plan with a chat-session adapter -> loud reject; linear replay would re-invoke completed providers, which is forbidden).

## Checker pins + FIRE (each demonstrated RED on a mutated/negative case)
- Claim atomicity: two concurrent claims -> exactly one wins, second loudly rejected; removing the atomic guard -> RED.
- Token form: a minted token matching UUID/ULID shapes -> RED (self-test the minter).
- Door: submission carrying a forbidden key ('status','success','result',...) -> rejected VERBATIM (assert the rejected payload is unmodified — laundering = RED); submission containing a UUID-shaped string -> rejected BEFORE evidence write; token mismatch/absent -> rejected.
- Resume admission: parked + no claim -> fail closed; claim + no submission -> fail closed; valid claim+submission -> resumes and the walk's next step runs.
- Graph law: linear plan + chat-session step -> rejected at admission.
- Path admission: any new file shapes (claim record, submission slot) admitted in BOTH path checkers; omission from either -> RED.
- Full gate: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all -> exit 0 (temp source copy acceptable for tempdir-blocked sandboxes — report which you ran and the real code).

## Proof required (run, report honestly — claims only from execution)
END-TO-END TEMP DRIVE (the centerpiece): in a temp output_root, declare a graph building with a chat-session step (agent-object:dev declares the capability) -> S1 parks -> CLAIM it (show the token and the ledger fact) -> second claim attempt loudly rejected -> SUBMIT a valid payload with the token -> RESUME -> completed steps replay from record, the chat step's return is the submission, the walk continues and gates compute -> building proceeds/closes. Then the negative drives listed above. Report each with the actual command/probe output.

## Hard constraints (law)
- No scheduler / queue / retry / timer / polling. Everything is operator- or session-initiated, synchronous, fails-closed.
- Link closed vocabulary untouched; no link/ edits; no new Movement/state literals; park/claim/submit live in support records + derived observations.
- Submission can NEVER trigger engine computation; gates compute only at re-entry.
- No credential/session text in any record; word-form tokens only.
- Append-only history; no pin weakening; project/ untouched.
- This building carries a work reroute budget of 3: if attack-QA finds defects, expect in-building repair rounds — honest partial returns with exact gaps beat green-looking claims.

## Desired Output
Working S2+S3 (claim/submit/resume) with the end-to-end temp drive transcript, all negative drives, FIRE results, and the full-gate exit code — each from actual execution.
