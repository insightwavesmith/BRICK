# BRICK 6-Surface Audit — Claude's Independent Opinion — 2026-06-30

Companion to `brick-6-surface-audit-claude-review-addenda-0630.md` (the factual additions and
corrections). This file is my **judgment** about the audit as an artifact — how it aggregates, ranks,
and frames its evidence — not a re-litigation of individual findings. Verified at HEAD `17eaade`
(= the audit's commit); claims I checked myself this session are tagged `[self]`.

## One-sentence verdict

The audit is a **trustworthy findings inventory wearing a misleading verdict** — the per-finding work
is honest and well-cited, but the flat "6/6 ISSUE" and the single P0 stack flatten two different
questions ("is it architecturally clean?" and "is it safe to ship?") into one label, and its static
method quietly cannot certify the one failure class that would actually break a customer build.

## What the audit gets right (so the critique is fair)

- **Citation fidelity.** HEAD equals the audited commit, quantitative claims reproduce exactly, and
  ~95% of `file:line` citations are precise. The misses are off-by-a-few-lines, never invented facts.
- **The proof-limit creed.** "Checker green is support evidence only" is applied consistently and is
  the audit's best feature. S5-F1 ("`assembly_equivalence` green proves the shrink *remains*, not that
  the boundary is correct") is exactly the kind of false-green-catching rigor that should be standard.
- **Honest Rejected-Shortcuts in every packet.** It argues against its own easy conclusions
  ("Link is broken" → rejected; "Gemini is retired" → rejected; "`--all` green means customer-ready"
  → rejected). That is the discipline of someone trying to be right, not to look done.
- **It resists the two seductive wrong moves:** re-adding a hard-coded `--large` route (P3), and
  treating checker-green as customer-ready. Both refusals are correct.

The critiques below are about the *frame around* this good work.

## Opinion 1 — The flat "6/6 ISSUE" verdict discards the gradient the packets already computed (high)

Every surface returns the identical `ISSUE`, yet the packets carry a real gradient — roughly
**27 high / 11 medium-high / 19 medium / 2 low-medium / 1 positive** across the six. S6 even contains
an explicitly *positive* finding (S6-F1, "official customer route exists and is checker-covered") and
still returns the same `ISSUE` as the Link axis, whose own packet says the core is "not collapsed."
A reader cannot tell from the verdict that the Brick/Agent/Link **cores are sound** while the
product/deployment surface holds the true publication blockers.

→ **Fix:** a per-surface readiness tuple `{core-sound? / axis-blockers n / ship-blockers n / worst-severity}`.
The data already exists in the packets; this is aggregation, not new investigation.

## Opinion 2 — The audit runs two different goals through one verdict pipe (high)

- **Goal A — axis cleanliness:** does support leak into Brick/Agent/Link ownership? (most of S1–S3)
- **Goal B — ship-readiness:** can a stranger install and get a *safe* result? (most of S4-F9…F12, S6-F9…F15)

These share almost no remedy, owner, or deadline, yet both feed one severity vocabulary and one P0/P1
stack. The sharp symptom: **S2-F2** (`AGENTS.md` still says `read-write-scoped` while live objects use
`probe-write-scoped` — pure doc drift; `[self]` confirmed `AGENTS.md:119-132` has zero
`probe_write`/`source_write` tokens) and **S4-F9** (release export can publish a local secret) are
*both* labeled `high`. A taxonomy lag and a secret-exfil path are not the same kind of "high."

→ **Fix:** score each finding on **two** axes — architecture/axis-integrity impact, and
customer-ship/safety impact — instead of one averaged severity word.

## Opinion 3 — P0 mixes deployment-security with protocol-correctness as if they share urgency (high)

P0 interleaves two unlike classes:
- Items **1–2** (release-export clean-room, dashboard ingest HMAC/replay) are deployment-security that
  only matters **at/after public ship**.
- Items **3–6** (return-shape truth, AgentFact closure, `declared_gate_refs` absence, invalid-concern
  pending target) are protocol-correctness that is live in **every build the engine runs today**.

And the audit itself says shipping is **not proven imminent** — S6-F8 (fresh-machine not proven at
HEAD) and zero `.github` CI (`[self]` confirmed). So a return-shape shrink (S1-F1) is observable in
every fan-in build *now*, while "add HMAC to a dashboard that may not be deployed" is gated on an event
the audit can't confirm is near. There's even a **circularity**: P0 ranks security-before-ship at the
top while "Later #1" defers the fresh-machine proof that would tell you whether ship is near.

→ **Fix:** gate the P0 ordering on an explicit "are we publishing soon?" decision, and present **two**
orderings — *pre-ship* (correctness-first) and *ship-imminent* (security-first) — rather than one stack
that silently assumes imminence.

## Opinion 4 — The 3-axis lens is over-applied to deployment findings (medium)

Through S1–S3 the Brick/Agent/Link lens is an honest discriminating tool. In S4 the deployment-security
findings get axis attributions that are labels over non-axis content — S4-F9 "support release
mechanics," S4-F10 "support dashboard projection," S4-F11 "support runtime/env," S4-F12 "support
dashboard deployment mechanics." None of these is a Brick/Agent/Link ownership question; the axis field
becomes a formality that just says "support." A hostile reviewer would say the axis frame is being used
as a **universal label rather than a discriminating tool**, letting every support-mechanics bug borrow
gravitas from an axis it doesn't really threaten.

→ **Fix:** give infra/security findings their own non-axis category ("infra hardening") instead of
force-fitting an axis attribution.

## Opinion 5 — Proof-limit discipline is mostly rigor, but Not-Proven occasionally hedges a settled conclusion (medium)

When *every* finding ends in a "not proven" line regardless of whether the **actionable** part is
proven, a reader can't separate "unproven, needs work to confirm" from "proven-by-reading; only the
live exploit is unproven." Clearest case: **S6-F9** release export — the structural fact ("the export
is not fail-closed against local secrets") is fully proven by reading (`[self]` confirmed
`release_export.sh` ships untracked-unignored with only `project/` excluded, and `.gitignore` has no
secret patterns); only "a secret *actually* leaked" is empirically open. The packet's flat
"live release leak not proven" risks reading as "this isn't established" when the actionable part is.

→ **Fix:** split "Proof status" into **structural claim** (proven/not) vs **empirical/live claim**
(proven/not), so the discipline never flattens a settled structural conclusion into the same
"not proven" as a genuinely open question.

## Opinion 6 — The method is structurally blind to runtime / dynamic / adversarial-execution failure (high)

This is the one I weight most. The method is **static read + checker-green + single-operator synthesis**,
with no real build, no live provider, no fresh machine (the synthesis "Final Proof Limits" says so). Across
all six packets only S1 and S5 ran live repros; S2/S3/S4 are essentially pure code-inspection. That
method cannot, by construction, see:

1. **Concurrency/ordering** in the live frontier ThreadPool (S4-F2 names `walker_kernel.py:1086-1117`
   then never exercises it).
2. **Resume/replay divergence under real interleaving** — S3-F2 literally says "Full dynamic-run
   reproduction not performed."
3. **Real provider misbehavior** — partial writes, timeout/stall (all `NOT_PROVEN`).
4. **Integration failures** that only appear when 28 profiles + real evidence + a real worktree
   interact end-to-end (the audit ran profiles in isolation).

Plus a second-order blind spot from **single-operator synthesis**: the 3-axis framing bias is never
cross-checked by a reviewer who doesn't share it. The audit honestly *lists* these as proof limits, but
never names them as a **blind-spot class** that should down-weight the "core is sound" reassurances —
which rest on the same static method that cannot see a dynamic collapse.

**The balancing fact (credit where due):** where my own review *did* test the dynamic angle the audit
skipped — the fan-in ThreadPool — the engine turned out **correct-by-construction and checker-tested**:
all shared-state mutation happens on the main-thread serial drain, each adapter gets its own temp dir,
codex runs `--ephemeral` to dodge the session-lock deadlock, the pool is forced to 1 on resume, and
`check_bounded_agent_proposed_routing_loop0.py` (P6-C) asserts pool=1 vs pool=4 produce byte-equal
evidence while proving they overlapped. So the blind spot is real **as a method gap**, even though this
particular instance is sound. The lesson is not "the engine is racy" — it's "the audit's method can't
certify that, and its reassurances should say so."

→ **Fix:** add one end-to-end live build (real worktree, real or stubbed provider, resume across a HOLD)
to the audit method before any "core is sound / customer-ready" language, and have a second reviewer who
does **not** hold the 3-axis lens sanity-check the synthesis.

## What I would do with this audit

1. **Treat the findings as sound, the priority *stack* as a draft** pending one decision (ship-imminent?)
   and one method caveat (dynamic behavior uncertified).
2. **Act now, independent of ship timing, on the three live evidence-integrity/honesty items** from the
   addenda — they are customer-data-shaped and true today:
   - **ADD-2** raw-stream secret/PII scrub (engine writes credentials/PII into the ledger unredacted),
   - **ADD-1** resume-outside-sandbox (a credited isolation control doesn't cover the resume path),
   - **ADD-3** dead pytest (the declared test surface is dead and breaks if run — and it is the direct
     evidence for Opinion 6: BRICK's only self-verification is static checker analysis).
3. **Re-issue the verdict with a two-axis score** (Opinions 1–4) so "architecturally impure but safe"
   and "architecturally fine but unsafe to ship" stop colliding under one word.

The audit asked the right questions about ownership and was honest about its limits. Its weakness is
that it answered with one verdict where the evidence supports two, and certified soundness with a method
that cannot see the failure mode most likely to actually break a build.
