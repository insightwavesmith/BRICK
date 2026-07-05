"""Brick-owned public comparison fact surface."""

from __future__ import annotations

import fnmatch
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Iterable

from brick_protocol.brick.work import parse_required_return_shape


_OBSERVED_MATCH_KINDS: tuple[str, ...] = ("matched", "missing", "mismatched", "unknown")
_MUTATION_RED_REQUIRED_FIELDS: tuple[str, ...] = (
    "revert_ref",
    "red_cmd",
    "red_rc",
    "restore_rc",
)


def _path_matches_scope(path: str, pattern: str) -> bool:
    """Match exact paths or explicit globs.

    Note: directory-looking entries do not include children (a bare directory
    entry matches only itself, never a nested file).

    Moved verbatim from ``support/operator/write_observation`` as part of the
    REDO: comparing a changed path against a declared scope pattern is the
    written-vs-scope 정보가공 that belongs to the Brick axis, not the support
    write observer.
    """

    clean_pattern = pattern.strip().replace("\\", "/")
    if not clean_pattern:
        return False
    return fnmatch.fnmatch(path, clean_pattern) or path == clean_pattern.rstrip("/")


path_matches_scope = _path_matches_scope


def compare_changed_paths_to_write_scope(
    changed_files: Iterable[str],
    write_scope: Mapping[str, Any],
) -> dict[str, list[str]]:
    """Compare RAW changed paths against the Brick-recommended write_scope.

    This is the written-vs-scope comparison (정보가공) the REDO moves OUT of
    ``support/operator/write_observation`` into the Brick axis. The support write
    observer produces the RAW ``changed_files`` (and the before/after git refs);
    this Brick function classifies them against the *declared* scope and returns
    the comparison-fact buckets the approval/merge-review gate weighs:

      - ``observed_paths_outside_declared_scope``: a changed path matching NONE of
        the declared ``allowed_paths`` globs (a declared-empty allowed list
        records nothing here -- no entry-guard).
      - ``forbidden_paths_matched``: a changed path matching a user-declared
        ``write_scope.forbidden_paths`` glob.

    No building-stop is decided here: Brick recommends, the worktree isolates,
    merge-review is the real gate. Sensitive-path (.env/.pem/.key) detection is a
    RAW structural observation and stays with the support write observer; the
    ``.git`` floor stays a support integrity raise. Only buckets with at least one
    entry are returned.
    """

    raw_forbidden = write_scope.get("forbidden_paths")
    if raw_forbidden is not None and not isinstance(raw_forbidden, list):
        raise TypeError("write_scope.forbidden_paths must be a list")
    raw_allowed = write_scope.get("allowed_paths")
    if raw_allowed is not None and not isinstance(raw_allowed, list):
        raise TypeError("write_scope.allowed_paths must be a list")
    allowed = tuple(
        str(item).replace("\\", "/")
        for item in (raw_allowed or ())
        if isinstance(item, str) and item.strip()
    )
    forbidden = tuple(
        str(item).replace("\\", "/")
        for item in (raw_forbidden or ())
        if isinstance(item, str) and item.strip()
    )
    facts: dict[str, list[str]] = {
        "forbidden_paths_matched": [],
        "observed_paths_outside_declared_scope": [],
    }
    for raw_path in changed_files:
        clean = str(raw_path).strip().replace("\\", "/")
        if not clean:
            continue
        if any(_path_matches_scope(clean, pattern) for pattern in forbidden):
            facts["forbidden_paths_matched"].append(clean)
        if allowed and not any(
            _path_matches_scope(clean, pattern) for pattern in allowed
        ):
            facts["observed_paths_outside_declared_scope"].append(clean)
    return {key: value for key, value in facts.items() if value}


def compare_proof_runs_to_declared_obligations(
    observed_proof_runs: Iterable[Mapping[str, Any]],
    declared_obligations: Iterable[Mapping[str, Any]],
    *,
    returned_value: Mapping[str, Any] | None = None,
) -> dict[str, list[str]]:
    """Compare observed proof facts against declared proof obligations.

    The support observer records command/rc/log facts. This Brick comparison
    derives mismatch buckets only; it chooses no Movement and judges no quality.
    """

    observed = [_clean_proof_run(item) for item in observed_proof_runs]
    obligations = [_clean_proof_obligation(item) for item in declared_obligations]
    returned = returned_value or {}
    facts: dict[str, list[str]] = {
        "proof_run_expect_rc_mismatch": [],
        "proof_obligation_unrun": [],
        "mutation_red_missing_or_malformed_fields": [],
    }
    by_command: dict[str, list[Mapping[str, Any]]] = {}
    for run in observed:
        command = str(run.get("command") or "").strip()
        if command:
            by_command.setdefault(command, []).append(run)
    consumed_by_command: dict[str, int] = {}
    for obligation in obligations:
        command = str(obligation.get("command") or "").strip()
        if not command:
            continue
        kind = str(obligation.get("kind") or "command").strip() or "command"
        if kind == "mutation_red":
            if not _mutation_red_observation_present(returned, command):
                facts["mutation_red_missing_or_malformed_fields"].append(command)
            continue
        runs = by_command.get(command, [])
        consumed_index = consumed_by_command.get(command, 0)
        if consumed_index >= len(runs):
            facts["proof_obligation_unrun"].append(command)
            continue
        consumed_by_command[command] = consumed_index + 1
        expected = obligation.get("expect_rc", 0)
        observed_rc = runs[consumed_index].get("rc")
        if observed_rc != expected:
            facts["proof_run_expect_rc_mismatch"].append(
                f"{command} expected {expected!r} observed {observed_rc!r}"
            )
    return {key: value for key, value in facts.items() if value}


def compare_return_claims_to_observed_facts(
    returned_value: Mapping[str, Any] | None,
) -> dict[str, list[str]]:
    """Compare selected Agent return claims against measured support facts."""

    if not isinstance(returned_value, Mapping):
        return {}
    if returned_value.get("made_changes") is not True:
        return {}
    worktree = returned_value.get("worktree_observation")
    if not isinstance(worktree, Mapping):
        return {}
    changed = worktree.get("observed_changed_files")
    if isinstance(changed, list) and not changed:
        return {"made_changes_claim_without_observed_change": ["made_changes=true"]}
    return {}


def apply_proof_obligation_comparison(
    comparison: "BrickComparisonFact",
    *,
    returned_value: Any | None,
    declared_obligations: Iterable[Mapping[str, Any]],
) -> "BrickComparisonFact":
    """Append proof mismatch buckets to an existing comparison fact.

    Present-only invariant: when no Brick row declares proof_obligations this
    function returns the original comparison byte-for-byte.
    """

    declared = tuple(declared_obligations)
    if not declared:
        return comparison
    returned_mapping = returned_value if isinstance(returned_value, Mapping) else None
    observed_runs = ()
    if returned_mapping is not None:
        raw_runs = returned_mapping.get("observed_proof_runs")
        if isinstance(raw_runs, list):
            observed_runs = tuple(item for item in raw_runs if isinstance(item, Mapping))
    buckets = compare_proof_runs_to_declared_obligations(
        observed_runs,
        declared,
        returned_value=returned_mapping,
    )
    buckets.update(compare_return_claims_to_observed_facts(returned_mapping))
    if not buckets:
        return comparison
    synthetic_fields = tuple(
        f"proof_obligation.{name}" for name in sorted(buckets)
    )
    required = tuple(dict.fromkeys((*comparison.required_return_fields(), *synthetic_fields)))
    missing = tuple(dict.fromkeys((*comparison.missing_return_fields(), *synthetic_fields)))
    evidence = _replace_comparison_evidence_fields(
        comparison.comparison_evidence,
        prefix="required_return_fields:",
        values=required,
    )
    evidence = _replace_comparison_evidence_fields(
        evidence,
        prefix="missing_return_fields:",
        values=missing,
    )
    for name in sorted(buckets):
        evidence = (
            *evidence,
            f"proof_comparison.{name}: " + "; ".join(buckets[name]),
        )
    return BrickComparisonFact.from_parts(
        work_reference=comparison.work_reference,
        comparison_evidence=evidence,
        observed_match_kind="missing",
        comparison_rule=comparison.comparison_rule,
        required_return_shape_evidence=comparison.required_return_shape_evidence,
        forbidden_shortcut_evidence=comparison.forbidden_shortcut_evidence,
    )


def _clean_proof_run(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _clean_proof_obligation(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mutation_red_observation_present(
    returned_value: Mapping[str, Any],
    command: str,
) -> bool:
    runs = returned_value.get("mutation_red_runs")
    if not isinstance(runs, list):
        return False
    for item in runs:
        if not isinstance(item, Mapping):
            continue
        if command and str(item.get("red_cmd") or "").strip() != command:
            continue
        if not all(field in item for field in _MUTATION_RED_REQUIRED_FIELDS):
            continue
        if not str(item.get("revert_ref") or "").strip():
            continue
        if not str(item.get("red_cmd") or "").strip():
            continue
        if isinstance(item.get("red_rc"), bool) or not isinstance(item.get("red_rc"), int):
            continue
        if isinstance(item.get("restore_rc"), bool) or not isinstance(item.get("restore_rc"), int):
            continue
        return True
    return False


def _replace_comparison_evidence_fields(
    comparison_evidence: tuple[str, ...],
    *,
    prefix: str,
    values: Iterable[str],
) -> tuple[str, ...]:
    replacement = prefix + " " + ", ".join(tuple(dict.fromkeys(values)))
    kept = tuple(line for line in comparison_evidence if not line.startswith(prefix))
    return (*kept, replacement)


@dataclass(frozen=True)
class BrickComparisonFact:
    """Observed contract-comparison evidence owned by the Brick axis."""

    work_reference: str
    comparison_evidence: tuple[str, ...] = field(default_factory=tuple)
    observed_match_kind: str = ""
    comparison_rule: str = ""
    required_return_shape_evidence: str = ""
    forbidden_shortcut_evidence: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "work_reference",
            self._required_text("work_reference", self.work_reference),
        )
        object.__setattr__(
            self,
            "comparison_evidence",
            self._text_tuple("comparison_evidence", self.comparison_evidence),
        )
        object.__setattr__(
            self,
            "observed_match_kind",
            self._observed_match_kind(self.observed_match_kind),
        )
        object.__setattr__(
            self,
            "comparison_rule",
            self._optional_text("comparison_rule", self.comparison_rule),
        )
        object.__setattr__(
            self,
            "required_return_shape_evidence",
            self._optional_text(
                "required_return_shape_evidence",
                self.required_return_shape_evidence,
            ),
        )
        object.__setattr__(
            self,
            "forbidden_shortcut_evidence",
            self._text_tuple(
                "forbidden_shortcut_evidence",
                self.forbidden_shortcut_evidence,
            ),
        )

    @classmethod
    def from_parts(
        cls,
        work_reference: str,
        comparison_evidence: Iterable[str] | str | None = None,
        observed_match_kind: str = "",
        comparison_rule: str = "",
        required_return_shape_evidence: str = "",
        forbidden_shortcut_evidence: Iterable[str] | str | None = None,
    ) -> "BrickComparisonFact":
        return cls(
            work_reference=work_reference,
            comparison_evidence=cls._text_tuple(
                "comparison_evidence",
                comparison_evidence,
            ),
            observed_match_kind=observed_match_kind,
            comparison_rule=comparison_rule,
            required_return_shape_evidence=required_return_shape_evidence,
            forbidden_shortcut_evidence=cls._text_tuple(
                "forbidden_shortcut_evidence",
                forbidden_shortcut_evidence,
            ),
        )

    @classmethod
    def from_returned_value(
        cls,
        *,
        work_reference: str,
        required_fields: Iterable[str],
        returned_value: Any | None,
        comparison_rule: str = "",
        required_return_shape_evidence: str = "",
        forbidden_shortcut_evidence: Iterable[str] | str | None = None,
    ) -> "BrickComparisonFact":
        """Build a comparison fact from an already-determined required-field set.

        Mirrors the support comparison rule exactly: ``required_fields`` is the
        field set the caller has already derived (Brick declaration plus any
        gate-derived fields — that union stays in support); this factory only
        observes which of those fields are present on ``returned_value`` and
        formats the comparison evidence. It does not compute gate-derived fields
        and does not apply forbidden-key filtering.
        """

        required = tuple(dict.fromkeys(str(item) for item in required_fields))
        observed_fields: tuple[str, ...] = ()
        missing: list[str] = []
        waived: list[str] = []
        if not isinstance(returned_value, Mapping):
            missing.extend(required or ("returned.mapping",))
        else:
            observed_fields = tuple(
                sorted(str(key) for key in returned_value.keys())
            )
            for field_name in required:
                if field_name in returned_value:
                    continue
                if field_name == "made_changes" and "no_changes_reason" in returned_value:
                    waived.append("made_changes via no_changes_reason")
                    continue
                if field_name == "transition_concern_evidence":
                    waived.append("transition_concern_evidence absent means no concern")
                    continue
                missing.append(field_name)
        missing_fields = tuple(dict.fromkeys(missing))
        waived_fields = tuple(dict.fromkeys(waived))

        comparison_evidence = [
            "adapter returned value is available for Brick comparison observation",
        ]
        if required:
            comparison_evidence.append(
                "required_return_fields: " + ", ".join(required)
            )
        if observed_fields:
            comparison_evidence.append(
                "observed_return_fields: " + ", ".join(observed_fields)
            )
        if waived_fields:
            comparison_evidence.append(
                "waived_return_fields: " + ", ".join(waived_fields)
            )
        if missing_fields:
            comparison_evidence.append(
                "missing_return_fields: " + ", ".join(missing_fields)
            )
        elif required:
            comparison_evidence.append("missing_return_fields: none")
        if missing_fields:
            observed_match_kind = "missing"
        elif required:
            observed_match_kind = "matched"
        else:
            observed_match_kind = "unknown"
        return cls.from_parts(
            work_reference=work_reference,
            comparison_evidence=comparison_evidence,
            observed_match_kind=observed_match_kind,
            comparison_rule=comparison_rule,
            required_return_shape_evidence=required_return_shape_evidence,
            forbidden_shortcut_evidence=forbidden_shortcut_evidence,
        )

    def fields_from_evidence(self, prefix: str) -> tuple[str, ...]:
        """Parse a comma-delimited evidence line back into field names.

        Mirrors the support accessor: find the first ``comparison_evidence``
        item beginning with ``prefix``, drop the prefix, treat empty or
        ``none`` as no fields, otherwise split on commas with ``-`` normalized
        to ``_`` and empty tokens dropped.
        """

        for item in self.comparison_evidence:
            if not item.startswith(prefix):
                continue
            text = item[len(prefix):].strip()
            if not text or text == "none":
                return ()
            return tuple(
                field
                for field in (
                    part.strip().replace("-", "_") for part in text.split(",")
                )
                if field
            )
        return ()

    def required_return_fields(self) -> tuple[str, ...]:
        fields = self.fields_from_evidence("required_return_fields:")
        if fields:
            return fields
        return parse_required_return_shape(self.required_return_shape_evidence)

    def missing_return_fields(self) -> tuple[str, ...]:
        return self.fields_from_evidence("missing_return_fields:")

    def waived_return_fields(self) -> tuple[str, ...]:
        return self.fields_from_evidence("waived_return_fields:")

    @classmethod
    def apply_proof_obligation_comparison(
        cls,
        comparison: "BrickComparisonFact",
        *,
        returned_value: Any | None,
        declared_obligations: Iterable[Mapping[str, Any]],
    ) -> "BrickComparisonFact":
        return apply_proof_obligation_comparison(
            comparison,
            returned_value=returned_value,
            declared_obligations=declared_obligations,
        )

    @classmethod
    def _required_text(cls, field_name: str, value: str) -> str:
        cleaned = cls._optional_text(field_name, value)
        if not cleaned:
            raise ValueError(f"{field_name} must not be blank")
        return cleaned

    @staticmethod
    def _optional_text(field_name: str, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be text")
        return value.strip()

    @classmethod
    def _observed_match_kind(cls, value: str) -> str:
        cleaned = cls._optional_text("observed_match_kind", value).lower()
        if cleaned and cleaned not in _OBSERVED_MATCH_KINDS:
            allowed = ", ".join(_OBSERVED_MATCH_KINDS)
            raise ValueError(f"observed_match_kind must be blank or one of: {allowed}")
        return cleaned

    @staticmethod
    def _text_tuple(
        field_name: str,
        values: Iterable[str] | str | None,
    ) -> tuple[str, ...]:
        if values is None:
            return ()
        if isinstance(values, str):
            values = (values,)

        facts: list[str] = []
        for index, value in enumerate(values):
            if not isinstance(value, str):
                raise TypeError(f"{field_name}[{index}] must be text")
            cleaned = value.strip()
            if not cleaned:
                raise ValueError(f"{field_name}[{index}] must not be blank")
            facts.append(cleaned)
        return tuple(facts)


__all__ = [
    "BrickComparisonFact",
    "apply_proof_obligation_comparison",
    "compare_changed_paths_to_write_scope",
    "compare_proof_runs_to_declared_obligations",
    "compare_return_claims_to_observed_facts",
    "path_matches_scope",
]
