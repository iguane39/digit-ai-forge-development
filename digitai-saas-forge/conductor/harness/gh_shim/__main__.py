"""Point d'entrée exécutable du shim : `python -m conductor.harness.gh_shim <args gh>`.

Invoqué par les lanceurs ``gh``/``gh.cmd`` placés en tête de PATH (cf. ``install.py``). Construit
le backend ``az`` réel sur le répertoire courant (le dépôt cible où BAD opère), délègue à
``translate`` et émet stdout/stderr/code exactement comme l'aurait fait ``gh``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from conductor.harness.gh_shim.backend import SubprocessAzBackend
from conductor.harness.gh_shim.translate import translate


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:]) if argv is None else list(argv)
    result = translate(args, SubprocessAzBackend(Path.cwd()))
    if result.stdout:
        sys.stdout.write(result.stdout if result.stdout.endswith("\n") else result.stdout + "\n")
    if result.stderr:
        sys.stderr.write(result.stderr if result.stderr.endswith("\n") else result.stderr + "\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
