"""Shared checker import bootstrap helpers.

Support checker mechanics only: this module prepares import paths for direct
checker execution and owns no checker judgment, pin, profile, or axis logic.
"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_checker_imports(repo: Path | str) -> None:
    repo_path = Path(repo).resolve()
    import_identity = repo_path / "support" / "import_identity"
    for entry in (str(import_identity), str(repo_path)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
