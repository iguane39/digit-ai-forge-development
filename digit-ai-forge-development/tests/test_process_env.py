"""SubprocessProcessRunner : overlay d'environnement (PATH du shim) sans régression."""

from __future__ import annotations

import sys
from pathlib import Path

from conductor.process import SubprocessProcessRunner


def test_env_overlay_is_visible_to_child_process(tmp_path: Path) -> None:
    runner = SubprocessProcessRunner(env_overlay={"CONDUCTOR_SHIM_MARKER": "42"})
    res = runner.run(
        [sys.executable, "-c", "import os;print(os.environ.get('CONDUCTOR_SHIM_MARKER',''))"]
    )
    assert res.returncode == 0
    assert res.stdout.strip() == "42"


def test_no_overlay_inherits_current_env() -> None:
    # env_overlay=None → comportement historique : l'enfant hérite de l'environnement courant.
    runner = SubprocessProcessRunner()
    res = runner.run([sys.executable, "-c", "import os;print('PATH' in os.environ)"])
    assert res.stdout.strip() == "True"
