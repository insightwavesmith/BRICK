# B2a checker profile diet copy-stage
Implement the first safe slice of B2 from checker-profile-diet-impl-0625 design.
Goal: create concern-coherent sub-profile staging files without deleting or thinning the original yet.
Required work:
1. Read support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml.
2. Create three new profiles:
   - support/checkers/profiles/building_skill_preset_builder_composition.yaml
   - support/checkers/profiles/building_skill_preset_agent_resource_boundary.yaml
   - support/checkers/profiles/building_skill_preset_intake_adapter_gate.yaml
3. Populate them by copying/relocating relevant existing assertions from the original as staging copies. Do NOT remove assertions from the original in B2a.
4. Update support/checkers/profiles/core.yaml path_allowlist to include the three new files.
5. Run: git diff --check; check_profile.py --profile core; check_profile.py --profile each new profile; and --self-test if supported. Avoid --all unless narrow checks pass quickly.
6. If runner/lib changes are needed, stop with transition_concern_evidence; do not edit support/checkers/lib/*.
7. Return changed_files, commands_run, observed_evidence, not_proven, remaining_delta, and whether B2b can thin/delete original next.
