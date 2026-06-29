# Operator skill APPLY-LIST (building-ease 0623)

> The running operator session uses `~/.claude/skills` LIVE. This pass authored all
> skill content IN-REPO under `brick/templates/skills/` and did NOT touch the live
> dir. Smith runs the commands below in their own terminal to apply. Every step is
> a directory copy or a delete — no in-place edit of a live file.

## What changed (in-repo, this pass)

NEW in-repo ship dir: `brick/templates/skills/` (sibling of `tasks/` and `presets/`).

| In-repo skill | Role | Live action |
|---|---|---|
| `building-sizing-method/` | NEW — dimensions → graph packet shape (sizes the official graph input) | COPY in (new) |
| `brick-task-author/` | CONSOLIDATED — PHASE 1 task body → PHASE 2 official build route (`brick build --graph <packet>` for graph mode) → PHASE 3 hold-triage (folded in); graph-syntax block MOVED OUT to building-sizing-method | COPY over (replaces live) |
| `make-a-brick/` | NEW — replaces `brick-declaration-author` mode 1 (scaffold-then-register a KIND) | COPY in (new) |
| `make-an-agent/` | NEW — replaces `brick-declaration-author` mode 2 (a lane) | COPY in (new) |
| `make-a-gate/` | NEW — replaces `brick-declaration-author` mode 3 (a gate) | COPY in (new) |

## APPLY (run in a terminal; absolute in-repo source = the BRICK product tree)

Set `BRICK` to the product repo root (e.g. `/path/to/BRICK`):

```bash
BRICK=/path/to/BRICK

# 1. NEW: sizing skill (sizes the input the launch skill consumes)
cp -R "$BRICK/brick/templates/skills/building-sizing-method"  ~/.claude/skills/building-sizing-method

# 2. REPLACE: consolidated launch skill (absorbs hold-triage as PHASE 3,
#    syntax block moved out, graph mode uses brick build --graph <packet>)
cp -R "$BRICK/brick/templates/skills/brick-task-author/SKILL.md"  ~/.claude/skills/brick-task-author/SKILL.md

# 3. NEW: three creation skills (replace brick-declaration-author's 3 modes)
cp -R "$BRICK/brick/templates/skills/make-a-brick"   ~/.claude/skills/make-a-brick
cp -R "$BRICK/brick/templates/skills/make-an-agent"  ~/.claude/skills/make-an-agent
cp -R "$BRICK/brick/templates/skills/make-a-gate"    ~/.claude/skills/make-a-gate
```

## DELETE (run in a terminal — do NOT delete live from a session)

```bash
# brick-hold-triage is now PHASE 3 of brick-task-author
rm -rf ~/.claude/skills/brick-hold-triage

# brick-declaration-author is superseded by make-a-brick / make-an-agent / make-a-gate
rm -rf ~/.claude/skills/brick-declaration-author
```

## RESULT — operator launch surface after apply

- **2 launch-path skills:** `building-sizing-method` (sizes the shape) → `brick-task-author`
  (launches + triages). ONE skill launches a building. Satisfied.
- **3 creation skills:** `make-a-brick`, `make-an-agent`, `make-a-gate` (scaffold-then-register;
  each ends with the made component USABLE, proven by an in-repo checker).
- **Deleted:** `brick-hold-triage` (folded), `brick-declaration-author` (superseded).

## NOTE — verify after apply

The live skills only carry the procedure text; graph mode enters the official
`brick build --graph <packet>` route, while scaffold helpers such as
`support.operator.brick_kind_scaffold.scaffold_brick_kind` ship in the BRICK repo.
After `git merge` of this branch into the product tree, the skills resolve their
helpers from the installed BRICK package. No live-env Python changes.
