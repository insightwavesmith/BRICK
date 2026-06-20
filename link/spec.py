"""Link-owned plan-level declarable grammar (axis single-source API, E2/§2 AXIS C).

This is the START of the Link single-source API (E2 design §2 AXIS C / §8 S3):
the plan-level Link grammar a builder DECLARES is Link-axis property, not support
mechanics. Today it owns the gate-concept translation table (the materializer's
``gate_concept_profile`` token -> live ``declared_gate_ref`` map) plus the one
``translate_gate_concept`` helper. Later E2 steps (S4+) fold the Link envelope
schemas, the forbidden-ref-prefix vocabulary, and ``LINK_ROW_ALLOWED_KEYS`` here.

It defines plan-level Link vocabulary; it authors no Movement, invents no route,
and judges no success or quality. The gate-concept -> gate-ref translation is
single-sourced HERE (the support materializer in composition.py imports the
table + helper instead of re-stating either). Both derive from the Link-owned
``link.gate.DECLARED_GATE_REFS`` so the produced refs cannot drift from the gate
vocabulary.
"""

from __future__ import annotations

from collections.abc import Mapping

from brick_protocol.link.gate import DECLARED_GATE_REFS


# GATE-CONCEPT TRANSLATION (Link plan grammar; moved from
# support/operator/composition.py at E2/S3). A preset DECLARES a
# ``gate_concept_profile`` of concept tokens; the materializer TRANSLATES each
# token into a live ``declared_gate_ref`` on a specific row. The token -> ref map
# is single-sourced here over the Link-owned gate vocabulary
# (``DECLARED_GATE_REFS``: [0]=default-transition, [1]=strict, [2]=human,
# [3]=coo). MODE tokens (default-transition / fan-in-wait-all / portfolio-policy)
# have NO gate ref here on purpose: they are not Link gates (fan-in-wait-all =
# declared graph topology requirement, portfolio-policy = driver surface).
GATE_CONCEPT_TOKEN_GATE_REFS: Mapping[str, str] = {
    "strict-evidence": DECLARED_GATE_REFS[1],
    "coo-review": DECLARED_GATE_REFS[3],
    "human-review": DECLARED_GATE_REFS[2],
}


def translate_gate_concept(token: str) -> str:
    """Translate ONE gate-concept token to its live ``declared_gate_ref``.

    The single Link-owned reader of ``GATE_CONCEPT_TOKEN_GATE_REFS``. Raises
    ``KeyError`` for a non-translating token (MODE tokens or unknown labels never
    reach this helper: the materializer guards on membership before calling).
    Returns the byte-identical ref the prior inline ``GATE_CONCEPT_TOKEN_GATE_REFS[token]``
    subscripts produced.
    """

    return GATE_CONCEPT_TOKEN_GATE_REFS[token]
