"""Reglages et historique : persistance, valeurs par defaut, migrations."""

import json

import pytest

from app.core import history
from app.core import settings as cfg


class TestReglages:
    def test_valeurs_par_defaut_completes(self, appdata):
        s = cfg.load()
        for cle in ("download_folder", "max_concurrent_downloads", "post_processing",
                    "embed_metadata", "chapters_mode", "subscriptions_check_on_start",
                    "language"):
            assert cle in s

    def test_aller_retour(self, appdata):
        s = cfg.load()
        s["max_concurrent_downloads"] = 7
        s["embed_metadata"] = False
        cfg.save(s)
        assert cfg.load()["max_concurrent_downloads"] == 7
        assert cfg.load()["embed_metadata"] is False

    def test_cle_absente_reprend_le_defaut(self, appdata):
        """Une version anterieure n'ecrivait pas les nouvelles cles : elles
        doivent apparaitre avec leur valeur par defaut, pas manquer."""
        chemin = appdata / "DownAccess" / "settings.json"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps({"download_folder": "D:/x"}), encoding="utf-8")
        s = cfg.load()
        assert s["download_folder"] == "D:/x"
        assert s["embed_metadata"] is cfg.DEFAULTS["embed_metadata"]

    def test_fichier_corrompu(self, appdata):
        chemin = appdata / "DownAccess" / "settings.json"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text("pas du json", encoding="utf-8")
        assert cfg.load()["post_processing"] == cfg.DEFAULTS["post_processing"]

    def test_migration_du_format_none(self, appdata):
        """« Aucun post-traitement » a ete renomme « auto » : l'ancien code
        doit etre replie, sinon le format par defaut devient invalide."""
        chemin = appdata / "DownAccess" / "settings.json"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps({"post_processing": "none"}), encoding="utf-8")
        assert cfg.load()["post_processing"] == "auto"

    def test_les_defauts_ne_sont_pas_partages(self, appdata):
        """Modifier les reglages charges ne doit jamais contaminer DEFAULTS."""
        s = cfg.load()
        s["subtitle_langs"].append("de")
        assert "de" not in cfg.DEFAULTS["subtitle_langs"]


class TestHistorique:
    def test_ajout_et_relecture(self, appdata):
        history.add(history.HistoryEntry(url="https://a/1", title="Un", status="success"))
        entrees = history.load()
        assert len(entrees) == 1
        assert entrees[0].title == "Un"

    def test_plafond_garde_les_plus_recents(self, appdata):
        """Au-dela de MAX_ENTRIES, ce sont les plus anciennes qui partent."""
        depassement = 5
        for i in range(history.MAX_ENTRIES + depassement):
            history.add(history.HistoryEntry(url=f"https://a/{i}", title=str(i)))
        entrees = history.load()
        assert len(entrees) == history.MAX_ENTRIES
        titres = [e.title for e in entrees]
        assert str(history.MAX_ENTRIES + depassement - 1) in titres
        assert "0" not in titres

    def test_vider(self, appdata):
        history.add(history.HistoryEntry(url="https://a/1"))
        history.clear()
        assert history.load() == []

    def test_fichier_corrompu(self, appdata):
        chemin = appdata / "DownAccess" / "history.json"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text("{{{", encoding="utf-8")
        assert history.load() == []

    def test_echec_conserve_son_message(self, appdata):
        history.add(history.HistoryEntry(url="https://a/1", status="failed",
                                         error="disque plein"))
        assert history.load()[0].error == "disque plein"


@pytest.mark.parametrize("cle,attendu", [
    ("embed_metadata", True),        # les fichiers nus etaient le defaut historique
    ("chapters_mode", "embed"),      # les reperes dans le fichier ne coutent rien ;
                                     # decouper change le nombre de fichiers : opt-in
    ("subscriptions_check_on_start", True),
    ("subscriptions_announce", False),   # regle UX : demarrage silencieux
])
def test_defauts_sensibles(cle, attendu):
    """Ces valeurs par defaut sont des decisions produit, pas des details."""
    assert cfg.DEFAULTS[cle] is attendu
