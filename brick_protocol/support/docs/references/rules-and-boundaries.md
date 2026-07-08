# Rules and boundaries for contributors

Brick Protocol enforces a small set of hard rules in code and checkers, not in
prose. This page surfaces those rules for humans so you do not have to read the
checker source to know what will reject your change. Every rule below is grounded
in a source file in this repository; where the source is silent or a behavior is
not proven, this page says so.

The single most important framing: Brick is the work, Agent is the performer, and
Link is the transfer/carry/movement. Those are the only three meaning axes.
Everything else — `brick_protocol/support/`, checkers, docs, projections, runtime, providers — is
support, evidence, or projection. Support records facts; it never judges.

## 1. File and document location law

There is no root-level `docs/` directory. It was rebased. `AGENTS.md` records the
active path rebase:

```text
docs/              -> brick_protocol/support/docs/
.status/           -> project/brick-protocol/status/
brick_protocol/support/status/    -> project/brick-protocol/status/
tests/checkers/    -> brick_protocol/support/checkers/
building-evidence/ -> project/brick-protocol/building-evidence/
```

The path admission checker (`brick_protocol/support/checkers/check_package_path_admission.py`)
enforces these as forbidden roots, with two distinct rejection messages (both
forbidden). Relocation roots — `docs/`, `.status/`, `building-evidence/`, and
root-level `brick_protocol/` — are rejected with a "superseded by" message, e.g. a
path at or under `docs/` gives `old physical path docs is superseded by
brick_protocol/support/docs/`. The legacy/runtime owner roots are rejected with a different
message, `legacy/runtime/support owner root <root> is not admitted`; these are nine
roots: `brick_engine`, `engine`, `runtime`, `storage`, `wiki`, `legacy`,
`provider`, `scheduler`, `dashboard`.

### Where docs live

Documentation lives under `brick_protocol/support/docs/<admitted subdir>`. The admitted doc
subdirectories, as listed in the checker's `ALLOWED_DIRS`, are exactly:

```text
brick_protocol/support/docs/spec
brick_protocol/support/docs/spec/full-spec
brick_protocol/support/docs/spec/physical-blueprint
brick_protocol/support/docs/reviews
brick_protocol/support/docs/references
brick_protocol/support/docs/projection
```

A new `.md` file **inside an already-admitted doc folder is free** — no admission
edit is needed. The checker admits, by pattern, any `.md` file directly under
`brick_protocol/support/docs/spec/`, `brick_protocol/support/docs/reviews/`, `brick_protocol/support/docs/references/`, and
`brick_protocol/support/docs/projection/`. (This page itself is a new `.md` under
`brick_protocol/support/docs/references/`, which is why no checker change was required to add it.)

> Note: `brick_protocol/support/docs/spec` and `brick_protocol/support/docs/projection` are admitted as
> directories in `ALLOWED_DIRS`, but the by-pattern `.md` admission in
> `allowed_path()` matches files under `brick_protocol/support/docs/spec/`, `.../reviews/`,
> `.../references/`, and `.../projection/`. `brick_protocol/support/docs/templates/` was
> retired (#24, 0610); its only file (`work_contract_template.md`) moved to
> `archive/docs-templates/`. `SUPPORT_DOC_TEMPLATE_FILES` is now an empty set
> with no live admission class.

### A new top-level path needs seed admission

If you want to create a path that is **not** under an already-admitted folder, the
checker will reject it with:

```text
path <your-path> is not listed in current seed admission set
```

Opening a new top-level surface is a deliberate "seed admission" step: it means
adding the new directory or file family to `check_package_path_admission.py`
(`ALLOWED_DIRS`, a target set, or a path-predicate function). This is intentional
friction — surfaces are opened one at a time, on purpose, not by accident.

> Limitation: this checker only inspects path admission. As its own help text
> states, it does not prove implementation correctness, source truth, Movement, or
> project success. Passing it means "this path is allowed to exist," nothing more.

## 2. Session ids and provider-runtime ids must never appear in support records

A session id, provider session id, credential, or auth/token body must never be
written into a support record, projection, or evidence file. This is enforced in
several independent places:

- **Agent Object resources.** `brick_protocol/support/connection/agent_resources.py` defines
  `_FORBIDDEN_AGENT_OBJECT_KEYS`, which includes `session_id`,
  `provider_session_id`, `credential_body`, `setup_token`, and
  `setup_token_value`. An Agent Object (`brick_protocol/agent/objects/*.yaml`) carrying any of
  these keys is rejected at load time with `forbidden Agent Object keys: ...`.
- **Required redaction hook.** The same module requires every Agent Object to
  carry `hook:resource-ref-redaction` (`_HOOK_RESOURCE_REF_REDACTION`); an object
  missing it is rejected.
- **Building evidence files.** `brick_protocol/support/checkers/check_building_lifecycle_path_shape.py`
  lists `session_id`, `session`, `token`, `auth`, `credential`, `credentials`, and
  `credential_body` in `ADAPTER_ERROR_FORBIDDEN_KEYS`, so adapter-error evidence
  cannot contain them; it also rejects credential-like text.
- **Adapter source bodies.** `brick_protocol/support/connection/agent_adapter.py` actively redacts
  before recording: `safe_source_fact_body()` replaces matched secrets with
  `[REDACTED_RAW_CREDENTIAL]` and matched provider sessions with
  `[REDACTED_PROVIDER_SESSION_REF]`, and `_reject_secret_text()` rejects raw
  credential-looking text outright.

The rule in plain terms: support connects to a provider, but it stores
**provider-neutral references only**. Identity such as a live session id or a
credential body is runtime state, not evidence, and the protocol treats writing it
into evidence as a violation.

## 3. Truth vs Quality: support records facts, humans judge quality

Support records **facts only**. It records what was received, what was returned,
what was missing, and what is not proven. It does **not** decide whether the work
was good, successful, or correct. Quality judgment is a **separate layer, appended
later, authored by a human** (or a human-adopted review), never auto-written by the
support machinery.

The fact vocabulary appears throughout the sources:

- `brick_protocol.support.operator.run` records "what was received, what was
  returned, and what Link facts were declared" (see
  `brick_protocol/support/docs/references/quickstart.md`), and states that evidence "is not source
  truth, not a success judgment, not a quality judgment, and not Movement authority."
- GateFact (Link sufficiency) reports `missing_required_facts` and `sufficiency`
  only; `AGENTS.md` states it "does not choose Movement, route, destination,
  rollback, retry, hold state, next target, quality, success, failure, outcome,
  runtime execution, or storage truth."
- Every resolver in `brick_protocol/support/connection/agent_resources.py` returns
  `proof_limits` and `not_proven` lists that explicitly include "not success
  judgment" and "not quality judgment."

So when you add a support record or projection, the test is: **am I stating a fact
(received / returned / missing / not_proven), or am I stating a verdict?** If it is
a verdict — "the Brick was mis-cut," "the Agent under-delivered," "this passed" —
it does not belong in the brick_protocol/support/truth layer. It belongs in a separate,
human-authored quality note added after the facts exist.

> This page describes the principle as it appears in the sources (the fact fields,
> the `proof_limits`/`not_proven` discipline, and the "support never judges"
> language in `AGENTS.md`). The detailed two-layer evidence machinery is an
> evolving area; treat the principle as binding and the specific file layout as
> subject to change.

## 4. Three axes — and support is not a fourth

`AGENTS.md` is explicit:

```text
Brick = work
Agent = performer
Link = transfer / carry / movement
```

and:

```text
Support is not a fourth axis.
Protocol is the project name, not a fourth axis.
```

Runtime, engine, storage, wiki, docs, tests, checkers, memory, tools, providers,
generated output, dashboards, reporters, projections, and project records are all
support / evidence / projection surfaces only. Per `AGENTS.md`, they must not
become source truth, success judgment, quality judgment, Movement authority, a
target selector, a route inventor, or a fourth axis.

Concretely for contributors:

- Support may **walk, validate shape, record evidence, render projections, and
  observe frontiers.**
- Support must **not** choose Movement, invent route targets, create undeclared
  GateFacts, classify Agent returns as success/failure, judge quality, store
  credential/session bodies, or open scheduler/queue/retry runtime ownership.

Axis meaning is owned by the axis. Code under `brick_protocol/support/` reads and records; it does
not own Brick, Agent, or Link meaning. The Agent Object, for example, is "an
Agent-axis provider-neutral contract data resource" and is explicitly "not a BAL
fact class, not a fourth axis, not a provider runtime" (`AGENTS.md`,
`brick_protocol/support/connection/agent_resources.py`).

## How these rules are checked

The two checkers cited above run as part of the support checker profiles. Path
admission and lifecycle/evidence shape are mechanical gates: they confirm a path is
admitted and that forbidden keys are absent. They do **not** confirm your change is
correct, complete, or good — that remains a separate, human judgment. When in
doubt about opening a new surface or recording a new field, prefer to ask before
adding it; seed admission and the truth/quality split are deliberate, not
incidental.
