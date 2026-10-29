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


def test_getsession_hors_serveur_commentaire_et_tests_ignores(tmp_path: Path) -> None:
    fichiers = {
        "app/notes.tsx": "// ne jamais appeler supabase.auth.getSession() ici\nexport {}\n",
        "tests/auth.test.ts": "await supabase.auth.getSession();\n",
        "node_modules/x/app/page.tsx": "await supabase.auth.getSession();\n",
        "lib/client.ts": "await supabase.auth.getSession();\n",
    }
    racine = _projet(tmp_path, dependances=_DEPS_SSR, fichiers=fichiers)
    assert _kinds(racine) == []


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


def test_cli_usage_rend_2(tmp_path: Path) -> None:
    assert main([]) == 2
    assert main([str(tmp_path), "de trop"]) == 2
