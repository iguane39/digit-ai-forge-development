"""Gate « Supabase côté serveur » (TF-2008, étude du pilot du 28/10/2026, ligne S6) — trois
défauts que la documentation Supabase nomme elle-même, dans un projet JavaScript qui rend des
pages côté serveur avec Supabase Auth.

LE FAIT. Le 28/10/2026, aucune forge ne citait ``@supabase/ssr`` (``git grep``, 0 fichier hors des
cinq surfaces Supabase du 16/10). Or la documentation lue le 29/10/2026 désigne trois pièges qui
ne se voient qu'en service : une session lue sans vérification dans du code serveur, un paquet
remplacé, et un fichier ``proxy.ts`` que Next.js ignore avant sa version 16.

1. **auth-helpers-deprecie** — ``package.json`` (racine) déclare un paquet
   ``@supabase/auth-helpers-*``. La page « Migrating to the SSR package from Auth Helpers » fait
   désinstaller ``@supabase/auth-helpers-nextjs``, ``-sveltekit`` et ``-remix`` et installer
   ``@supabase/ssr``.
2. **getsession-serveur** — un appel ``.auth.getSession(`` dans du code serveur. Page « Creating a
   Supabase client for SSR » : « *Never* trust ``supabase.auth.getSession()`` inside server code
   such as Proxy. It reads the session out of the cookie without revalidating it. » et « Always
   use ``supabase.auth.getClaims()`` to protect pages and user data ». Code serveur, au sens de ce
   gate : ``proxy`` et ``middleware`` (racine ou ``src/``), les fichiers ``*.server.*`` et
   ``+server.*``, tout fichier qui s'ouvre sur ``'use server'``, un ``server.*`` rangé dans un
   dossier ``supabase`` et, dans un projet qui déclare ``next`` seulement, ``pages/api/`` et tout
   fichier sous ``app/`` qui ne s'ouvre pas sur ``'use client'`` (composants serveur,
   gestionnaires de route, actions).
3. **proxy-jamais-appele** — un ``proxy.ts`` (ou ``.js``) sans ``middleware`` à côté, dans un
   projet qui déclare Next.js avant 16. Même page : « On Next.js 15 and earlier, a ``proxy.ts``
   file is never called, so sessions never refresh and users get signed out. »

Contrôle STATIQUE, même posture que ``static_cache_gate`` et ``runtime_parity_gate`` : coïncidence
de chaîne, aucune exécution, aucun réseau. SANS_OBJET tracé sans ``package.json`` ou sans
dépendance ``@supabase/``. Limites v0 : un appel construit autrement que ``.auth.getSession(``
(alias, déstructuration de ``auth``) échappe au contrôle 2 ; une ligne de commentaire est ignorée,
un commentaire en fin de ligne de code ne l'est pas ; un fichier de test rangé sous ``app/``, hors
``*.test.*`` et ``__tests__``, est lu comme du code ; une version de Next.js écrite en intervalle
(``>=15 <17``) ou en étiquette (``latest``) n'est pas lue, le contrôle 3 le trace. La page « Server-
Side Rendering » dit ``@supabase/ssr`` « currently in beta » : le gate prescrit le remplaçant que
Supabase désigne, sans juger sa maturité.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from conductor.contracts import GateVerdict

_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
_EXCLUS = {"node_modules", ".next", ".svelte-kit", ".git", ".venv", "__tests__"}
# Sous un dossier de routes, ces noms sont des segments d'URL : `app/test/page.tsx` sert /test.
_EXCLUS_HORS_ROUTES = {"dist", "build", "out", "coverage", "tests", "test", "e2e"}
_RACINES_DE_ROUTES = {"app", "pages", "routes"}
_FICHIER_TEST = re.compile(r"\.(?:test|spec)\.[cm]?[jt]sx?$")
_GETSESSION = re.compile(r"\.auth\s*\.\s*getSession\s*\(")
_DIRECTIVE = re.compile(
    r"""^\s*(?:(?://[^\n]*|/\*.*?\*/)\s*)*["'](use client|use server)["']""", re.S
)
_MAJEURE = re.compile(r"^[\^~=v]?\s*(\d+)(?:\.[\dx*]+)*(?:-[\w.]+)?$")


def _dependances(paquet: dict[str, Any]) -> dict[str, str]:
    deps: dict[str, str] = {}
    for cle in ("dependencies", "devDependencies"):
        section = paquet.get(cle)
        if isinstance(section, dict):
            deps.update({str(k): str(v) for k, v in section.items()})
    return deps


def check_auth_helpers(package_json: Path, deps: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "kind": "auth-helpers-deprecie",
            "file": str(package_json),
            "issue": f"paquet '{nom}' déclaré — Supabase le fait désinstaller au profit de "
            "@supabase/ssr (page « Migrating to the SSR package from Auth Helpers », lue le "
            "29/10/2026) ; remplacer le paquet par @supabase/ssr",
        }
        for nom in sorted(deps)
        if nom.startswith("@supabase/auth-helpers-")
    ]


def _directive(texte: str) -> str | None:
    m = _DIRECTIVE.match(texte)
    return m.group(1) if m else None


def _est_serveur(relatif: Path, texte: str, *, next_js: bool) -> bool:
    """Les dossiers `app/` et `pages/api/` ne sont du code serveur que dans un projet Next.js :
    une application Vite peut ranger son code navigateur sous `src/app/`."""
    parties = relatif.parts
    nom = relatif.name
    racine_ou_src = len(parties) == 1 or (len(parties) == 2 and parties[0] == "src")
    directive = _directive(texte)
    if directive == "use server":
        return True
    if racine_ou_src and relatif.stem in ("proxy", "middleware"):
        return True
    if ".server." in nom or relatif.stem == "+server":
        return True
    if relatif.stem == "server" and len(parties) >= 2 and parties[-2] == "supabase":
        return True
    if not next_js:
        return False
    sous_src = parties[1:] if parties[:1] == ("src",) else parties
    if sous_src[:1] == ("app",):
        return directive != "use client"
    return sous_src[:2] == ("pages", "api")


def _exclu(relatif: Path) -> bool:
    parties = relatif.parts
    if _EXCLUS.intersection(parties):
        return True
    sous_src = parties[1:] if parties[:1] == ("src",) else parties
    if _RACINES_DE_ROUTES.intersection(sous_src[:1]):
        return False
    return bool(_EXCLUS_HORS_ROUTES.intersection(parties))


def _sources(project_dir: Path) -> list[Path]:
    fichiers: list[Path] = []
    for chemin in sorted(project_dir.rglob("*")):
        relatif = chemin.relative_to(project_dir)
        if _exclu(relatif) or chemin.suffix not in _EXTENSIONS:
            continue
        if chemin.is_file() and not _FICHIER_TEST.search(chemin.name):
            fichiers.append(chemin)
    return fichiers


def check_getsession_serveur(project_dir: Path, deps: dict[str, str]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for chemin in _sources(project_dir):
        texte = chemin.read_text(encoding="utf-8", errors="ignore")
        if not _GETSESSION.search(texte):
            continue
        if not _est_serveur(chemin.relative_to(project_dir), texte, next_js="next" in deps):
            continue
        # Le constat se cherche sur tout le texte : un appel chaîné s'écrit sur plusieurs lignes.
        lignes: set[int] = set()
        for appel in _GETSESSION.finditer(texte):
            debut = texte.rfind("\n", 0, appel.start()) + 1
            if not texte[debut : appel.start()].lstrip().startswith(("//", "/*", "*")):
                lignes.add(texte.count("\n", 0, appel.start()) + 1)
        for numero in sorted(lignes):
            findings.append(
                {
                    "kind": "getsession-serveur",
                    "file": str(chemin),
                    "ligne": str(numero),
                    "issue": "auth.getSession() dans du code serveur : « It reads the session "
                    "out of the cookie without revalidating it », et un cookie se forge (page "
                    "« Creating a Supabase client for SSR », lue le 29/10/2026) — appeler "
                    "supabase.auth.getClaims(), qui vérifie la signature du jeton",
                }
            )
    return findings


def _majeure(spec: str) -> int | None:
    m = _MAJEURE.match(spec.strip())
    return int(m.group(1)) if m else None


def check_proxy(project_dir: Path, deps: dict[str, str]) -> list[dict[str, str]]:
    proxys = [
        project_dir / d / f"proxy{ext}"
        for d in ("", "src")
        for ext in (".ts", ".js", ".mjs")
        if (project_dir / d / f"proxy{ext}").is_file()
    ]
    if not proxys or "next" not in deps:
        return []
    middleware = any(
        (project_dir / d / f"middleware{ext}").is_file()
        for d in ("", "src")
        for ext in (".ts", ".js", ".mjs")
    )
    if middleware:
        return []
    majeure = _majeure(deps["next"])
    if majeure is None:
        return [
            {
                "skipped": f"version de next non lisible ('{deps['next']}') — le contrôle du "
                "proxy (Next.js 16 et plus) n'est pas jugé"
            }
        ]
    if majeure >= 16:
        return []
    return [
        {
            "kind": "proxy-jamais-appele",
            "file": str(chemin),
            "issue": f"proxy sans middleware et next déclaré en {deps['next']} (majeure "
            f"{majeure}) : « On Next.js 15 and earlier, a proxy.ts file is never called, so "
            "sessions never refresh and users get signed out » (page « Creating a Supabase "
            "client for SSR », lue le 29/10/2026) — renommer en middleware.ts avec "
            "`export async function middleware`, ou passer à Next.js 16",
        }
        for chemin in proxys
    ]


def run_supabase_ssr_gate(project_dir: Path) -> GateVerdict:
    """P-06 : sans ``package.json`` ou sans dépendance ``@supabase/`` → SKIP tracé (SANS_OBJET)."""
    package_json = project_dir / "package.json"
    if not package_json.is_file():
        return GateVerdict(
            gate="supabase-ssr",
            passed=True,
            findings=[{"skipped": "aucun package.json à la racine du projet (SANS_OBJET)"}],
            log_ref=str(project_dir),
        )
    try:
        paquet: Any = json.loads(package_json.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError as exc:
        return GateVerdict(
            gate="supabase-ssr",
            passed=True,
            findings=[{"skipped": f"package.json illisible : {exc}"}],
            log_ref=str(project_dir),
        )
    deps = _dependances(paquet) if isinstance(paquet, dict) else {}
    if not any(nom.startswith("@supabase/") for nom in deps):
        return GateVerdict(
            gate="supabase-ssr",
            passed=True,
            findings=[{"skipped": "aucune dépendance @supabase/ dans package.json (SANS_OBJET)"}],
            log_ref=str(project_dir),
        )
    findings = (
        check_auth_helpers(package_json, deps)
        + check_getsession_serveur(project_dir, deps)
        + check_proxy(project_dir, deps)
    )
    blocking = [f for f in findings if "skipped" not in f]
    return GateVerdict(
        gate="supabase-ssr", passed=not blocking, findings=findings, log_ref=str(project_dir)
    )


def main(argv: list[str] | None = None) -> int:
    """Entrée CLI : ``python -m conductor.gates.supabase_ssr_gate <project_dir>``."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m conductor.gates.supabase_ssr_gate <project_dir>", file=sys.stderr)
        return 2
    verdict = run_supabase_ssr_gate(Path(args[0]))
    if verdict.passed:
        print("supabase-ssr gate: PASS")
        return 0
    blocking = [f for f in verdict.findings if "skipped" not in f]
    print(f"supabase-ssr gate: FAIL ({len(blocking)} constat(s))", file=sys.stderr)
    for f in blocking:
        loc = f.get("ligne")
        localisation = f"{f['file']}:{loc}" if loc else f["file"]
        print(f"  - [{f['kind']}] {localisation} : {f['issue']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
