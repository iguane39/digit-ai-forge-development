"""Gate « Supabase côté serveur » (TF-2008) : trois défauts que la documentation Supabase nomme.

Pages lues le 29/10/2026 sur supabase.com :

- « Creating a Supabase client for SSR » : « *Never* trust `supabase.auth.getSession()` inside
  server code such as Proxy. It reads the session out of the cookie without revalidating it. »
  et « Always use `supabase.auth.getClaims()` to protect pages and user data » ; même page,
  « On Next.js 15 and earlier, a `proxy.ts` file is never called, so sessions never refresh and
  users get signed out » ;
- « Migrating to the SSR package from Auth Helpers » : `npm uninstall
  @supabase/auth-helpers-nextjs` (et `-sveltekit`, `-remix`), puis `npm install @supabase/ssr`.

Recette DOUBLE SENS : chaque constat a sa fixture rouge, et le remède que son message propose est
joué sur la même fixture et doit passer (TF-1013).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conductor.gates.supabase_ssr_gate import main, run_supabase_ssr_gate


def _projet(
    tmp_path: Path,
    *,
    dependances: dict[str, str] | None = None,
    fichiers: dict[str, str] | None = None,
) -> Path:
    racine = tmp_path / "projet"
    racine.mkdir()
    if dependances is not None:
        paquet = {"name": "app", "dependencies": dependances}
        (racine / "package.json").write_text(json.dumps(paquet), encoding="utf-8")
    for relatif, contenu in (fichiers or {}).items():
        chemin = racine / relatif
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(contenu, encoding="utf-8")
    return racine


_DEPS_SSR = {"next": "^16.0.0", "@supabase/supabase-js": "^2.0.0", "@supabase/ssr": "^0.7.0"}

_PROXY_GETCLAIMS = """import { createServerClient } from "@supabase/ssr";
export async function proxy(request) {
  const supabase = createServerClient(URL, KEY, { cookies: { getAll() {}, setAll() {} } });
  const { data } = await supabase.auth.getClaims();
  return data;
}
"""

_PAGE_SERVEUR_GETSESSION = """import { createClient } from "@/lib/supabase/server";
export default async function Page() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.user.email;
}
"""

_PAGE_CLIENT_GETSESSION = """'use client'
import { createClient } from "@/lib/supabase/client";
export default function Bouton() {
  const supabase = createClient();
  supabase.auth.getSession();
  return null;
}
"""


def _kinds(racine: Path) -> list[str]:
    return [f["kind"] for f in run_supabase_ssr_gate(racine).findings if "kind" in f]


# --- Sens vert et périmètre ---------------------------------------------------------------------


def test_sens_vert_projet_ssr_conforme(tmp_path: Path) -> None:
    racine = _projet(tmp_path, dependances=_DEPS_SSR, fichiers={"proxy.ts": _PROXY_GETCLAIMS})
    verdict = run_supabase_ssr_gate(racine)
    assert verdict.passed is True
    assert [f for f in verdict.findings if "kind" in f] == []


def test_sans_supabase_est_sans_objet(tmp_path: Path) -> None:
    racine = _projet(tmp_path, dependances={"next": "^16.0.0"})
    verdict = run_supabase_ssr_gate(racine)
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_sans_package_json_est_sans_objet(tmp_path: Path) -> None:
    verdict = run_supabase_ssr_gate(_projet(tmp_path))
    assert verdict.passed is True
    assert "package.json" in verdict.findings[0]["skipped"]


# --- 1. Paquet auth-helpers déprécié ------------------------------------------------------------


def test_rouge_auth_helpers_puis_remede(tmp_path: Path) -> None:
    deps = {"next": "^15.1.0", "@supabase/auth-helpers-nextjs": "^0.10.0"}
    racine = _projet(tmp_path, dependances=deps)
    verdict = run_supabase_ssr_gate(racine)
    constats = [f for f in verdict.findings if f.get("kind") == "auth-helpers-deprecie"]
    assert len(constats) == 1
    assert "@supabase/auth-helpers-nextjs" in constats[0]["issue"]
    assert main([str(racine)]) == 1
    # Remède proposé : remplacer le paquet par @supabase/ssr.
    paquet = {"name": "app", "dependencies": {"next": "^15.1.0", "@supabase/ssr": "^0.7.0"}}
    (racine / "package.json").write_text(json.dumps(paquet), encoding="utf-8")
    assert _kinds(racine) == []
    assert main([str(racine)]) == 0


def test_auth_helpers_en_dependance_de_developpement(tmp_path: Path) -> None:
    racine = _projet(tmp_path)
    paquet = {"name": "app", "devDependencies": {"@supabase/auth-helpers-sveltekit": "^0.13.0"}}
    (racine / "package.json").write_text(json.dumps(paquet), encoding="utf-8")
    assert _kinds(racine) == ["auth-helpers-deprecie"]


# --- 2. getSession() de confiance côté serveur --------------------------------------------------


def test_rouge_getsession_dans_un_composant_serveur_puis_remede(tmp_path: Path) -> None:
    racine = _projet(
        tmp_path, dependances=_DEPS_SSR, fichiers={"app/compte/page.tsx": _PAGE_SERVEUR_GETSESSION}
    )
    verdict = run_supabase_ssr_gate(racine)
    constats = [f for f in verdict.findings if f.get("kind") == "getsession-serveur"]
    assert len(constats) == 1
    assert constats[0]["ligne"] == "4"
    assert "getClaims" in constats[0]["issue"]
    # Remède proposé : getClaims() à la place de getSession().
    page = racine / "app" / "compte" / "page.tsx"
    page.write_text(
        _PAGE_SERVEUR_GETSESSION.replace("getSession()", "getClaims()"), encoding="utf-8"
    )
    assert _kinds(racine) == []


def test_getsession_dans_un_composant_client_nest_pas_un_constat(tmp_path: Path) -> None:
    racine = _projet(
        tmp_path, dependances=_DEPS_SSR, fichiers={"app/bouton.tsx": _PAGE_CLIENT_GETSESSION}
    )
    assert _kinds(racine) == []


def test_getsession_dans_les_fichiers_serveur_connus(tmp_path: Path) -> None:
    """Proxy, middleware, route API, fichiers SvelteKit `.server`, action `'use server'`."""
    appel = "const s = await supabase.auth.getSession();\n"
    fichiers = {
        "middleware.ts": appel,
        "src/pages/api/profil.ts": appel,
        "src/routes/compte/+page.server.ts": appel,
        "src/hooks.server.ts": appel,
        "lib/actions.ts": "'use server'\n" + appel,
        "lib/supabase/server.ts": appel,
    }
    racine = _projet(tmp_path, dependances=_DEPS_SSR, fichiers=fichiers)
    constats = [
        f for f in run_supabase_ssr_gate(racine).findings if f.get("kind") == "getsession-serveur"
    ]
    assert len(constats) == 6


def test_dossier_app_dune_application_vite_nest_pas_du_serveur(tmp_path: Path) -> None:
    """Sans `next` déclaré, `src/app/` est du code navigateur : getSession() y est permis."""
    deps = {"vite": "^7.0.0", "@supabase/supabase-js": "^2.0.0"}
    racine = _projet(
        tmp_path,
        dependances=deps,
        fichiers={"src/app/compte.tsx": "await supabase.auth.getSession();\n"},
    )
    assert _kinds(racine) == []
    # Le même fichier dans un projet Next.js est un composant serveur : constat.
    paquet = {"name": "app", "dependencies": {**deps, "next": "^16.0.0"}}
    (racine / "package.json").write_text(json.dumps(paquet), encoding="utf-8")
    assert _kinds(racine) == ["getsession-serveur"]


def test_getsession_hors_serveur_commentaire_et_tests_ignores(tmp_path: Path) -> None:
    fichiers = {
        "app/notes.tsx": "// ne jamais appeler supabase.auth.getSession() ici\nexport {}\n",
        "tests/auth.test.ts": "await supabase.auth.getSession();\n",
        "node_modules/x/app/page.tsx": "await supabase.auth.getSession();\n",
        "lib/client.ts": "await supabase.auth.getSession();\n",
    }
    racine = _projet(tmp_path, dependances=_DEPS_SSR, fichiers=fichiers)
    assert _kinds(racine) == []


def test_rouge_route_nommee_comme_un_dossier_ecarte(tmp_path: Path) -> None:
    """`app/test/page.tsx` est la route /test, pas un dossier de tests (revue du 29/10/2026)."""
    routes = ("test", "tests", "e2e", "build", "dist", "out", "coverage")
    fichiers = {f"app/{r}/page.tsx": "await supabase.auth.getSession();\n" for r in routes}
    fichiers["src/routes/test/+page.server.ts"] = "await supabase.auth.getSession();\n"
    racine = _projet(tmp_path, dependances=_DEPS_SSR, fichiers=fichiers)
    assert _kinds(racine) == ["getsession-serveur"] * 8


def test_dossiers_de_tests_et_de_build_restent_ecartes(tmp_path: Path) -> None:
    appel = "await supabase.auth.getSession();\n"
    fichiers = {
        "test/app/page.tsx": appel,
        "e2e/middleware.server.ts": appel,
        "src/tests/a.server.ts": appel,
        "dist/app/page.js": appel,
        "app/__tests__/page.tsx": appel,
        "app/test/page.test.tsx": appel,
        "app/node_modules/x/page.js": appel,
        "app/.next/page.js": appel,
    }
    racine = _projet(tmp_path, dependances=_DEPS_SSR, fichiers=fichiers)
    assert _kinds(racine) == []


def test_rouge_appel_ecrit_sur_plusieurs_lignes_puis_remede(tmp_path: Path) -> None:
    """Le fichier était retenu sur tout son texte, le constat cherché ligne par ligne : rien."""
    fichiers = {"app/page.tsx": "const s = await supabase\n  .auth\n  .getSession();\n"}
    racine = _projet(tmp_path, dependances=_DEPS_SSR, fichiers=fichiers)
    verdict = run_supabase_ssr_gate(racine)
    assert not verdict.passed
    assert [f["ligne"] for f in verdict.findings] == ["2"]
    (racine / "app/page.tsx").write_text(
        "const s = await supabase\n  .auth\n  .getClaims();\n", encoding="utf-8"
    )
    assert run_supabase_ssr_gate(racine).passed


def test_appel_multiligne_lignes_et_commentaires(tmp_path: Path) -> None:
    fichiers = {
        "app/a.tsx": "// await supabase\n//   .auth\n//   .getSession();\nexport {}\n",
        "app/b.tsx": "/*\n * await supabase.auth\n *   .getSession();\n */\nexport {}\n",
        "app/c.tsx": "a.auth.getSession(); b.auth.getSession();\n\nc\n.auth.getSession();\n",
    }
    racine = _projet(tmp_path, dependances=_DEPS_SSR, fichiers=fichiers)
    verdict = run_supabase_ssr_gate(racine)
    lignes = sorted((Path(f["file"]).name, f["ligne"]) for f in verdict.findings)
    assert lignes == [("c.tsx", "1"), ("c.tsx", "4")]


# --- 3. proxy.ts jamais appelé avant Next.js 16 -------------------------------------------------


def test_rouge_proxy_avant_next_16_puis_remede(tmp_path: Path) -> None:
    deps = {**_DEPS_SSR, "next": "^15.3.0"}
    racine = _projet(tmp_path, dependances=deps, fichiers={"src/proxy.ts": _PROXY_GETCLAIMS})
    verdict = run_supabase_ssr_gate(racine)
    constats = [f for f in verdict.findings if f.get("kind") == "proxy-jamais-appele"]
    assert len(constats) == 1
    assert "15" in constats[0]["issue"]
    # Remède proposé : renommer en middleware.ts (fonction middleware) tant que Next.js < 16.
    middleware = _PROXY_GETCLAIMS.replace("function proxy", "function middleware")
    (racine / "src" / "proxy.ts").unlink()
    (racine / "src" / "middleware.ts").write_text(middleware, encoding="utf-8")
    assert _kinds(racine) == []


def test_proxy_avec_next_16_est_appele(tmp_path: Path) -> None:
    racine = _projet(tmp_path, dependances=_DEPS_SSR, fichiers={"proxy.ts": _PROXY_GETCLAIMS})
    assert _kinds(racine) == []


def test_version_next_non_lisible_est_tracee(tmp_path: Path) -> None:
    deps = {**_DEPS_SSR, "next": "latest"}
    racine = _projet(tmp_path, dependances=deps, fichiers={"proxy.ts": _PROXY_GETCLAIMS})
    verdict = run_supabase_ssr_gate(racine)
    assert [f for f in verdict.findings if "kind" in f] == []
    assert any("next" in f.get("skipped", "") for f in verdict.findings)


# --- Verdict non jugé distinct du PASS (TF-2049, convention P-06) --------------------------------
# P-06 : matière illisible ou absente → SKIP tracé, jamais un échec implicite (README du conductor,
# « PASS, FAIL avec constats localisés, ou SKIP tracé » ; mutation_gate : stats illisibles → SKIP).
# Le défaut : le SKIP était tracé dans les constats, mais le CLI imprimait « PASS » et rien d'autre.


def _projet_package_json_invalide(tmp_path: Path) -> Path:
    racine = _projet(tmp_path, fichiers={"app/page.tsx": _PAGE_SERVEUR_GETSESSION})
    (racine / "package.json").write_text('{"dependencies": {"next": ', encoding="utf-8")
    return racine


def test_rouge_package_json_invalide_est_non_juge_pas_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    racine = _projet_package_json_invalide(tmp_path)
    verdict = run_supabase_ssr_gate(racine)
    assert verdict.passed is True  # P-06 : pas d'échec implicite
    assert "illisible" in verdict.findings[0]["skipped"]
    assert verdict.findings[0]["non_juge"] == "gate entier"
    assert main([str(racine)]) == 0
    sortie = capsys.readouterr().out
    assert sortie.startswith("supabase-ssr gate: SKIP")
    assert "PASS" not in sortie
    assert "illisible" in sortie


def test_remede_package_json_valide_rend_le_constat_getsession(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Le remède du SKIP — réparer le JSON — fait juger le même code, qui est refusé."""
    racine = _projet_package_json_invalide(tmp_path)
    paquet = {"dependencies": {"next": "^16.0.0", "@supabase/ssr": "^0.7.0"}}
    (racine / "package.json").write_text(json.dumps(paquet), encoding="utf-8")
    assert main([str(racine)]) == 1
    assert "getsession-serveur" in capsys.readouterr().err


def test_cli_sens_vert_dit_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    racine = _projet(tmp_path, dependances=_DEPS_SSR, fichiers={"proxy.ts": _PROXY_GETCLAIMS})
    assert main([str(racine)]) == 0
    assert capsys.readouterr().out.strip() == "supabase-ssr gate: PASS"


def test_cli_sans_objet_dit_skip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(_projet(tmp_path, dependances={"next": "^16.0.0"}))]) == 0
    sortie = capsys.readouterr().out
    assert sortie.startswith("supabase-ssr gate: SKIP")
    assert "SANS_OBJET" in sortie


def test_cli_controle_partiel_reste_pass_et_dit_ce_qui_manque(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Version de next illisible : les contrôles 1 et 2 ont jugé, le 3 non — PASS qui le dit."""
    deps = {"next": "latest", "@supabase/ssr": "^0.7.0"}
    racine = _projet(tmp_path, dependances=deps, fichiers={"proxy.ts": _PROXY_GETCLAIMS})
    assert main([str(racine)]) == 0
    sortie = capsys.readouterr().out
    assert sortie.startswith("supabase-ssr gate: PASS")
    assert "non jugé" in sortie
    assert "next" in sortie


# --- package.json valide mais non objet : verdict exact (TF-2059) ---------------------------
# Un `[]`, un `"x"`, un `42` ou `null` sont du JSON valide, pas un package.json. Le gate disait
# « aucune dépendance @supabase/ » : un motif approximatif, qui laissait croire qu'un objet
# avait été lu et trouvé sans dépendance. Le verdict exact nomme la forme reçue.


@pytest.mark.parametrize(
    ("contenu", "nom_type"),
    [("[]", "liste"), ('"x"', "chaîne"), ("42", "nombre"), ("null", "null"), ("true", "booléen")],
)
def test_rouge_package_json_non_objet_est_non_juge_et_le_dit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], contenu: str, nom_type: str
) -> None:
    racine = _projet(tmp_path, fichiers={"app/page.tsx": _PAGE_SERVEUR_GETSESSION})
    (racine / "package.json").write_text(contenu, encoding="utf-8")
    verdict = run_supabase_ssr_gate(racine)
    assert verdict.passed is True  # P-06 : pas d'échec implicite
    constat = verdict.findings[0]
    assert constat["non_juge"] == "gate entier"
    assert "n'est pas un objet JSON" in constat["skipped"]
    assert nom_type in constat["skipped"]
    assert "@supabase/" not in constat["skipped"]  # plus le motif « aucune dépendance »
    assert main([str(racine)]) == 0
    sortie = capsys.readouterr().out
    assert sortie.startswith("supabase-ssr gate: SKIP")
    assert "n'est pas un objet JSON" in sortie


def test_remede_package_json_objet_rend_le_constat_getsession(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Le remède du SKIP — un vrai objet — fait juger le même code, qui est refusé."""
    racine = _projet(tmp_path, fichiers={"app/page.tsx": _PAGE_SERVEUR_GETSESSION})
    (racine / "package.json").write_text("[]", encoding="utf-8")
    assert main([str(racine)]) == 0
    capsys.readouterr()
    paquet = {"dependencies": {"next": "^16.0.0", "@supabase/ssr": "^0.7.0"}}
    (racine / "package.json").write_text(json.dumps(paquet), encoding="utf-8")
    assert main([str(racine)]) == 1
    assert "getsession-serveur" in capsys.readouterr().err


def test_objet_sans_dependance_supabase_garde_son_motif(tmp_path: Path) -> None:
    """Un objet réel sans @supabase/ reste SANS_OBJET avec son motif d'origine."""
    verdict = run_supabase_ssr_gate(_projet(tmp_path, dependances={"next": "^16.0.0"}))
    assert "aucune dépendance @supabase/" in verdict.findings[0]["skipped"]


def test_cli_usage_rend_2(tmp_path: Path) -> None:
    assert main([]) == 2
    assert main([str(tmp_path), "de trop"]) == 2
