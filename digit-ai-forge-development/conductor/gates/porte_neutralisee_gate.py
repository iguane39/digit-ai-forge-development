"""Gate porte neutralisée (TF-1040, 14/09/2026) — la doctrine devient oracle exécutable.

Convention documentée dans `../../docs/run-playbook.md` § « Produit livrable — disciplines de
production » : un contrôle qualifié de PORTE (son échec bloque un déploiement ou un merge) n'en
est une que si la chaîne peut réellement l'entendre dire non. Un contrôle dont le code de sortie
est NEUTRALISÉ dans le fichier de chaîne (``|| true``, ``continue-on-error: true``, ``|| exit 0``
accolé à une commande de lint/test/check/build) n'est plus une porte, quelle que soit sa preuve
passée d'avoir déjà échoué : la chaîne a été rendue sourde à son verdict.

MESURE FONDATRICE (Produit-11, RT-59, 11/09/2026) : six contrôles qualifiés de « porte » dans la
chaîne d'un produit tiers étaient VERTS PAR CONSTRUCTION — aucune fixture rouge, rien qui les
force jamais à échouer. La présence d'un contrôle avait été prise pour sa fiabilité.

Contrôle STATIQUE (coïncidence de chaîne, même posture que ``demo_markers_gate``) : il relève
CHAQUE ligne d'un fichier de chaîne CI qui neutralise le code de sortie d'une commande dont
l'intitulé porte un mot de contrôle (lint/test/check/gate/ruff/mypy/pytest). Il ne juge PAS
l'absence de preuve « vue rouge » elle-même — un fait humain daté, hors périmètre d'un gate
statique (cf. limites déclarées au playbook).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from conductor.contracts import GateVerdict

# Un mot de contrôle sur la ligne (ou son nom de step au-dessus) rend l'accusation sûre : on ne
# signale pas la neutralisation d'une commande qui n'a rien d'un contrôle de qualité.
_MOT_CONTROLE = re.compile(
    r"\blint\b|\btest\b|\bcheck\b|\bgate\b|\bruff\b|\bmypy\b|\bpytest\b", re.IGNORECASE
)
# `|| true`, `|| exit 0` : neutralisation en shell. `continue-on-error: true` : neutralisation
# déclarative GitHub Actions/Azure Pipelines.
_NEUTRALISATION = re.compile(
    r"\|\|\s*(true\b|exit\s+0\b)|continue-on-error\s*:\s*true", re.IGNORECASE
)

_WORKFLOWS_GLOBS = ("*.yml", "*.yaml")


def _fichiers_de_chaine(racine: Path) -> list[Path]:
    dossier = racine / ".github" / "workflows"
    if not dossier.exists():
        return []
    fichiers: list[Path] = []
    for motif in _WORKFLOWS_GLOBS:
        fichiers.extend(sorted(dossier.glob(motif)))
    return fichiers


def relever_controles_neutralises(racine: Path) -> list[dict[str, str]]:
    """Une ligne par neutralisation trouvée, sur une commande dont l'intitulé nomme un contrôle."""
    findings: list[dict[str, str]] = []
    for fichier in _fichiers_de_chaine(racine):
        lignes = fichier.read_text(encoding="utf-8", errors="ignore").splitlines()
        for i, ligne in enumerate(lignes, start=1):
            if not _NEUTRALISATION.search(ligne):
                continue
            # Le mot de contrôle peut être sur la ligne elle-même (`run: ruff check . || true`)
            # ou juste au-dessus (`name: Ruff (lint)` / `- name: Pytest`, cf. double-gate.yml) —
            # une fenêtre de 2 lignes avant suffit à cette convention, sans sur-généraliser.
            contexte = "\n".join(lignes[max(0, i - 3) : i])
            if not _MOT_CONTROLE.search(contexte):
                continue
            findings.append(
                {
                    "file": str(fichier),
                    "ligne": str(i),
                    "issue": f"neutralise le code de sortie d'un contrôle : « {ligne.strip()} »",
                }
            )
    return findings


def run_porte_neutralisee_gate(racine: Path) -> GateVerdict:
    """P-06 : aucune arborescence de chaîne CI → SKIP tracé, jamais un échec implicite."""
    if not racine.exists():
        return GateVerdict(
            gate="porte-neutralisee",
            passed=True,
            findings=[{"skipped": f"racine absente : {racine}"}],
        )
    if not _fichiers_de_chaine(racine):
        return GateVerdict(
            gate="porte-neutralisee",
            passed=True,
            findings=[{"skipped": "aucun fichier de chaîne CI (.github/workflows/*.yml)"}],
        )
    findings = relever_controles_neutralises(racine)
    return GateVerdict(
        gate="porte-neutralisee", passed=not findings, findings=findings, log_ref=str(racine)
    )


def main(argv: list[str] | None = None) -> int:
    """Entrée CLI : ``python -m conductor.gates.porte_neutralisee_gate <racine>``."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m conductor.gates.porte_neutralisee_gate <racine>", file=sys.stderr)
        return 2
    verdict = run_porte_neutralisee_gate(Path(args[0]))
    if verdict.passed:
        print("porte-neutralisee gate: PASS")
        return 0
    blocking = [f for f in verdict.findings if "skipped" not in f]
    print(f"porte-neutralisee gate: FAIL ({len(blocking)} contrôle(s) neutralisé(s))",
          file=sys.stderr)
    for f in blocking:
        print(f"  - [{f['file']}:{f['ligne']}] {f['issue']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
