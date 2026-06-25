# G1 customer-entry/readiness reconciliation
Read-only Building. Reconcile the customer-entry / readiness state before P12.
Required analyses:
1. Identify customer-facing docs/status surfaces that still drift from current facts (profiles=24, presets=28, active checkout vs release/frozen path, FIRST_USE/install/setup/verify route).
2. Propose the minimal docs/status write scope for the follow-up repair Building, without editing now.
3. Produce a readiness matrix: required before P12, can carry as not_proven, and must be deferred.
4. Name exact checker/profile gates for P12 launch scope.
5. Preserve BRICK boundaries: no source truth, no quality/success, no Movement choice.
Return concise observed evidence, proposed_next_work_boundaries, remaining_delta, not_proven.
