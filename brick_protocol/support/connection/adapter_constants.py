"""Pure constant leaf for the Agent Adapter support surface.

PURE constants only: adapter refs, tool-policy refs, capability literals,
model refs, and the adapter capability/allow tables. ZERO intra-package
imports -- this module is loaded first by ``agent_resources`` and
``brick_protocol/agent/spec`` and must not depend on any sibling connection module.
"""

from __future__ import annotations

from pathlib import Path


ADAPTER_LOCAL = "adapter:local"
ADAPTER_CODEX_LOCAL = "adapter:codex-local"
# codex-fugu-local is a 1:1 SAKANA variant of codex-local: the SAME codex
# executable + codex-exec invocation, with provider-routing -c overrides
# (model_provider="sakana" + the Sakana model catalog) carried on the spec as
# DATA. It is its OWN provider-neutral adapter row (sakana<->codex-fugu-local),
# not a re-skin of codex-local; codex-local stays byte-identical.
ADAPTER_CODEX_FUGU_LOCAL = "adapter:codex-fugu-local"
ADAPTER_CLAUDE_LOCAL = "adapter:claude-local"
ADAPTER_GEMINI_LOCAL = "adapter:gemini-local"
# Local Grok Build CLI (xAI). Headless single-turn via `grok -p` (same binary as
# personal Grok TUI). Observed-write only when Brick write_scope + write-tier policy.
ADAPTER_GROK_LOCAL = "adapter:grok-local"
# Retired from active adapter admission. The literal is kept only so legacy
# support checks and historical evidence can reject it explicitly.
ADAPTER_GEMINI_API = "adapter:gemini-api"
ADAPTER_CHAT_SESSION = "adapter:chat-session"
READ_WRITE_TOOL_POLICY_REF = "tool-policy:read-write-scoped"
PROBE_WRITE_TOOL_POLICY_REF = "tool-policy:probe-write-scoped"
REVIEWER_READONLY_TOOL_POLICY_REF = "tool-policy:reviewer-readonly"
LEADER_COORDINATION_TOOL_POLICY_REF = "tool-policy:leader-coordination"
WEB_CAPABLE_TOOL_POLICY_REF = "tool-policy:web-capable"
READ_ONLY_TOOL_POLICY_REFS = frozenset(
    {
        REVIEWER_READONLY_TOOL_POLICY_REF,
        LEADER_COORDINATION_TOOL_POLICY_REF,
    }
)
WRITE_TIER_TOOL_POLICY_REFS = frozenset(
    {
        READ_WRITE_TOOL_POLICY_REF,
        PROBE_WRITE_TOOL_POLICY_REF,
    }
)
READ_TIER_TOOL_POLICY_REFS = READ_ONLY_TOOL_POLICY_REFS | WRITE_TIER_TOOL_POLICY_REFS
KNOWN_TOOL_POLICY_REFS = READ_TIER_TOOL_POLICY_REFS | frozenset({WEB_CAPABLE_TOOL_POLICY_REF})
ADAPTER_CAPABILITY_READ = "read"
ADAPTER_CAPABILITY_WRITE = "write"
ADAPTER_CAPABILITY_REVIEW = "review"
ADAPTER_CAPABILITY_WEB = "web"
ADAPTER_CAPABILITY_LITERALS = frozenset(
    {
        ADAPTER_CAPABILITY_READ,
        ADAPTER_CAPABILITY_WRITE,
        ADAPTER_CAPABILITY_REVIEW,
        ADAPTER_CAPABILITY_WEB,
    }
)
MODEL_REF_DEFAULT = "model:default"
MODEL_REF_CODEX_DEFAULT = "model:codex:default"
MODEL_REF_CLAUDE_INHERIT = "model:claude:inherit"
MODEL_REF_GEMINI_DEFAULT = "model:gemini:default"
MODEL_REF_GEMINI_FLASH = "model:gemini:gemini-3.5-flash"
MODEL_REF_GEMINI_LOCAL_FLASH = "model:gemini:gemini-3.5-flash"
MODEL_REF_GROK_DEFAULT = "model:grok:grok-4.5"
MODEL_REF_GROK_45 = "model:grok:grok-4.5"
# Sakana model refs reachable through the codex-fugu-local adapter. The provider
# token is "sakana" (matches codex's model_provider="sakana" routing); the model
# id is the Sakana catalog slug. ``fugu`` is the catalog default; ``fugu-ultra``
# is the documented upper variant of the same provider grammar.
MODEL_REF_SAKANA_FUGU = "model:sakana:fugu"
MODEL_REF_SAKANA_FUGU_ULTRA = "model:sakana:fugu-ultra"
MODEL_PROVIDER_BY_ADAPTER = {
    ADAPTER_CODEX_LOCAL: "codex",
    ADAPTER_CODEX_FUGU_LOCAL: "sakana",
    ADAPTER_CLAUDE_LOCAL: "claude",
    ADAPTER_GEMINI_LOCAL: "gemini",
    ADAPTER_GROK_LOCAL: "grok",
}
_RETIRED_WRITE_ADAPTER_REFS = frozenset(
    {
        "adapter:codex-write-local",
        "adapter:claude-write-local",
    }
)
_OBSERVED_WRITE_ADAPTER_REFS = frozenset(
    {
        ADAPTER_CODEX_LOCAL,
        ADAPTER_CODEX_FUGU_LOCAL,
        ADAPTER_CLAUDE_LOCAL,
        ADAPTER_GEMINI_LOCAL,
        ADAPTER_GROK_LOCAL,
    }
)

ALLOWED_ADAPTER_REFS = frozenset(
    {
        ADAPTER_LOCAL,
        ADAPTER_CODEX_LOCAL,
        ADAPTER_CODEX_FUGU_LOCAL,
        ADAPTER_CLAUDE_LOCAL,
        ADAPTER_GEMINI_LOCAL,
        ADAPTER_GROK_LOCAL,
        ADAPTER_CHAT_SESSION,
    }
)
_ADAPTER_CAPABILITIES = {
    ADAPTER_LOCAL: frozenset({ADAPTER_CAPABILITY_READ}),
    ADAPTER_CODEX_LOCAL: frozenset({ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_WRITE}),
    # codex-fugu-local copies codex-local's READ+WRITE brain capability (same
    # codex executable + codex-exec path); only the provider routing differs.
    ADAPTER_CODEX_FUGU_LOCAL: frozenset({ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_WRITE}),
    ADAPTER_CLAUDE_LOCAL: frozenset(
        {ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_WRITE, ADAPTER_CAPABILITY_WEB}
    ),
    # gemini-local is a local CLI adapter with technical write projection, but
    # that capability is not authority: effective write still requires Brick
    # write_scope NEED + read-write-scoped policy + observed-write admission.
    ADAPTER_GEMINI_LOCAL: frozenset(
        {
            ADAPTER_CAPABILITY_READ,
            ADAPTER_CAPABILITY_WRITE,
            ADAPTER_CAPABILITY_REVIEW,
            ADAPTER_CAPABILITY_WEB,
        }
    ),
    ADAPTER_GROK_LOCAL: frozenset(
        {
            ADAPTER_CAPABILITY_READ,
            ADAPTER_CAPABILITY_WRITE,
            ADAPTER_CAPABILITY_REVIEW,
            ADAPTER_CAPABILITY_WEB,
        }
    ),
    ADAPTER_CHAT_SESSION: frozenset({ADAPTER_CAPABILITY_READ}),
}

ADAPTER_BOUNDARY_PROOF_LIMITS = (
    "support adapter boundary evidence only",
    "adapter identity is not write authority",
    "write_effective still requires Brick write_scope NEED, write-tier Agent policy, and observed-write support",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
ADAPTER_BOUNDARY_NOT_PROVEN = (
    "credential validity",
    "provider availability",
    "provider process integrity",
    "future Building correctness",
    "semantic quality of Agent returns",
)
_ADAPTER_BOUNDARY_ROWS = {
    ADAPTER_LOCAL: {
        "boundary_strength": "stub-local-read-only",
        "credential_path_class": "none",
        "write_boundary": "no observed-write adapter support; read-only local callable fixture",
        "known_limits": (
            "not a real provider boundary",
            "cannot prove provider credential readiness",
            "cannot perform source writes",
        ),
    },
    ADAPTER_CODEX_LOCAL: {
        "boundary_strength": "local-cli-isolated-provider",
        "credential_path_class": "provider-native-file-or-env-ref",
        "write_boundary": "observed-write support only when Brick write_scope and write-tier Agent policy are both present",
        "known_limits": (
            "provider auth body is outside Brick evidence",
            "local CLI reliability is observed only at run time",
            "write capability is technical capability, not authority",
        ),
    },
    ADAPTER_CODEX_FUGU_LOCAL: {
        "boundary_strength": "local-cli-isolated-provider-routed",
        "credential_path_class": "provider-native-file-or-env-ref",
        "write_boundary": "same observed-write support as codex-local; Sakana routing data does not grant write authority",
        "known_limits": (
            "Sakana routing depends on codex provider config at run time",
            "provider auth body is outside Brick evidence",
            "write capability is technical capability, not authority",
        ),
    },
    ADAPTER_CLAUDE_LOCAL: {
        "boundary_strength": "local-cli-isolated-provider",
        "credential_path_class": "provider-native-keychain-or-env-ref",
        "write_boundary": "observed-write support only when Brick write_scope and write-tier Agent policy are both present",
        "known_limits": (
            "provider auth body is outside Brick evidence",
            "macOS keychain readiness is environment-local",
            "write capability is technical capability, not authority",
        ),
    },
    ADAPTER_GEMINI_LOCAL: {
        "boundary_strength": "local-cli-provider-policy-projected",
        "credential_path_class": "provider-native-env-ref",
        "write_boundary": "observed-write support only when Brick write_scope and write-tier Agent policy are both present",
        "known_limits": (
            "API key presence is not credential validity proof",
            "Gemini CLI tool policy projection is observed at run time",
            "write capability is technical capability, not authority",
        ),
    },
    ADAPTER_GROK_LOCAL: {
        "boundary_strength": "local-cli-isolated-provider",
        "credential_path_class": "provider-native-env-or-oauth-ref",
        "write_boundary": "observed-write support only when Brick write_scope and write-tier Agent policy are both present",
        "known_limits": (
            "Grok CLI auth body is outside Brick evidence",
            "local CLI reliability is observed only at run time",
            "write capability is technical capability, not authority",
        ),
    },
    ADAPTER_CHAT_SESSION: {
        "boundary_strength": "human-session-handoff",
        "credential_path_class": "none",
        "write_boundary": "no observed-write adapter support; parked chat-session handoff only",
        "known_limits": (
            "not a provider runtime",
            "not an automated execution boundary",
            "cannot perform source writes",
        ),
    },
}


def adapter_boundary_matrix() -> tuple[dict[str, object], ...]:
    """Return support-only customer boundary evidence for admitted adapters."""

    rows: list[dict[str, object]] = []
    for adapter_ref in sorted(ALLOWED_ADAPTER_REFS):
        base = _ADAPTER_BOUNDARY_ROWS[adapter_ref]
        rows.append(
            {
                "adapter_ref": adapter_ref,
                "provider": MODEL_PROVIDER_BY_ADAPTER.get(adapter_ref, "none"),
                "capabilities": tuple(
                    capability
                    for capability in (
                        ADAPTER_CAPABILITY_READ,
                        ADAPTER_CAPABILITY_WRITE,
                        ADAPTER_CAPABILITY_REVIEW,
                        ADAPTER_CAPABILITY_WEB,
                    )
                    if capability in _ADAPTER_CAPABILITIES[adapter_ref]
                ),
                "observed_write_adapter": adapter_ref in _OBSERVED_WRITE_ADAPTER_REFS,
                "boundary_strength": base["boundary_strength"],
                "credential_path_class": base["credential_path_class"],
                "write_boundary": base["write_boundary"],
                "known_limits": tuple(base["known_limits"]),
                "proof_limits": ADAPTER_BOUNDARY_PROOF_LIMITS,
                "not_proven": ADAPTER_BOUNDARY_NOT_PROVEN,
            }
        )
    return tuple(rows)


_REPO_ROOT = Path(__file__).resolve().parents[3]
