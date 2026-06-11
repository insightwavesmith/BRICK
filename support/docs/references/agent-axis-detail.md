# The Agent axis in detail

Brick Protocol is a three-axis work protocol for human-agent work: **Brick** is the work, **Agent** is the performer, and **Link** is the transfer / carry / movement between work boundaries. This document is a deep dive on the middle axis — the **Agent**, the performer.

If you have not yet run a Building, read [quickstart.md](quickstart.md) first. The quickstart shows where an Agent Object is named in a plan (the Agent row). This document explains what that Agent Object is, which ones exist, what they are allowed to touch, and how one gets selected.

## What an Agent Object is

An **Agent Object** is an Agent-axis, **provider-neutral** contract data resource. It describes a performer role without naming a specific provider, model, credential, or session. The active Agent Objects live as YAML files under `agent/objects/`.

An Agent Object may contain only provider-neutral references:

```text
prompt_refs              the instruction prompt(s) for the role
skill_refs               the skill resources the role may use
hook_refs                the hooks bound to the role
tool_policy_refs         what the role is allowed to read/write (see below)
discipline_refs          the return disciplines the role must follow
adapter_refs             which provider-neutral adapters can back the role
callable_performer_refs  performer-callability metadata for support adapter connection
```

`hook_refs` name **advisory intents** — they are never executed (every entry
in `agent/hooks/registry.yaml` carries `execution_opened: false`). The
EXECUTING hooks are per-machine config (`.claude/hooks/`, `.codex/hooks/`)
wired by the onboard recording step, not these Agent-axis records.

What an Agent Object is **not** (from `AGENTS.md`):

- not a BAL fact class, and not a fourth axis;
- not a provider runtime, not a setup pack, not a credential owner;
- not a tool/hook executor;
- not source truth, not success judgment, not quality judgment, and not Movement authority.

In particular, `callable_performer_refs` is just metadata that lets support connect a performer. It is not provider identity, tool-execution authority, Movement authority, success judgment, or quality judgment.

Two more boundaries worth stating plainly:

- A `selected_adapter_ref` (chosen in the Building Plan / step, not in the Agent Object) is a "brain/capability connection." It exposes **technical capability only** — never authority.
- Setup tokens, auth, credential bodies, provider runtime/session state, and provider-specific session ids must **never** be stored in an Agent Object (or in any adapter ref, AgentFact, plan, Link fact, or support record).

## The available Agent Objects

There are eight Agent Objects under `agent/objects/`. Each declares a `lane` and is backed by a `tool_policy_ref`. The `lane` is the broad role kind; the tool policy is what that role may actually do to files.

| Agent Object | `lane` | Tool policy | Role (plain) |
| --- | --- | --- | --- |
| `coo` | `leader` | `tool-policy:leader-coordination` | Coordinates a Building; reads task/design/evidence; pure read-only — the Movement/judgment authority carries no write tools. |
| `pm-lead` | `leader` | `tool-policy:leader-coordination` + `tool-policy:read-write-scoped` | Planning / intake leadership. |
| `design-lead` | `leader` | `tool-policy:leader-coordination` + `tool-policy:read-write-scoped` | Design leadership. |
| `cto-lead` | `leader` | `tool-policy:leader-coordination` + `tool-policy:read-write-scoped` | Architecture / slicing leadership; may implement directly under a Brick write NEED; delegating to DEV remains the normal pattern for larger slices. |
| `dev` | `worker` | `tool-policy:read-write-scoped` | The implementer; the only `worker`-lane role; writes only within a declared scope. |
| `qa-lead` | `leader` | `tool-policy:leader-coordination` + `tool-policy:read-write-scoped` | QA leadership; evidence verification and gap detection. |
| `qa` | `reviewer` | `tool-policy:reviewer-readonly` | Reviewer; reads scoped files and runs verification commands. |
| `inspector` | `reviewer` | `tool-policy:reviewer-readonly` | Axis/structure inspection of prior Brick / Agent / Link output. |

(The list of current roles is also recorded in `AGENTS.md` under "Agent Axis.")

Notice the shape of this set: **five leaders, one worker, two reviewers.** Only `dev` sits in the `worker` lane, but the read-write tool policy is carried by the worker **and** the four team leads (`pm-lead`, `design-lead`, `cto-lead`, `qa-lead`); the COO stays read-only (the Movement/judgment authority carries no write tools), and the two reviewers stay read-only. Capability is not authority: a write-capable role still writes only where a Brick declares its write NEED (`requires_brick_write_scope`) — capability without that NEED stays read-only. This is deliberate, not an accident of configuration — see the next two sections.

## Tool policies: what a performer may touch

A **tool policy** is an Agent-axis resource (`owner_axis: Agent`) that states what a performer in that lane is allowed to do. There are three, all under `agent/tool_policies/`. (A fourth, `support-readonly`, was deleted 0610 — no Agent Object ever bound it; support surfaces are readers by construction, not tool-policy holders.)

### `read-write-scoped` (the only write-capable policy)

Used by `dev` and by the four team leads (`pm-lead`, `design-lead`, `cto-lead`, `qa-lead`, each alongside `leader-coordination`; the COO stays read-only — the Movement/judgment authority carries no write tools). Its `allowed_use` is: *"read and edit only through an admitted Brick `write_scope` and compatible write-capable adapter support."* Its `mutation_scope` is *"Brick-declared `write_scope` only; no free tool execution"*, and it is the only policy with `execution_opened: true`.

Crucially, the policy spells out that being write-capable is **not enough on its own**. Its `execution_opening_condition` reads:

> Effective write opens only when Brick `write_scope`, this read-write scoped Agent policy, compatible adapter mapping/technical capability, and support write observation are all present; **not adapter identity alone**.

And it explicitly forbids:

```text
write outside Brick-declared write_scope
write secret, token, credential, auth, or .git paths
git commit or git push
choose Link Movement
create GateFact
classify success, failure, quality, or approval
```

So `write_scope` is the Brick-declared boundary of files an Agent is permitted to edit; the read-write-scoped policy is the Agent-side permission to edit *at all*. A write happens only where all four line up: Brick `write_scope` + this Agent policy + adapter capability + support write observation.

### `leader-coordination`

Used by `coo`, `pm-lead`, `design-lead`, `cto-lead`, `qa-lead` (the four team leads each alongside `read-write-scoped`; for the COO it is the ONLY tool policy — pure read-only). `allowed_use`: read declared task/design/evidence/resource refs and prepare coordination or assignment returns. `mutation_scope`: *"write only within a Brick-declared write_scope; no Movement/quality/route authority."* `execution_opened: false`. Forbidden use includes "write outside Brick-declared write_scope" — i.e. a leader's write still happens only where a Brick declares the write NEED; with no such NEED the leader stays read-only (and the COO, carrying no write policy at all, stays read-only always).

### `reviewer-readonly`

Used by `qa`, `inspector`. `allowed_use`: read scoped files and run verification commands. `mutation_scope`: *"none unless an in-scope repair is separately assigned."* `execution_opened: false`. A reviewer reads and runs checks; it does not mutate files unless a separate repair Brick is declared.

### What every tool policy refuses

All three policies carry the same `proof_limits` block, which is the heart of the Agent axis:

```text
Agent-axis tool policy only
not a provider runtime
not source truth
not success judgment
not quality judgment
not Movement authority
```

And all three forbid the same authority moves: `git commit` / `git push`, choosing Link Movement, and classifying success, failure, quality, or approval. Choosing a route target is forbidden for EVERYONE by axis law — route-target choice is Link/CoO authority, never an Agent-axis capability — so it is not a property any tool policy grants or withholds. (Two of them — `leader-coordination` and `reviewer-readonly` — happen to also list it in their `forbidden_use`, and `read-write-scoped` instead also lists `create GateFact`, but those are redundant restatements of the axis law, not the source of the prohibition.) In other words, no tool policy — not even the write-capable one — lets a performer decide whether the work was good or where it goes next. Those are Link-axis and human decisions, not Agent-axis ones.

## NEED ↔ CAPABILITY: how an Agent is selected

A newcomer might expect a plan to hard-name the performer. It can, but that name is **not authority**. The intended model is a match between what a Brick *needs* and what an Agent *can do*.

Each Brick spec (`brick/templates/bricks/<kind>/brick.md`) declares its need in frontmatter:

- `requires_brick_write_scope` — `yes` or `no`: does this work require writing files?
- `performer_lane_need` — `leader`, `worker`, or `reviewer`: what kind of performer does it need?
- `agent_object_hint_ref` — an **optional** pre-fill hint, *not* a selection authority.

The Builder then **selects** a performing Agent by matching the Brick's `performer_lane_need` / `requires_brick_write_scope` against each Agent Object's `lane` and tool policy (and adapter capability). The selection logic and its intent are documented in `support/checkers/check_bricks_spec_completeness.py`:

> The performing agent is NOT named here as authority — the Builder SELECTS it by matching the Brick's `performer_lane_need` / `requires_brick_write_scope` against each Agent Object's `lane` / `tool_policy` / adapter capability. `agent_object_hint_ref` is an OPTIONAL fallback/hint only; it is NOT a selection authority.

The current Brick kinds make the matching concrete:

| Brick kind | `requires_brick_write_scope` | `performer_lane_need` | `agent_object_hint_ref` | Matches a performer in lane… |
| --- | --- | --- | --- | --- |
| `work` | `yes` | `worker` | `agent-object:dev` | `worker` (only `dev` qualifies — it is the only `worker`-lane object) |
| `development` | `no` | `leader` | `agent-object:cto-lead` | `leader` |
| `plan` | `no` | `leader` | `agent-object:pm-lead` | `leader` |
| `design` | `no` | `leader` | `agent-object:design-lead` | `leader` |
| `review` | `no` | `leader` | `agent-object:qa-lead` | `leader` |
| `closure` | `no` | `leader` | `agent-object:coo` | `leader` |
| `inspect` | `no` | `reviewer` | `agent-object:inspector` | `reviewer` |
| `axis-attack-qa` | `no` | `reviewer` | `agent-object:inspector` | `reviewer` |
| `code-attack-qa` | `no` | `reviewer` | `agent-object:qa` | `reviewer` |
| `evidence-integrity` | `no` | `reviewer` | `agent-object:inspector` | `reviewer` |

Read the writer row carefully: a `work` Brick declares `requires_brick_write_scope: yes` + `performer_lane_need: worker`. The only Agent Object in the `worker` lane is `dev`, so the lane match lands `work` on `dev` — without anyone hard-wiring "use dev" as an authority. The match itself is **capability >= need**: a write-capable Agent may also serve a read-only Brick (lane must still equal `performer_lane_need`); only the write NEED filters out non-writers. Leaders are write-capable too, so a leader-lane Brick that declares a write NEED can match a leader directly. The per-step provider sandbox follows the Brick's NEED, not the Agent's capability: a read-only Brick yields a read-only sandbox even for a write-capable leader. And there is no silent write grant — at live run admission, a brick row carrying `write_scope` must explicitly declare `requires_brick_write_scope: true`, or the run is rejected.

This mirrors the file-write rule from `AGENTS.md`: the active write intersection is *Brick `write_scope` + Agent tool policy + adapter technical capability + write observation*. The NEED↔CAPABILITY match is the Agent-selection side of that same intersection.

> **Limitation / not proven here.** This document describes the *intended* selection model as stated in the brick specs and the completeness checker. The fields `requires_brick_write_scope`, `performer_lane_need`, and `agent_object_hint_ref` are present in `brick/templates/bricks/<kind>/brick.md` frontmatter, and `lane` is present in every `agent/objects/*.yaml`; the checker enforces that those fields exist and resolve, and `support/checkers/lib/rule_runners.py` enforces an agent's expected `lane`. The narrow claim grounded here is "the fields and the lane check exist." It is not proven by this document that any given end-to-end plan actually ran the match, nor that the selected provider produced correct work.

## The return disciplines: facts, not verdicts

Every Agent Object binds the same two disciplines (`discipline_refs`): `discipline:closed-agentfact` and `discipline:proof-limits`. These govern what a performer is allowed to *return*, and they are where the "Agent performs but does not judge" boundary becomes enforceable.

### Closed AgentFact

The closed AgentFact discipline (`agent/disciplines/closed-agentfact.md`) says the return is recorded as exactly:

```text
AgentFact(received_work, returned)
```

and instructs the performer:

> Do not add status, verdict, score, credential body, provider session, route, or Link decision fields to the returned payload.

This is backed in code. `agent/return_fact.py` defines `AgentFact` as a frozen dataclass with only two fields, `received_work` and `returned`, and `make_agent_fact(...)` requires both. The same module keeps a `RETURNED_FORBIDDEN_KEYS` set that lists the keys a returned payload may not contain — including `approved`, `complete`, `done`, `fail`/`failed`/`failure`, `movement`/`movement_choice`, `quality`/`quality_score`, `result`, `route_target`, `score`, `status`, `success`, `verdict`, and credential/secret/session keys. An Agent that tries to declare its own success, failure, quality, movement, or route is returning a forbidden key by construction.

### Proof limits

The proof-limits discipline (`agent/disciplines/proof-limits.md`) shapes *how* a return is phrased. Every Agent return should preserve:

```text
observed evidence
narrowly proven
not proven
next Movement as caller or Link supplied, never Agent supplied
```

and the discipline closes with: *"This discipline records reporting shape only. It does not judge the work."* So even the act of stating what was proven is bounded: a performer reports observed evidence and what it could *not* prove, and it never supplies the next Movement — that comes from the caller or from Link.

### Raising a concern without claiming authority

`agent/return_fact.py` also admits a structured, **non-binding** way for a performer to flag a problem: `transition_concern_evidence`. It must set `binding: false`, name a `concern_kind` from the admitted set —

```text
design_gap, implementation_gap, upstream_gap, boundary_mismatch,
insufficient_input, replay_needed, verification_gap, unknown
```

— and may optionally reference Brick boundaries in `related_boundary_refs`. The validator (`validate_transition_concern_evidence`) rejects any unadmitted key. The actually-required fields are: a `concern_ref` that starts with `transition-concern:`, a `concern_kind` from the admitted set above, a `binding` that is exactly `false`, and non-empty `reason_refs`. `related_boundary_refs` is **optional** (it defaults to empty), and the Brick-boundary prefix check runs only over entries that are actually present. This lets a reviewer or worker say "I think there is a gap here" as **evidence**, while the discipline still forbids it from deciding the verdict or the Movement.

## How this fits together

The Agent axis is the performer, and it is built so the performer can do real work while being unable to grade it:

1. An **Agent Object** declares a provider-neutral role (`agent/objects/*.yaml`) with a `lane`.
2. A **tool policy** (`agent/tool_policies/*.yaml`) bounds what that role may touch — only `read-write-scoped` (carried by `dev` and the four team leads; the COO and the reviewers stay read-only) can write, and only inside a Brick-declared `write_scope`.
3. A Brick declares its **NEED** (`requires_brick_write_scope` + `performer_lane_need`); the Builder **selects** an Agent whose lane/policy/capability **matches**, with `agent_object_hint_ref` as an optional hint, not an authority.
4. The selected Agent returns a **closed AgentFact** (`received_work`, `returned`) under the **proof-limits** discipline — observed evidence and what is not proven, never a verdict and never the next Movement.

Whether the work was good (quality), whether it counts (success), and where it goes next (Movement) all live outside the Agent axis. Support records what was received and returned as evidence; it is *not* source truth, *not* a success judgment, *not* a quality judgment, and *not* Movement authority.

## Historical note: P7 provider-to-role matrix (0531)

The P7 recompile (0531) recorded a provider-class to role matrix: builder lane = `dev` (Codex-class); attack-review = `inspector` or `design-lead` (Opus-class); broad-review = `qa`, `qa-lead`, or `inspector` (Gemini-class). Since F-AGENT (0610), role projections are provider-native per Agent Object and the sandbox/tool mapping is code-enforced (`codex_projection_native` / `claude_projection_native` kernel checks); the matrix above is the historical 0531 assignment, not a live binding rule.

## Source files

Everything above is grounded in:

```text
agent/objects/*.yaml              the eight Agent Objects (lane + refs)
agent/tool_policies/*.yaml        read-write-scoped, leader-coordination, reviewer-readonly
agent/disciplines/closed-agentfact.md
agent/disciplines/proof-limits.md
agent/return_fact.py              AgentFact, RETURNED_FORBIDDEN_KEYS, transition-concern validation
brick/templates/bricks/<kind>/brick.md       brick specs declaring requires_brick_write_scope / performer_lane_need / agent_object_hint_ref
support/checkers/check_bricks_spec_completeness.py   the NEED<->CAPABILITY selection intent + enforcement
support/checkers/lib/rule_runners.py                 the agent-resource lane check
AGENTS.md                         the Agent Axis section and the write-intersection rule
```
