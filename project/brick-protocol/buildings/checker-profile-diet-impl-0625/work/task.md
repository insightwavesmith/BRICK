# G5 checker/profile diet implementation (B2 then B3)
Implement the checker/profile diet split described by checker-profile-diet-implementation-plan-0625.
Mandatory order inside this Building:
1. B2: split support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml into concern-coherent sub-profiles while preserving all existing assertions.
2. B3: separate provider runtime-smoke checks from support/checkers/profiles/agent_axis_behavioral.yaml and/or read_side_projection_boundary.yaml into a dedicated runtime-smoke profile.
3. Update support/checkers/profiles/core.yaml path_allowlist for any new profile files.
4. Do not edit support/checkers/lib/* unless absolutely necessary; if a lib edit is required, return a transition_concern_evidence rather than broadening scope.
5. Run targeted checks: check_profile.py --self-test if available, each touched/new profile, core if feasible, git diff --check. Avoid broad --all unless narrow checks pass and time remains.
6. Preserve BRICK principles: no source truth, no success/quality/Movement claims; return changed_files, commands_run, observed_evidence, not_proven, remaining_delta.
