"""Gate frontière démo/production (RV-3, TF-0010) : oracle exécutable de la doctrine."""

from __future__ import annotations

from pathlib import Path

from conductor.gates.demo_markers_gate import main, run_demo_markers_gate


def test_marqueur_demo_derriere_un_drapeau_passe(tmp_path: Path) -> None:
    """Fixture verte : le marqueur de démo est associé à un garde *_MODE_DEMO dans le fichier."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "seed.py").write_text(
        'if os.environ.get("BILLING_MODE_DEMO") == "1":\n'
        '    creer_client_demo()  # fixture de démonstration\n',
        encoding="utf-8",
    )
    verdict = run_demo_markers_gate(src)
    assert verdict.passed is True
    assert verdict.findings == []


def test_marqueur_demo_sans_drapeau_echoue(tmp_path: Path) -> None:
    """Fixture rouge : un marqueur de démo non gardé par un drapeau fait échouer le gate."""
    src = tmp_path / "app"
    src.mkdir()
    (src / "seed.py").write_text(
        "def creer_client_demo():\n    return Client(nom='Client Démo')\n", encoding="utf-8"
    )
    verdict = run_demo_markers_gate(src)
    assert verdict.passed is False
    assert verdict.findings[0]["file"].endswith("seed.py")


def test_fixtures_de_test_hors_perimetre(tmp_path: Path) -> None:
    """Un marqueur de démo dans tests/ (fixtures de test légitimes) n'est pas un défaut."""
    src = tmp_path / "app"
    tests_dir = src / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_seed.py").write_text(
        "def demo_payload():\n    return {}\n", encoding="utf-8"
    )
    assert run_demo_markers_gate(src).passed is True


def test_arborescence_absente_est_skip_trace(tmp_path: Path) -> None:
    """P-06 : pas d'arborescence source → skip tracé, jamais un échec implicite."""
    verdict = run_demo_markers_gate(tmp_path / "absent")
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_cli_main_pass_et_fail(tmp_path: Path) -> None:
    src = tmp_path / "app"
    src.mkdir()
    (src / "seed.py").write_text("def creer_client_demo():\n    pass\n", encoding="utf-8")
    assert main([str(src)]) == 1
    (src / "seed.py").write_text(
        'if os.environ.get("MODE_DEMO"):\n    creer_client_demo()\n', encoding="utf-8"
    )
    assert main([str(src)]) == 0


def test_fixtures_synthetiques_declarees_ne_sont_pas_signalees(tmp_path: Path) -> None:
    """TF-2093, fixture rouge : des fixtures synthétiques déclarées (marqueur SYNTHETIC) sont
    l'objet même du Gate A du laboratoire, pas une fuite de démo (frontière posée dans le fichier).
    """
    src = tmp_path / "lab"
    src.mkdir()
    (src / "corpus.py").write_text(
        '"""Fixtures SYNTHETIC : jeu de données fabriqué, jamais issu de la production."""\n'
        "FIXTURE_CLIENTS = [{'nom': 'Client A'}]\n",
        encoding="utf-8",
    )
    (src / "autre.py").write_text(
        "# SYNTHETIC_ONLY\ndef fixture_commandes():\n    return []\n", encoding="utf-8"
    )
    verdict = run_demo_markers_gate(src)
    assert verdict.passed is True
    assert verdict.findings == []


def test_vrai_marqueur_de_demo_reste_signale_malgre_synthetic_ailleurs(tmp_path: Path) -> None:
    """TF-2093, double sens : la déclaration est locale au fichier ; un fichier voisin non
    déclaré, ou qui n'évoque « synthetic » qu'en prose minuscule, reste signalé."""
    src = tmp_path / "lab"
    src.mkdir()
    (src / "corpus.py").write_text("# SYNTHETIC\nFIXTURE = []\n", encoding="utf-8")
    (src / "seed.py").write_text(
        "def creer_client_demo():\n    return Client(nom='Client Démo')\n", encoding="utf-8"
    )
    (src / "prose.py").write_text(
        "# données synthetic maison\ndef creer_client_demo():\n    pass\n", encoding="utf-8"
    )
    (src / "mot.py").write_text("SYNTHETICS = 1\ndef fixture():\n    pass\n", encoding="utf-8")
    verdict = run_demo_markers_gate(src)
    assert verdict.passed is False
    signales = sorted(Path(f["file"]).name for f in verdict.findings)
    assert signales == ["mot.py", "prose.py", "seed.py"]
