"""Brick-owned public work-structure fact surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class BuildingWork:
    """Work structure fact owned by the Brick axis."""

    work_units: tuple[str, ...] = field(default_factory=tuple)
    nested_building_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "work_units",
            self._text_tuple("work_units", self.work_units),
        )
        object.__setattr__(
            self,
            "nested_building_refs",
            self._text_tuple("nested_building_refs", self.nested_building_refs),
        )
        if not self.work_units and not self.nested_building_refs:
            raise ValueError("BuildingWork must name at least one work fact")

    @classmethod
    def from_parts(
        cls,
        work_units: Iterable[str] | str | None = None,
        nested_building_refs: Iterable[str] | str | None = None,
    ) -> "BuildingWork":
        return cls(
            work_units=cls._text_tuple("work_units", work_units),
            nested_building_refs=cls._text_tuple(
                "nested_building_refs",
                nested_building_refs,
            ),
        )

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


__all__ = ["BuildingWork"]
