"""Brick-owned public work fact surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


def parse_required_return_shape(value: Any) -> tuple[str, ...]:
    """Parse a Brick ``required_return_shape`` declaration into field names.

    Mirrors the support comparison rule exactly: the declaration is split on
    commas and slashes, each token is stripped and has ``-`` normalized to
    ``_``, and empty tokens are dropped. The order of declared fields is
    preserved and duplicates are NOT removed; forbidden-key filtering is
    intentionally NOT applied here (that remains an adapter concern).

    A JSON-object-shaped string (one that, after stripping, starts with ``{``
    or ``[`` or contains ``":``) is REJECTED with ``ValueError`` because the
    comma/slash split would shred it into garbage field names and silently
    yield a false-negative gate. The declaration must be a field list, not a
    serialized JSON value.
    """

    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise TypeError("optional value must be text")
    if not text:
        return ()
    if text.startswith("{") or text.startswith("[") or '":' in text:
        raise ValueError(
            "required_return_shape must be a comma/slash-separated field list, "
            "not a JSON object"
        )
    return tuple(
        field
        for field in (
            item.strip().replace("-", "_")
            for chunk in text.split(",")
            for item in chunk.split("/")
        )
        if field
    )


@dataclass(frozen=True)
class BrickWork:
    """Work definition fact owned by the Brick axis."""

    work_statement: str
    comparison_rule: str = ""
    required_return_shape: str = ""
    source_facts: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "work_statement",
            self._required_text("work_statement", self.work_statement),
        )
        object.__setattr__(
            self,
            "comparison_rule",
            self._optional_text("comparison_rule", self.comparison_rule),
        )
        object.__setattr__(
            self,
            "required_return_shape",
            self._optional_text("required_return_shape", self.required_return_shape),
        )
        object.__setattr__(
            self,
            "source_facts",
            self._source_fact_tuple(self.source_facts),
        )

    @classmethod
    def from_parts(
        cls,
        work_statement: str,
        comparison_rule: str = "",
        required_return_shape: str = "",
        source_facts: Iterable[str] | None = None,
    ) -> "BrickWork":
        return cls(
            work_statement=work_statement,
            comparison_rule=comparison_rule,
            required_return_shape=required_return_shape,
            source_facts=source_facts,
        )

    @staticmethod
    def _required_text(field_name: str, value: str) -> str:
        cleaned = BrickWork._optional_text(field_name, value)
        if not cleaned:
            raise ValueError(f"{field_name} must not be blank")
        return cleaned

    @staticmethod
    def _optional_text(field_name: str, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be text")
        return value.strip()

    @staticmethod
    def _source_fact_tuple(values: Iterable[str] | None) -> tuple[str, ...]:
        if values is None:
            return ()
        if isinstance(values, str):
            values = (values,)

        facts: list[str] = []
        for index, value in enumerate(values):
            facts.append(BrickWork._optional_text(f"source_facts[{index}]", value))
        return tuple(facts)


__all__ = ["BrickWork", "parse_required_return_shape"]
