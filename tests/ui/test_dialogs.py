"""Fenetres : construction, focus initial, ordre de tabulation, etiquetage.

Ces tests ne remplacent pas un essai au lecteur d'ecran, mais ils verrouillent
mecaniquement les regles d'accessibilite du projet, qui sont structurelles :
chaque champ porte un nom, le focus arrive sur le contenu et non sur un bouton,
et l'ordre de tabulation est pose explicitement.
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core.settings import DEFAULTS
from app.ui.add_url_dialog import AddUrlDialog
from app.ui.playlist_dialog import PlaylistDialog, label_from_url
from app.ui.settings_dialog import SettingsDialog
from app.ui.transcript_dialog import TranscriptDialog


def nommes(parent):
    """Controles interactifs sans nom accessible (donc muets au lecteur)."""
    muets = []
    for enfant in parent.GetChildren():
        if isinstance(enfant, wx.TextCtrl | wx.Choice | wx.ListCtrl | wx.CheckBox):
            if not enfant.GetName() or enfant.GetName() == "control":
                muets.append(enfant)
        muets.extend(nommes(enfant))
    return muets


class TestAjoutUrl:
    def test_focus_sur_la_saisie(self, frame):
        """Regle du projet : le focus arrive sur le contenu, pas sur un bouton."""
        dlg = AddUrlDialog(frame)
        assert dlg.FindFocus() is dlg.txt_urls
        dlg.Destroy()

    def test_pas_de_champ_extrait_par_defaut(self, frame):
        dlg = AddUrlDialog(frame)
        assert dlg.txt_start is None
        dlg.Destroy()

    def test_champs_extrait_a_la_demande(self, frame):
        dlg = AddUrlDialog(frame, with_range=True)
        assert dlg.txt_start is not None and dlg.txt_end is not None
        assert dlg.lbl_start.GetLabel()
        dlg.Destroy()

    def test_titre_distinct_selon_le_parcours(self, frame):
        simple = AddUrlDialog(frame)
        extrait = AddUrlDialog(frame, with_range=True)
        assert simple.GetTitle() != extrait.GetTitle()
        simple.Destroy()
        extrait.Destroy()

    @pytest.mark.parametrize("debut,fin,attendu", [
        ("", "", None),
        ("4:20", "1:05:30", (260.0, 3930.0)),
        ("10", "", (10.0, float("inf"))),
        ("", "30", (0.0, 30.0)),
    ])
    def test_lecture_de_l_extrait(self, frame, debut, fin, attendu):
        dlg = AddUrlDialog(frame, with_range=True)
        dlg.txt_start.SetValue(debut)
        dlg.txt_end.SetValue(fin)
        assert dlg.get_section() == attendu
        dlg.Destroy()

    def test_moment_illisible_designe_le_champ(self, frame):
        dlg = AddUrlDialog(frame, with_range=True)
        dlg.txt_start.SetValue("bidule")
        with pytest.raises(ValueError, match="start"):
            dlg.get_section()
        dlg.txt_start.SetValue("0")
        dlg.txt_end.SetValue("nawak")
        with pytest.raises(ValueError, match="end"):
            dlg.get_section()
        dlg.Destroy()

    def test_urls_multiples(self, frame):
        dlg = AddUrlDialog(frame)
        dlg.txt_urls.SetValue("https://a/1\n\n  https://a/2  \n")
        assert dlg.get_urls() == ["https://a/1", "https://a/2"]
        dlg.Destroy()


class TestTranscription:
    def test_focus_sur_le_texte_en_lecture_seule(self, frame):
        """Un TextCtrl (et non un StaticText) permet la navigation au curseur
        et la recherche ; le focus doit y arriver directement."""
        dlg = TranscriptDialog(frame, "Ma video", "du texte", "fr")
        assert dlg.FindFocus() is dlg.txt
        assert not dlg.txt.IsEditable()
        dlg.Destroy()

    def test_contenu_intact(self, frame):
        texte = "paragraphe un\n\nparagraphe deux"
        dlg = TranscriptDialog(frame, "T", texte, "fr")
        assert dlg.txt.GetValue() == texte
        dlg.Destroy()

    def test_nom_de_fichier_propose_assaini(self, frame):
        dlg = TranscriptDialog(frame, 'Ma video : test / 2026', "x", "fr")
        propose = dlg._default_filename()
        assert propose.endswith(".txt")
        assert not any(c in propose for c in r':/\<>"|?*')
        dlg.Destroy()

    def test_titre_vide_ne_casse_pas(self, frame):
        dlg = TranscriptDialog(frame, "", "x")
        assert dlg._default_filename() == "transcription.txt"
        dlg.Destroy()


class TestPreferences:
    def test_construction(self, frame):
        dlg = SettingsDialog(frame, dict(DEFAULTS))
        assert dlg.notebook.GetPageCount() >= 5
        dlg.Destroy()

    @pytest.mark.parametrize("attribut,cle", [
        ("chk_metadata", "embed_metadata"),
        ("chk_subs_start", "subscriptions_check_on_start"),
        ("chk_subs_announce", "subscriptions_announce"),
    ])
    def test_aller_retour_des_cases(self, frame, attribut, cle):
        dlg = SettingsDialog(frame, dict(DEFAULTS))
        case = getattr(dlg, attribut)
        for valeur in (True, False):
            case.SetValue(valeur)
            assert dlg._collect_values()[cle] is valeur
        dlg.Destroy()

    def test_chaque_case_porte_une_etiquette(self, frame):
        dlg = SettingsDialog(frame, dict(DEFAULTS))
        for attribut in ("chk_metadata", "chk_subs_start"):
            assert getattr(dlg, attribut).GetLabel().strip()
        dlg.Destroy()

    @pytest.mark.parametrize("mode", ["embed", "split", "ignore"])
    def test_aller_retour_du_traitement_des_chapitres(self, frame, mode):
        """Les trois comportements doivent etre atteignables depuis la fenetre :
        c'est tout l'interet d'avoir remplace la case a cocher par un choix."""
        reglages = dict(DEFAULTS)
        reglages["chapters_mode"] = mode
        dlg = SettingsDialog(frame, reglages)
        assert dlg._collect_values()["chapters_mode"] == mode
        dlg.Destroy()

    def test_les_trois_chapitres_sont_proposes(self, frame):
        dlg = SettingsDialog(frame, dict(DEFAULTS))
        assert dlg.choice_chapters.GetCount() == 3
        assert all(dlg.choice_chapters.GetString(i).strip() for i in range(3))
        dlg.Destroy()

    def test_controles_tous_nommes(self, frame):
        """Un controle sans nom n'est pas annonce par le lecteur d'ecran."""
        dlg = SettingsDialog(frame, dict(DEFAULTS))
        muets = nommes(dlg)
        assert muets == [], [type(c).__name__ for c in muets]
        dlg.Destroy()


class TestListePlaylist:
    """Une entree sans titre ne doit pas s'annoncer comme une URL entiere.

    Les collections Arte arrivent sans aucun titre (yt-dlp renvoie des
    `url_result` nus). A defaut de titre, le dernier morceau du chemin est
    souvent le titre en toutes lettres, et se lit, lui.
    """

    @pytest.mark.parametrize("url,attendu", [
        ("https://www.arte.tv/fr/videos/133232-001-A/speed/", "Speed"),
        ("https://www.arte.tv/fr/videos/124239-072-A/arte-reportage/", "Arte reportage"),
        ("https://exemple.org/a/mon-super-episode.html", "Mon super episode"),
    ])
    def test_libelle_lisible(self, url, attendu):
        assert label_from_url(url) == attendu

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",   # segment de routage
        "https://vimeo.com/123456",                      # identifiant nu
        "https://www.arte.tv/fr/videos/133232-002-A/",   # identifiant nu
        "",
    ])
    def test_rien_a_tirer_de_l_url(self, url):
        assert label_from_url(url) == ""

    def test_la_fenetre_affiche_le_libelle_et_non_l_url(self, frame):
        entries = [
            {"url": "https://www.arte.tv/fr/videos/133232-001-A/speed/"},
            {"url": "https://vimeo.com/123456"},
            {"title": "Ofenbach — Cabaret Vert 2026",
             "url": "https://www.arte.tv/fr/videos/133232-006-A/ofenbach/"},
        ]
        dlg = PlaylistDialog(frame, "Cabaret Vert", entries)
        libelles = [dlg.lst.GetItemText(i) for i in range(dlg.lst.GetItemCount())]
        assert libelles[0] == "1. Speed"
        assert "vimeo.com" not in libelles[1]          # repli generique
        assert libelles[2] == "3. Ofenbach — Cabaret Vert 2026"
        dlg.Destroy()


class TestOngletAbonnements:
    """Les reglages d'abonnement vivaient dans l'onglet General, entre le choix
    du navigateur et une option d'interception : introuvables pour la fonction
    la plus visible de l'application."""

    def test_l_onglet_existe(self, frame):
        dlg = SettingsDialog(frame, dict(DEFAULTS))
        titres = [dlg.notebook.GetPageText(i)
                  for i in range(dlg.notebook.GetPageCount())]
        assert any("bonnement" in t or "ubscription" in t for t in titres)
        dlg.Destroy()

    def test_les_cinq_reglages_sont_lus_et_ecrits(self, frame):
        reglages = dict(DEFAULTS)
        reglages.update({"subscriptions_check_on_start": False,
                         "subscriptions_daily_only": True,
                         "subscriptions_on_new": "window",
                         "subscriptions_announce": True,
                         "subscriptions_default_format": "mp3"})
        dlg = SettingsDialog(frame, reglages)
        valeurs = dlg._collect_values()
        assert valeurs["subscriptions_check_on_start"] is False
        assert valeurs["subscriptions_daily_only"] is True
        assert valeurs["subscriptions_on_new"] == "window"
        assert valeurs["subscriptions_announce"] is True
        assert valeurs["subscriptions_default_format"] == "mp3"
        dlg.Destroy()

    def test_valeur_inconnue_retombe_sur_le_defaut(self, frame):
        """Fichier de reglages d'une version future ou abime."""
        reglages = dict(DEFAULTS)
        reglages["subscriptions_default_format"] = "format_inexistant"
        reglages["subscriptions_on_new"] = "n_importe_quoi"
        dlg = SettingsDialog(frame, reglages)
        valeurs = dlg._collect_values()
        assert valeurs["subscriptions_default_format"] == ""
        assert valeurs["subscriptions_on_new"] == "counter"
        dlg.Destroy()

    def test_controles_de_l_onglet_tous_nommes(self, frame):
        """Un controle sans nom n'est pas annonce par le lecteur d'ecran."""
        dlg = SettingsDialog(frame, dict(DEFAULTS))
        muets = nommes(dlg._page_subs)
        assert muets == [], [type(c).__name__ for c in muets]
        dlg.Destroy()
