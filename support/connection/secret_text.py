"""Single source for raw-credential ("raw secret") text detection.

ONE canonical pattern set governs EVERY credential-rejection site: the adapter
return-payload guard, the plan/primitive intake validator, the step-output
recording validator, and the design-resource reader. Patterns are
word-boundary + minimum-length regexes, so ordinary text that merely CONTAINS a
marker prefix as a substring (e.g. "task-source", "kiosk-mode", "AIzaWizard",
"-----BEGIN NOTE-----") is NOT misread as a secret, while a real credential
(marker + a long random body) still is.

Leaf module: imports only ``re``, so any layer (connection / operator /
recording) may import it without an import cycle.
"""

from __future__ import annotations

import re

RAW_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bxoxb-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bghp_[A-Za-z0-9_]{12,}"),
    re.compile(r"\bgho_[A-Za-z0-9_]{12,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{12,}"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{12,}"),
    re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"),
)


def contains_raw_secret_text(text: str) -> bool:
    """Return True iff ``text`` carries a raw credential by the canonical patterns."""

    return any(pattern.search(text) for pattern in RAW_SECRET_PATTERNS)
