"""Gemini HTTP API adapter + bare-text design-AI invocation seams.

★S11 SEAM★ Extracted VERBATIM from ``support/connection/agent_adapter.py`` (E2
split, extraction 6/7). PURE relocation -- no logic/name/signature change. This
module owns:

* The direct Gemini HTTP API adapter path (stdlib ``urllib``, env key, NO
  subprocess): ``_gemini_api_key_from_env``, ``_gemini_api_model_name``,
  ``_build_gemini_api_request``, ``_parse_gemini_api_response``,
  ``_gemini_api_urlopen``, ``_invoke_gemini_api``, ``_gemini_api_key_env_present``.
* The bare prompt -> text design-AI seams: ``invoke_gemini_text`` (HTTP) plus
  ``invoke_claude_text`` / ``invoke_codex_text`` (local CLI) and their
  ``_text_cli_executable`` / ``_clean_text_cli_option`` helpers.

The ``agent_adapter`` facade re-exports every symbol here (public AND
underscore-private) so late-bound ``agent_adapter.<sym>`` access never breaks.
In particular ``kernel_checks.py`` patches ``agent_adapter.urllib.request.urlopen``
and calls ``agent_adapter._gemini_api_urlopen``; the facade keeps
``import urllib.request`` and re-exports ``_gemini_api_urlopen`` /
``_parse_gemini_api_response`` so that seam is preserved.

This module imports siblings DIRECTLY (adapter_validation, adapter_model_casting,
adapter_grant_policy, adapter_constants) and NEVER
``from support.connection.agent_adapter import ...`` at top level (cycle). The
stay-behind carriers, constants, and helper functions that still live in
``agent_adapter`` (``_GEMINI_API_SPEC``, ``_GEMINI_API_BASE_URL``,
``_GEMINI_API_MODEL_FALLBACK``, ``_GEMINI_API_KEY_ENV_VARS``,
``_proof_limits_for_request``, ``_not_proven_for_request``, ``_merge_texts``,
``_run_text_cli``, ``_raw_text_from_completed``) are reached LAZILY in-function
(the ``from .agent_adapter import ...`` back-edge runs only at call time, after
both modules are fully loaded) so there is no import cycle and the moved bodies
keep their exact statements. ``AgentAdapterRequest`` / ``LocalCliCompleted`` /
``CommandRunner`` are annotation-only here (``from __future__ import annotations``
keeps them strings).
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .adapter_grant_policy import (
    _build_prompt,
    _extract_required_return_fields,
    _merge_structured_return_fields,
)
from .adapter_model_casting import (
    _model_cli_arg_from_ref,
    _node_casting_fields_ordered,
)
from .adapter_validation import _reject_secret_text, _safe_excerpt

if TYPE_CHECKING:
    from .agent_adapter import AgentAdapterRequest, CommandRunner, LocalCliCompleted


def _gemini_api_key_from_env() -> str:
    """Return the Gemini API key from env, or raise FileNotFoundError (no-key).

    Decision 1 (locked): key from GEMINI_API_KEY else GOOGLE_API_KEY; absent key
    is a CLEAN typed adapter-error that MIRRORS the local_cli_missing shape. We
    raise FileNotFoundError so it flows the EXACT B2-hardened adapter-error/hold
    path in run.py (_adapter_error_kind -> 'local_cli_missing'), never a crash and
    never a subprocess. The key value is NEVER returned in evidence or logged.
    """
    from .agent_adapter import _GEMINI_API_KEY_ENV_VARS

    for env_var in _GEMINI_API_KEY_ENV_VARS:
        value = os.environ.get(env_var)
        if value and value.strip():
            return value.strip()
    raise FileNotFoundError(
        "gemini-api adapter requires an API key in env "
        + " or ".join(_GEMINI_API_KEY_ENV_VARS)
        + " (none set)"
    )


def _gemini_api_model_name(request: AgentAdapterRequest) -> str:
    """Resolve the bare Gemini model name for the HTTP path (no provider state)."""
    from .agent_adapter import _GEMINI_API_MODEL_FALLBACK, _GEMINI_API_SPEC

    model_id = _model_cli_arg_from_ref(
        request.selected_model_ref or _GEMINI_API_SPEC.default_model_ref,
        _GEMINI_API_SPEC,
    )
    # _model_cli_arg_from_ref returns "" for the gemini default sentinel; the HTTP
    # endpoint always needs a concrete model, so fall back to flash.
    return model_id or _GEMINI_API_MODEL_FALLBACK


def _build_gemini_api_request(
    api_key: str,
    model_name: str,
    prompt: str,
) -> "urllib.request.Request":
    """Build the signed Gemini generateContent POST request (pure, no network)."""
    from .agent_adapter import _GEMINI_API_BASE_URL

    url = f"{_GEMINI_API_BASE_URL}/{model_name}:generateContent"
    body = json.dumps(
        {"contents": [{"parts": [{"text": prompt}]}]},
        ensure_ascii=True,
    ).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    # Auth header (preferred over ?key=): keeps the key out of the URL/logs.
    request.add_header("x-goog-api-key", api_key)
    request.add_header("Content-Type", "application/json")
    return request


def _parse_gemini_api_response(raw_body: bytes) -> str:
    """Parse candidates[0].content.parts[0].text from a Gemini API response body.

    Any malformed/missing shape raises a CLEAN ValueError (flows the B2 hold path,
    never a raw KeyError/IndexError crash).
    """
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("gemini-api response was not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("gemini-api response must be a JSON object")
    candidates = payload.get("candidates")
    if not isinstance(candidates, Sequence) or not candidates:
        raise ValueError("gemini-api response missing candidates")
    first = candidates[0]
    if not isinstance(first, Mapping):
        raise ValueError("gemini-api candidate must be an object")
    content = first.get("content")
    if not isinstance(content, Mapping):
        raise ValueError("gemini-api candidate missing content")
    parts = content.get("parts")
    if not isinstance(parts, Sequence) or not parts:
        raise ValueError("gemini-api content missing parts")
    texts = [
        part["text"]
        for part in parts
        if isinstance(part, Mapping) and isinstance(part.get("text"), str)
    ]
    if not texts:
        raise ValueError("gemini-api response missing parts[].text")
    text = "".join(texts)
    if not text.strip():
        raise ValueError("gemini-api response text was empty")
    return text


def _gemini_api_urlopen(
    request: "urllib.request.Request",
    *,
    timeout_seconds: int,
) -> bytes:
    """Perform the HTTP call via stdlib urllib, converting failures to clean errors.

    Timeout / non-200 / transport failure all become a clean typed ValueError that
    flows the B2 hold path (never a raw urllib traceback crash). NO subprocess is
    spawned anywhere on this path.
    """
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", None)
            if status is None:
                status = response.getcode()
            if status != 200:
                raise ValueError(f"gemini-api HTTP status {status} (non-200)")
            return response.read()
    except urllib.error.HTTPError as exc:
        # Non-2xx surfaced as an exception by urllib. Read+discard the body to
        # avoid leaking a provider error body (may echo prompt/credentials).
        raise ValueError(f"gemini-api HTTP error status {exc.code}") from exc
    except (socket.timeout, TimeoutError) as exc:
        raise ValueError("gemini-api request timed out") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            raise ValueError("gemini-api request timed out") from exc
        raise ValueError("gemini-api request failed (transport error)") from exc


def _invoke_gemini_api(
    request: AgentAdapterRequest,
    *,
    timeout_seconds: int,
    urlopen: Callable[["urllib.request.Request", int], bytes] | None = None,
) -> tuple[Mapping[str, Any], tuple[str, ...], tuple[str, ...]]:
    """Direct Gemini HTTP API adapter (stdlib urllib, env key, NO subprocess).

    Mirrors _invoke_local_cli_adapter's return triple exactly so the engine stays
    adapter-agnostic. The optional urlopen seam exists ONLY so a checker FIRE can
    capture/mocks the request without a network/credential; live calls leave it
    None (the default stdlib path). Absent key / HTTP error / timeout / malformed
    response all become CLEAN typed adapter-errors (never a crash, never a spawn).
    """
    from .agent_adapter import (
        _GEMINI_API_SPEC,
        _merge_texts,
        _not_proven_for_request,
        _proof_limits_for_request,
    )

    spec = _GEMINI_API_SPEC
    proof_limits = _proof_limits_for_request(request, spec)
    not_proven = _not_proven_for_request(request, spec)
    prompt = _build_prompt(request, spec)
    api_key = _gemini_api_key_from_env()  # no-key -> FileNotFoundError (hold path)
    model_name = _gemini_api_model_name(request)
    http_request = _build_gemini_api_request(api_key, model_name, prompt)
    if urlopen is not None:
        raw_body = urlopen(http_request, timeout_seconds)
    else:
        raw_body = _gemini_api_urlopen(http_request, timeout_seconds=timeout_seconds)
    output_text = _parse_gemini_api_response(raw_body)
    _reject_secret_text("gemini_api_output", output_text)
    returned = {
        "returned_summary": "Gemini HTTP API Agent Adapter returned support evidence",
        "adapter_ref": spec.adapter_ref,
        # E2/S6★: serialize the casting dials by LOOPING the single-source
        # NODE_CASTING_FIELDS instead of naming the model dial. Each declared
        # (truthy) ``selected_<base>`` value joins the bag; an undeclared dial is
        # absent, so today this emits exactly ``selected_model_ref`` (byte-identical
        # to the prior single key) and a NEW dial (effort) rides along when declared.
        **{
            _ck: getattr(request, _ck)
            for _ck in _node_casting_fields_ordered()
            if getattr(request, _ck)
        },
        "agent_object_ref": request.agent_object_ref,
        "brain_surface_ref": spec.brain_surface_ref,
        # No CLI version on the HTTP path; record the resolved endpoint model name
        # (NOT the key, NOT the URL with any secret) as the provider identity.
        "api_model_name": model_name,
        "api_call_ref": f"support-api-call:{spec.adapter_ref}:{request.building_id}",
        "output_excerpt": _safe_excerpt(output_text),
        "evidence_refs": [
            request.output_packet_ref or f"support-ref:{spec.adapter_ref}:http-api-output"
        ],
        "proof_limits": list(proof_limits),
        "not_proven": list(not_proven),
    }
    _merge_structured_return_fields(
        returned,
        _extract_required_return_fields(
            output_text,
            request.required_return_shape,
        ),
    )
    return returned, _merge_texts(proof_limits, request.proof_limits), _merge_texts(
        not_proven,
        request.not_proven,
    )


def invoke_gemini_text(
    prompt: str,
    *,
    model_name: str = "gemini-2.5-flash",
    timeout_seconds: int = 90,
    urlopen: Callable[..., bytes] | None = None,
) -> str:
    """PUBLIC prompt -> text seam over the Gemini HTTP API (H3b customer entry).

    This is an ADDITIVE thin wrapper composing the EXISTING private helpers --
    ``_gemini_api_key_from_env`` (env key, never logged), ``_build_gemini_api_request``
    (pure request build), ``_gemini_api_urlopen`` (stdlib urllib, clean typed
    errors), ``_parse_gemini_api_response`` (candidates[0]...text) -- plus the
    output secret-scrub. It exists so a caller (the H3b ``ai_invoke`` default)
    can turn a bare design prompt into bare text WITHOUT building an
    ``AgentAdapterRequest`` (the per-Brick dispatch path stays untouched).

    Key handling mirrors decision 1 (locked): the key is read from
    ``GEMINI_API_KEY`` else ``GOOGLE_API_KEY``; an ABSENT key raises the SAME
    ``FileNotFoundError`` the per-Brick path raises (mirrors the B2-hardened
    ``local_cli_missing`` adapter-error shape) -- a CLEAN typed error, NEVER a
    crash and NEVER a subprocess. HTTP error / timeout / malformed response all
    surface as the helpers' clean ``ValueError`` (no raw traceback). The key is
    never returned in the result and never logged.

    The optional ``urlopen`` seam exists ONLY so a checker FIRE can mock the HTTP
    call (capture the request, return a canned body) with NO network / credential;
    a live caller leaves it None (the default stdlib ``_gemini_api_urlopen`` path).
    It is called as ``urlopen(request, timeout_seconds=...)`` -- the same keyword
    shape as ``_gemini_api_urlopen``.
    """
    from .agent_adapter import _GEMINI_API_MODEL_FALLBACK

    if not isinstance(prompt, str):
        raise TypeError("invoke_gemini_text requires a str prompt")
    api_key = _gemini_api_key_from_env()  # no-key -> FileNotFoundError (clean, no spawn)
    bare_model = str(model_name).strip() or _GEMINI_API_MODEL_FALLBACK
    http_request = _build_gemini_api_request(api_key, bare_model, prompt)
    if urlopen is not None:
        raw_body = urlopen(http_request, timeout_seconds=timeout_seconds)
    else:
        raw_body = _gemini_api_urlopen(http_request, timeout_seconds=timeout_seconds)
    output_text = _parse_gemini_api_response(raw_body)
    _reject_secret_text("gemini_api_text_output", output_text)
    return output_text


def invoke_claude_text(
    prompt: str,
    *,
    model_name: str = "",
    timeout_seconds: int = 120,
    command_runner: CommandRunner | None = None,
) -> str:
    """PUBLIC prompt -> text seam over the local Claude CLI.

    This additive design-AI seam mirrors ``invoke_gemini_text``'s narrow
    contract: caller supplies a prompt, the provider returns raw text, and the
    output must be non-empty and secret-free. It does not build or return an
    AgentFact and does not touch the Building adapter path.
    """
    from .agent_adapter import _raw_text_from_completed, _run_text_cli

    if not isinstance(prompt, str):
        raise TypeError("invoke_claude_text requires a str prompt")
    executable_path = _text_cli_executable("claude", command_runner)
    args_list = [executable_path, "-p", prompt, "--output-format", "text"]
    bare_model = _clean_text_cli_option("claude model_name", model_name)
    if bare_model:
        args_list.extend(("--model", bare_model))
    completed = _run_text_cli(
        tuple(args_list),
        timeout_seconds=timeout_seconds,
        command_runner=command_runner,
    )
    return _raw_text_from_completed("claude_text_output", completed.stdout, completed)


def invoke_codex_text(
    prompt: str,
    *,
    model_name: str = "",
    timeout_seconds: int = 180,
    command_runner: CommandRunner | None = None,
) -> str:
    """PUBLIC prompt -> text seam over ``codex exec --output-last-message``.

    The Codex CLI writes the last assistant message to a temp file; this wrapper
    returns that file's raw text after the same empty-output and secret-output
    guards used by the Gemini text seam.
    """
    from .agent_adapter import _raw_text_from_completed, _run_text_cli

    if not isinstance(prompt, str):
        raise TypeError("invoke_codex_text requires a str prompt")
    executable_path = _text_cli_executable("codex", command_runner)
    bare_model = _clean_text_cli_option("codex model_name", model_name)
    with tempfile.TemporaryDirectory(prefix="bp-codex-text-") as tmpdir:
        output_path = Path(tmpdir) / "last-message.txt"
        args_list = [
            executable_path,
            "exec",
            "--sandbox",
            "read-only",
        ]
        if bare_model:
            args_list.extend(("-m", bare_model))
        args_list.extend(("--output-last-message", str(output_path), prompt))
        completed = _run_text_cli(
            tuple(args_list),
            timeout_seconds=timeout_seconds,
            command_runner=command_runner,
        )
        try:
            output_text = output_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ValueError("codex text output file was not written") from exc
    return _raw_text_from_completed("codex_text_output", output_text, completed)


def _text_cli_executable(executable_name: str, command_runner: CommandRunner | None) -> str:
    executable_path = executable_name if command_runner is not None else shutil.which(executable_name)
    if not executable_path:
        raise FileNotFoundError(f"{executable_name} CLI executable not found")
    return executable_path


def _clean_text_cli_option(label: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be text")
    text = value.strip()
    if "\x00" in text or "\n" in text:
        raise ValueError(f"{label} contains unsupported control text")
    if text:
        _reject_secret_text(label, text)
    return text


def _gemini_api_key_env_present(env: Mapping[str, str]) -> bool:
    from .agent_adapter import _GEMINI_API_KEY_ENV_VARS

    return any((env.get(env_var) or "").strip() for env_var in _GEMINI_API_KEY_ENV_VARS)
