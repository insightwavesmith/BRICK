"""Pure constant leaf for the Agent Adapter support surface.

PURE constants only: adapter refs, tool-policy refs, capability literals,
model refs, and the adapter capability/allow tables. ZERO intra-package
imports -- this module is loaded first by ``agent_resources`` and
``agent/spec`` and must not depend on any sibling connection module.
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
# Retired from active adapter admission. The literal is kept only so legacy
# support checks and historical evidence can reject it explicitly.
ADAPTER_GEMINI_API = "adapter:gemini-api"
ADAPTER_CHAT_SESSION = "adapter:chat-session"
READ_WRITE_TOOL_POLICY_REF = "tool-policy:read-write-scoped"
REVIEWER_READONLY_TOOL_POLICY_REF = "tool-policy:reviewer-readonly"
LEADER_COORDINATION_TOOL_POLICY_REF = "tool-policy:leader-coordination"
WEB_CAPABLE_TOOL_POLICY_REF = "tool-policy:web-capable"
READ_ONLY_TOOL_POLICY_REFS = frozenset(
    {
        REVIEWER_READONLY_TOOL_POLICY_REF,
        LEADER_COORDINATION_TOOL_POLICY_REF,
    }
)
READ_TIER_TOOL_POLICY_REFS = READ_ONLY_TOOL_POLICY_REFS | frozenset({READ_WRITE_TOOL_POLICY_REF})
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
    }
)

ALLOWED_ADAPTER_REFS = frozenset(
    {
        ADAPTER_LOCAL,
        ADAPTER_CODEX_LOCAL,
        ADAPTER_CODEX_FUGU_LOCAL,
        ADAPTER_CLAUDE_LOCAL,
        ADAPTER_GEMINI_LOCAL,
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
    ADAPTER_CHAT_SESSION: frozenset({ADAPTER_CAPABILITY_READ}),
}

_REPO_ROOT = Path(__file__).resolve().parents[2]
