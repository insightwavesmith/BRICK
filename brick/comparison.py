"""Brick-owned public comparison fact surface."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Iterable

from brick_protocol.brick.work import parse_required_return_shape


_OBSERVED_MATCH_KINDS: tuple[str, ...] = ("matched", "missing", "mismatched", "unknown")


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


__all__ = ["BrickComparisonFact"]
