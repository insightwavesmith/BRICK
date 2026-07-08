"""Live frontier queue helpers for the dynamic graph walker."""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Mapping, Sequence
from typing import Any

from brick_protocol.support.operator.walker_fan_in import (
    _fan_in_wait_all_state,
    _splice_declared_successors,
)
from brick_protocol.support.recording.contracts import require_positive_int

@dataclasses.dataclass(frozen=True)
class _ReadyItemsResult:
    """Support-only ready batch returned by the live frontier driver."""

    items: tuple[dict[str, Any], ...]
    hold_item: Mapping[str, Any] | None = None
    hold_observation: Mapping[str, Any] | None = None


class _FrontierDriver:
    """Own the live frontier queue and cursor."""

    def __init__(
        self,
        items: Sequence[dict[str, Any]],
        *,
        scheduled_fan_steps: set[tuple[str, int]] | None = None,
    ) -> None:
        self._items = list(items)
        self._cursor = 0
        self._scheduled_fan_steps = (
            scheduled_fan_steps if scheduled_fan_steps is not None else set()
        )

    def next_item(self) -> dict[str, Any] | None:
        # Serial/default mode returns exactly one cursor-front item. P6-C's
        # opt-in pool path uses ready_items() and leaves this path byte-stable.
        if self._cursor >= len(self._items):
            return None
        item = self._items[self._cursor]
        self._cursor += 1
        return item

    def ready_items(
        self,
        *,
        max_items: int,
        has_fan_groups: bool,
        fan_in_sources_by_target: Mapping[str, tuple[str, ...]],
        completed_fan_steps: set[tuple[str, int]],
        running_fan_steps: set[tuple[str, int]],
        held_fan_steps: set[tuple[str, int]],
        fan_in_deferrals: dict[tuple[str, int], int],
    ) -> _ReadyItemsResult:
        if max_items <= 0:
            raise ValueError("frontier ready max_items must be positive")
        ready: list[dict[str, Any]] = []
        while self._cursor < len(self._items) and len(ready) < max_items:
            item = self._items[self._cursor]
            step_ref = str(item.get("step_ref", ""))
            cascade_depth = int(item.get("cascade_depth", 0))
            if has_fan_groups:
                wait_state, wait_observation = _fan_in_wait_all_state(
                    step_ref=step_ref,
                    cascade_depth=cascade_depth,
                    fan_in_sources_by_target=fan_in_sources_by_target,
                    completed_fan_steps=completed_fan_steps,
                    running_fan_steps=running_fan_steps,
                    held_fan_steps=held_fan_steps,
                    pending_queue=self._items[self._cursor + 1 :],
                    fan_in_deferrals=fan_in_deferrals,
                )
                if wait_state == "defer":
                    self._cursor += 1
                    self.defer(item)
                    continue
                if wait_state == "hold":
                    if ready:
                        break
                    self._cursor += 1
                    return _ReadyItemsResult(
                        items=(),
                        hold_item=item,
                        hold_observation=wait_observation,
                    )
            # HOLD-SAFE PARALLEL: a fan-in TARGET (join) dispatches ALONE, never batched
            # with siblings/sources. A reroute/HOLD only emerges AFTER a node RUNS, and
            # ready_items cannot foresee it; batching a join alongside a node about to
            # reroute/HOLD lets the join BODY run before the HOLD applies (the knot3-cohort-g
            # break). So joins are batch-terminal: this item either starts a fresh batch
            # alone (ready empty -> append + break) or waits for the next batch (ready
            # non-empty -> break WITHOUT advancing). Independent fan-out lanes still batch.
            is_fan_in_target = bool(fan_in_sources_by_target.get(step_ref))
            if is_fan_in_target and ready:
                break
            self._cursor += 1
            ready.append(item)
            if has_fan_groups:
                running_fan_steps.add((step_ref, cascade_depth))
            if is_fan_in_target:
                break
        return _ReadyItemsResult(items=tuple(ready))

    def pending_items(self) -> list[dict[str, Any]]:
        return self._items[self._cursor :]

    def append(self, items: Sequence[dict[str, Any]]) -> None:
        self._items.extend(items)

    def defer(self, item: dict[str, Any]) -> None:
        self.append([item])

    def splice_after_current(
        self,
        items: Sequence[dict[str, Any]],
        *,
        offset: int = 0,
    ) -> None:
        if not items:
            return
        insert_at = self._cursor + offset
        self._items[insert_at:insert_at] = list(items)

    def splice_declared_successors_after_current(
        self,
        *,
        source_step_ref: str,
        cascade_depth: int,
        parent_reroute_ref: str,
        successors_by_source: Mapping[str, tuple[str, ...]],
        offset: int = 0,
    ) -> None:
        successor_items: list[dict[str, Any]] = []
        _splice_declared_successors(
            successor_items,
            insert_at=0,
            source_step_ref=source_step_ref,
            cascade_depth=cascade_depth,
            parent_reroute_ref=parent_reroute_ref,
            successors_by_source=successors_by_source,
            scheduled_fan_steps=self._scheduled_fan_steps,
        )
        self.splice_after_current(successor_items, offset=offset)


def _fanout_dispatch_pool_size(plan: Mapping[str, Any]) -> int:
    raw_value = os.environ.get(
        "BRICK_FANOUT_DISPATCH_POOL_SIZE",
        plan.get("fanout_dispatch_pool_size", 1),
    )
    if raw_value is None or raw_value == "":
        return 1
    return require_positive_int(raw_value, "fanout_dispatch_pool_size")


# AUTO-PARALLEL default: a drawn fan() IS the parallel declaration. When the plan has fan
# groups and NO explicit pool override is set, default the dispatch pool to this cap so
# fan-out runs concurrent BY DEFAULT. HOLD-safe because ready_items forces fan-in TARGETS
# (joins) to dispatch alone (batch-terminal), so a sibling's data-dependent reroute/HOLD is
# applied before any join body runs. Record order stays canonical (the drain pops
# pending_outcomes FIFO = submission/frontier order, independent of completion timing).
# Resume/replay stays serial until the current HOLD disposition is applied; live
# continuation then recovers this declared fan-out pool. An explicit env/plan
# override still wins.
_FANOUT_AUTO_POOL = 8


def _has_explicit_fanout_pool_override(plan: Mapping[str, Any]) -> bool:
    env = os.environ.get("BRICK_FANOUT_DISPATCH_POOL_SIZE")
    if env not in (None, ""):
        return True
    return "fanout_dispatch_pool_size" in plan
