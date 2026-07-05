# W1-S1 Contract Kernel 좌표조사 최종본 (0706 — w1s1-contractkernel-0706a design attempt-3 수확)

주의(정직 공개): 이 설계의 공격 QA 레인은 일시 claude rc=1로 사망 — 맵은 3라운드 자기교정본이나 적대 검증 미완. 적대 검증은 각 이관 슬라이스의 COO 게이트(행동-동등성+변이-RED)가 대체 수행한다.
source truth·성공/품질 판정·Movement 권한 아님.

===== design_summary =====
Repaired W1-S1 Contract Kernel design responding to the carried closure concerns. D1 inventory now includes the previously missed plan_validation.py:1398 on_missing_required_facts subset literal and the previously dropped walker_reroute_budget.py:96 / driver.py:2444 / plan_validation.py:1867 local _positive_int duplicates plus both stale disposition-error texts, each with an explicit disposition. D2 resolves the axis-home question in favor of the task-source acceptance criterion: gate policy-action vocabulary physically moves to link/ (precedent: link/gate.py:21-30 GATE_REGISTRY derivation and walker_reroute_budget.py:27-29 importing DISPOSITION_ACTIONS from link/transition.py), with support keeping import-only projections — removing the one measured 4th-axis inversion (support/recording modules consuming support/operator/gate_sequence.py as vocabulary authority). D3 re-scopes K3: WR-001/002/004/005/006 are sealed at HEAD so no re-sealing work is proposed; the slice instead converts the hollow text-pin checker into behavioral probes and registers mutation-RED entries. D4 maps all seven S12-WR rows to HEAD state with the two live residues (WR-007 segment-aware matcher; checker hollowness) assigned to slices.

===== proposed_changes =====
[0] K1' (vocabulary re-homing): declare ADMITTED_POLICY_ACTIONS, the two partition subsets (ON_MISSING_REQUIRED_FACTS_ACTIONS={'reroute','hold'}, ON_SUFFICIENT_ACTIONS={'next','forward'}), and ONE canonical case-normalization function in link/gate.py (or a link/spec.py registry row mirroring GATE_REGISTRY style); support/operator/gate_sequence.py keeps a re-export for compatibility; repoint plan_validation.py:1398/1403/1483, spine_projection.py:93, claims_link.py:32 to the link/ home so subset literals are derived, not re-stated.
[1] K2' (semantics unification with recorded dispositions): plan_validation._gate_sequence_action_literal and gate_sequence._action_literal both delegate to the single link/-homed normalizer; replay reader _record_policy_action stays STRICT by explicit recorded decision (records are writer-normalized; strictness is reader re-verification per WR-006) with a fixture pinning 'mixed-case record rejected at replay'. Positive-int dispositions: driver.py:2444 CONSOLIDATE to require_positive_int (error-type changes TypeError->ValueError — gated by an explicit probe); walker_reroute_budget.py:96 CONSOLIDATE (message text change gated); plan_validation.py:1867 KEEP-PINNED (documented injected-coercer contract :1876-1880) or consolidate via error_text parameter — Smith choice recorded either way; walker_resume.py:1070-1075 KEEP (reader-specific revision-chain error contract). Fix both stale disposition error texts (plan_validation.py:1841, walker_reroute_budget.py:161) by deriving the message from DISPOSITION_ACTIONS.
[2] K3' (verification de-hollowing — REPLACES the stale prior K3 which proposed already-landed seals): add behavioral probes that import live functions and assert reject/accept behavior (bool rejection, decimal-text policy per allow_decimal_text, vocabulary rejection, mixed-case replay rejection); extend check_positive_int_bool_boundary.py inventory to cover walker_reroute_budget.py/driver.py/plan_validation.py or supersede text pins with the behavioral probe module; register the class in mutation_red_manifest.yaml.
[3] K4' (WR-007 residue): make brick/comparison.py path_matches_scope segment-aware ('*'=single segment, '**'=recursive), keeping brick/ as the only matcher home already enforced by the AST pin.
[4] K5' (out-of-slice residue, no code): absent advertised evidence roots stay routed to the deferred Smith queue; not part of W1 file sets.

===== relevant_current_structure =====
[0] Vocabulary family: support/operator/gate_sequence.py:26-27 (declaration home, WRONG axis), plan_validation.py:1398/1403/1483 (validator-side literals), plan_validation.py:1478-1485 + gate_sequence.py:498-502 (duplicate normalization writers), gate_sequence.py:402-413 (strict replay reader), spine_projection.py:93,2157-2162 + claims_link.py:32,430-436 (recording readers).
[1] Disposition family: link/transition.py:10 (canonical, correct axis), walker_reroute_budget.py:27-29,158-166 (importing validator with stale error text :161), plan_validation.py:1839-1842 (second stale error text).
[2] Positive-int family: contracts.py:14-31 (canonical), delegating wrappers auto_repair_replay.py:400-401 + route_materialization.py:445-446, direct users per checker inventory (step_outputs.py:70, plan_expansion.py:200, composition_compose.py:758, etc.), non-inventoried locals walker_reroute_budget.py:96-103, driver.py:2444-2451 (TypeError divergence), plan_validation.py:1867-1874 (pinned injected coercer), walker_resume.py:1070-1075.
[3] write_scope matcher: brick/comparison.py:22-40 (single Brick home, fnmatch-based), AST single-source pin in check_assembly_equivalence.py.
[4] Verification: check_positive_int_bool_boundary.py:12-101 (text pins + textual mutation probes only).

===== invariants =====
[0] One physical declaration per vocabulary; support surfaces may re-export but never re-state literals.
[1] Writer-normalized, reader-strict: anything persisted passes the single normalizer; replay readers reject non-canonical forms (WR-006 class preserved).
[2] Every existing reject stays a reject and every existing accept stays an accept across K1'/K2'/K4' (behavior-equivalence gate), except the three explicitly gated divergences: driver.py bool TypeError->ValueError, two consolidated error-message texts, and K4' segment matching (which must flip the V2-ATT-002 over-match from accept to reject).
[3] Every inventory item carries a recorded disposition (consolidate | keep-pinned-with-reason); no silent drops — the failure mode the carried concern measured in attempt-2.
[4] New/changed guard surfaces land only with a behavioral RED probe, not a text pin alone (checker-companion principle).

===== checker_or_verifier_plan =====
[0] Behavioral probe module (K3'): imports live require_positive_int and each consuming site's entry, asserts True/False rejection, decimal-text policy per site flag, ValueError type, vocabulary rejection at _record_policy_action including mixed-case, and DISPOSITION_ACTIONS-derived error text containing 'reroute'.
[1] Vocabulary single-source pin: AST-level check (pattern: check_assembly_equivalence.py's matcher pin) that no module outside link/ declares the policy-action literal set; grep-level fallback rejecting {'forward','hold','next','reroute'} re-statements outside link/.
[2] Behavior-equivalence gate per slice: fixed input corpus (valid/bool/decimal-text/mixed-case/unadmitted-action/subset-violation) run before and after; identical accept/reject verdicts required except the three declared divergences, each with its own RED->GREEN fixture.
[3] K4' matcher corpus: (path,pattern) table with V2-ATT-002 reproduction as RED-before/GREEN-after plus all currently-passing scope pairs pinned green.
[4] mutation_red_manifest.yaml entries linking each new probe to its surface so fixture deletion fails the manifest checker (W2 alignment).

===== not_proven =====
[0] brain surface behavior
[1] credential validity
[2] tool or hook execution
[3] runtime or scheduler behavior
[4] quality of returned work
[5] git log --grep landing attribution for 묶음1/5/6/7: this review environment provides read/grep/glob only, no git execution — seal states were measured as HEAD file-state plus status-doc records (external-audit-repair-phases-0705.md:30), not commit attribution; the work_statement's git-log measurement remains open for a lane with command execution.
[6] Runtime reachability of the declaration-normalize vs replay-strict divergence through a live Building walk (statically measured only).
[7] Runtime module-identity behavior of the dual import styles (support.* in auto_repair_replay.py:15-19 vs brick_protocol.support.* elsewhere) — routed to the deferred Smith queue by the closure; not re-measured here.
[8] Whether the on_missing_required_facts subset asymmetry is exploitable through recorded gate decisions (plan_validation.py:1892-1937 replay region read only via grep context, not exhaustively).
[9] Whether absent advertised evidence roots (evidence/claim_trace/agent/returned_claims.json, work/building-map.json, raw/agent-return.jsonl) were never written or written elsewhere — the prior building's workspace for task-statement-36f31f91173f-node was not found anywhere in this repo (glob/grep returned nothing), so those three paths could not be inspected at all.
[10] Exhaustive completeness of the positive-int duplicate census beyond grep of 'def _positive_int|require_positive_int' (e.g. inline isinstance guards under other names may exist).
[11] check_positive_int_bool_boundary.py hollowness was confirmed structurally (text-pin architecture), not by executing the QA mutant; the in-memory mutant demonstration is carried from QA attempt-2, not re-run here.
[12] Semantic fitness and implementation readiness of K1'-K4' — design proposal only; the Link gate owns sufficiency and the human owns quality.
[13] WR-008 (raw/link.jsonl parse-discipline split) remains backlog per orders doc :133; not inventoried here.

