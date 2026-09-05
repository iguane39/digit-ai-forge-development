"""Gate « statique versionné » (TF-0798) : oracle exécutable de la huitième discipline.

Recette DOUBLE SENS, au sens strict du lot : le MÊME projet instancié est joué deux fois —
une fois avec ses statiques servis NUS (constat rendu, exit 1), une fois après versionnement
(PASS, exit 0). Sans le sens rouge, un gate qui ne trouve jamais rien est indiscernable d'un
gate qui ne regarde rien.
"""

from __future__ import annotations

from pathlib import Path

from conductor.gates.static_cache_gate import est_versionnee, main, run_static_cache_gate

_GABARIT_NU = """<!doctype html>
<html><head>
  <link rel="stylesheet" href="/static/tokens.css">
  <link rel="stylesheet" href="/static/app.css">
  <script src="/static/app.js"></script>
</head><body></body></html>
"""

_GABARIT_VERSIONNE = """<!doctype html>
<html><head>
  <link rel="stylesheet" href="/static/tokens.css?v={{ version_app }}">
  <link rel="stylesheet" href="/static/app.css?v={{ version_app }}">
  <script src="/static/app.js?v={{ version_app }}"></script>
</head><body></body></html>
"""

_SERVEUR_AVEC_CACHE = (
    'STATIC_HEADERS = {"Cache-Control": "public, max-age=31536000, immutable"}\n'
    'HTML_HEADERS = {"Cache-Control": "no-cache"}  # text/html : jamais figé\n'
)


def _projet(tmp_path: Path, gabarit: str, *, serveur: str = _SERVEUR_AVEC_CACHE) -> Path:
    """Un projet instancié minimal : un gabarit de rendu + une couche serveur."""
    racine = tmp_path / "projet"
    (racine / "app" / "templates").mkdir(parents=True)
    (racine / "app" / "templates" / "base.html").write_text(gabarit, encoding="utf-8")
    (racine / "app" / "main.py").write_text(serveur, encoding="utf-8")
    return racine


# --- Recette double sens ------------------------------------------------------


def test_sens_rouge_statique_nu_est_refuse(tmp_path: Path) -> None:
    """Fixture ROUGE : trois statiques servis nus → trois constats, gate refusé."""
    racine = _projet(tmp_path, _GABARIT_NU)
    verdict = run_static_cache_gate(racine)
    assert verdict.passed is False
    nus = [f for f in verdict.findings if f["kind"] == "statique-nu"]
    assert len(nus) == 3
    assert {f["issue"].split("'")[1] for f in nus} == {
        "/static/tokens.css",
        "/static/app.css",
        "/static/app.js",
    }


def test_sens_vert_statique_versionne_passe(tmp_path: Path) -> None:
    """Fixture VERTE : le MÊME projet, `?v={{ version_app }}` posé → PASS, zéro constat."""
    racine = _projet(tmp_path, _GABARIT_VERSIONNE)
    verdict = run_static_cache_gate(racine)
    assert verdict.passed is True
    assert verdict.findings == []


def test_double_sens_par_le_cli_sur_le_meme_projet(tmp_path: Path) -> None:
    """Le double sens joué comme la recette du gabarit le joue : exit 1, correctif, exit 0."""
    racine = _projet(tmp_path, _GABARIT_NU)
    assert main([str(racine)]) == 1
    (racine / "app" / "templates" / "base.html").write_text(_GABARIT_VERSIONNE, encoding="utf-8")
    assert main([str(racine)]) == 0


# --- Le mécanisme est libre : empreinte de contenu acceptée à égalité ---------


def test_nom_empreinte_vaut_versionnement(tmp_path: Path) -> None:
    """Sortie de bundler (Vite/webpack) : le nom porte l'empreinte, aucun `?v=` exigé."""
    gabarit = (
        '<link rel="stylesheet" href="/assets/app.4f3c9a21.css">\n'
        '<script src="/assets/index-DkL2mQ8x.js"></script>\n'
    )
    assert run_static_cache_gate(_projet(tmp_path, gabarit)).passed is True


def test_faux_amis_d_empreinte_restent_des_statiques_nus(tmp_path: Path) -> None:
    """`app.min.css` (trop court) et `app.production.css` (aucun chiffre) ne sont PAS empreintés."""
    gabarit = (
        '<link rel="stylesheet" href="/static/app.min.css">\n'
        '<link rel="stylesheet" href="/static/app.production.css">\n'
    )
    verdict = run_static_cache_gate(_projet(tmp_path, gabarit))
    assert verdict.passed is False
    assert len([f for f in verdict.findings if f["kind"] == "statique-nu"]) == 2


def test_ressource_d_une_autre_origine_hors_perimetre(tmp_path: Path) -> None:
    """Un CDN tiers ne se versionne pas depuis ici : hors périmètre, jamais un constat."""
    gabarit = (
        '<link rel="stylesheet" href="https://cdn.exemple/a.css">\n'
        '<script src="//cdn.exemple/b.js"></script>\n'
        '<link rel="stylesheet" href="/static/app.css?v={{ version_app }}">\n'
    )
    assert run_static_cache_gate(_projet(tmp_path, gabarit)).passed is True


def test_json_n_est_pas_un_script(tmp_path: Path) -> None:
    """`.json` ne doit pas être lu comme `.js` — sinon le gate refuse ce qu'il n'a pas à juger."""
    gabarit = (
        '<link rel="manifest" href="/static/site.json">\n'
        '<script src="/static/app.js?v={{ version_app }}"></script>\n'
    )
    assert run_static_cache_gate(_projet(tmp_path, gabarit)).passed is True


# --- En-tête de cache ---------------------------------------------------------


def test_cache_control_absent_est_un_constat(tmp_path: Path) -> None:
    """Des statiques versionnés servis sans aucun `Cache-Control` déclaré : constat rendu."""
    racine = _projet(tmp_path, _GABARIT_VERSIONNE, serveur="app = creer_app()\n")
    verdict = run_static_cache_gate(racine)
    assert verdict.passed is False
    assert [f["kind"] for f in verdict.findings] == ["cache-control-absent"]


def test_cache_long_sur_du_html_est_un_constat(tmp_path: Path) -> None:
    """Le HTML figé un an annule le versionnement d'amont : la nouvelle adresse n'est jamais lue."""
    racine = _projet(
        tmp_path,
        _GABARIT_VERSIONNE,
        serveur='HEADERS = {"text/html": {"Cache-Control": "max-age=31536000"}}\n',
    )
    verdict = run_static_cache_gate(racine)
    assert verdict.passed is False
    assert [f["kind"] for f in verdict.findings] == ["cache-control-html-long"]


def test_meta_http_equiv_ne_vaut_pas_declaration(tmp_path: Path) -> None:
    """Un `<meta http-equiv="Cache-Control">` est ignoré par les navigateurs : pas un PASS."""
    gabarit = (
        '<meta http-equiv="Cache-Control" content="no-cache">\n'
        '<link rel="stylesheet" href="/static/app.css?v={{ version_app }}">\n'
    )
    racine = _projet(tmp_path, gabarit, serveur="app = creer_app()\n")
    verdict = run_static_cache_gate(racine)
    assert verdict.passed is False
    assert [f["kind"] for f in verdict.findings] == ["cache-control-absent"]


# --- Do-no-harm : ce que le gate refuse de juger, il le DIT -------------------


def test_arborescence_absente_est_skip_trace(tmp_path: Path) -> None:
    """P-06 : pas de projet → skip tracé, jamais un échec implicite."""
    verdict = run_static_cache_gate(tmp_path / "absent")
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_projet_sans_statique_est_skip_trace(tmp_path: Path) -> None:
    """Aucune adresse statique locale : un PASS muet se lirait comme une mesure — on le DIT."""
    racine = _projet(tmp_path, "<html><body>rien à servir</body></html>\n")
    verdict = run_static_cache_gate(racine)
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_suite_de_tests_du_projet_hors_perimetre(tmp_path: Path) -> None:
    """Un gabarit nu dans `tests/` du projet audité est une fixture, pas un livrable."""
    racine = _projet(tmp_path, _GABARIT_VERSIONNE)
    (racine / "tests").mkdir()
    (racine / "tests" / "fixture.html").write_text(_GABARIT_NU, encoding="utf-8")
    assert run_static_cache_gate(racine).passed is True


def test_cli_usage_rend_2(tmp_path: Path) -> None:
    assert main([]) == 2
    assert main([str(tmp_path), "de trop"]) == 2


def test_est_versionnee_unitaire() -> None:
    assert est_versionnee("/static/app.css?v={{ version_app }}") is True
    assert est_versionnee("/static/app.css?v=1.4.2") is True
    assert est_versionnee("/static/app.css?v=") is False
    assert est_versionnee("/static/app.css") is False
    assert est_versionnee("/assets/app.4f3c9a21.css") is True
