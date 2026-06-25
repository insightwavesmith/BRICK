Repair the building_automation profile RED caused by malformed Building map evidence.

Trigger evidence:
After commit d8e2839, direct profile run `uv run python3 support/checkers/check_profile.py --profile building_automation` failed in kernel check building_map_graph. The failure was not from the adapter-timeout patch; it rejected existing evidence:
- project/brick-protocol/buildings/checker-module-diet-implementation-0625/work/building-map.json
Failures included unresolved target_brick_instance_ref prefix-only text for axis-attack/evidence-integrity lanes and unresolved group member_refs.

Brick objective:
Find the smallest BRICK-law-compatible repair so building_automation profile no longer fails on malformed stale evidence, without hiding real current evidence problems.

Required work:
1. Inspect checker-module-diet-implementation-0625 evidence root and determine whether it is a failed/held/obsolete malformed Building root, a committed source-truth record, or active evidence that must be preserved.
2. Determine correct repair surface:
   - fix malformed evidence if it is admitted and repairable,
   - quarantine/mark obsolete if it is failed/stale evidence that should not be scanned as active Building evidence,
   - or adjust checker selection only if the checker is wrongly scanning non-active/held malformed roots.
3. Preserve BRICK law: evidence/checker output is support evidence only; do not make support a success/quality/Movement authority; do not delete evidence silently.
4. Keep edits narrow. Do not edit AGENTS.md. Do not add runtime scheduler/queue/retry behavior.
5. Run targeted verification: `uv run python3 support/checkers/check_profile.py --profile building_automation` or a narrower direct check if the full profile is too broad; also `git diff --check` and compile/import smoke if code changed.

Write scope candidates:
- project/brick-protocol/buildings/checker-module-diet-implementation-0625/**
- project/brick-protocol/status/kernel/*.md
- support/checkers/lib/kernel_checks.py
- support/checkers/profiles/*.yaml
- support/checkers/*.py

Return shape:
made_changes, changed_files, observed_evidence, commands_run, blocked_or_missing_evidence, handoff_refs, not_proven.
