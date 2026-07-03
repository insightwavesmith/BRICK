"""MCP/connect/native projection kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes MCP/connect and provider-native projection surfaces; it owns no axis
crossing, decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    _ensure_import_identity,
)

_MCP_STDIO_SMOKE_TIMEOUT_SECONDS = 30


def run_mcp_stdio_smoke(repo: Path) -> KernelResult:
    """Execution smoke: bare-launch the MCP projection server like a real host.

    A real MCP host launches ``support/connection/mcp_projection.py`` as a plain
    Python script with a CLEAN environment (no PYTHONPATH pointing at the
    import_identity shim). The script's own __file__ bootstrap must therefore put
    everything it needs on sys.path; if it forgets the import_identity shim the
    bare launch crashes at import (ModuleNotFoundError: brick_protocol) before it
    can answer a single JSON-RPC request.

    This check subprocess-launches that script with PYTHONPATH deleted, pipes one
    ``initialize`` JSON-RPC line, and asserts the server did not crash and did
    answer with a JSON-RPC result. subprocess is permitted here in the checker
    layer (it observes the script from the outside, like a host); it must stay out
    of mcp_projection.py itself, which owns no execution surface.
    """
    script = repo / "support" / "connection" / "mcp_projection.py"
    if not script.is_file():
        raise ProfileError(f"mcp_stdio_smoke could not find MCP server script: {script}")

    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)

    request_line = (
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        + "\n"
    )
    try:
        completed = subprocess.run(
            [sys.executable, str(script), "--repo", str(repo)],
            input=request_line,
            capture_output=True,
            text=True,
            env=clean_env,
            cwd=str(repo),
            timeout=_MCP_STDIO_SMOKE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProfileError(
            "mcp_stdio_smoke: bare-launched MCP server timed out "
            f"after {_MCP_STDIO_SMOKE_TIMEOUT_SECONDS}s without responding"
        ) from exc

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if "Traceback" in stderr or "ModuleNotFoundError" in stderr:
        raise ProfileError(
            "mcp_stdio_smoke: bare-launched MCP server (clean env, no PYTHONPATH) "
            "crashed at startup:\n" + stderr.strip()
        )
    if '"result"' not in stdout:
        raise ProfileError(
            "mcp_stdio_smoke: bare-launched MCP server did not emit a JSON-RPC "
            f"'\"result\"' to initialize.\nstdout:\n{stdout.strip()}\n"
            f"stderr:\n{stderr.strip()}"
        )

    return KernelResult(
        check_id="mcp_stdio_smoke",
        inspected=1,
        output=(
            "mcp stdio smoke passed: bare-launched server (clean env, no "
            "PYTHONPATH) responded to initialize"
        ),
    )


_CONNECT_CONFIG_LAUNCH_TIMEOUT_SECONDS = 30


def _parse_codex_mcp_config(config_text: str) -> tuple[str, str, str]:
    """Extract (command, script_path, repo_arg) from the emitted Codex TOML.

    The generator emits exactly:

        [mcp_servers.brick-protocol]
        command = "python3"
        args = ["<script>", "--repo", "<repo>"]

    This parses those three values out of the rendered block so the checker
    launches EXACTLY what the generator told the user to run (not a
    hand-written command). Parsing failure is a ProfileError: a malformed
    generated config is itself a defect.
    """

    command: str | None = None
    args_line: str | None = None
    for raw in config_text.splitlines():
        line = raw.strip()
        if line.startswith("command"):
            _, _, value = line.partition("=")
            command = value.strip().strip('"')
        elif line.startswith("args"):
            args_line = line

    if command is None or args_line is None:
        raise ProfileError(
            "connect_config_launch: generated Codex config missing command/args "
            f"line(s):\n{config_text}"
        )

    _, _, args_value = args_line.partition("=")
    args_value = args_value.strip()
    if not (args_value.startswith("[") and args_value.endswith("]")):
        raise ProfileError(
            f"connect_config_launch: generated args is not a list literal: {args_value!r}"
        )
    items = [
        item.strip().strip('"')
        for item in args_value[1:-1].split(",")
        if item.strip()
    ]
    if len(items) != 3 or items[1] != "--repo":
        raise ProfileError(
            "connect_config_launch: generated args do not match "
            f'["<script>", "--repo", "<repo>"]: {items!r}'
        )
    script_path, _flag, repo_arg = items
    return command, script_path, repo_arg


def run_connect_config_launch(repo: Path) -> KernelResult:
    """Execution proof: the generated Codex connect config yields a working server.

    Imports the read-only connect generator (support/connection/connect.py),
    renders the Codex MCP config for THIS repo, extracts the command + server
    script + ``--repo`` it tells the user to run, and then subprocess-launches
    EXACTLY that command with a CLEAN environment (PYTHONPATH deleted) and one
    piped ``initialize`` JSON-RPC line. The launch must return a JSON-RPC
    ``"result"`` with no Traceback / ModuleNotFoundError. This proves
    "generated config -> actually working connection" end to end, not just that
    the generator emitted a plausible-looking string.

    Also asserts the emitted script path is ``<repo>/support/connection/
    mcp_projection.py`` and exists, the emitted ``--repo`` equals this repo, and
    that connect.py's source carries no hardcoded user-home literal (the path
    must be computed, never baked in).

    subprocess lives here in the checker layer (it observes the generated
    command from the outside, like a real MCP host); the generator itself runs
    no subprocess and owns no execution surface.
    """

    repo_text = str(repo)
    if repo_text not in sys.path:
        sys.path.insert(0, repo_text)
    connect = importlib.import_module("support.connection.connect")

    # The generated config must carry no hardcoded absolute user path; the path
    # is computed from the checkout. Guard the source directly.
    connect_source_path = repo / "support" / "connection" / "connect.py"
    if not connect_source_path.is_file():
        raise ProfileError(
            f"connect_config_launch: connect generator missing: {connect_source_path}"
        )
    connect_source = connect_source_path.read_text(encoding="utf-8")
    user_home_literal = "/" + "Users/"
    if user_home_literal in connect_source:
        raise ProfileError(
            "connect_config_launch: connect.py source contains a hardcoded "
            "user-home literal; the repo path must be computed, never baked in."
        )

    config_text = connect.render_codex_mcp_config(repo)
    command, script_path, repo_arg = _parse_codex_mcp_config(config_text)

    expected_script = (repo / "support" / "connection" / "mcp_projection.py").resolve()
    emitted_script = Path(script_path).resolve()
    if emitted_script != expected_script:
        raise ProfileError(
            "connect_config_launch: generated config points at "
            f"{emitted_script}, expected {expected_script}"
        )
    if not emitted_script.is_file():
        raise ProfileError(
            f"connect_config_launch: generated server script does not exist: {emitted_script}"
        )
    if Path(repo_arg).resolve() != repo.resolve():
        raise ProfileError(
            "connect_config_launch: generated --repo "
            f"{repo_arg} does not match this repo {repo}"
        )

    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)

    request_line = (
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        + "\n"
    )
    launch_argv = [command, script_path, "--repo", repo_arg]
    try:
        completed = subprocess.run(
            launch_argv,
            input=request_line,
            capture_output=True,
            text=True,
            env=clean_env,
            cwd=str(repo),
            timeout=_CONNECT_CONFIG_LAUNCH_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise ProfileError(
            "connect_config_launch: generated command could not be launched "
            f"(command not found on PATH): {launch_argv!r}: {exc}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ProfileError(
            "connect_config_launch: generated config server timed out "
            f"after {_CONNECT_CONFIG_LAUNCH_TIMEOUT_SECONDS}s without responding"
        ) from exc

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if "Traceback" in stderr or "ModuleNotFoundError" in stderr:
        raise ProfileError(
            "connect_config_launch: generated config server (clean env, no "
            "PYTHONPATH) crashed at startup:\n" + stderr.strip()
        )
    if '"result"' not in stdout:
        raise ProfileError(
            "connect_config_launch: generated config server did not emit a "
            f"JSON-RPC '\"result\"' to initialize.\nstdout:\n{stdout.strip()}\n"
            f"stderr:\n{stderr.strip()}"
        )

    return KernelResult(
        check_id="connect_config_launch",
        inspected=1,
        output=(
            "connect config launch passed: generated Codex config "
            "(computed repo path, no hardcoded user-home literal) launched the "
            "server with a clean env (no PYTHONPATH) and it answered initialize"
        ),
    )


def run_codex_projection_native(repo: Path) -> KernelResult:
    """Execution proof: the Codex projection is a REAL Codex-native TOML subagent.

    Imports the read-only renderer (support/connection/agent_resources.py) and
    asserts, BY EXECUTION over admitted Agent Objects, that render_codex_subagent_toml:

      (a) parses as VALID TOML (tomllib) and carries the required Codex subagent
          keys name + description + developer_instructions;
      (b) sandbox_mode is "workspace-write" for the dev (read-write-scoped) agent
          and "read-only" for a leader/reviewer agent -- a REAL tool-policy
          mapping, not a constant (this is the load-bearing FIRE pin: making
          sandbox_mode constant must turn this RED);
      (c) the Codex TOML is materially DIFFERENT from the generic/claude seed
          text -- the codex output is valid TOML whereas the claude seed is
          markdown that does NOT parse as a TOML table (real translation, not a
          relabel);
      (d) developer_instructions carries the "enforced by Brick MCP" honesty note
          (return shape / Link / evidence are not native-Codex-expressible).

    This is checker-layer support evidence only: it imports the renderer
    in-process, runs no subprocess, writes no file, and chooses no Movement. The
    renderer it pins is itself read-only (no subprocess in connection/).
    """

    import tomllib

    repo_text = str(repo)
    if repo_text not in sys.path:
        sys.path.insert(0, repo_text)
    _ensure_import_identity(repo)
    agent_resources = importlib.import_module("support.connection.agent_resources")

    list_refs = agent_resources.list_agent_object_refs
    render_toml = agent_resources.render_codex_subagent_toml
    render_claude_seed = agent_resources.render_claude_projection_seed
    render_packet = agent_resources.render_agent_packet
    render_codex_seed = agent_resources.render_codex_projection_seed

    refs = list(list_refs(repo))
    if not refs:
        raise ProfileError(
            "codex_projection_native: no admitted Agent Object refs to project"
        )

    roles = [ref.removeprefix("agent-object:") for ref in refs]

    # (a) + (d): every admitted role must yield valid TOML with the required
    # Codex subagent keys and the Brick-MCP honesty note.
    write_roles: list[str] = []
    read_only_roles: list[str] = []
    inspected = 0
    for role in roles:
        toml_text = render_toml(role, repo_root=repo)
        try:
            parsed = tomllib.loads(toml_text)
        except tomllib.TOMLDecodeError as exc:
            raise ProfileError(
                f"codex_projection_native: render_codex_subagent_toml({role!r}) "
                f"is not valid TOML: {exc}"
            ) from exc
        for required_key in ("name", "description", "developer_instructions"):
            value = parsed.get(required_key)
            if not isinstance(value, str) or not value.strip():
                raise ProfileError(
                    f"codex_projection_native: {role!r} TOML missing required Codex "
                    f"subagent key {required_key!r}"
                )
        if parsed.get("name") != role:
            raise ProfileError(
                f"codex_projection_native: {role!r} TOML name must equal the role"
            )
        sandbox_mode = parsed.get("sandbox_mode")
        if sandbox_mode not in {"workspace-write", "read-only"}:
            raise ProfileError(
                f"codex_projection_native: {role!r} TOML sandbox_mode must be "
                f"workspace-write or read-only, got {sandbox_mode!r}"
            )
        if "enforced by Brick MCP" not in parsed["developer_instructions"]:
            raise ProfileError(
                f"codex_projection_native: {role!r} developer_instructions is "
                "missing the 'enforced by Brick MCP' honesty note (return shape / "
                "Link / evidence are not native-Codex-expressible)"
            )
        if sandbox_mode == "workspace-write":
            write_roles.append(role)
        else:
            read_only_roles.append(role)
        inspected += 1

    # (b) REAL tool-policy mapping, not a constant. The dev agent
    # (tool-policy:read-write-scoped) MUST map to workspace-write; a leader and a
    # reviewer (read-only policies) MUST map to read-only. Making sandbox_mode a
    # constant (ignoring tool policy) is what this FIRE pin catches.
    if "dev" in roles:
        dev_sandbox = tomllib.loads(render_toml("dev", repo_root=repo))["sandbox_mode"]
        if dev_sandbox != "workspace-write":
            raise ProfileError(
                "codex_projection_native: dev (tool-policy:read-write-scoped) must "
                f"map to sandbox_mode workspace-write, got {dev_sandbox!r}"
            )
    if not write_roles:
        raise ProfileError(
            "codex_projection_native: no role mapped to workspace-write; a "
            "constant read-only sandbox_mode would hide the read-write-scoped "
            "worker (mapping is not real)"
        )
    if not read_only_roles:
        raise ProfileError(
            "codex_projection_native: no role mapped to read-only; a constant "
            "workspace-write sandbox_mode would over-grant every leader/reviewer "
            "(mapping is not real)"
        )

    # (e) PER-STEP write_need gate. The per-agent TOML above is the DESCRIPTIVE
    # max-capability projection; the RUN-TIME provider projection FOR A STEP must
    # additionally gate sandbox_mode on the step's Brick write NEED. A
    # write-capable agent (read-write-scoped) on a read-only Brick (write_need
    # False) MUST project read-only sandbox -- the agent's CAPABILITY must never
    # override the Brick NEED. Removing the write_need gate (back to keying on
    # tool_policy alone) turns this RED.
    sandbox_for_policies = agent_resources.codex_sandbox_mode_for_tool_policies
    write_probe_role = "pm-lead" if "pm-lead" in roles else "dev"
    write_probe_packet = render_packet(write_probe_role, repo_root=repo)
    write_capable_policies = list(write_probe_packet["agent_object"]["tool_policy_refs"])
    write_capable_resources = list(write_probe_packet["tool_policy_resources"])
    leak_sandbox = sandbox_for_policies(
        write_capable_policies,
        write_need=False,
        native_grant_resources=write_capable_resources,
    )
    if leak_sandbox != "read-only":
        raise ProfileError(
            "codex_projection_native: a write-capable agent on a read-only Brick "
            f"(write_need=False) must project sandbox_mode read-only, got "
            f"{leak_sandbox!r} (capability overrode the Brick NEED)"
        )
    write_sandbox = sandbox_for_policies(
        write_capable_policies,
        write_need=True,
        native_grant_resources=write_capable_resources,
    )
    if write_sandbox != "workspace-write":
        raise ProfileError(
            "codex_projection_native: a write-capable agent on a write-needed "
            f"Brick (write_need=True) must project sandbox_mode workspace-write, "
            f"got {write_sandbox!r} (over-restricted a legitimate write)"
        )

    # (c) materially DIFFERENT from the generic/claude seed: codex is valid TOML
    # with the subagent keys; the claude seed's rendered_instruction_text is
    # markdown that does NOT parse as a TOML table carrying those keys.
    probe_role = "dev" if "dev" in roles else roles[0]
    claude_text = render_claude_seed(probe_role, repo_root=repo)["rendered_instruction_text"]
    codex_toml = render_toml(probe_role, repo_root=repo)
    if claude_text.strip() == codex_toml.strip():
        raise ProfileError(
            "codex_projection_native: codex TOML is byte-identical to the claude "
            "seed text (relabel, not a real translation)"
        )
    claude_is_toml_subagent = False
    try:
        claude_parsed = tomllib.loads(claude_text)
        claude_is_toml_subagent = isinstance(claude_parsed.get("name"), str) and isinstance(
            claude_parsed.get("developer_instructions"), str
        )
    except tomllib.TOMLDecodeError:
        claude_is_toml_subagent = False
    if claude_is_toml_subagent:
        raise ProfileError(
            "codex_projection_native: the claude seed text also parses as a Codex "
            "subagent TOML; the codex projection is not a materially different form"
        )

    # The wired Codex projection seed must surface the real TOML without dropping
    # the existing generic instruction text other consumers/checkers rely on.
    seed = render_codex_seed(probe_role, repo_root=repo)
    if "rendered_codex_subagent_toml" not in seed:
        raise ProfileError(
            "codex_projection_native: render_codex_projection_seed dropped the "
            "rendered_codex_subagent_toml key"
        )
    if "rendered_instruction_text" not in seed:
        raise ProfileError(
            "codex_projection_native: render_codex_projection_seed dropped the "
            "existing rendered_instruction_text key (would break other consumers)"
        )
    if tomllib.loads(seed["rendered_codex_subagent_toml"])["name"] != probe_role:
        raise ProfileError(
            "codex_projection_native: seed rendered_codex_subagent_toml is not the "
            "role's valid TOML"
        )

    return KernelResult(
        check_id="codex_projection_native",
        inspected=inspected,
        output=(
            "codex projection native passed: "
            f"{inspected} Agent Object(s) rendered valid Codex-native subagent TOML "
            f"(write={sorted(write_roles)}, read-only count={len(read_only_roles)}); "
            "real tool-policy -> sandbox_mode mapping, honesty note present, "
            "materially different from the claude markdown seed"
        ),
    )


def _split_claude_frontmatter(md_text: str) -> tuple[str, str]:
    """Split a Claude subagent .md into (frontmatter_yaml, body).

    The Claude subagent format is ``--- <yaml> --- <body>``. Leading HTML
    comments (the read-only provenance banner this renderer stamps) precede the
    opening fence, so we scan for the first non-blank, non-comment line and
    require it to be the ``---`` fence, then capture up to the closing fence.
    Raises ProfileError if no valid frontmatter block is present.
    """

    lines = md_text.splitlines()
    idx = 0
    # Skip the leading provenance comment banner + blank lines before the fence.
    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped or (stripped.startswith("<!--")):
            idx += 1
            continue
        break
    if idx >= len(lines) or lines[idx].strip() != "---":
        raise ProfileError(
            "claude_projection_native: subagent .md does not open with a '---' "
            "YAML frontmatter fence"
        )
    open_fence = idx
    close_fence = -1
    for j in range(open_fence + 1, len(lines)):
        if lines[j].strip() == "---":
            close_fence = j
            break
    if close_fence == -1:
        raise ProfileError(
            "claude_projection_native: subagent .md frontmatter has no closing "
            "'---' fence"
        )
    frontmatter = "\n".join(lines[open_fence + 1 : close_fence])
    body = "\n".join(lines[close_fence + 1 :])
    return frontmatter, body


def run_claude_projection_native(repo: Path) -> KernelResult:
    """Execution proof: the Claude projection is a REAL Claude-native .md subagent.

    Imports the read-only renderer (support/connection/agent_resources.py) and
    asserts, BY EXECUTION over admitted Agent Objects, that render_claude_subagent_md:

      (a) parses as a real Claude subagent file -- '---' YAML frontmatter '---'
          plus a body -- and the frontmatter carries the required name +
          description + tools keys;
      (b) REAL tool-policy mapping: the dev agent (tool-policy:read-write-scoped)
          tools INCLUDE Edit, Write, and Bash; a leader/reviewer agent (read-only
          policy) tools EXCLUDE Edit/Write/Bash -- so making the tool list a constant
          (ignoring policy) turns this RED (this is the load-bearing FIRE pin);
      (c) materially DIFFERENT from the codex form: the codex render is valid
          TOML; the claude render is markdown-with-frontmatter that does NOT
          parse as a Codex subagent TOML table (real translation, not a relabel);
      (d) the "enforced by Brick MCP" honesty note is present in the body.

    This is checker-layer support evidence only: it imports the renderer
    in-process, runs no subprocess, writes no file, and chooses no Movement. The
    renderer it pins is itself read-only (no subprocess in connection/).
    """

    import tomllib

    from support.checkers.lib.yaml_subset import parse_yaml_subset

    repo_text = str(repo)
    if repo_text not in sys.path:
        sys.path.insert(0, repo_text)
    _ensure_import_identity(repo)
    agent_resources = importlib.import_module("support.connection.agent_resources")

    list_refs = agent_resources.list_agent_object_refs
    render_md = agent_resources.render_claude_subagent_md
    render_toml = agent_resources.render_codex_subagent_toml
    render_claude_seed = agent_resources.render_claude_projection_seed
    render_packet = agent_resources.render_agent_packet

    refs = list(list_refs(repo))
    if not refs:
        raise ProfileError(
            "claude_projection_native: no admitted Agent Object refs to project"
        )

    roles = [ref.removeprefix("agent-object:") for ref in refs]

    def _tool_list(role: str) -> list[str]:
        md_text = render_md(role, repo_root=repo)
        frontmatter, body = _split_claude_frontmatter(md_text)
        parsed = parse_yaml_subset(frontmatter)
        if not isinstance(parsed, Mapping):
            raise ProfileError(
                f"claude_projection_native: {role!r} frontmatter is not a YAML "
                "mapping"
            )
        for required_key in ("name", "description", "tools"):
            value = parsed.get(required_key)
            if not isinstance(value, str) or not value.strip():
                raise ProfileError(
                    f"claude_projection_native: {role!r} frontmatter missing "
                    f"required Claude subagent key {required_key!r}"
                )
        if parsed.get("name") != role:
            raise ProfileError(
                f"claude_projection_native: {role!r} frontmatter name must equal "
                "the role"
            )
        if "enforced by Brick MCP" not in body:
            raise ProfileError(
                f"claude_projection_native: {role!r} body is missing the 'enforced "
                "by Brick MCP' honesty note (return shape / Link / evidence are "
                "not native-Claude-expressible)"
            )
        return [tool.strip() for tool in str(parsed["tools"]).split(",") if tool.strip()]

    # (a) + (d): every admitted role must yield a parseable subagent .md with the
    # required keys and the Brick-MCP honesty note. Split into write/read-only by
    # the REAL tool mapping (Edit + Write + Bash present == write-capable).
    write_tool_names = {"Edit", "Write", "Bash"}
    write_roles: list[str] = []
    read_only_roles: list[str] = []
    inspected = 0
    for role in roles:
        tools = _tool_list(role)
        tool_set = set(tools)
        if write_tool_names.issubset(tool_set):
            write_roles.append(role)
        elif tool_set.isdisjoint(write_tool_names):
            read_only_roles.append(role)
        else:
            raise ProfileError(
                f"claude_projection_native: {role!r} tools list is half-write "
                f"(Edit/Write/Bash must be all present or all absent), got {tools}"
            )
        inspected += 1

    # (b) REAL tool-policy mapping, not a constant. The dev agent
    # (tool-policy:read-write-scoped) MUST include Edit AND Write; a leader and a
    # reviewer (read-only policies) MUST exclude both. Making the tools list a
    # constant (ignoring tool policy) is what this FIRE pin catches.
    if "dev" in roles:
        dev_tools = _tool_list("dev")
        if not write_tool_names.issubset(set(dev_tools)):
            raise ProfileError(
                "claude_projection_native: dev (tool-policy:read-write-scoped) "
                f"tools must INCLUDE Edit, Write, and Bash, got {dev_tools}"
            )
    if not write_roles:
        raise ProfileError(
            "claude_projection_native: no role's tools include Edit/Write/Bash; a "
            "constant read-only tools list would hide the read-write-scoped "
            "worker (mapping is not real)"
        )
    if not read_only_roles:
        raise ProfileError(
            "claude_projection_native: no role's tools exclude Edit/Write/Bash; a "
            "constant write-capable tools list would over-grant every "
            "leader/reviewer (mapping is not real)"
        )

    # (e) PER-STEP write_need gate. The per-agent .md above is the DESCRIPTIVE
    # max-capability projection; the RUN-TIME provider projection FOR A STEP must
    # additionally gate the tool set on the step's Brick write NEED. A
    # write-capable agent (read-write-scoped) on a read-only Brick (write_need
    # False) MUST project a tool set with NO Edit/Write/Bash -- the agent's CAPABILITY
    # must never override the Brick NEED. Removing the write_need gate (back to
    # keying on tool_policy alone) turns this RED.
    tools_for_policies = agent_resources.claude_tools_for_tool_policies
    write_probe_role = "pm-lead" if "pm-lead" in roles else "dev"
    write_probe_packet = render_packet(write_probe_role, repo_root=repo)
    write_capable_policies = list(write_probe_packet["agent_object"]["tool_policy_refs"])
    write_capable_resources = list(write_probe_packet["tool_policy_resources"])
    leak_tools = list(
        tools_for_policies(
            write_capable_policies,
            write_need=False,
            native_grant_resources=write_capable_resources,
        )["tools"]
    )
    if not write_tool_names.isdisjoint(set(leak_tools)):
        raise ProfileError(
            "claude_projection_native: a write-capable agent on a read-only Brick "
            f"(write_need=False) must project a tool set with NO Edit/Write/Bash, got "
            f"{leak_tools} (capability overrode the Brick NEED)"
        )
    write_tools = list(
        tools_for_policies(
            write_capable_policies,
            write_need=True,
            native_grant_resources=write_capable_resources,
        )["tools"]
    )
    if not write_tool_names.issubset(set(write_tools)):
        raise ProfileError(
            "claude_projection_native: a write-capable agent on a write-needed "
            f"Brick (write_need=True) must project a tool set INCLUDING Edit, "
            f"Write, and Bash, got {write_tools} (over-restricted a legitimate write)"
        )

    # (c) materially DIFFERENT from the codex form: the claude render is markdown
    # with YAML frontmatter; the codex render is valid TOML. Assert codex != claude
    # shape -- the claude .md must NOT parse as a Codex subagent TOML table, and
    # the two texts must not be byte-identical.
    probe_role = "dev" if "dev" in roles else roles[0]
    claude_md = render_md(probe_role, repo_root=repo)
    codex_toml = render_toml(probe_role, repo_root=repo)
    if claude_md.strip() == codex_toml.strip():
        raise ProfileError(
            "claude_projection_native: claude .md is byte-identical to the codex "
            "TOML (relabel, not a real translation)"
        )
    claude_is_codex_toml = False
    try:
        claude_parsed = tomllib.loads(claude_md)
        claude_is_codex_toml = isinstance(
            claude_parsed.get("name"), str
        ) and isinstance(claude_parsed.get("developer_instructions"), str)
    except tomllib.TOMLDecodeError:
        claude_is_codex_toml = False
    if claude_is_codex_toml:
        raise ProfileError(
            "claude_projection_native: the claude .md also parses as a Codex "
            "subagent TOML; the claude projection is not a materially different "
            "form"
        )

    # The wired Claude projection seed must surface the real .md + tools without
    # dropping the existing generic instruction text other consumers rely on, and
    # without leaking the codex toml key into the claude seed.
    seed = render_claude_seed(probe_role, repo_root=repo)
    if "rendered_claude_subagent_md" not in seed:
        raise ProfileError(
            "claude_projection_native: render_claude_projection_seed dropped the "
            "rendered_claude_subagent_md key"
        )
    if "claude_tools" not in seed:
        raise ProfileError(
            "claude_projection_native: render_claude_projection_seed dropped the "
            "claude_tools key"
        )
    if "rendered_instruction_text" not in seed:
        raise ProfileError(
            "claude_projection_native: render_claude_projection_seed dropped the "
            "existing rendered_instruction_text key (would break other consumers)"
        )
    if "rendered_codex_subagent_toml" in seed:
        raise ProfileError(
            "claude_projection_native: the claude seed leaked the codex "
            "rendered_codex_subagent_toml key (host seeds must not cross-leak)"
        )
    seed_frontmatter, _ = _split_claude_frontmatter(seed["rendered_claude_subagent_md"])
    if parse_yaml_subset(seed_frontmatter).get("name") != probe_role:
        raise ProfileError(
            "claude_projection_native: seed rendered_claude_subagent_md is not the "
            "role's valid subagent .md"
        )

    return KernelResult(
        check_id="claude_projection_native",
        inspected=inspected,
        output=(
            "claude projection native passed: "
            f"{inspected} Agent Object(s) rendered valid Claude-native subagent .md "
            f"(write={sorted(write_roles)}, read-only count={len(read_only_roles)}); "
            "real tool-policy -> tools allow/deny mapping (dev and write-capable "
            "leaders have Edit+Write+Bash, reviewers remain read-only), honesty note "
            "present, materially different from the codex TOML form"
        ),
    )


def _run_read_side_projection_boundary_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "read_side_projection_boundary",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def probe_mutation_red(repo: Path) -> list[str]:
    source = Path(__file__).resolve()
    original = source.read_text(encoding="utf-8")
    needle = "def run_mcp_stdio_smoke(repo: Path) -> KernelResult:"
    poisoned = "def run_mcp_stdio_smoke_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError(
            "mcp_connect_projection mutation probe could not find MCP entrypoint"
        )

    backup = tempfile.NamedTemporaryFile(
        prefix=".mcp-connect-projection-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_read_side_projection_boundary_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "mcp_connect_projection mutation probe did not turn "
                "read_side_projection_boundary profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_read_side_projection_boundary_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "mcp_connect_projection mutation probe restored source but "
            f"read_side_projection_boundary remained RED:\n{excerpt}"
        )

    return [
        "MCP/connect projection mutation RED probe passed: disabling the moved "
        "run_mcp_stdio_smoke entrypoint made check_profile.py --profile "
        "read_side_projection_boundary exit non-zero, then restoring the "
        "temp-backed self file returned read_side_projection_boundary to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for MCP/connect projection."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved run_mcp_stdio_smoke "
            "entrypoint, assert read_side_projection_boundary profile exits RED, "
            "restore from a temp backup, then assert read_side_projection_boundary GREEN"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = (
            probe_mutation_red(repo)
            if args.probe_mutation_red
            else [
                run_mcp_stdio_smoke(repo).output,
                run_connect_config_launch(repo).output,
                run_codex_projection_native(repo).output,
                run_claude_projection_native(repo).output,
            ]
        )
    except ProfileError as exc:
        print("MCP/connect projection check rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
