# Customer-Ready P7 Fresh-Clone Probe — 0630

Status: support evidence only. Not source truth / success / quality / Movement authority / P7 PASS.
This records the FIRST actual P7 fresh-machine-shaped probe (operator transcript). The probe is a
gap extractor, not a success verdict.

## Probe shape (documented steps only)

- Fresh temp HOME + BRICK_HOME (NO `~/.brick` pre-state; verified absent before start).
- `origin/main` content cloned into the fresh HOME at `369ea44` (== origin/main HEAD).
- Network `gh repo clone` of the private repo needs the teammate's OWN `gh auth` (documented
  prerequisite); under an overridden empty HOME that auth is absent, so the content was cloned
  from the local mirror at the same `origin/main` commit to exercise the POST-clone documented route.

## Observed (PASS) steps

1. `uv sync` succeeds on the fresh clone (resolves brick-protocol + pyyaml into a fresh `.venv`).
2. `uv run python3 -m brick_protocol.support.operator.onboard codex` runs; lands the
   `onboarding-example-0` example building under the fresh `~/.brick` (frontier `agent_incomplete`
   for the local example stub, as designed).
3. The in-repo official CLI route
   `uv run python3 -m brick_protocol.support.operator.cli build --task ... --preset
   building-chain-preset:design-contract-only --adapter adapter:local` runs end-to-end and returns
   a structured packet with `build_input_mode=preset_task`, `evidence_root`, and `frontier_kind`.
4. `evidence_root` is operator-readable on the fresh clone: `capture/events.jsonl`, `raw/*`,
   `evidence/evidence-manifest.json`, `work/*` all present.
5. Frontier-honesty wording (P5-B3) holds: non-complete renders `not_ready` +
   "inspect evidence_root", and `brick build` exit 0 is not treated as PASS.

## Named gaps (UNMET → repair surfaces)

P7-G1 [P5/P7 docs] — Bare `brick` entrypoint is not reliable on a fresh machine.
  The documented README/quickstart first-run line uses `brick build ...`. The `brick` entrypoint is
  only installed by `install.sh`'s pipx step (which itself requires the gh clone). On a machine
  where another `brick` already sits on PATH (observed here: `/opt/homebrew/bin/brick` from an
  unrelated package), the documented line hits the wrong binary and dies with
  `ModuleNotFoundError: No module named 'brick'`. The reliable, install-free route is the in-repo
  `uv run python3 -m brick_protocol.support.operator.cli build ...`. Docs should either guarantee
  the pipx entrypoint before showing `brick build`, or present the `uv run ... cli build` form as
  the primary fresh-clone route.

P7-G2 [P5/P7] — The documented first-run preset example does NOT reach `frontier=complete` on a
  fresh machine without real providers. `building-chain-preset:design-contract-only` materializes
  design (`adapter:codex-local`) -> review (`adapter:gemini-local`) -> closure (`adapter:codex-local`);
  the top-level `--adapter adapter:local` does not override those role/verdict node adapters (verdict
  nodes reject the `adapter:local` stub by design). With no logged-in codex/gemini CLI, the design
  lane returns `local_cli_nonzero` -> `frontier_kind=agent_incomplete` -> `not_ready`. So the
  documented first example is honest support evidence but is NOT a `frontier=complete` proof on a
  fresh machine. A true P7 `frontier=complete` needs either (a) a real logged-in provider, or
  (b) a documented all-`adapter:local` work-only example shape.

P7-G3 [P3/compose] — A pure `adapter:local` work-node graph cannot reach `frontier=complete`
  either: a `work` node that declares `write_scope` is rejected at composition with
  `missing_adapter_write_capability: Brick row write_scope requires an observed-write selected
  adapter ref` (because `adapter:local` is a non-observed-write stub). So there is currently NO
  zero-real-provider path to a written `frontier=complete` building on a fresh machine; the
  provider-free example is inherently read-only/example-stub. This is expected by design but means
  P7 PASS as written ("documented steps only ... frontier=complete") REQUIRES a real provider step,
  which should be stated explicitly in the P7 criteria.

## Disposition

P7 is NOT passed. The fresh-clone plumbing (clone content + `uv sync` + onboard + in-repo official
CLI + readable evidence + honest frontier wording) works; the gap to `frontier=complete` is
provider-readiness + the `brick`-entrypoint/first-example documentation (G1/G2) and the explicit
provider requirement in the P7 target (G3). Next movement: a documented real-provider fresh-clone
run, or doc repair (G1/G2) + P7-criteria clarification (G3), then re-probe.

## Proof limits

Operator transcript evidence only. Local-mirror clone substitutes for the gh network clone; real
network clone, real provider auth, release-export parity, and customer comprehension remain
not_proven.

## P7-B1 doc-repair Building disposition (0630)

A composition-first Building (`p7-b1-fresh-clone-doc-repair-0630`, graph packet
`GOAL/p7-b1-fresh-clone-doc-repair-graph-0630.json`) was launched via the official
`brick build --graph` route to land the G1/G2/G3 doc/criteria repairs.

- Attempt 1 HELD early at the inspect node with `local_cli_nonzero` (codex CLI tool-router
  parse error) → `frontier_kind=agent_incomplete`, no step outputs. Classified as provider/runtime
  flakiness (codex-local ran fine for P5-B3/P5-B4 the same session), not a packet defect.
- Attempt 2 (`-r2`) ran all five nodes (inspect → work → evidence-integrity QA ∥ axis-inspect →
  closure) but landed `frontier_kind=link_paused`: closure returned a NON-BINDING
  `implementation_gap` transition concern (`related_boundary_refs: work`) about residual
  launch-guide wording, so the Link frontier paused for COO disposition. The disposable W1 worktree
  was disposed and no sandbox commit was produced, so there is no mergeable doc-repair commit yet.

COO disposition: HOLD (not forward). The doc/criteria repairs are NOT yet on main; they must be
re-run (the residual-wording concern is the next repair input) or applied through a fresh Building
that reaches `frontier=complete`. The committed deliverable from this turn is THIS probe note + gap
list; the G1/G2/G3 repairs remain open remaining_delta.
