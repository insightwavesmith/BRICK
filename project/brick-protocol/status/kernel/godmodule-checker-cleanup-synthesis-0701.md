# Godmodule + Checker Cleanup — Synthesized Plan (0701)

## 0702 재실측 (재도출)

이 문서는 0702에 독립 멀티에이전트 재검증으로 갱신됨. 0701 베이스라인(main HEAD
`62a02c2`) 수치 중 흐른(drift) 것은 아래에서 새 값으로 대체하고, 확인된 것은
그대로 두었으며, 재검증 결과 모호하거나 재확정 불가능해진 것은 인라인 노트로
표시했다. 현재 HEAD는 `8faeafe3` (2026-07-02) — 0701 베이스라인 이후 17개+
커밋이 더 랜딩했다.

**바뀐 것 (드리프트 확인, 값 교체):**
- `kernel_checks.py` LOC 10201 → **10141**
- `check_profile.py` LOC 1391 → **1397**; import block 이름수 "~17개+call_main" →
  **27개**(26 + call_main) — 원 수치는 상당히 과소집계였음
- 3개 axis-vocab allowlist 줄번호 118/129/137 → **119/130/138**
- `case_runners.py` LOC 8507 → **8512**
- `kernel_checks.py:3427`의 `_preset_completion_command_runner` import →
  **3429번 줄**(및 이전에 언급 안 된 두 번째 위치 3635번 줄도 존재)
- `RULE_RUNNERS` 소재지 주장 "`rule_runners.py`로 이동" → **오류로 판명**,
  실제로는 `check_profile.py:235`에 딕셔너리 자체가 정의됨(`rule_runners.py`는
  개별 rule-runner 함수만 보유)
- `check_profile.py`의 `case_runners.py` import 블록 이름수 "~37개" →
  **정확히 33개**(case_runners.py 쪽만); `rule_runners.py` 쪽 15개 합쳐 총 48개
- `RULE_RUNNERS` 딕셔너리 줄 234 → **235**
- `check_bounded_agent_proposed_routing_loop0.py` LOC 7087 → **7176**
- `walker_kernel.py` LOC 2306 → **2479**
- `module_registry.yaml` LOC 2052 → **2072**; 행수 162 → **164**
- `checker_strict_validation` phantom 참조 줄번호 78/523/535 → **78/533/545**
  (78은 불변, 나머지 2개 드리프트)
- `profiles/*.yaml` 라이브 프로필 수 30 → **31**(문서가 언급 안 한 신규 2개:
  `provider_registry_ladder.yaml`, `raw_evidence_stream_scrub.yaml`)
- `KERNEL_DISPATCH` 키 수 65 → **67**
- **`.github/workflows/` 존재 안 함" 주장 → 정면 반박됨.** `release-gate.yaml`이
  실존(커밋 `60b46b9`, 2026-07-01, "P8 ship safety" 빌딩 산출물) — CI 게이트가
  이미 생김
- fixture vessel 관련 줄번호: `~7813-8020` → **7767-8029**;
  `read_side_projection_boundary.yaml` 핀 줄 479 → **488**
- `check_adapter_usage_meter.py`: `probe_mutation_red` 함수 978 → **1021**;
  `--probe-mutation-red` 플래그 1115 → **1159**; `agent_adapter.py` stale 참조
  1118 → **1162** (그리고 `agent_adapter.py`는 삭제된 게 아니라 **실존하는 다른
  파일** — 참조가 잘못된 대상을 가리키는 것이지 존재하지 않는 파일이 아님)
- `assert_registry_closure()` 줄 1061-1085 → **1068-1094**; `validate_profile()`
  줄 1098 → **1104**
- `check_adapter_usage_meter.py`의 스트레이 `def test_*` 함수 줄 311/935 →
  **312/978**
- 0630 감사 S4-F8 `.brick/builds` 가드 줄 8489/8728 → **8574/8829**
- **P9(최종 동적 증명) 게이팅 상태 변경**: 0701 문서 작성 시점엔 미종결이었으나,
  같은 날 0701 19:57에 종결/채택됨(커밋 `46d02e4`,
  `brick-6-p9-dynamic-proof-closure-disposition-0701.md` 참고). 즉 본 문서
  §4의 "P9 종결 후 시작" 전제조건은 **이제 충족됨**(단, P0-P9 전체 골 완료
  선언을 위한 별도 최종 검토는 여전히 남아있음).

**확인됨 (드리프트 없음, 그대로 유지):**
- 8개 leaf module 추출 전부 실존 확인
- `run_*` 엔트리포인트 수 16 (kernel_checks.py)
- `check_profile.py`가 kernel_checks.py의 유일한 임포터
- `_AXIS_VOCAB_*_ALLOWLIST` 3개 모두 실존(줄번호만 이동)
- `kernel_common.py` / `kernel_checks_*.py` 부재 확인
- case_runners.py 8개 추출 파일 전부 실존; 2위 최대 파일 순위 유지
- `run_.*_case` 함수 수 28
- `check_building_operator_driver0.py:75`의 `_graph_test_plan_from_linear` import
- `check_bounded_agent_proposed_routing_loop0.py` — "3번째로 큰 파일이며 어느
  문서도 분해 클러스터맵을 만든 적 없음" 주장은 실질적으로 유지(단, "the
  largest checker file" 표현은 문서 자체의 기존 내부 모순이며 0701 당시부터
  있었던 것 — 실제로는 3번째로 큼)
- `building_skill_preset_agent_tool_hardening.yaml` LOC 4237, 라벨수 99,
  3개 스플릿 사본 LOC/라벨수/중복수학(12 중복/87 미소속) 전부 정확
- `RULE_RUNNERS` 키 수 50 (안정적)
- 죽은 pytest 선언 수정, setup.md/checker-profile-map.md 하드코딩 수정 —
  모두 여전히 유효
- `walker_kernel.py` 스플릿(clusters A-E) 완료 상태 — 여전히 유효
- 12개 중복 checker-diet 라벨에 대한 mutation-RED probe 부재 — 여전히 유효
- anti-toothless-profile 가드 미구현 — 여전히 유효(§4 item 6은 여전히 실행
  가능한 미완 작업)
- item 5(`checker_strict_validation` phantom row 정리)는 여전히 미수리 —
  단, 재검증 결과 이것이 기능적 결함이 아니라 **무해한 stale 서술 텍스트**임이
  새로 확인됨(아래 §1 module_registry.yaml 항목 참고) — 코드 어디도
  `pinned_by:` 필드를 읽지 않으며, `checker_strict_validation`의 실제 검증
  커버리지는 `structure_template_integrity.yaml`로 통합되어 살아있음

---

Baseline: main HEAD `62a02c2` (2026-07-01). All numbers below are the operator's
fresh measurements taken moments ago, cross-checked against `wc -l` /
`grep -c` re-runs during verification. Treat every LOC/count figure in any
prior doc (0625/0626/0628, and the 0630 audit cluster) as stale unless
re-stated here. This doc supersedes the file-shape numbers in all 8 source
docs; it does not re-litigate their design reasoning where that reasoning
still holds.

**0702 re-verification note:** the numbers below have themselves drifted
again in the one day since this doc's own baseline. See the "0702 재실측"
section above for the current corrected values. Coordinates below are left
in their original 0701 form where a section explicitly discusses drift as a
phenomenon (Section 2), and corrected inline elsewhere.

---

## 1. 확정 필요 (Confirmed still-needed)

Organized by target file. Numbers are current (0702, re-verified), not the
stale figures carried in the source docs or in this doc's own 0701 pass.

### `support/checkers/lib/kernel_checks.py` — 10141 LOC (was cited 10201; drifted -60)
- Still monolithic. Has already shed 8 leaf modules since 0626/0628
  (`no_smith_residue_check.py`, `install_release_export_lint_check.py`,
  `provider_preflight_check.py`, `design_ai_text_seams_check.py`,
  `codex_connect_stall_classification_check.py`, `onboard_smoke_check.py`,
  `gemini_local_only_adapter_check.py`, `graph_topology_fan_barrier.py`) but
  is still the single largest checker file by a wide margin. All 8 confirmed
  to still exist on disk with real extraction commit history
  (`a779a2c`, `c3d8e03`, `1486bb8`, `c48dd9e`, `0d18b79`, `2405a9d`).
  kernel_checks.py still re-exports several of these back in via
  `from ... import` (facade pattern, explicitly commented in-file as
  intentional so `check_profile.py`'s import block stays byte-identical).
- `grep -nE '^def run_'` today = 16 public entrypoints (not the 23/24 cited
  in 0626 docs — those were correct for their own snapshot, extraction has
  since removed 8). Confirmed unchanged at 16.
- `check_profile.py` (**1397 lines**, was cited 1391) is still the sole
  importer (confirmed — no other file imports kernel_checks as a module).
  Import block is **27 names total** (26 `run_*`/utility names + `call_main`),
  not "~17 + call_main" as previously stated — that figure was a material
  undercount.
- 3 axis-vocab self-allowlist pins still present (`_AXIS_VOCAB_MOVEMENT_ENUM_ALLOWLIST`,
  `_AXIS_VOCAB_DISPOSITION_ENUM_ALLOWLIST`, `_AXIS_VOCAB_ADAPTER_ENUM_ALLOWLIST`)
  at current lines **119/130/138** (was cited 118/129/137, each +1) — these
  must relocate with whatever module re-encodes the enum literals, or
  `axis_vocab_drift` goes RED. The consuming checker `run_axis_vocab_drift`
  (line 594) is confirmed wired into `check_profile.py`
  (`KERNEL_DISPATCH["axis_vocab_drift"]` at line 329) and referenced in
  `core.yaml:5` and `module_registry.yaml:645`, so this consequence is real.
  **All prior line-number citations for this file (0625/0626/0628, and now
  0701 itself) are dead — re-derive at implementation time, do not trust any
  cached coordinate.**
- Still no `kernel_common.py` or `kernel_checks_*.py` split-module naming
  exists — confirmed absent (`ls`/`find` both empty). None of the earlier
  proposed module names were adopted; the 8 extractions that did happen used
  flat domain-named siblings instead (`support/checkers/lib/<domain>_check.py`)
  — with a nuance: 6 of 8 follow the exact `<domain>_check.py` suffix
  pattern; 2 of 8 deviate (`install_release_export_lint_check.py` still ends
  in `_check.py` but has a compound domain name; `graph_topology_fan_barrier.py`
  has **no** `_check` suffix at all). Any future split should follow the
  established convention but note it is not 100% uniform today.

### `support/checkers/lib/case_runners.py` — 8512 LOC (was cited 8507; drifted +5)
- Partially split since 0628: 8 extraction commits pulled out
  `preset_completion_fixture.py`, `gate_evidence_readers.py`,
  `plan_fixture_helpers.py`, `materialized_plan_observers.py`,
  `materialize_reject_scaffold.py`, `adapter_capability_checks.py`,
  `materialized_return_shape_guards.py`, `casting_node_carry_check.py` — all
  flat siblings in `support/checkers/lib/`, all confirmed to exist on disk.
- Still the second-largest checker file (confirmed ranking: kernel_checks.py
  10141 > case_runners.py 8512 > check_bounded_agent_proposed_routing_loop0.py
  7176). Not "done", just further along than any prior doc recorded.
- `grep '^def run_.*_case'` = 28 public case functions remain in-file.
  Confirmed exact match.
- Cross-module private-helper imports still exist and still constrain any
  further split: `kernel_checks.py` imports `_preset_completion_command_runner`
  at **line 3429** (was cited 3427; drifted +2) — and a **second, previously
  uncited occurrence exists at line 3635**, so there are now two import
  sites, not one. `check_building_operator_driver0.py:75` imports
  `_graph_test_plan_from_linear` — confirmed unchanged at line 75. **Re-derive
  exact line before touching — this number has moved at least 4 times across
  the source docs (4401/5276 → 3978/4853 → 3427 → 3429/3635) and will move
  again.**
- **Correction to a prior claim:** `RULE_RUNNERS` (50 keys, confirmed) does
  **not** live in `support/checkers/lib/rule_runners.py` as previously
  stated — direct inspection shows the dict literal itself is defined in
  `support/checkers/check_profile.py` at **line 235** (spanning to line 286).
  `rule_runners.py` (635 LOC) holds the individual rule-runner *functions*
  the dict dispatches to (15 of them: `run_path_exists`, `run_path_absent`,
  `run_path_absent_glob`, `run_path_allowlist`, `text_rule`,
  `run_yaml_literal_set`, `run_json_required_paths`, `run_json_value_paths`,
  `run_agent_resource_boundary`, `run_agent_preferred_adapter_rejects`,
  `run_agent_resource_retired_ref_rejects`, `run_building_plan_boundary`,
  `run_route_policy_boundary`, plus 2 validator helpers) — not the dict
  itself. This file's own `RULE_RUNNERS` mention is a docstring reference
  only (line 6), not a definition. Any split must keep the 50-key set
  byte-identical; the dict's home is `check_profile.py`, not either lib file.
- `check_profile.py` import block for this file (`case_runners.py`): starts
  at **line 86** (confirmed accurate) and contains **exactly 33** `run_*`
  names (lines 87-123), not "~37" as previously stated — that figure appears
  to have conflated this block with the separate `rule_runners.py` import
  block (15 names, starting line 69). Combined across both lib-file imports:
  33 + 15 = 48 names; the remaining 2 of the 50 `RULE_RUNNERS` keys are
  inline `text_contains`/`text_absent` lambdas defined directly in
  `check_profile.py` (lines 240-241). `RULE_RUNNERS` dict itself starts at
  `check_profile.py:235` (was cited 234, off by one).

### `support/checkers/check_bounded_agent_proposed_routing_loop0.py` — 7176 LOC (was cited 7087; drifted +89)
- Root cause of the +89 confirmed: exactly one commit touched this file
  since the 0701 baseline (`4f0d147`, 2026-07-01, an unrelated fan-out/fan-in
  latency fix), +91/-2 lines, net +89. Arithmetic checks out exactly
  (7087 + 89 = 7176).
- Not touched by any split work in any source doc. **Third-largest checker
  file** (ranking confirmed unchanged: behind kernel_checks.py and
  case_runners.py), growing (was 6923 at the 0630 audit, now +253 lines
  since — not +164 as the 0701 doc computed against its own now-stale
  baseline). Still wired via `_CallMainKernel` from `check_profile.py`'s
  `KERNEL_DISPATCH`.
- No prior plan proposes a concrete split shape for this file — confirmed
  across all 8 discoverable source docs, this file has zero function-level
  cluster map, family breakdown, or split-shape proposal anywhere. Every
  mention is a bare filename in a list, a LOC/size fact, or a passing
  cross-reference to one symbol/line.
  **Inline flag: the phrase "it is the largest checker file with zero
  decomposition analysis" (as written both in 0701 and carried from that
  baseline) is imprecise** — read literally it's wrong (this file is
  3rd-largest, not largest, both then and now); read as "largest checker
  file *among those with zero decomposition analysis*" it holds, since
  kernel_checks.py/case_runners.py do have partial extraction work. This
  ambiguity predates the 0702 refresh and is not new drift — flagging it
  here rather than silently resolving it either way.
- Needs its own read-first pass before any split proposal exists.

### `support/operator/walker_kernel.py` — 2479 LOC (was cited 2306; drifted +173)
- **First split already landed and is done** (commit `f0b4679`, 2026-06-26):
  5 leaf modules extracted (`walker_carry.py` 669L, `walker_frontier_driver.py`
  186L, `walker_report_events.py` 296L, `walker_resume_seed.py` 400L,
  `walker_runtime_mail.py` 237L), `walker_kernel.py` kept as slim
  orchestrator + re-export facade for 10 externally-imported names.
  Verified via 4-dimension adversarial workflow at landing time
  (byte-identity, `check_profile.py --all` exit 0, sha256-equal
  `_run_dynamic_graph_walker`, registry/admission complete). Confirmed still
  accurate, commit exists exactly as cited.
- `_run_dynamic_graph_walker` remains intact, unsplit. **Note: exact current
  line number for this function was not re-derived in this pass (file grew
  +173 lines since 0701's cited "line 805" — that coordinate should be
  treated as stale and re-derived fresh before any implementation work
  touches it, consistent with this doc's own standing rule on cached
  coordinates).** **HOLD confirmed still honored** — no further extraction
  has touched this function since 0628.
- Do-not-split reasoning still applies as originally stated: ~30 shared
  mutable locals, 7 nested closures, no `WalkerState` dataclass exists yet.
  Any future split needs P4 resume-preservation proof plus a
  `WalkerState`-gated design — this is unchanged and still the correct gate.

### `support/checkers/module_registry.yaml` — 2072 LOC / 164 rows (was cited 2052 LOC / 162 rows; both drifted)
- Growing in lockstep with every leaf extraction (each new lib module = 1
  new row). This is expected mechanical growth, not drag — do not target
  for reduction.
- Confirmed live: `support/operator/*.py` census = **63 files / 63 registry
  rows** (exact match; was cited 61/61 at 0628 — also drifted, +2 files/rows
  since, shape of the claim still holds). `support/checkers/lib/*.py`
  census = 20 files, all 20 with matching registry rows — unchanged.
  (Row-counting note: correct pattern is `^  - module:` = 164; a naive
  `grep -c "module:"` returns 166 because 2 extra hits are
  `module: support/checkers/check_profile.py` and
  `module: support/operator/report_sinks.py` inside an unrelated
  `decomposition_ceilings:` block at file-end, not actual module rows.)
- Still carries a phantom `checker_strict_validation` profile reference at
  3 lines, now **78, 533, 545** (was cited 78, 523, 535 — 2 of 3 drifted),
  with no corresponding `support/checkers/profiles/checker_strict_validation.yaml`
  file on disk (confirmed absent via `ls`/`find`). This is real registry
  drift, confirmed by direct grep, not yet repaired by any landed commit.
  **Re-derived functional-impact determination (new this pass): this is
  harmless stale prose, not a live functional defect.** No code anywhere in
  the repo reads or dereferences the `pinned_by:` field (`grep -rn
  "pinned_by" --include="*.py" .` = zero hits repo-wide) — it is purely a
  human-readable annotation. The actual validation coverage that
  `checker_strict_validation` used to represent was not lost: it was folded
  into the live profile `structure_template_integrity.yaml` (confirmed
  registered, one of the 31 live profiles), whose own `description:` field
  states it is a "PASS-2 fold of brick_template_catalog_restructure,
  checker_strict_validation, current_context_prune." What actually validates
  `module_registry.yaml` structurally is `check_package_path_admission.py`
  and `check_axis_crossing_elegance.py` (both enforce G4 bidirectional
  disk/registry-row existence — unrelated to `pinned_by` content). The
  registry's own `not_proven:` section (lines 2070-2072) self-declares that
  `pinned_by` is descriptive only, not enforced by the registry itself. Item
  5 in Section 4 remains a valid, actionable cleanup (fix 3 stale prose
  lines + 1 stale code comment at `check_profile.py:34`), but should be
  understood as a documentation-accuracy fix, not a dead-dependency repair.

### `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml` — 4237 LOC
- Still the checker-diet target. Still not thinned (B2b never ran) — file
  LOC unchanged at 4237 across the most recent touching commit (`2ff4d5d`),
  confirmed no LOC-reducing/split-completion commit landed.
- Current label count: **99** `label:` rows (drifted up from 97 cited in
  0626/0628 — 2 labels were added since). Confirmed exact match.
- 3 staged split copies exist and are registered in `core.yaml`
  `path_allowlist` (confirmed at lines 76-79, `path_allowlist:` key itself
  at line 64) alongside the original:
  - `building_skill_preset_builder_composition.yaml` — 320 LOC, 8 labels
    (all 8 overlap with original) — confirmed exact.
  - `building_skill_preset_intake_adapter_gate.yaml` — 131 LOC, 4 labels
    (all 4 overlap with original) — confirmed exact.
  - `building_skill_preset_agent_resource_boundary.yaml` — 259 LOC, **1**
    label (drifted from the 0 originally recorded — a label was added since
    the split) — confirmed exact; the single label
    (`agent-resource-digest-sentinel-materialized-fast-fix`) confirmed
    absent from the original's 99-label set, i.e. genuinely non-overlapping.
- Current conservation math: 12 labels duplicated (8+4, the
  `agent_resource_boundary` label does not overlap with original) / **87**
  labels carried ONLY by the original (99 − 12), not the 85 cited earlier.
  All figures confirmed exact via `comm -12`/`comm -23` set operations.
- `check_profile.py` confirmed to have **no** extends/include/inherit/facade
  primitive (the only "facade" hit is a comment describing `check_profile.py`
  itself, not a profile-inheritance mechanism) — a delegating facade is
  structurally impossible; diet must be complete-the-split-then-delete, not
  facade-preserving.
- Must use `support/checkers/lib/yaml_subset.py`'s loader for any inventory
  work — directly reproduced that PyYAML cannot parse `module_registry.yaml`
  (`ScannerError: mapping values are not allowed here` — confirmed at
  **line 400, column 251**, not line 390 as previously cited; that
  coordinate has drifted). The hedged "likely similar issues in this profile
  file" is now **confirmed, not merely likely**: PyYAML also fails to parse
  `building_skill_preset_agent_tool_hardening.yaml` itself
  (`ScannerError` at line 3690, column 51 — an unquoted scalar with an
  embedded colon: `expected_message: preferred_model_ref rejected:
  selected_model_ref provider must match selected adapter`).

### `support/checkers/profiles/*.yaml` — 31 live profiles (was cited 30; drifted +1)
- Confirmed current count (was 24 at 0625, 28 at 0628/0630-audit, 30 per the
  0701 pass, now **31**). New since 0628: `graph_topology_fan_barrier.yaml`
  (commit `2405a9d`) plus the 3 checker-diet split copies above (already
  counted) — **and two additional new profiles the 0701 doc never named:
  `provider_registry_ladder.yaml` and `raw_evidence_stream_scrub.yaml`**.
  Arithmetic: 28 (0628 baseline) + 3 new (graph_topology_fan_barrier,
  provider_registry_ladder, raw_evidence_stream_scrub) = 31, matches. Docs
  must stop hardcoding this number — see §2, already partly fixed.
- `RULE_RUNNERS` = 50 keys (stable across every measurement window, confirmed
  unchanged since 0625). Its dict definition lives in `check_profile.py:235`
  (see case_runners.py section above for the correction on this point).
- `KERNEL_DISPATCH` = **67** keys (was cited 65 at the 0701 pass, itself
  already updated from 62 at 0625 / 63 at 0626 — has grown further, +2 more
  since 0701). Confirmed via two independent counting methods, no
  duplicates.

### Checker-system-wide structural facts
- **CORRECTION — previously stated as still true, now refuted:** the claim
  "no `.github/workflows/` directory exists anywhere in the repo — no
  CI/branch-protection release gate exists at all" is **no longer accurate**.
  `.github/workflows/release-gate.yaml` now exists (612 bytes, added by
  commit `60b46b9`, dated 2026-07-01, titled "BRICK building output:
  brick-6-p8-ship-safety-impl-0701a" — landed the same day as this doc's own
  0701 baseline, evidently after the baseline snapshot was taken). Content:
  a GitHub Actions workflow triggered on `pull_request`/`push to main`/
  `workflow_dispatch` that checks out the repo, sets up Python 3.11 + `uv`,
  runs `uv sync --locked`, then `sh support/onboarding/release_gate.sh`.
  This directly affects Section 4 item 8 below — see note there. (A second,
  irrelevant `.github/workflows` also exists under vendored
  `support/dashboard/node_modules/reusify/` — not part of the repo's own CI.)
- `check_profile.py --all` sweeps are not strictly read-only:
  `case_runners.py` creates fixture vessels under `repo/project/<vessel_id>`
  (confirmed exact at line 1930, unchanged), and a second fixed-vessel-id
  pattern for `checker-projection-fixture-vessel` — function span now
  **lines 7767-8029** (was cited ~7813-8020), pinned by
  `read_side_projection_boundary.yaml:488` (was cited :479, drifted +9).
  Cleanup is `finally`-only (confirmed via direct read of lines 8023-8025,
  `shutil.rmtree(vessel_dir, ignore_errors=True)`, no `atexit`/signal-handler
  guard) — a SIGKILL mid-run leaves an orphan directory that hard-RUDs the
  next `--all` run (the code explicitly refuses to reuse/remove any
  pre-existing fixture dir it did not just create). This makes ordinary
  sweeps non-reentrant under interruption. Substance confirmed unchanged;
  only line coordinates drifted.
- `check_adapter_usage_meter.py` still exposes `--probe-mutation-red`
  (function now at **line 1021**, was cited 978; flag registration now at
  **line 1159**, was cited 1115 — both drifted +43/+44) which mutates the
  live `support/connection/adapter_local_cli.py` in place (confirmed via
  code-read: backs up via `cp`, writes in place, re-runs as subprocess,
  restores) — an out-of-band probe that writes inside the inspected repo.
  Its help text, now at **line 1162** (was cited 1118), still references
  `agent_adapter.py`. **Clarification on this reference (new this pass):**
  `agent_adapter.py` is not a deleted/renamed file — it still exists on disk
  as a distinct, real file from the actual mutation target
  (`adapter_local_cli.py`). So the help text doesn't point at nothing; it
  points at the **wrong existing file**. Framing correction: "stale
  reference" should read "help text names the wrong file, not a nonexistent
  one" — separate from the mutation-write concern either way.
- `validate_profile()` (now at `check_profile.py:1104`, was cited 1098) and
  `assert_registry_closure()` (now at lines **1068-1094**, was cited
  1061-1085) enforce schema/profile-ID presence and known-kernel-ID
  membership only — no requirement for non-empty `description`,
  `proof_limits`, `not_proven`, or at least one active tooth. A profile can
  be schema-valid and toothless today. Confirmed by direct read of both
  function bodies; substance unchanged, only line coordinates drifted. No
  commit since the 0701 baseline touches either function.

---

## 2. 이미 해결됨 / 낡음 (Resolved or stale)

- **`support/operator/walker_kernel.py` split (clusters A-E)** — done,
  commit `f0b4679` (2026-06-26), predates most of the source docs that still
  describe it as pending. Do not re-propose. Confirmed unchanged.
- **Dead pytest declaration in `pyproject.toml`** — fixed same-day, commit
  `40ea12d` ("P6: correct verification surface honesty", 2026-07-01). The
  `[tool.pytest.ini_options]` / `testpaths = ["support/checkers"]` block was
  removed entirely; current `pyproject.toml` has no pytest section
  (confirmed, zero matches). A regression guard was added
  (`brick_cli_entrypoint.yaml` `text_absent` rule, confirmed present at
  line 96) that fails if the declaration reappears. (Stray `def test_*`-named
  helper functions still exist inside `check_adapter_usage_meter.py`, now at
  **lines 312/978** — was cited 311/935, drifted — those are unchanged in
  substance and harmless now that pytest isn't pointed at the directory; not
  worth separate action.)
- **`setup.md` hardcoded "24 profiles"** — fixed same-day, commit `40ea12d`.
  Text now instructs `find support/checkers/profiles -maxdepth 1 -name
  '*.yaml' | wc -l` instead of a fixed number. Confirmed unchanged, line 36.
- **`checker-profile-map.md` hardcoded "24 profiles / 54 kernel_checks"** —
  fixed same commit `40ea12d`. Replaced with a "measured checkout fact, not
  a constitutional constant" framing plus a dated observation block
  (profiles: 30 observed on 2026-07-01; kernel_checks referenced: 66
  observed on 2026-07-01 — both of those dated snapshot numbers are
  themselves now further stale per the fresh 31/67 figures above, which is
  expected and exactly the behavior this fix was designed to tolerate).
  Superseded the ADD-13 finding from the 0630 audit. Confirmed unchanged in
  substance.
- **0626/0628 kernel_checks.py and case_runners.py line-coordinate tables**
  (function line numbers, cross-import line numbers, self-allowlist line
  numbers) — every single cited coordinate across all three 0626/0628 docs
  has drifted at least once, several multiple times. Only the *existence* of
  the pins/imports/allowlists is reliable; re-derive positions fresh at
  implementation time. **This pattern is further reinforced by the 0702
  pass itself: nearly every line-number coordinate in this doc's own 0701
  version had already drifted again by 0702**, including this doc's own
  "current" 0701 coordinates for the `.brick/builds` guard (cited as
  8489/8728, now actually at 8574/8829) — i.e. the observation that
  "line numbers rot fast in this repo" is not just historical, it is an
  ongoing, currently-active property of this codebase.
- **0626 proposed module names for kernel_checks split**
  (`kernel_common.py`, `kernel_checks_axis_vocab.py`, etc.) — never adopted.
  Confirmed absent. The 8 extractions that actually happened used a
  different, already-established flat-domain-name convention. Proposed
  names are moot.
- **"kernel_checks unchanged surfaces" claim (0626 decision table)** —
  refuted by its own quality-judge pass at the time, and further superseded
  since: the file's dispatch surface has changed substantially via 8
  subsequent extractions. (Provenance claim about a prior doc's internal
  self-refutation — not independently re-verified in this pass beyond
  confirming the underlying 8-extraction fact holds.)
- **`godmodule-decision-merged-0626.md` and
  `godmodule-decomposition-decision-table-0626.md` LOC/coordinate tables** —
  superseded wholesale by the 0628 doc, which is itself now superseded by
  this document. Keep only for historical trail, not for coordinates.
  Confirmed both files still exist on disk at
  `project/brick-protocol/status/kernel/research-0626/`.
- **0630 audit's S4-F8 line citation (`kernel_checks.py:8541`)** — the
  underlying `.brick/builds` guard message still exists but has moved again,
  now at lines **8574 and 8829** (this doc's own 0701 pass had already
  updated the citation to 8489/8728 — those have since drifted a further
  +85/+101). The finding's substance (it's a negative-guard string inside a
  `text_absent`/guard-check pattern, not a live default path) is still
  correct on inspection.

---

## 3. 미검증 의견 (Unverifiable recommendations)

Kept for human judgment — these are design/process opinions, not
re-measurable facts. Listed once, de-duplicated across sources.

- Facade-preserving split is the right default shape for kernel_checks.py /
  case_runners.py (vs. a clean break with re-pointed importers). Consensus
  across 0626/0628 docs, never adjudicated against actual implementation
  cost.
- A green split-copy profile proves only what it carries — every moved
  label/assertion needs a **mutation-RED probe** (deliberately break the
  behavior, confirm the checker catches it) before it can be called
  "conserved." No such probes exist yet for any of the 12 currently-
  duplicated checker-diet labels — confirmed still true, no mutation-RED
  probe directory/mechanism found anywhere in the repo.
- `path_allowlist` cannot serve as a deletion-safety oracle (it rejects
  unexpected files, not missing expected ones) — so it cannot prove a
  profile deletion is safe by itself.
- Checker complexity should be hidden behind a customer-facing product-
  status translation layer (state/reason/next-action/evidence-refs) rather
  than exposed as raw checker/profile vocabulary. No implementation attempt
  yet in any reviewed closure — confirmed still true, no matching
  translation-layer code found anywhere in `support/`.
- Profile schema should require non-empty `description`/`proof_limits`/
  `not_proven` and at least one active tooth (anti-toothless-profile guard).
  Confirmed gap, unimplemented (re-confirmed this pass via direct read of
  `validate_profile()` and `assert_registry_closure()` — `description`,
  `proof_limits`, `not_proven` are permitted keys only, never checked for
  presence/non-emptiness; no "at least one tooth" check exists either);
  whether to gate future profile authoring on this is a judgment call, not
  a fact.
- `check_bounded_agent_proposed_routing_loop0.py`'s `0`-suffix naming should
  not be assumed "retired/dead" by default — some `0`-suffixed / `--large`
  style names are intentional negative guards. Applies caution to any future
  pruning pass on this file.
- Whether `_ensure_import_identity` fan-out (originally cited as touching 9
  domains inside kernel_checks.py) is still a real cross-cutting constraint
  post-extraction was not independently re-confirmed this round — **still
  treat as open**. Partial data point from this pass: 5 call sites remain
  inside `kernel_checks.py` itself (in 5 distinct functions), and 5 of the 8
  extracted domain files also call it — roughly 10 call-site locations
  total, close to but not an exact match for the originally-cited "9
  domains" figure (which used semantic domain-grouping this pass did not
  attempt to re-derive). Not resolved either way.

---

## 4. 제안 범위 (Proposed scope)

**Explicitly sequenced to start only after the current
brick-6-surface-audit-repair goal's P9 (final dynamic proof) closes.**
**Status update (0702): this precondition is now satisfied.** P9 closed
same-day as the 0701 baseline (0701 19:57, ~3 hours after this doc's own
16:04 baseline snapshot), via a two-attempt Building sequence with attempt 2
adopted (commit `46d02e4`); see
`brick-6-p9-dynamic-proof-closure-disposition-0701.md`, which concludes
"P9's live dynamic proof is demonstrated and adopted." Note: that
disposition doc itself says P9 closure does not by itself declare the
*entire* P0-P9 goal complete — a separate final COO/Smith review across all
phases plus Rules 8/9/10 is still pending per that doc. None of this scope
folds into that goal's P0-P9. This is the P6-class "engine cleanup /
godmodule decomposition" work the 0628 doc already scoped as post-customer-
path — that framing still holds and is reinforced here.

1. **Split `support/checkers/lib/kernel_checks.py` (10141 LOC, was cited
   10201) by domain, flat-sibling shape.**
   Follow the naming convention already established by the 8 completed
   extractions (`<domain>_check.py` under `support/checkers/lib/`, noting 2
   of 8 deviate slightly from the exact suffix pattern — see §1), not the
   older `kernel_checks_*.py` proposal. Blocked on: fresh re-derivation of
   the 16 remaining `run_*` entrypoint boundaries, the 3 axis-vocab
   self-allowlist relocations (now at lines 119/130/138), and confirming
   whether any profile `text_contains` pins target private helper bodies
   inside this file (would need to move with their function, not stay in a
   re-export shell). Gate: `check_profile.py --all` exit 0 +
   `module_registry.yaml` row per new leaf + G5 forbidden-ownership echo per
   leaf.

2. **Split `support/checkers/lib/case_runners.py` (8512 LOC, was cited
   8507) by support-surface family, flat-sibling shape.**
   Already 8 leaves extracted; remaining 28 `run_*_case` functions plus
   private helpers need re-clustering by family (adapter/materialize/
   intake/drain/link, or whatever grouping the current file content
   actually supports — re-derive, don't reuse 0626's line-based guess).
   Blocked on: re-deriving the exact current line for the two known
   cross-module private-helper imports (`_preset_completion_command_runner`
   from `kernel_checks.py` — now at lines 3429 **and** 3635, two sites, not
   one; `_graph_test_plan_from_linear` from `check_building_operator_driver0.py`
   — confirmed still at line 75), and an explicit decision on
   facade-vs-direct-importer-update for the `check_profile.py` import block
   (33 names from case_runners.py + 15 from rule_runners.py, not "~37" as
   previously stated — see §1 for the full correction on `RULE_RUNNERS`'
   actual location in `check_profile.py:235`).

3. **First-ever read-first inspection of
   `support/checkers/check_bounded_agent_proposed_routing_loop0.py` (7176
   LOC, was cited 7087) for split feasibility.**
   No prior doc has produced a cluster map for this file — it is
   third-largest checker file (see §1 flag on the "largest" wording
   ambiguity) with zero decomposition analysis done anywhere in the 8
   sources. Blocked on: nothing (this is the missing first step); should
   happen before or alongside item 1/2 since it may share fixture/helper
   machinery with `case_runners.py`.

4. **Complete checker-diet on
   `building_skill_preset_agent_tool_hardening.yaml` (4237 LOC, 99 labels).**
   Confirmed no facade primitive exists — this must be complete-the-split
   then delete, not thin-in-place. 87 labels currently have no split home;
   12 are duplicated with no drift check. Blocked on: (a) mutation-RED probe
   per moved/duplicated label before any deletion, (b) an explicit
   disposition for the 5 concern families that currently have no matching
   split target (p5/p6 source-fact-carry, gate-sequence, hard-graph,
   multi-leader, governance-hint), (c) removing the corresponding
   `core.yaml` `path_allowlist` entry in the *same* change as any file
   deletion.

5. **Repair `module_registry.yaml` phantom `checker_strict_validation`
   row(s)** (3 lines, now confirmed at **78, 533, 545** — was cited 78, 523,
   535) — either author the missing profile or remove the dead reference.
   **Re-scoped based on 0702 re-verification: this is a documentation-
   accuracy fix, not a functional-dependency repair** — no code reads
   `pinned_by:`, and the underlying validation coverage already lives on in
   `structure_template_integrity.yaml` (confirmed live, registered). Small,
   independent, no blockers — could land before or during item 4 without
   waiting on it. Also touch the matching stale comment at
   `check_profile.py:34`.

6. **Add anti-toothless-profile schema guard** to `validate_profile()`
   (now at line 1104) / `assert_registry_closure()` (now at lines
   1068-1094): require non-empty `description`, `proof_limits`,
   `not_proven`, and at least one active tooth. **Confirmed still fully
   unimplemented as of 0702** — no commit in the 17+ commits since the 0701
   baseline touches either function. Independent of the split work; should
   land before item 4's checker-diet deletion so the diet's own split-copy
   profiles are held to the new standard.

7. **Isolate/harden `check_profile.py --all` fixture writes.**
   Two known non-reentrant fixed-path fixture vessels
   (`case_runners.py:1930` repo/project vessel, and the
   `checker-projection-fixture-vessel` function now spanning lines
   7767-8029, pinned at `read_side_projection_boundary.yaml:488` — was
   cited ~7813-8020 / :479) both rely on `finally`-only cleanup and
   hard-raise if a stale directory exists from an interrupted prior run.
   Move to temp-root isolation or add a startup self-heal. Independent of
   the split work.

8. **Add CI/release gate** (GitHub Actions or equivalent) wiring
   `compileall`, `check_profile.py --all`/targeted profiles, `brick verify`,
   dashboard build, and release-export negative probes into a required
   branch-protection check.
   **STATUS CHANGE (0702): this item's premise is now partly overtaken.**
   `.github/workflows/release-gate.yaml` **now exists** (commit `60b46b9`,
   2026-07-01, "P8 ship safety" building), running `uv sync --locked` +
   `sh support/onboarding/release_gate.sh` on `pull_request`/`push to main`/
   `workflow_dispatch`. The claim "currently zero `.github/workflows/`
   exist" is refuted. **This item needs re-scoping, not deletion**: verify
   whether `release_gate.sh` already covers `compileall`,
   `check_profile.py --all`, `brick verify`, dashboard build, and
   release-export negative probes, or whether it's a narrower stub that
   still needs the full checklist added. That verification was not
   performed in this pass — flagging as unresolved rather than guessing.
   Sequence after items 1-4 so the gate isn't immediately broken by
   in-flight splits (this sequencing rationale still holds regardless of
   the workflow file's current contents).

9. **Retire `check_adapter_usage_meter.py --probe-mutation-red`'s
   live-source mutation pattern** — convert to a temp-copy probe, and fix
   its stale `agent_adapter.py` help-text reference (now at line 1162; note
   per §1, `agent_adapter.py` is a real, different, still-existing file —
   the fix is to point the help text at the correct target
   `adapter_local_cli.py`, not to remove a reference to something deleted).
   Small, independent.

**Explicit non-goals for this scope:** splitting `_run_dynamic_graph_walker`
(HOLD stands until P4 resume-preservation is proven with focused checker
evidence — do not revisit without that proof), and any work that changes
Brick/Agent/Link axis meaning — this is structural-drag cleanup only, per
the 0628 doc's own framing, which still holds.
