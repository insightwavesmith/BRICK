# BRICK build() — Fluency Roadmap (as easy as a workflow) — 0626

Source: workflow `build-as-fluent-as-workflow` (wf_0b35874b), measured @ struct-surgery-0623 / 3d22955.
Vision (Smith): pick **Brick(work) + Agent(who/permission) + Link(flow/gate)** like Lego, drop into `build()`, run — as fluent as the Claude Code workflow harness (`agent`/`parallel`/`pipeline`).

## Correspondence (workflow ↔ BRICK today)
- **pipeline ↔ build()** = ALREADY CLEAN. List order = spine; adjacency N→N+1 auto-edge + auto data-carry (`_auto_declare_chained_carry`, assembly.py:963). Skill states "build() IS pipeline".
- **parallel ↔ fan()** = BLOCKED. `fan()` is a nested block only; build() raises on fan-first (assembly.py:534) / fan-last (:537). Every parallel must be bracketed source-above + convergence-below. The #1 gap.
- **agent(prompt,opts) ↔ brick()+agent()** = DEEPEST gap. Performer is RESOLVED by kind→NEED↔CAPABILITY (plan_rendering.py:830), not picked; permission composed from 3 places (plan_rendering.py:42); only free dial = casting (adapter/model/effort).

## Change ladder (smallest-first, all checker-first)
- **C1 (START)**: build() allow fan-first/last (auto-synthesize source/sink) — the immediate ergonomics win Smith asked for.
- **C2**: standalone `parallel([...])` verb (auto source+convergence, mirrors workflow parallel).
- **C3**: move auto-returns/auto-alias to the lower tier (chain/fan_in auto-derive from kind template) → kills hand-tier fiddliness everywhere (assembly.py:447/471 → fire at lowering).
- **C4**: validate `kind` at authoring time (clear "unknown kind X; valid {...}" instead of late compile fail).
- **C5**: write= honest (raise on read-only kind, not silent drop @ assembly.py:1058).
- **C6**: `run(build([...]))` one honest call — absorb the 4 launch footguns + exit on `frontier_kind=='complete'` (the genuine false-success fix), driver seal intact.
- **C7**: per-node `gate=` (gate placement as a Lego piece, not coarse building-wide auto @ assembly.py:810).
- **C8 (Smith's call — constitutional)**: loosen agent from need-bound to pickable within capability + a permission dial. Touches the NEED↔CAPABILITY model — NOT a silent refactor.

## Target shape (the bar)
```python
design = brick("design", "draft the plan")
impl   = brick("work",   "implement", write="support/auth/**", agent=agent("dev", model="codex"))
qa     = parallel([ brick("code-attack-qa","..."), brick("axis-attack-qa","...") ])  # standalone
done   = brick("closure","verdict", gate="human-review")                              # per-node gate
run(build([design, impl, qa, done]))                                                  # one honest call
```

## Deliberate kept difference (do NOT remove)
`kind` stays a closed 10-set (plan/design/development/work/review/inspect/code-attack-qa/axis-attack-qa/evidence-integrity/closure). Constitutional rule "no naked prompt/agent/checker" — every node carries declared Brick+Agent+Link meaning. = fluency, not anarchy.

## Maps to goal
Track B-1 (launch ergonomics) **detailed roadmap**. C1 = first build. C6 folds in the honest-launch (real false-success fix). C8 = separate operator decision. See [[single-entry-multiroot-finding-0626]] (engine supports the multi-root C1/C2 needs) and [[build-exit-zero-3axis-finding-0626]] (the honest-exit C6 must respect).
