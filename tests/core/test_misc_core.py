"""Modules coeur restants : langue, recherche de sites, cookies, file d'attente."""

import pytest

from app.core import i18n
from app.core.cookies import _normalize_domain, jar_path_for
from app.core.custom_sites import detect_audio_tracks, is_custom_site_extractor, is_custom_site_url
from app.core.site_search import (
    _clean_summary,
    _page_slice,
    _slugify,
    _arte_api_token,
    _arte_program_entry,
    arte_collection_id,
    arte_program_entries,
    arte_video_id,
    categories,
    supports_browse,
)


class TestLangue:
    @pytest.mark.parametrize("brut,attendu", [
        ("fr", "fr"),
        ("en", "en"),
        ("FR", "fr"),
        ("auto", "auto"),
        ("", "auto"),
        (None, "auto"),
        ("de", "auto"),        # langue non prise en charge -> detection
    ])
    def test_normalisation(self, brut, attendu):
        assert i18n.normalize_ui_language(brut) == attendu

    def test_resolution_explicite(self):
        assert i18n.resolve_language("fr") == "fr"
        assert i18n.resolve_language("en") == "en"

    def test_resolution_auto_donne_une_langue_reelle(self):
        assert i18n.resolve_language("auto") in ("fr", "en")

    def test_langues_prises_en_charge(self):
        assert set(i18n.get_supported_language_codes()) >= {"fr", "en"}

    def test_traduction_anglaise_effective(self, english_ui):
        assert i18n.get_current_language_code() == "en"
        assert _("Annuler") == "Cancel"

    def test_source_francaise_identite(self):
        """Pas de catalogue pour le francais : le msgid EST le texte affiche."""
        assert _("Annuler") == "Annuler"


class TestResumesEtSlugs:
    def test_html_nettoye(self):
        assert _clean_summary("<p>Bonjour <b>tout</b> le monde</p>") == "Bonjour tout le monde"

    def test_entites_decodees(self):
        assert "&" in _clean_summary("Rock &amp; roll")

    def test_espace_insecable_remplace(self):
        """L'espace insecable d'Arte gene la lecture au lecteur d'ecran."""
        assert "\xa0" not in _clean_summary("Arte\xa0Regards")

    def test_vide(self):
        assert _clean_summary(None) == ""
        assert _clean_summary("") == ""

    @pytest.mark.parametrize("brut,attendu", [
        ("Les Enfants Terribles", "les-enfants-terribles"),
        ("Éducation & société", "education-societe"),
        ("", "video"),
    ])
    def test_slug(self, brut, attendu):
        assert _slugify(brut) == attendu


class TestPagination:
    @pytest.fixture
    def entrees(self):
        return [{"n": i} for i in range(25)]

    def test_premiere_page(self, entrees):
        page = _page_slice(entrees, 1, 10)
        assert len(page["entries"]) == 10
        assert page["page"] == 1
        assert page["total_pages"] == 3
        assert page["total_count"] == 25

    def test_derniere_page_partielle(self, entrees):
        page = _page_slice(entrees, 3, 10)
        assert len(page["entries"]) == 5

    def test_page_hors_limites_ramenee(self, entrees):
        assert _page_slice(entrees, 99, 10)["page"] == 3
        assert _page_slice(entrees, 0, 10)["page"] == 1

    def test_liste_vide(self):
        page = _page_slice([], 1, 10)
        assert page["entries"] == []
        assert page["total_pages"] == 1


class TestSitesPersonnalises:
    @pytest.mark.parametrize("url", [
        "https://www.france.tv/documentaires/x",
        "https://www.arte.tv/fr/videos/123/",
    ])
    def test_reconnus(self, url):
        assert is_custom_site_url(url)

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/watch?v=x",
        "https://vimeo.com/1",
        "",
    ])
    def test_autres_sites(self, url):
        assert not is_custom_site_url(url)

    def test_par_cle_d_extracteur(self):
        assert is_custom_site_extractor("FranceTV")
        assert not is_custom_site_extractor("Youtube")
        assert not is_custom_site_extractor(None)

    def test_piste_normale_et_audiodescription(self):
        """france.tv expose la version originale et l'audiodescription : les
        deux doivent ressortir, et l'AD doit etre reconnue comme telle."""
        formats = [
            {"format_id": "audio-fr", "vcodec": "none", "acodec": "mp4a", "language": "fr"},
            {"format_id": "audio-fr-qad", "vcodec": "none", "acodec": "mp4a",
             "language": "fr", "format_note": "Audiodescription"},
            {"format_id": "video-1080", "vcodec": "avc1", "acodec": "none"},
        ]
        pistes = detect_audio_tracks(formats)
        assert len(pistes) == 2
        assert sum(1 for p in pistes if p.is_audio_description) == 1
        assert all(p.format_ids for p in pistes)

    def test_aucune_piste_audio_isolee(self):
        formats = [{"format_id": "v", "vcodec": "avc1", "acodec": "mp4a"}]
        assert detect_audio_tracks(formats) == []


class TestCatalogues:
    @pytest.mark.parametrize("site", ["francetv", "arte"])
    def test_categories_disponibles(self, site):
        assert supports_browse(site)
        assert len(categories(site)) > 0

    def test_youtube_n_a_pas_de_catalogue(self):
        assert not supports_browse("youtube")


class TestCookies:
    @pytest.mark.parametrize("url,domaine", [
        ("https://www.youtube.com/x", "youtube.com"),
        ("https://YOUTUBE.COM/x", "youtube.com"),
        ("https://sub.exemple.org/x", "sub.exemple.org"),
    ])
    def test_domaine_normalise(self, url, domaine):
        assert _normalize_domain(url) == domaine

    def test_chemin_de_jar_sans_caractere_interdit(self, appdata):
        chemin = jar_path_for("https://www.exemple.org/x")
        assert chemin.endswith("exemple.org.txt")
        assert not any(c in chemin.rsplit("\\", 1)[-1] for c in ':*?"<>|')


class TestCollectionArte:
    """Rapprochement des entrees d'une collection Arte avec l'API EMAC."""

    @pytest.mark.parametrize("url,attendu", [
        ("https://www.arte.tv/fr/videos/RC-014468/cabaret-vert/", ("fr", "RC-014468")),
        ("https://www.arte.tv/de/videos/RC-027513/twin-peaks/", ("de", "RC-027513")),
        # Langue non servie par Arte -> repli francais
        ("https://www.arte.tv/nl/videos/RC-014468/x/", ("fr", "RC-014468")),
    ])
    def test_reconnait_une_collection(self, url, attendu):
        assert arte_collection_id(url) == attendu

    @pytest.mark.parametrize("url", [
        "https://www.arte.tv/fr/videos/133232-001-A/speed/",   # video, pas collection
        "https://www.youtube.com/playlist?list=PLabc",
        "",
    ])
    def test_ignore_le_reste(self, url):
        assert arte_collection_id(url) is None

    def test_identifiant_de_video(self):
        assert arte_video_id(
            "https://www.arte.tv/fr/videos/133232-001-A/speed/") == "133232-001-A"
        assert arte_video_id(
            "https://www.arte.tv/de/videos/133232-001-a/speed/") == "133232-001-A"
        assert arte_video_id("https://www.arte.tv/fr/videos/RC-014468/x/") == ""


class TestProgrammeArte:
    """Source complete des titres d'une collection : l'API « programmes »."""

    COLLECTION = "https://www.arte.tv/fr/videos/RC-014468/cabaret-vert/"

    def test_le_jeton_se_lit_toujours_dans_yt_dlp(self):
        """Garde-fou : DownAccess emprunte le jeton a yt-dlp plutot que de le
        figer. Si yt-dlp renomme l'attribut, on veut le savoir ici — pas par un
        utilisateur devant une liste d'URL brutes."""
        assert _arte_api_token()

    def test_normalisation_d_une_video(self):
        entree = _arte_program_entry({
            "kind": "SHOW",
            "title": "ARTE Reportage",
            "subtitle": "Afghanistan / Sud-Liban",
            "url": "https://www.arte.tv/fr/videos/124239-072-A/arte-reportage/",
            "durationSeconds": "3175",       # l'API renvoie une chaine
            "shortDescription": "Depuis le retour des talibans...",
            "programId": "124239-072-A",
        })
        assert entree["title"] == "ARTE Reportage — Afghanistan / Sud-Liban"
        assert entree["duration"] == 3175
        assert entree["_summary"].startswith("Depuis le retour")

    def test_sans_sous_titre(self):
        entree = _arte_program_entry({
            "kind": "SHOW", "title": "Speed",
            "url": "https://www.arte.tv/fr/videos/133232-001-A/speed/",
        })
        assert entree["title"] == "Speed"
        assert entree["duration"] is None

    @pytest.mark.parametrize("item", [
        {"kind": "TRAILER", "title": "Bande-annonce", "url": "https://x/1"},  # pas une emission
        {"kind": "SHOW", "title": "Sans adresse"},                            # inexploitable
    ])
    def test_ecarte_ce_qui_n_est_pas_telechargeable(self, item):
        assert _arte_program_entry(item) is None

    def test_sans_jeton_pas_de_requete(self, monkeypatch):
        """Repli silencieux : l'appelant passe alors a l'API web."""
        import app.core.site_search as site_search
        monkeypatch.setattr(site_search, "_arte_api_token", lambda: "")
        monkeypatch.setattr(site_search.cffi_requests, "get", _interdit)
        assert arte_program_entries(self.COLLECTION) == []

    def test_api_en_erreur_ne_remonte_pas(self, monkeypatch):
        import app.core.site_search as site_search
        monkeypatch.setattr(site_search, "_arte_api_token", lambda: "jeton")
        monkeypatch.setattr(site_search.cffi_requests, "get", _explose)
        assert arte_program_entries(self.COLLECTION) == []

    def test_hors_collection_pas_de_requete(self, monkeypatch):
        import app.core.site_search as site_search
        monkeypatch.setattr(site_search.cffi_requests, "get", _interdit)
        assert arte_program_entries("https://www.youtube.com/watch?v=a") == []


def _interdit(*args, **kwargs):
    raise AssertionError("aucune requete ne devait partir")


def _explose(*args, **kwargs):
    raise OSError("API injoignable")
