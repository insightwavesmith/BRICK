"""Wiki carry behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    rule_items,
)


def run_wiki_carry_truncation_survival_case(
    repo: Path, profile: Mapping[str, Any]
) -> int:
    """Pin: the load-bearing PATH + NOTE survive DOWNSTREAM re-truncation.

    The blocker (0619 adversarial verify): the wiki view is floored by
    ``safe_source_fact_body`` once in the walker AND AGAIN downstream in the
    agent adapter (``_clean_source_fact_bodies`` limit 12000,
    ``_source_fact_bodies_for_prompt`` limit 12000 / small-limit probe 4000). Every floor
    truncates the TAIL. When ``returned`` is large the whole serialized view
    blows past a downstream limit; if PATH/NOTE rode in the tail (the old
    layout) they were silently amputated and the worker lost the "go look"
    address (operator measured: 12534-char view -> ``wiki_carry_path_text``
    None at limit 12000 AND 4000).

    This pin builds the view through the REAL ``_wiki_carry_view`` with an
    OVERSIZE ``returned`` (well past every limit), re-truncates it at limit
    12000 AND 4000 via the REAL ``safe_source_fact_body``, and asserts the
    absolute PATH and the NOTE SURVIVE both. It also asserts a small ``returned``
    keeps path + note + a JSON-parseable summary. Reordering the view so PATH/
    NOTE land in the tail REDs this pin (mutation guard).
    """

    items = rule_items(profile, "wiki_carry_truncation_survival_case")
    if not items:
        return 0
    from brick_protocol.support.connection.adapter_validation import (
        _SOURCE_FACT_BODY_LIMIT,
        safe_source_fact_body,
    )
    from support.operator.walker_kernel import (
        _WIKI_CARRY_NOTE,
        _wiki_carry_view,
        wiki_carry_path_text,
        wiki_carry_summary_text,
    )

    count = 0
    for raw in items:
        mapping = require_mapping(raw, "wiki_carry_truncation_survival_case item")
        label = require_string(
            mapping.get("label"), "wiki_carry_truncation_survival_case.label"
        )
        # The YAML subset returns bare scalars as strings; accept int or
        # int-valued string and coerce.
        raw_oversize = mapping.get("oversize_returned_chars", 20000)
        try:
            oversize_chars = int(raw_oversize)
        except (TypeError, ValueError):
            raise ProfileError(
                f"wiki_carry_truncation_survival_case rejected {label}: "
                "oversize_returned_chars must be a positive integer"
            )
        if oversize_chars <= 0:
            raise ProfileError(
                f"wiki_carry_truncation_survival_case rejected {label}: "
                "oversize_returned_chars must be a positive integer"
            )

        # Use a tmp building root so _wiki_carry_view resolves a real absolute
        # path (the on-disk step-output is never read by this pin; only the path
        # text is exercised). The blocker is in the VIEW LAYOUT, not file IO.
        with tempfile.TemporaryDirectory(prefix="bp-wiki-carry-survival-") as tmpdir:
            building_root = Path(tmpdir)
            step_output_ref = "work/step-outputs/oversize-attempt-1/step-output.json"
            absolute_path = str((building_root / step_output_ref).resolve())

            # OVERSIZE returned: a step-output JSON whose `returned.answer` alone
            # dwarfs every downstream limit, so the serialized view is far past
            # 12000 (and 4000).
            oversize_body = json.dumps(
                {
                    "envelope_marker": "should-not-ride",
                    "raw_stream_ref": "should-not-ride",
                    "returned": {
                        "body_marker": "oversize-body",
                        "answer": "X" * oversize_chars,
                    },
                }
            )
            view = _wiki_carry_view(building_root, step_output_ref, oversize_body)

            # The view itself must already exceed both limits, else this pin is
            # not actually exercising the re-truncation seam.
            if len(view) <= _SOURCE_FACT_BODY_LIMIT:
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    f"oversize view is only {len(view)} chars, not past limit "
                    f"{_SOURCE_FACT_BODY_LIMIT} -- raise oversize_returned_chars"
                )

            for limit in (_SOURCE_FACT_BODY_LIMIT, 4000):
                retruncated = safe_source_fact_body(view, limit=limit)
                # The downstream floor MUST have actually fired (tail cut), or
                # the pin proves nothing about survival under truncation.
                if len(retruncated) <= len(view) and len(view) <= limit:
                    raise ProfileError(
                        f"wiki_carry_truncation_survival_case rejected {label}: "
                        f"view did not exceed limit {limit}"
                    )
                carry_path = wiki_carry_path_text(retruncated)
                if carry_path is None:
                    raise ProfileError(
                        f"wiki_carry_truncation_survival_case rejected {label}: "
                        f"absolute PATH amputated by tail-truncate at limit {limit} "
                        f"(view layout puts PATH in the tail)"
                    )
                if carry_path != absolute_path:
                    raise ProfileError(
                        f"wiki_carry_truncation_survival_case rejected {label}: "
                        f"PATH corrupted at limit {limit}: {carry_path!r} != "
                        f"{absolute_path!r}"
                    )
                if not Path(carry_path).is_absolute():
                    raise ProfileError(
                        f"wiki_carry_truncation_survival_case rejected {label}: "
                        f"surviving PATH is not absolute at limit {limit}"
                    )
                if _WIKI_CARRY_NOTE not in retruncated:
                    raise ProfileError(
                        f"wiki_carry_truncation_survival_case rejected {label}: "
                        f"NOTE amputated by tail-truncate at limit {limit}"
                    )

            # Small returned: full fidelity -- path + note + JSON-parseable
            # summary all present (no truncation regression on the common case).
            small_body = json.dumps(
                {
                    "envelope_marker": "should-not-ride",
                    "returned": {"body_marker": "small-body", "answer": "ok"},
                }
            )
            small_view = _wiki_carry_view(building_root, step_output_ref, small_body)
            if wiki_carry_path_text(small_view) != absolute_path:
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    "small-returned view lost its absolute PATH"
                )
            if _WIKI_CARRY_NOTE not in small_view:
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    "small-returned view lost its NOTE"
                )
            summary = wiki_carry_summary_text(small_view)
            if summary is None:
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    "small-returned view lost its SUMMARY"
                )
            try:
                small_returned = json.loads(summary)
            except json.JSONDecodeError as exc:
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    "small-returned summary is not JSON"
                ) from exc
            if (
                not isinstance(small_returned, Mapping)
                or small_returned.get("body_marker") != "small-body"
            ):
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    "small-returned summary did not round-trip `returned`"
                )
        count += 1
    return count
