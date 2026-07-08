# Repository role, source boundary, and history

This page covers the repository's own role/provenance narrative: what this
protocol repository is (vs. the legacy Brick Engine), the FSR-0 physical
surface reorganization, current control-surface records, and the historical
governed-goal disposition note. It moved out of `README.md` (split 0701, see
`project/brick-protocol/status/kernel/brick-followon-doc-skill-checker-catalog-0701.md`)
because it is repo-internal governance/history material, not first-clone
quickstart material. For the current live module architecture, see
[architecture-map.md](architecture-map.md). For getting started, see
[quickstart](quickstart.md) and [setup](setup.md).

Note: this page references `project/brick-protocol/...` paths that are local
vessel/status evidence. Those paths do not exist in a fresh release export
(`project/` is excluded by `brick_protocol/support/onboarding/release_export.sh`); the first
onboard/run in a given checkout creates them.

## Repository Role

This repository is a clean-room protocol repository.

It starts from the closed Brick / Agent / Link specification package and the
physical blueprint, not from the legacy Brick Engine implementation tree.

The current governed work is completion audit for the governed TSK / dogfood
roadmap. The next possible work is:

```text
Smith Movement on whether to mark the active goal complete
```

DASH-0 creates dashboard projection guidance and read-only viewer boundary
guidance for the external starter-kit project and records project-local
Building evidence for both. It does not create a dashboard application, sync,
runtime/provider/scheduler/storage surfaces, central storage, adoption proof,
dashboard-need proof, projection-correctness proof, or new protocol contracts.

## Source Boundary

Brick Protocol defines:

```text
rules
contracts
structure
boundaries
```

Brick Engine remains:

```text
legacy runtime evidence
reference implementation material
measurement source
contamination sample
```

Brick Engine is not the source of truth for this repository.

## Current Physical Surfaces

FSR-0 reorganizes the working tree around five protocol surfaces:

```text
brick_protocol/brick/    Brick axis physical surface
brick_protocol/agent/    Agent axis physical surface
brick_protocol/link/     Link axis physical surface
brick_protocol/support/  support machine location only
project/  project-local evidence destination only
```

The import identity is retained under support:

```text
brick_protocol/support/import_identity/brick_protocol/
  Python import identity marker only
```

Root-level `brick_protocol/` is no longer an active repository root. The Python
namespace remains `brick_protocol`; only the address marker moved under
`brick_protocol/support/`.

`architecture-review-site/` is no longer an active repository root. Root-level
public docs site / Vercel projection surfaces are removed from the active repo
shape and must not be recreated without a later explicit admission.

Support is not an axis, module family, source truth, success judgment,
Movement authority, runtime, storage, or wiki. Project evidence under
`project/brick-protocol/building-evidence/` is an evidence destination only,
not source truth.

The v0.1 internal candidate freeze preserves BAL semantics and the public
`brick_protocol.*` import API. FSR-0 changes physical locations only; it does
not mutate the `v0.1-internal-candidate-20260518` tag.

## Active Records

Current control surfaces:

```text
AGENTS.md
project/brick-protocol/PROGRESS.md
brick_protocol/support/docs/spec/
brick_protocol/support/docs/reviews/
brick_protocol/support/docs/projection/
brick_protocol/support/checkers/
```

Current Building automation chain:

```text
BUILDING-METHOD-0
-> COO-IDENTITY-SKILL-0
-> AGENT-RESOURCE-TOOLKIT-0
-> COO-SYNC-0
-> MCP-PROJECTION-0
-> BUILDING-GRAPH-NEED-0
```

COO-SYNC-0 writes only local COO projection files for Codex and Claude from the
Agent-axis resource source. Projection files are not source truth and do not
replace `brick_protocol/agent/`.

MCP-PROJECTION-0 exposes the admitted Agent resource renderer through a
read-only support call door for local apps. MCP is projection only; it is not a
fourth axis, runtime, provider owner, storage/wiki surface, source truth, or
Movement authority.

BUILDING-GRAPH-NEED-0 closes why graph projection is required for three-axis
problem analysis before graph/multi-lane runner implementation.

Historical dev log (FSR-0 / TSK-0..4 / TEAM-0..1 / DASH-0 phase records,
review dispositions, and superseded spec history from 0518-0531) lives in the
HISTORY repository (`brick-protocol`, the repo this product repo was split
from at REPO-SPLIT 0611), under its top-level `archive/` productization
museum. This product repo ships NO archive/ tree at all (CLEAN-YARD v3,
0611): the engine repo starts at project zero, and a check that needs
building evidence generates it with the real engine at check time and
removes it. Archived records are historical support evidence only -- not
source truth, not success judgment, not Movement authority. The live,
checker-pinned records stay under `brick_protocol/support/docs/` and
`project/brick-protocol/status/kernel/`.

## Historical Support Note

```text
Historical disposition wording: pass
Target: Smith disposition on whether to mark the historical governed TSK /
dogfood roadmap goal complete.

TSK-0 recorded the starter-kit / dogfood phase sequence after MIA-0. TSK-1
defined the future external project boundary only. TSK-2 created only the
admitted starter-kit wrapper guidance/templates. TSK-3 records the first real
starter-kit Building, `FIRST_USE.md`, project-local Building evidence, local
verification, Opus review, Gemini 3.5 review, Codex disposition, and accepted
wording repairs as support evidence. TSK-4 records repeated self-dogfood work
products, two project-local Building evidence packets, local verification, Opus
review, Gemini 3.5 review, Codex disposition, and accepted no-patch disposition
as support evidence. TEAM-0 now records local-trial and privacy-boundary
guidance, evidence, local verification, Opus review, Gemini 3.5 review, Codex
disposition, and accepted no-patch disposition as support evidence. It does not
create TEAM-1, runtime, provider adapters, sync, dashboard, storage/wiki,
source truth, success judgment, quality judgment, team adoption proof, dashboard
need proof, mandatory raw transcript sharing, or Movement authority.
TEAM-1 now records claim-trace export and multi-local projection guidance and
evidence, and does not create DASH-0, runtime, provider adapters, sync,
dashboard, storage/wiki, central storage, source truth, success judgment,
quality judgment, team adoption proof, dashboard need proof, projection
correctness proof, mandatory raw transcript sharing, or Movement authority.
Opus and Gemini 3.5 returned PASS with no BLOCKER or MINOR findings; Codex
recorded no-patch support notes for future DASH-0/table-shape risks.
DASH-0 now records dashboard projection and read-only viewer boundary guidance
and evidence, and does not create a dashboard application, runtime, provider
adapters, sync, storage/wiki, central storage, source truth, success judgment,
quality judgment, team adoption proof, dashboard need proof, projection
correctness proof, mandatory raw transcript sharing, or Movement authority.
Opus and Gemini 3.5 returned PASS with no BLOCKER or MINOR findings; Codex
accepted the completion-audit-surface memo and recorded this completion audit.

Reviews and checkers are not source truth and not Movement authority. Smith
remains closure authority and commit/push authority.
```
