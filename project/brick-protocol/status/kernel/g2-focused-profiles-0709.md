# G2 focused profiles — 0709 measure

| | |
|---|---|
| **Class** | **support evidence only** |
| **Not** | source truth · success judgment · quality judgment · Movement authority · G2 Exit seal |
| **When (UTC)** | 2026-07-09T12:05:15Z → 12:05:20Z |
| **Repo** | `/Users/smith/projects/BRICK` |
| **HEAD** | `c95bb1488` (main, ahead of origin/main by 4 at measure time) |
| **HOME** | `/Users/smith` (REAL HOME) |
| **PYTHONPATH** | `.` |
| **Command family** | `python3 brick_protocol/support/checkers/check_profile.py --repo . --profile <name>` |
| **Product source** | not modified by this measure |

---

## Purpose

Read-only measurement of G2 authoring-related focused checker profiles on current main checkout, to feed ACTIVE_COO_GOAL G2 Exit evidence (not to declare Exit).

ACTIVE_COO_GOAL G2 row (measure-time wording):

```text
G2 Authoring Product | W1a defer fixtures + W1b 제품 + #3 order-chain; focused profile green
Status: IN PROGRESS (building complete + WIP land 0b2f43dc5; Exit 미확정)
```

04 Exit bullets relevant to this measure:

```text
- clean-tree profile green
- G2 Exit seal: focused profiles green on landed authoring code
```

---

## Profiles / checks run

| Name | How run | Profile YAML exists? |
|---|---|---|
| `building_call_authoring` | `check_profile.py --profile building_call_authoring` | yes — `brick_protocol/support/checkers/profiles/building_call_authoring.yaml` |
| `building_call_lowering` | `check_profile.py --profile building_call_lowering` | yes — `…/building_call_lowering.yaml` |
| `structure_plan_fan_barrier` | `check_profile.py --profile structure_plan_fan_barrier` | yes — `…/structure_plan_fan_barrier.yaml` |
| `package_path_admission` | **no dedicated profile YAML**; standalone `check_package_path_admission.py --repo .` | no profile file; also embedded as `kernel_checks` in the three profiles above (and many others) |

---

## Results (rc / pass-fail / log)

| Target | rc | Overall | Log |
|---|---:|---|---|
| `building_call_authoring` | **1** | **FAIL** | `/tmp/g2-profile-building_call_authoring.log` |
| `building_call_lowering` | **1** | **FAIL** | `/tmp/g2-profile-building_call_lowering.log` |
| `structure_plan_fan_barrier` | **1** | **FAIL** | `/tmp/g2-profile-structure_plan_fan_barrier.log` |
| `package_path_admission` (standalone) | **1** | **FAIL** | `/tmp/g2-profile-package_path_admission.log` |

### Per-profile kernel observation summary

Runner pattern: declarative rules completed without red; authoring-related kernel contracts completed without red; **only** `package_path_admission` observed `red(source)` and caused profile rejection.

#### `building_call_authoring` (rc=1)

| Kernel check | Observation |
|---|---|
| `building_call_authoring_contract` | DONE, **no red** |
| `package_path_admission` | **red(source)** → profile reject |
| `axis_crossing_elegance` | DONE after red isolation, **no red** |

Declarative rules (path_exists, text_contains, cases, …): all progress DONE; no rule-level red in log.

#### `building_call_lowering` (rc=1)

| Kernel check | Observation |
|---|---|
| `building_call_lowering_contract` | DONE, **no red** |
| `structure_plan_fan_barrier` | DONE, **no red** |
| `package_path_admission` | **red(source)** → profile reject |
| `axis_crossing_elegance` | DONE after red isolation, **no red** |

#### `structure_plan_fan_barrier` (rc=1)

| Kernel check | Observation |
|---|---|
| `structure_plan_fan_barrier` | DONE, **no red** |
| `package_path_admission` | **red(source)** → profile reject |

#### `package_path_admission` standalone (rc=1)

- Rejects paths “not listed in current seed admission set”.
- Counted unlisted paths in log: **1895**.
- Dominant class: `project/brick-protocol/buildings/<building>/…` (**1884**).
- Residual status paths: **11** under `project/brick-protocol/status/kernel/{fixtures,resume-declarations}/…`.

Unlisted building roots observed:

```text
prevention-l1-l2-hook-0709-v2
prevention-l1-l2-hook-0709-v3
prevention-l1-l2-hook-0709-v4
prevention-l3-3a-observe-0709-v2
prevention-l3-3a-observe-0709-v3
prevention-l3-3a-observe-0709-v4
w1a-defer-fixtures-0709
w1b-authoring-0709
w2-5-progress-autorefresh-0709
w2-6-charter-fill-0709
w2-6-charter-fill-official-0709
w2-ux-authoring-0709
```

Unlisted status paths (full list from log):

```text
project/brick-protocol/status/kernel/fixtures/g1-mid-hold-resume-dogfood-decl-0709.yaml
project/brick-protocol/status/kernel/fixtures/g2-authoring-w1b-decl-0709.yaml
project/brick-protocol/status/kernel/resume-declarations/building-call-authoring-0708e-forward.json
project/brick-protocol/status/kernel/resume-declarations/building-call-authoring-0708e-repair-forward.json
project/brick-protocol/status/kernel/resume-declarations/g1-mid-hold-resume-dogfood-0709-forward-b.json
project/brick-protocol/status/kernel/resume-declarations/g1-mid-hold-resume-dogfood-0709-forward.json
project/brick-protocol/status/kernel/resume-declarations/g2-authoring-w1b-0709b-forward.json
project/brick-protocol/status/kernel/resume-declarations/l3-3a-v3-reroute.json
project/brick-protocol/status/kernel/resume-declarations/prevention-l1-l2-hook-0709-forward.json
project/brick-protocol/status/kernel/resume-declarations/prevention-l3-3a-observe-0709-forward.json
project/brick-protocol/status/kernel/resume-declarations/route-walker-6e-7-advisory-view-0709-forward.json
```

Proof limit on checker itself (from log):

```text
proof limit: this checker only inspects path admission; absence is not semantic readiness.
```

---

## Failure class (measurement)

```text
Single shared reject: package_path_admission seed-admission drift
  = repo-local building evidence trees + status fixtures/resume-decls
  present on disk but not admitted in seed set.
```

Not observed as red on this run:

```text
building_call_authoring_contract
building_call_lowering_contract
structure_plan_fan_barrier
axis_crossing_elegance
profile declarative rules for the three focused profiles
```

Interpretation bound: “contract green / fan-barrier green inside the profile” is **isolated observation**, not a standalone green profile result. Profile rc remains 1 because every focused G2 profile embeds `package_path_admission`.

---

## Does this block G2 Exit per ACTIVE_COO_GOAL?

| Question | Measured answer |
|---|---|
| Does ACTIVE_COO_GOAL / 04 require focused / clean-tree profile green for G2 Exit? | **Yes** (wording: “focused profile green”; 04 Exit: “clean-tree profile green”; memo: “Product Exit still needs focused profile green on main”) |
| Are the three G2 authoring focused profiles green on this measure? | **No** (all rc=1) |
| Therefore: does this measure block sealing G2 Exit **now**? | **Yes — Exit seal remains blocked** until focused profiles measure green (or Exit criteria are explicitly re-dispositioned by human/COO with record) |
| Is authoring-contract logic itself the observed red? | **No** on this run — red is path admission / tree hygiene on this checkout |
| Does rc=1 prove authoring product broken? | **No** — support evidence only; not success/quality/Movement judgment |
| Are G2-a/G2-b dogfood / G2-c order-chain closed by this measure? | **No** — this measure only covers focused profiles |

Additional G2 Exit items **not** measured here (still open or out of scope for this file):

```text
G2-a fixture/변이 닫힘
G2-b authoring → confirm → lowering → brick build on G1 path dogfood complete
direct_preset = trivial only policy + checker alignment
G2-c cleanup-10e order-chain
```

---

## Ops note (hygiene vs product)

At measure time `git status` showed dirty/untracked surfaces including under `project/brick-protocol/buildings/` and modified status kernel docs. That matches the package_path red class (unadmitted building evidence + status fixture/resume paths).

This report does **not** prescribe delete/admit/move. Disposition options remain operator/Building work (support hygiene or seed admission update), not implied by this measure.

---

## Reproduction

```bash
cd /Users/smith/projects/BRICK
export PYTHONPATH=.

python3 brick_protocol/support/checkers/check_profile.py --repo . --profile building_call_authoring \
  > /tmp/g2-profile-building_call_authoring.log 2>&1; echo rc=$?

python3 brick_protocol/support/checkers/check_profile.py --repo . --profile building_call_lowering \
  > /tmp/g2-profile-building_call_lowering.log 2>&1; echo rc=$?

python3 brick_protocol/support/checkers/check_profile.py --repo . --profile structure_plan_fan_barrier \
  > /tmp/g2-profile-structure_plan_fan_barrier.log 2>&1; echo rc=$?

# no package_path_admission profile yaml; standalone kernel checker:
python3 brick_protocol/support/checkers/check_package_path_admission.py --repo . \
  > /tmp/g2-profile-package_path_admission.log 2>&1; echo rc=$?
```

---

## Bottom line

```text
G2 focused profiles on REAL HOME main @ c95bb1488: ALL FAIL (rc=1)
Shared red: package_path_admission (seed admission / unlisted project buildings + status fixtures)
Authoring contracts + structure_plan_fan_barrier kernel bodies: no red on this run
ACTIVE_COO_GOAL G2 Exit: still blocked by "focused profile green" measurement requirement
This file = support evidence only; does not seal or unseal G2
```
