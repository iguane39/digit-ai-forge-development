"""Gate « statique versionné » (TF-0798) — la huitième discipline devient oracle exécutable.

Convention documentée dans `../../docs/run-playbook.md` § « Produit livrable — disciplines de
production » : **toute adresse de fichier statique porte la version de l'application ou une
empreinte de contenu**, et le projet déclare un `Cache-Control` cohérent (long pour l'empreinté,
court pour le HTML). Un statique servi NU rend une mise en production invisible : le serveur
répond 200 sur un fichier à jour pendant que le poste rend la version d'avant, et deux fichiers
n'expirent pas au même instant — script neuf + feuille vieille = fonctionnalité qui marche et
s'affiche cassée.

Contrôle STATIQUE, même posture heuristique que ``demo_markers_gate`` et
``ai_antipatterns_gate`` (coïncidence de chaîne, aucune exécution, aucun réseau) : le gate lit
les gabarits de rendu du projet et juge les adresses qu'ils écrivent LITTÉRALEMENT.

Trois classes de constat :

1. **statique-nu** — une adresse locale de `.css` / `.js` / `.mjs` sans marqueur de version
   (`?v=…`) ni empreinte dans le nom de fichier. C'est le défaut mesuré le 01/09/2026.
2. **cache-control-absent** — le projet sert des statiques et ne déclare `Cache-Control` nulle
   part : rien ne borne l'heuristique du navigateur, la fraîcheur est laissée au hasard.
3. **cache-control-html-long** — une durée de cache longue (``max-age`` ≥ 1 jour, ou
   ``immutable``) déclarée sur du HTML : le document qui porte les adresses versionnées est
   lui-même figé, donc la nouvelle version n'est jamais découverte. L'empreinté se met en cache
   longtemps parce que son NOM change ; le HTML jamais, parce que son nom ne change pas.

**Mécanisme retenu par la forge (le lot laisse le choix, TF-0798)** : `?v=<version_app>` est le
défaut, l'empreinte de contenu est ACCEPTÉE À ÉGALITÉ. Motif : le versionnement par requête ne
demande ni chaîne de construction, ni manifeste, ni réécriture de noms — un global de gabarits
suffit, et il couvre les pages rendues côté serveur, qui sont précisément celles qu'aucun
bundler n'empreinte. Refuser l'empreinte serait faux dans l'autre sens : la sortie d'un bundler
(Vite, webpack) est déjà empreintée, et la forcer à porter en plus un `?v=` serait du bruit. Le
gate juge donc la PROPRIÉTÉ — « cette adresse change quand le contenu change » — pas la forme.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from conductor.contracts import GateVerdict

# Gabarits de rendu inspectés (le HTML servi, quelle que soit la couche qui l'écrit).
_MARKUP_SUFFIXES = (".html", ".htm", ".jinja", ".jinja2", ".j2")

# Fichiers où un `Cache-Control` RÉEL peut être déclaré (code serveur, CDN, reverse proxy,
# infrastructure). Les gabarits de rendu sont volontairement exclus : un
# `<meta http-equiv="Cache-Control">` est ignoré par les navigateurs — l'accepter fabriquerait
# un PASS sur une déclaration sans effet.
_CONFIG_SUFFIXES = (
    ".py", ".ts", ".tsx", ".js", ".mjs", ".conf", ".yml", ".yaml", ".toml",
    ".json", ".tf", ".ini", ".nginx", ".cs", ".go", ".rb", ".php",
)
_CONFIG_FILENAMES = ("_headers", "web.config", "Caddyfile", ".htaccess")

# Hors périmètre : suites de tests, dépendances tierces, environnements virtuels.
_EXCLUDED_PARTS = ("test", "tests", "node_modules", ".venv", "venv", "vendor", ".git")

# Une adresse d'attribut pointant un fichier statique. Le lookahead évite d'attraper `.json`
# (« .js » suivi d'un caractère alphanumérique n'est pas une extension de script).
_STATIC_REF = re.compile(
    r"(?:href|src)\s*=\s*(?P<q>[\"'])"
    r"(?P<value>[^\"']*?\.(?:css|js|mjs)(?![A-Za-z0-9])[^\"']*)"
    r"(?P=q)",
    re.IGNORECASE,
)

# Un marqueur de version dans la requête : `?v=…`, `?ver=…`, `?version=…`, `?h=…`, `?hash=…`.
# La valeur peut être une expression de gabarit (`{{ version_app }}`) : c'est le cas nominal.
_VERSION_QUERY = re.compile(r"[?&](?:v|ver|version|h|hash|rev)=(?P<val>[^&]+)", re.IGNORECASE)

# Une empreinte dans le nom : segment ≥ 8 caractères, soit hexadécimal, soit alphanumérique
# mêlant chiffre et majuscule (sorties Vite/webpack/esbuild). `app.min.css` (trop court) et
# `app.production.css` (aucun chiffre) ne sont donc PAS pris pour des empreintes.
_FINGERPRINT = re.compile(
    r"[.\-_](?:"
    r"[0-9a-fA-F]{8,}"
    r"|(?=[A-Za-z0-9_-]*[0-9])(?=[A-Za-z0-9_-]*[A-Z])[A-Za-z0-9_-]{8,}"
    r")\.(?:css|js|mjs)$"
)

_CACHE_CONTROL = re.compile(r"Cache-Control", re.IGNORECASE)
_MAX_AGE = re.compile(r"max-age\s*=\s*(?P<sec>\d+)", re.IGNORECASE)
_HTML_MARKER = re.compile(r"text/html|\.html?\b|index\.html", re.IGNORECASE)

#: Au-delà d'un jour, une durée de cache n'est plus « courte » : le HTML qui porte les adresses
#: versionnées doit rester découvrable, sinon le versionnement en amont ne sert à rien.
SEUIL_MAX_AGE_HTML = 86_400


def _is_excluded(path: Path) -> bool:
    return any(part.lower() in _EXCLUDED_PARTS for part in path.parts)


def _is_external(value: str) -> bool:
    """Adresse hors du produit (CDN, autre origine) : sa fraîcheur ne lui appartient pas."""
    lowered = value.strip().lower()
    return lowered.startswith(("http://", "https://", "//", "data:", "blob:"))


def est_versionnee(value: str) -> bool:
    """Vrai si l'adresse change quand le contenu change — par requête OU par empreinte."""
    match = _VERSION_QUERY.search(value)
    if match is not None and match.group("val").strip():
        return True
    chemin = value.split("?", 1)[0].split("#", 1)[0]
    return _FINGERPRINT.search(chemin.rsplit("/", 1)[-1]) is not None


def check_adresses_statiques(project_dir: Path) -> tuple[list[dict[str, str]], int]:
    """Constats `statique-nu` + nombre total d'adresses statiques locales rencontrées."""
    findings: list[dict[str, str]] = []
    total = 0
    for path in sorted(project_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _MARKUP_SUFFIXES:
            continue
        if _is_excluded(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in _STATIC_REF.finditer(text):
            value = match.group("value")
            if _is_external(value):
                continue
            total += 1
            if est_versionnee(value):
                continue
            findings.append(
                {
                    "file": str(path),
                    "kind": "statique-nu",
                    "issue": f"adresse '{value}' sans version ni empreinte",
                }
            )
    return findings, total


def check_cache_control(project_dir: Path, *, statiques_presents: bool) -> list[dict[str, str]]:
    """Constats `cache-control-absent` et `cache-control-html-long`."""
    findings: list[dict[str, str]] = []
    declare = False
    for path in sorted(project_dir.rglob("*")):
        if not path.is_file() or _is_excluded(path):
            continue
        if path.suffix.lower() not in _CONFIG_SUFFIXES and path.name not in _CONFIG_FILENAMES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for ligne in text.splitlines():
            if not _CACHE_CONTROL.search(ligne):
                continue
            declare = True
            if not _HTML_MARKER.search(ligne):
                continue
            age = _MAX_AGE.search(ligne)
            trop_long = (age is not None and int(age.group("sec")) >= SEUIL_MAX_AGE_HTML) or (
                "immutable" in ligne.lower()
            )
            if trop_long:
                findings.append(
                    {
                        "file": str(path),
                        "kind": "cache-control-html-long",
                        "issue": f"cache long déclaré sur du HTML : {ligne.strip()[:120]}",
                    }
                )
    if statiques_presents and not declare:
        findings.append(
            {
                "file": str(project_dir),
                "kind": "cache-control-absent",
                "issue": "des statiques sont servis et aucun Cache-Control n'est déclaré",
            }
        )
    return findings


def run_static_cache_gate(project_dir: Path) -> GateVerdict:
    """P-06 : arborescence absente → SKIP tracé, jamais un échec implicite.

    Un projet SANS gabarit de rendu et sans adresse statique locale rend un SKIP tracé lui
    aussi : il n'y a rien à juger, et un PASS muet se lirait comme une mesure.
    """
    if not project_dir.exists():
        return GateVerdict(
            gate="static-cache",
            passed=True,
            findings=[{"skipped": f"arborescence projet absente : {project_dir}"}],
        )
    findings, total = check_adresses_statiques(project_dir)
    if total == 0:
        return GateVerdict(
            gate="static-cache",
            passed=True,
            findings=[{"skipped": "aucune adresse de statique locale dans les gabarits de rendu"}],
            log_ref=str(project_dir),
        )
    findings += check_cache_control(project_dir, statiques_presents=True)
    blocking = [f for f in findings if "skipped" not in f]
    return GateVerdict(
        gate="static-cache", passed=not blocking, findings=findings, log_ref=str(project_dir)
    )


def main(argv: list[str] | None = None) -> int:
    """Entrée CLI : ``python -m conductor.gates.static_cache_gate <project_dir>``."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m conductor.gates.static_cache_gate <project_dir>", file=sys.stderr)
        return 2
    verdict = run_static_cache_gate(Path(args[0]))
    if verdict.passed:
        print("static-cache gate: PASS")
        return 0
    blocking = [f for f in verdict.findings if "skipped" not in f]
    print(f"static-cache gate: FAIL ({len(blocking)} constat(s))", file=sys.stderr)
    for f in blocking:
        print(f"  - [{f['kind']}] {f['file']} : {f['issue']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
