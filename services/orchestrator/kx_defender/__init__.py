"""Kx-Defender orchestrator package."""

from __future__ import annotations

import sys
from pathlib import Path

__version__ = "0.4.0"

# Ensure repo-root `modules/` is importable for editable/CLI installs.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
