"""install_gh_shim : écrit des lanceurs gh/gh.cmd et renvoie le bin dir (overlay PATH)."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

from conductor.harness.gh_shim.install import install_gh_shim, path_overlay


def test_install_writes_both_launchers(tmp_path: Path) -> None:
    bin_dir = install_gh_shim(tmp_path / "bin")
    assert (bin_dir / "gh").exists()
    assert (bin_dir / "gh.cmd").exists()


def test_posix_launcher_is_executable_and_relays(tmp_path: Path) -> None:
    bin_dir = install_gh_shim(tmp_path / "bin")
    posix = bin_dir / "gh"
    if os.name != "nt":  # le bit exécutable n'a pas de sens sous Windows (chmod ignoré)
        assert posix.stat().st_mode & stat.S_IXUSR
    body = posix.read_text(encoding="utf-8")
    assert "conductor.harness.gh_shim" in body
    assert sys.executable in body


def test_windows_launcher_relays(tmp_path: Path) -> None:
    body = (install_gh_shim(tmp_path / "bin") / "gh.cmd").read_text(encoding="utf-8")
    assert "conductor.harness.gh_shim" in body
    assert "PYTHONPATH" in body


def test_path_overlay_prefixes_bin_dir(tmp_path: Path) -> None:
    overlay = path_overlay(tmp_path / "bin")
    path = overlay["PATH"]
    assert path.startswith(str(tmp_path / "bin") + os.pathsep)
    # le PATH courant est préservé derrière le shim
    assert os.environ.get("PATH", "") in path
