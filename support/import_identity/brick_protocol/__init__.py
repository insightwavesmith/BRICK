"""Brick Protocol public import identity.

The physical source roots live at repository root after FSR-0. This support
import-identity package exposes those roots under the canonical
``brick_protocol.*`` namespace. It does not own Brick / Agent / Link meaning
and does not provide runtime behavior.
"""

import importlib.util
from pathlib import Path
import sys

__all__: list[str] = []

_repo_root = Path(__file__).resolve().parents[3]
_package_roots = {
    "brick_protocol.brick": _repo_root / "brick",
    "brick_protocol.agent": _repo_root / "agent",
    "brick_protocol.link": _repo_root / "link",
    "brick_protocol.support": _repo_root / "support",
    "brick_protocol.support.connection": _repo_root / "support" / "connection",
    "brick_protocol.support.operator": _repo_root / "support" / "operator",
    "brick_protocol.support.recording": _repo_root / "support" / "recording",
}
_allowed_exact = frozenset(_package_roots)
_allowed_subtree_prefixes = (
    "brick_protocol.brick",
    "brick_protocol.agent",
    "brick_protocol.link",
    "brick_protocol.support.connection",
    "brick_protocol.support.operator",
    "brick_protocol.support.recording",
)


class _BrickProtocolAllowListFinder:
    def find_spec(self, fullname: str, path=None, target=None):
        if not fullname.startswith("brick_protocol."):
            return None
        if fullname == "brick_protocol":
            return None
        if fullname in _allowed_exact:
            return None
        if any(
            fullname.startswith(f"{prefix}.") for prefix in _allowed_subtree_prefixes
        ):
            return None
        raise ModuleNotFoundError(
            f"{fullname!r} is not an admitted Brick Protocol public package"
        )


if not any(
    finder.__class__.__name__ == "_BrickProtocolAllowListFinder"
    for finder in sys.meta_path
):
    sys.meta_path.insert(0, _BrickProtocolAllowListFinder())


def _install_package_alias(module_name: str, physical_root: Path):
    if not (physical_root / "__init__.py").is_file():
        return None
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(
        module_name,
        physical_root / "__init__.py",
        submodule_search_locations=[str(physical_root)],
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if module_name == "brick_protocol.support":
        module.__path__ = []  # type: ignore[attr-defined]
        module.__spec__.submodule_search_locations = []
    parent_name, _, child_name = module_name.rpartition(".")
    parent = sys.modules.get(parent_name)
    if parent is not None:
        setattr(parent, child_name, module)
    return module

for _module_name, _physical_root in _package_roots.items():
    _install_package_alias(_module_name, _physical_root)

del importlib, Path, sys, _repo_root, _package_roots
del _install_package_alias, _module_name, _physical_root
