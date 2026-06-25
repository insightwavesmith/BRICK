Repair the preset-count drift identified by broad-profile-drift-triage-0625.

Carry-forward evidence:
- broad-profile-drift-triage-0625 found building_skill_preset_agent_tool_hardening.yaml pins expected_preset_count: 27 while brick/templates/presets/*.md resolves 28 after brick/templates/presets/four-llm-standard-graph.md was added.
- The drift is isolated to support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml expected_preset_count and expected_preset_refs.

Objective:
Apply the minimal checker/profile repair so the profile recognizes building-chain-preset:four-llm-standard-graph.

Required work:
1. Edit only support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml unless a checker source change is strictly needed.
2. Change expected_preset_count 27 -> 28.
3. Add building-chain-preset:four-llm-standard-graph to expected_preset_refs in stable sorted/catalog order.
4. Run targeted verification:
   - git diff --check
   - uv run python3 support/checkers/check_profile.py --profile building_skill_preset_agent_tool_hardening
   - if time permits, uv run python3 support/checkers/check_profile.py --all or explicitly record not_proven if skipped.
5. Preserve proof limits: checker/profile pass is support evidence only, not source truth/success/quality/Movement authority.

Return shape:
made_changes, changed_files, observed_evidence, commands_run, blocked_or_missing_evidence, handoff_refs, not_proven.
