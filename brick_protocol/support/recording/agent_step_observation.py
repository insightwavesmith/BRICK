"""Derive per-step Agent support-observation facts from RAW adapter output.

REDO (Smith 0623): support = move(carry) + record. The ADAPTER returns the raw
answer plus the raw it already sees (the gemini tool-call stats, the stripped
top-level verdict key names, the effective-write request inputs); the support
WRITE OBSERVER produces the raw worktree observation (changed files, before/after
git refs); the BRICK axis compares changed paths against the recommended scope.

This recording module is where those raw observations are RECORDED as the named
per-step support facts. It never STOPS the building, never classifies success or
quality, and never chooses Movement. It only assembles facts:

  - ``observed_non_granted_gemini_tools``   (from the adapter raw tool-call list)
  - ``ignored_forbidden_return_key``        (from the adapter stripped key names)
  - the effective-write reason-token facts  (from the adapter request inputs)
  - ``git_refs_moved``                       (from the raw before/after git refs)

The written-vs-scope comparison (정보가공) is the BRICK axis's
(``brick.comparison.compare_changed_paths_to_write_scope``); the operator write
observer calls it and records the buckets. This module stays axis-import-free.

These are NESTED support evidence, NOT a new BAL fact class, NOT a fourth axis.
They carry NO Movement authority and make NO success / quality / fault judgment.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


# Raw side-channel keys the adapter exposes on
# ``AgentAdapterResult.adapter_raw_observations``. The adapter never RECORDS these
# as facts; it only EXPOSES the raw it already saw. This recorder turns them into
# the named per-step support facts.
RAW_NON_GRANTED_GEMINI_TOOLS_KEY = "non_granted_gemini_tool_names"
RAW_IGNORED_RETURN_KEYS_KEY = "ignored_forbidden_return_key_names"


def derive_effective_write_request_facts(
    *,
    write_scope_present: bool,
    tool_policy_has_read_write: bool,
    agent_object_ref: str,
    adapter_supports_observed_write: bool,
) -> tuple[str, ...]:
    """Record the effective-write write-policy facts from RAW request inputs.

    REDO: the ADAPTER exposes the raw request inputs (whether a Brick write_scope
    was present, whether the read-write tool policy is in tool_policy_refs, the
    Agent Object ref, whether the selected adapter mapping supports observed
    write); this recorder DERIVES the named reason-token facts. The four
    dispositions (formerly raised inside the adapter's
    ``_validate_effective_write_request``) are now RECORDED so the building
    continues and the merge-review gate weighs them:

      - ``missing_brick_write_scope``
      - ``legacy_adapter_identity_only_not_authority`` (non-dev, no read-write policy)
      - ``missing_agent_write_policy``                 (dev, no read-write policy)
      - ``missing_adapter_write_capability``

    The dev-name check only DISCRIMINATES which policy-missing fact is recorded;
    it is NOT an authority gate (a non-dev Agent with the full intersection
    records nothing here). An empty tuple means the full write intersection was
    present.
    """

    facts: list[str] = []
    if not write_scope_present:
        facts.append(
            "missing_brick_write_scope: no Brick row write_scope for a write-capable "
            "selected adapter"
        )
    if not tool_policy_has_read_write:
        if agent_object_ref != "agent-object:dev":
            facts.append(
                "legacy_adapter_identity_only_not_authority: adapter_capabilities "
                "write does not authorize a non-dev Agent Object without "
                "tool-policy:read-write-scoped"
            )
        else:
            facts.append(
                "missing_agent_write_policy: Agent tool_policy_refs omit "
                "tool-policy:read-write-scoped for a write attempt"
            )
    if not adapter_supports_observed_write:
        facts.append(
            "missing_adapter_write_capability: selected adapter mapping does not "
            "support observed workspace write"
        )
    return tuple(facts)


def derive_adapter_raw_observation_facts(
    raw_observations: Mapping[str, Any] | None,
) -> dict[str, list[str]]:
    """Record the per-step facts the adapter EXPOSED as raw, not as facts.

    REDO: the local-CLI adapter no longer attaches ``observed_non_granted_gemini_tools``
    to its returned payload, and ``connect_agent_brain`` no longer writes
    ``ignored_forbidden_return_key`` into the payload. Both ride back as RAW on the
    adapter side-channel. This recorder turns them into the named support facts.

    Only buckets with at least one entry are returned.
    """

    facts: dict[str, list[str]] = {}
    if not isinstance(raw_observations, Mapping):
        return facts
    gemini_tools = raw_observations.get(RAW_NON_GRANTED_GEMINI_TOOLS_KEY)
    if isinstance(gemini_tools, (list, tuple)) and gemini_tools:
        facts["observed_non_granted_gemini_tools"] = [
            str(name) for name in gemini_tools
        ]
    ignored_keys = raw_observations.get(RAW_IGNORED_RETURN_KEYS_KEY)
    if isinstance(ignored_keys, (list, tuple)) and ignored_keys:
        facts["ignored_forbidden_return_key"] = [str(name) for name in ignored_keys]
    return facts


def derive_git_refs_moved(
    before_refs: Mapping[str, str],
    after_refs: Mapping[str, str],
) -> dict[str, dict[str, str]]:
    """Record which git refs (HEAD/branch/upstream) moved, with before/after.

    REDO: normal git use is not floor-ripping. The support write observer produces
    the RAW before/after refs; this recorder records the delta (it used to raise
    inside ``write_observation._validate_git_refs_unchanged``). No building-stop.
    """

    before = dict(before_refs)
    after = dict(after_refs)
    moved: dict[str, dict[str, str]] = {}
    for key in sorted(set(before) | set(after)):
        before_value = str(before.get(key, ""))
        after_value = str(after.get(key, ""))
        if before_value != after_value:
            moved[key] = {"before": before_value, "after": after_value}
    return moved


__all__ = [
    "RAW_NON_GRANTED_GEMINI_TOOLS_KEY",
    "RAW_IGNORED_RETURN_KEYS_KEY",
    "derive_effective_write_request_facts",
    "derive_adapter_raw_observation_facts",
    "derive_git_refs_moved",
]
