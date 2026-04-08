"""Kořen repozitáře `code/` a složka statických souborů `resources/`."""

from __future__ import annotations

from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
CODE_ROOT = _PACKAGE_ROOT.parent
RESOURCES_DIR = CODE_ROOT / "resources"
