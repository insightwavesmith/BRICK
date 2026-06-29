# Customer-Ready Release Pruning — 0630

Status: support evidence only. Not source truth / success / quality / Movement authority.

## What this slice is

Critical-path step AFTER P8 (per the goal anchor: P8 dogfood = GOAL -> customer release pruning -> FINAL architecture cleanup).
Goal: the released customer export carries no operator-local trace and no internal evidence/status.

## release_export measurement (0630)

`sh support/onboarding/release_export.sh --output <tmp>` measured on the live checkout:

- `project/` and `brick_protocol.egg-info/` are excluded (4269 excluded path matches).
- No `project/.../status/kernel/*` goal/proof docs leak into the export.
- No `project/.../building*evidence*` leaks into the export.
- Export tree top-level = AGENTS.md, README.md, agent/, brick/, link/, support/, pyproject.toml, .gitignore.

So internal evidence / project status / stale goal docs are already kept out of the export by construction.

## Gap found and fixed: Smith-local path leak in customer-surface skills

The export DID still carry the operator-local literal `/Users/smith/projects/BRICK` inside five customer-surface skill docs:

```text
agent/skills/brick-task-author/SKILL.md
agent/skills/make-a-brick/SKILL.md
brick/templates/skills/brick-task-author/SKILL.md
brick/templates/skills/make-a-brick/SKILL.md
brick/templates/skills/APPLY-LIST.md
```

This is exactly the "Smith 로컬 흔적" the goal says to exclude/archive, and the existing
`product_no_smith_residue` checker only scans README.md, support/docs/spec, and agent/prompts —
so this surface was uncovered.

`support/checkers/*` also contain the literal, but those are DETECTION PATTERNS / synthetic probe
paths in the scanner itself, not a leak; they were left untouched.

## Fix via official Building (composition-first, real providers)

Run through `brick build --graph` with the declared P8-style shape
(Codex work -> Codex code-attack QA -> Gemini axis-attack QA -> Codex closure):

- First attempt (`cr-prune-smith-residue-20260629T183422Z`) returned `frontier_kind=link_paused`.
  This was a REAL QA catch, not a false pause: the dev had replaced `BRICK=/Users/smith/projects/BRICK`
  with `BRICK=$BRICK` (a self-referential no-op that breaks the teaching instruction). Code-attack QA
  flagged it as an `implementation_gap`; closure raised a non-binding transition concern pointing at
  `brick-cr-prune-work`; Link correctly paused. COO disposition: re-fire with a teaching placeholder,
  not a reroute. The paused building wrote no commit and disposed its worktree, so main stayed clean.
- Second attempt (`cr-prune-smith-residue-20260629T184047Z`) reached `frontier_kind=complete`,
  sandbox commit `05bfed543cc2f805ba2a7ad97bfb6e3af25ea4e8`, changing exactly the five files:
  `/Users/smith/projects/BRICK` -> `/path/to/BRICK` (a reader-teaching placeholder) and the stale
  `/Users/smith/projects/brick-protocol` mention -> "the frozen history repo". APPLY-LIST keeps a real
  `BRICK=/path/to/BRICK` assignment.

## Landed on main

The five-file edit from sandbox commit `05bfed54` was applied to the main worktree and committed.

Verification after applying:
- `git grep '/Users/smith' -- agent brick support ':!support/checkers' ':!support/docs/spec'` = empty (clean).
- `git diff --check` = green.
- REAL HOME `check_profile.py --all` = green (all profiles passed).

## Narrowly proven

- The release export already omits project/ internal evidence and status.
- The five customer-surface skill docs no longer carry the operator-local `/Users/smith` path.
- The fix went through the official customer graph route with real providers, and a real QA catch on
  attempt 1 demonstrates the work+QA lanes actually inspect the change.

## Not proven / caveats

- This closes the Smith-local-path leak in skill docs; a full customer-comprehension review of the
  exported tree is not proven.
- `product_no_smith_residue` checker scope was NOT widened in this slice; widening it to cover
  agent/skills + brick/templates/skills would be a durable guard (candidate follow-up), but is a
  checker change and is left as a named next step rather than silently expanded here.
- Byte-for-byte release-export parity and a real fresh-machine customer clone remain not proven.

## Next target candidate

- (optional durable guard) widen `product_no_smith_residue` to scan agent/skills and brick/templates/skills.
- FINAL architecture cleanup (godmodule decomposition) per `customer-ready-p6-cleanup-godmodule-plan-0628.md`.
