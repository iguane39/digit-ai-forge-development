"""Export de tokens design — charte → code, sans ressaisie (décision 08).

Délègue à `design.md export` (formats `css-tailwind` et `dtcg`). Le conductor ne génère
pas les tokens : il invoque l'outil épinglé via un runner injectable (subprocess en prod,
fake en test).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal, Protocol

from conductor.gates.design_gate import DESIGN_MD_PKG

ExportFormat = Literal["css-tailwind", "dtcg"]

# Extension de sortie par format.
_SUFFIX: dict[ExportFormat, str] = {"css-tailwind": "theme.css", "dtcg": "tokens.json"}


class ExportRunner(Protocol):
    """Exécute l'export et renvoie (code de sortie, contenu stdout)."""

    def export(self, design_md: Path, fmt: ExportFormat) -> tuple[int, str]: ...


class NpxExportRunner:
    def export(self, design_md: Path, fmt: ExportFormat) -> tuple[int, str]:
        cmd = [
            "npx", "--yes", "-p", DESIGN_MD_PKG,
            "designmd", "export", "--format", fmt, str(design_md),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout


def export_tokens(
    design_md: Path,
    fmt: ExportFormat,
    out_dir: Path,
    *,
    runner: ExportRunner | None = None,
) -> Path:
    """Exporte les tokens du DESIGN.md vers out_dir et renvoie le chemin écrit.

    Lève RuntimeError si l'export échoue (code != 0 ou sortie vide).
    """
    rc, content = (runner or NpxExportRunner()).export(design_md, fmt)
    if rc != 0 or not content.strip():
        raise RuntimeError(f"Export '{fmt}' a échoué (code {rc}) pour {design_md}")
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / _SUFFIX[fmt]
    dest.write_text(content, encoding="utf-8")
    return dest
