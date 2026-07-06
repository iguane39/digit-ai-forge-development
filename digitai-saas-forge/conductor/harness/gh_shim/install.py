"""Installe les lanceurs ``gh`` (POSIX) et ``gh.cmd`` (Windows) dans un dossier bin dédié.

Le superviseur préfixe ce dossier au PATH du sous-processus ``claude`` **ssi** le provider est
Azure DevOps ; BAD invoque alors ``gh`` en nom nu et tombe sur ce lanceur, qui relaie vers
``python -m conductor.harness.gh_shim``. Le PATH GitHub reste intact (aucun shim installé).
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

# Racine importable contenant le paquet ``conductor`` (….../digitai-saas-forge).
# install.py = conductor/harness/gh_shim/install.py → parents[3] = racine du dépôt forge.
_PKG_ROOT = Path(__file__).resolve().parents[3]


def default_bin_dir() -> Path:
    """Emplacement stable du bin du shim (dans la forge, jamais dans le dépôt cible)."""
    return _PKG_ROOT / ".gh-shim-bin"


def install_gh_shim(bin_dir: Path | None = None) -> Path:
    """Écrit les lanceurs et renvoie le dossier à préfixer au PATH.

    Les lanceurs propagent ``PYTHONPATH`` vers la racine de la forge : BAD s'exécute dans le
    dépôt *cible* (où ``conductor`` n'est pas importable par défaut)."""
    target = bin_dir or default_bin_dir()
    target.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    root = str(_PKG_ROOT)

    posix = target / "gh"
    posix.write_text(
        "#!/bin/sh\n"
        f'PYTHONPATH="{root}${{PYTHONPATH:+{os.pathsep}$PYTHONPATH}}" '
        f'exec "{py}" -m conductor.harness.gh_shim "$@"\n',
        encoding="utf-8",
    )
    posix.chmod(posix.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    windows = target / "gh.cmd"
    windows.write_text(
        "@echo off\r\n"
        f'set "PYTHONPATH={root};%PYTHONPATH%"\r\n'
        f'"{py}" -m conductor.harness.gh_shim %*\r\n',
        encoding="utf-8",
    )
    return target


def path_overlay(bin_dir: Path | None = None) -> dict[str, str]:
    """Overlay d'environnement préfixant le PATH avec le bin du shim (shim prioritaire)."""
    target = install_gh_shim(bin_dir)
    return {"PATH": f"{target}{os.pathsep}{os.environ.get('PATH', '')}"}
