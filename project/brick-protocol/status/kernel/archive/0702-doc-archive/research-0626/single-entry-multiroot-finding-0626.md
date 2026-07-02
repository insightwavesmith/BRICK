# Finding: single graph entry is build() convenience, NOT a fundamental engine rule — 0626

Source: workflow `single-entry-fundamental-or-convenience` (wf_2a26291b), measured + empirical probe @ 3d22955.

## Verdict: CONVENIENCE
- Engine validator (plan_graph.py:344-346): requires "**AT LEAST ONE** root" (roots = steps with in-degree 0), NOT exactly one. The Kahn walk seeds `ready = list(roots)` from ALL roots.
- build() (assembly.py:534-537) is the ONLY place forbidding fan-first/last — an ergonomic guard, not a structural invariant.
- Hand-tier `fan_in([a,b], c)` builds a valid GraphSpec with 2 predecessor-free roots; no lower primitive checks root-count.
- EMPIRICAL probe: 2-root accepted / 3-root accepted / 0-root (pure cycle) rejected ("at least one root"). Confirms ≥1, not ==1.

## Implication
- "N parallel from the start → converge to one" IS engine-supported. Only build() hides it.
- Feeds changes C1/C2 ([[build-fluency-roadmap-0626]]): let build() express multi-root via auto-synthesized fan_in.
- Used live: building `godmodule-design-0626` ran a true 4-parallel-root graph `fan_in([4 designs], closure)` to frontier=complete.

## Kept invariant: ONE conclusion
fan-LAST stays forbidden where it would create multiple sinks — **"entry can be N, exit must be 1"** mirrors the engine (≥1 root, converge to terminal). One building = one conclusion preserved.
