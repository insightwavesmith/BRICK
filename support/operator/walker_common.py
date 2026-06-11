"""Shared proof-limit / not-proven constants for the dynamic walker sublayer.

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
dynamic graph walker (support/operator/dynamic_walker.py) was a ~2638 LOC
god-module mixing forward walk + reroute adoption + per-node budget + HOLD +
fan-in/out + resume + frontier in one file. Its separable concerns were lifted
into single-concern collaborator modules behind a thin facade. This leaf module
homes the shared support-record proof-limit / not-proven vocabularies the walk
kernel, resume verb, HOLD builder, fan-in, and frontier writer all emit.

Support record only. It homes NO axis crossing, chooses no Movement, judges no
success or quality, schedules nothing, retries nothing, calls no provider.
"""

from __future__ import annotations


PROOF_LIMITS: tuple[str, ...] = (
    "support evidence only",
    "dynamic walker walks declared gate-adopted agent-proposed routes only",
    "support authors no route or Movement",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
NOT_PROVEN: tuple[str, ...] = (
    "semantic correctness of the agent-proposed reroute",
    "parallel runtime execution (P-walker-2 fan-in/fan-out out of scope here)",
    "scheduler / queue / retry behavior",
    "caller/COO disposition after a HOLD",
)
RESUME_NOT_PROVEN: tuple[str, ...] = (
    "adapter:local resume probes only unless caller uses another adapter",
    "parallel runtime execution",
    "full process-integrity across resumed provider processes",
    "semantic correctness of the human/COO disposition",
)
FAN_TOPOLOGY_PROOF_LIMITS: tuple[str, ...] = (
    "B3 fan-out / fan-in proof is adapter:local serial walk only",
    "not parallel runtime execution",
    "not scheduler / queue / retry behavior",
    "not full process-integrity proof",
)
FAN_TOPOLOGY_NOT_PROVEN: tuple[str, ...] = (
    "parallel execution",
    "full process integrity across concurrent providers",
)
