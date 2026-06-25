P5 checker/profile/module diet CODEx implementation slice.

Context: previous Building checker-module-diet-implementation-0625 paused because the design step could not read required files. Do not forward that blocked design. This Building uses the Codex work lane directly for a bounded implementation slice.

Objective: implement one concrete, low-risk checker/profile diet slice that helps the COO avoid defaulting to --all while preserving active invariants. Use existing evidence:
- project/brick-protocol/status/kernel/checker-profile-diet-measurement-0625-profile-table.md
- support/checkers/profiles/*.yaml
- support/checkers/check_profile.py and support/checkers/module_registry.yaml only if needed.

Preferred minimal outcome:
- Add or update a small status/kernel record or profile grouping/notes that clearly separates quick/core targeted profiles from live-heavy/provider/dogfood profiles, using current repo evidence.
- If a profile YAML change is safer and already supported by check_profile.py, make that narrow change instead.
- Do not remove coverage. Do not weaken checker rules. Do not edit AGENTS.md, brick/, agent/, or link/.

Required return/proof:
- changed_files and why each is a root-fix vs patch-debt
- commands_run: targeted checker/profile if applicable, git diff --check
- not_proven: full checker consolidation, semantic fitness, --all green unless actually run

Hard constraints: write only inside declared write_scope. Checker green is support evidence only; no success/quality/source-truth/Movement claims.
