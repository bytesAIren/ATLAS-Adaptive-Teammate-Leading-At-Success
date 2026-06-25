from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME312_SITE_PACKAGES = PROJECT_ROOT / "runtime312" / "Lib" / "site-packages"
LOCAL_DEPS = PROJECT_ROOT / "deps_py312"
LEGACY_VENV_SITE_PACKAGES = PROJECT_ROOT / "venv" / "Lib" / "site-packages"


def bootstrap_runtime() -> None:
    """
    Ensure imports resolve against the project-local dependency directory first.
    This keeps the app runnable on Python 3.12 even when the checked-in legacy
    venv was created on a different machine or Python build.
    """
    preferred_paths = [PROJECT_ROOT]
    for candidate in (RUNTIME312_SITE_PACKAGES, LOCAL_DEPS, LEGACY_VENV_SITE_PACKAGES):
        if candidate.exists():
            preferred_paths.insert(0, candidate)
            break

    for candidate in reversed(preferred_paths):
        candidate_str = str(candidate)
        if candidate.exists() and candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


def runtime_status() -> dict[str, str | bool]:
    return {
        "python_version": sys.version.split()[0],
        "project_root": str(PROJECT_ROOT),
        "runtime312_present": RUNTIME312_SITE_PACKAGES.exists(),
        "local_deps_present": LOCAL_DEPS.exists(),
        "legacy_venv_present": LEGACY_VENV_SITE_PACKAGES.exists(),
    }
