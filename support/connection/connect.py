"""Read-only MCP connect-config generator (CONNECT-GENERATOR-0).

Emits a CORRECT, PORTABLE MCP connect config for the Brick Protocol projection
server, computed from the user's OWN checkout — never a hardcoded absolute path.

WHY THIS EXISTS: the only connect docs before this generator were static and
hardcoded one developer's home directory. Any other user/host who copied
them got a wrong path. This module instead derives the repo root from its own
file location (the same ``parents[2]`` bootstrap mcp_projection.py uses) and
renders the config for THAT root. No PYTHONPATH is emitted either: the server's
own ``__file__`` bootstrap self-adds ``support/import_identity`` on a bare host
launch, so clients need to set nothing.

This is support evidence rendering ONLY. It emits text. It runs NO subprocess
(the read_side_projection_boundary guard forbids subprocess in
support/connection/*), writes NO file, stores NO credential, calls NO provider,
and owns NO Agent / Brick meaning, Movement, or success/quality judgment.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


_SERVER_NAME = "brick-protocol"
_MCP_SERVER_REL = "support/connection/mcp_projection.py"


def repo_root_from_here() -> Path:
    """Compute the repo root from this file's location.

    ``support/connection/connect.py`` -> parents[2] is the repo root, exactly
    like the mcp_projection.py bare-launch bootstrap. No hardcoded path.
    """

    return Path(__file__).resolve().parents[2]


def _server_script(repo_root: Path) -> Path:
    return Path(repo_root) / _MCP_SERVER_REL


def render_codex_mcp_config(repo_root: Path) -> str:
    """Render the Codex ``~/.codex/config.toml`` MCP server block for repo_root.

    The block names the python3 command and passes the server script plus
    ``--repo <repo_root>``. NO env PYTHONPATH: the server bootstrap self-fixes
    sys.path on a bare launch. repo_root is used verbatim (never a hardcoded
    absolute user path).
    """

    script = _server_script(repo_root)
    return (
        f"[mcp_servers.{_SERVER_NAME}]\n"
        'command = "python3"\n'
        f'args = ["{script}", "--repo", "{repo_root}"]\n'
    )


def render_claude_mcp_command(repo_root: Path) -> str:
    """Render the ``claude mcp add`` one-liner for repo_root.

    No PYTHONPATH; the server bootstrap self-fixes sys.path on a bare launch.
    """

    script = _server_script(repo_root)
    return (
        f"claude mcp add {_SERVER_NAME} -- "
        f"python3 {script} --repo {repo_root}"
    )


def _codex_guidance() -> str:
    return (
        "안내(초보자용):\n"
        "1) 아래 블록을 ~/.codex/config.toml 파일에 붙여넣으세요.\n"
        "2) Codex를 다시 시작하면 brick-protocol MCP 서버가 연결됩니다.\n"
        "3) PYTHONPATH 같은 환경설정은 필요 없습니다 (서버가 스스로 처리합니다)."
    )


def _claude_guidance() -> str:
    return (
        "안내(초보자용):\n"
        "1) 아래 명령을 터미널에서 그대로 실행하세요.\n"
        "2) 실행하면 brick-protocol MCP 서버가 Claude에 등록됩니다.\n"
        "3) PYTHONPATH 같은 환경설정은 필요 없습니다 (서버가 스스로 처리합니다)."
    )


def render_connect(target: str, repo_root: Path) -> str:
    """Render the chosen connect config plus beginner guidance."""

    if target == "codex":
        return _codex_guidance() + "\n\n" + render_codex_mcp_config(repo_root)
    if target == "claude":
        return _claude_guidance() + "\n\n" + render_claude_mcp_command(repo_root) + "\n"
    raise ValueError(f"unknown target: {target!r} (expected 'codex' or 'claude')")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Emit a portable MCP connect config for codex/claude, computed from "
            "this checkout (no hardcoded path). Read-only: prints text only."
        )
    )
    parser.add_argument("target", choices=("codex", "claude"))
    parser.add_argument(
        "--repo",
        default=None,
        help="Repo root override (default: computed from this file's location).",
    )
    args = parser.parse_args(argv)
    repo_root = Path(args.repo).resolve() if args.repo else repo_root_from_here()
    sys.stdout.write(render_connect(args.target, repo_root))
    sys.stdout.write("\n")
    return 0


__all__ = [
    "repo_root_from_here",
    "render_codex_mcp_config",
    "render_claude_mcp_command",
    "render_connect",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
