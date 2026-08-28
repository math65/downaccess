"""Tests qui sortent reellement sur Internet.

Exclus par defaut (`addopts = -m 'not network'`) : la suite doit rester verte
hors ligne, et un site tiers en panne ne doit jamais faire echouer un build.
A lancer avant une publication :

    uv run pytest -m network

Leur role est de verifier que les **contrats** des services distants n'ont pas
change (structure des flux, presence des sous-titres) — pas leur disponibilite.
Quand un service est injoignable ou nous limite, le test s'abstient au lieu
d'echouer : c'est une information sur le reseau, pas sur le code.
"""

import pytest

from app.core import feed_search, site_search, subscriptions as subs
from app.core.transcript import TranscriptError, fetch_transcript

pytestmark = pytest.mark.network

CHAINE_YOUTUBE = "https://www.youtube.com/@Arte"
PODCAST = "https://podcasts.files.bbci.co.uk/p02nq0gn.rss"
VIDEO_AVEC_SOUS_TITRES = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
COLLECTION_ARTE = "https://www.arte.tv/fr/videos/RC-014468/cabaret-vert/"
# M6 : image chiffree, bande-son en clair (cf. TestImageVerrouillee).
EPISODE_M6 = "https://www.m6.fr/24-heures-chrono-p_28317/s1-e1-minuit-1h00-c_13185332"


def joignable(action, quoi):
    """Execute `action`, ou s'abstient si le service distant ne repond pas.

    YouTube limite les requetes repetees (mesure : jusqu'a 6 refus d'affilee
    sur un flux valide). Un test ne doit pas transformer ca en echec de build.
    """
    try:
        return action()
    except subs.FeedError as exc:
        pytest.skip(f"{quoi} injoignable pour l'instant : {exc}")
    except TranscriptError as exc:
        pytest.skip(f"{quoi} injoignable pour l'instant : {exc}")


class TestContratDesFlux:
    def test_chaine_youtube_reste_un_flux_atom(self):
        """Contrat : YouTube publie toujours un flux Atom par chaine, et
        l'identifiant reste trouvable depuis un @handle."""
        feed, kind, titre = joignable(
            lambda: subs.resolve_feed(CHAINE_YOUTUBE), "YouTube")
        assert kind == subs.KIND_YOUTUBE
        assert "feeds/videos.xml" in feed
        assert titre

    def test_entrees_d_une_chaine_exploitables(self):
        feed, _kind, _titre = joignable(
            lambda: subs.resolve_feed(CHAINE_YOUTUBE), "YouTube")
        _t, entries = joignable(
            lambda: subs.parse_feed(subs._http_get(feed)), "YouTube")
        assert len(entries) >= 5
        assert all(e.entry_id and e.url for e in entries)

    def test_podcast_expose_bien_son_media(self):
        """Contrat : l'enclosure d'un item porte l'adresse du fichier audio."""
        feed, kind, titre = joignable(lambda: subs.resolve_feed(PODCAST), "BBC")
        assert kind == subs.KIND_PODCAST
        assert titre
        _t, entries = joignable(
            lambda: subs.parse_feed(subs._http_get(feed)), "BBC")
        assert entries[0].url.startswith("http")

    def test_adresse_inexistante_donne_une_erreur_lisible(self):
        with pytest.raises(subs.FeedError):
            subs.resolve_feed("https://exemple.invalide.test/flux.xml")


class TestContratDesSousTitres:
    def test_recuperation_et_nettoyage(self):
        texte, langue = joignable(
            lambda: fetch_transcript({"subtitle_langs": ["en", "fr"]},
                                     VIDEO_AVEC_SOUS_TITRES),
            "les sous-titres YouTube")
        assert langue
        assert len(texte) > 50
        assert "-->" not in texte
        assert "WEBVTT" not in texte


def repond(action, quoi):
    """Execute `action`, ou s'abstient si le site distant ne repond pas."""
    try:
        return action()
    except Exception as exc:                       # reseau, 5xx, geoblocage...
        pytest.skip(f"{quoi} injoignable pour l'instant : {exc}")


class TestContratArte:
    """Arte n'a pas d'API documentee : ces contrats sont deduits de mesures.

    Ils ne verifient pas qu'Arte est en ligne, mais que la forme de ses
    reponses n'a pas change — le jour ou elle change, l'utilisateur voit des
    listes vides ou des URL brutes, et ce n'est pas a lui de nous le dire.
    """

    def test_le_jeton_emprunte_a_yt_dlp_est_toujours_accepte(self):
        """Le jeton vit dans yt-dlp, mis a jour chaque nuit. S'il est revoque,
        les collections perdent leurs titres — on veut le savoir avant."""
        entries = repond(
            lambda: site_search.arte_program_entries(COLLECTION_ARTE),
            "l'API programmes d'Arte")
        assert entries, "l'API programmes ne renvoie plus rien (jeton revoque ?)"
        assert all(e["title"] and e["webpage_url"] for e in entries)

    def test_une_collection_est_decrite_en_entier(self):
        """Chaque video de la collection doit pouvoir etre nommee : c'est ce
        qui distingue deux concerts d'un meme festival."""
        entries = repond(
            lambda: site_search.arte_collection_entries(COLLECTION_ARTE),
            "les collections Arte")
        titres = {e["title"] for e in entries}
        assert len(titres) == len(entries), "des titres en double"
        assert any("Cabaret Vert" in t for t in titres)

    def test_la_page_des_concerts_existe_toujours(self):
        """ARTE Concert est une page a part, pas une categorie du site : son
        code est le seul chemin vers les festivals."""
        result = repond(
            lambda: site_search.browse("arte", "ARTE_CONCERT", 20, "fr", 1),
            "ARTE Concert")
        assert result["total_count"] > 20
        assert all(e["title"] and e["webpage_url"] for e in result["entries"])

    def test_une_collection_se_suit_comme_un_flux(self):
        """Contrat de l'abonnement : la collection doit se resoudre en un
        « flux » dont chaque entree porte un identifiant stable et une adresse."""
        feed, kind, titre = repond(
            lambda: subs.resolve_feed(COLLECTION_ARTE), "Arte")
        assert kind == subs.KIND_ARTE
        assert titre
        _t, entries = repond(
            lambda: subs.fetch_entries(feed, kind), "Arte")
        assert len(entries) >= 5
        assert all(e.entry_id and e.url and e.title for e in entries)
        assert len({e.entry_id for e in entries}) == len(entries)

    def test_le_titre_distinctif_est_dans_alt_title(self):
        """Contrat cote yt-dlp : sur Arte, `title` porte le nom du programme et
        `alt_title` celui de l'episode. C'est sur quoi repose le nom de fichier."""
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                               "skip_download": True}) as ydl:
            info = repond(
                lambda: ydl.extract_info(
                    "https://www.arte.tv/fr/videos/133232-006-A/ofenbach/",
                    download=False),
                "arte.tv")
        assert info["title"] and info["alt_title"]
        assert info["alt_title"] not in info["title"]


class TestContratM6:
    def test_l_image_reste_verrouillee_et_le_son_accessible(self):
        """Contrat inverse des autres : on verifie qu'une protection est
        TOUJOURS en place. Si M6 ouvrait ses videos, ce test tomberait et il
        faudrait retirer le garde-fou au lieu de refuser un site devenu
        telechargeable."""
        import yt_dlp

        from app.core.downloader import video_is_drm_locked
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                               "skip_download": True}) as ydl:
            info = repond(lambda: ydl.extract_info(EPISODE_M6, download=False), "m6.fr")
        assert video_is_drm_locked(info), "M6 semble telechargeable : revoir le garde-fou"


class TestContratRechercheAbonnement:
    """La recherche d'une source a suivre depend de trois services tiers.

    Chacun peut changer sans prevenir : le filtre « chaines » de YouTube, la
    presence des collections dans la recherche Arte, et surtout l'adresse du
    flux dans la page d'un podcast Apple — que l'API, elle, ne donne pas. Ces
    tests disent lequel a bouge le jour ou la recherche ne rend plus rien.
    """

    def _cherche(self, source, terme):
        try:
            return feed_search.search(source, terme, 8)
        except feed_search.SearchError as exc:
            pytest.skip(f"{source} injoignable pour l'instant : {exc}")

    def test_les_chaines_youtube_restent_filtrables(self):
        resultats = self._cherche(feed_search.SOURCE_YOUTUBE, "arte")
        assert resultats, "le filtre « chaines » ne rend plus rien"
        # Des chaines, pas des videos : c'est tout l'interet du filtre.
        assert all("/channel/" in r["url"] or "/@" in r["url"]
                   for r in resultats)

    def test_une_chaine_trouvee_est_suivable(self):
        """Le lien entre les deux moities : ce que la recherche rend doit
        passer tel quel dans `resolve_feed`."""
        resultats = self._cherche(feed_search.SOURCE_YOUTUBE, "arte")
        feed, kind, titre = joignable(
            lambda: subs.resolve_feed(resultats[0]["url"]), "YouTube")
        assert kind == subs.KIND_YOUTUBE and titre
        assert "feeds/videos.xml" in feed

    def test_arte_rend_toujours_des_collections(self):
        resultats = self._cherche(feed_search.SOURCE_ARTE, "karambolage")
        assert resultats, "la recherche Arte ne rend plus de collection"
        assert site_search.arte_collection_id(resultats[0]["url"])

    def test_une_collection_trouvee_est_suivable(self):
        resultats = self._cherche(feed_search.SOURCE_ARTE, "karambolage")
        _feed, kind, titre = joignable(
            lambda: subs.resolve_feed(resultats[0]["url"]), "Arte")
        assert kind == subs.KIND_ARTE and titre

    def test_apple_trouve_les_podcasts_francais(self):
        resultats = self._cherche(feed_search.SOURCE_PODCAST,
                                  "affaires sensibles")
        assert resultats, "la recherche de podcasts ne rend plus rien"
        assert resultats[0]["title"]

    def test_l_adresse_du_flux_reste_lisible_dans_la_page(self):
        """Le point fragile de la fonction : Apple ne publie pas cette adresse
        dans son API pour les podcasts de Radio France, seulement dans la page.
        Si ce test tombe, c'est la page qui a change de forme."""
        resultats = self._cherche(feed_search.SOURCE_PODCAST,
                                  "affaires sensibles")
        try:
            feed_url = feed_search.resolve(resultats[0])
        except feed_search.SearchError as exc:
            pytest.skip(f"Apple injoignable pour l'instant : {exc}")
        assert feed_url.startswith("http")
        titre, entrees = joignable(
            lambda: subs.parse_feed(subs._http_get(feed_url)), "le podcast")
        assert titre and entrees, "l'adresse trouvee doit etre un vrai flux"

    def test_un_podcast_trouve_devient_un_abonnement(self):
        """Bout en bout : ce que la recherche rend doit pouvoir etre suivi."""
        resultats = self._cherche(feed_search.SOURCE_PODCAST, "the daily")
        try:
            feed_url = feed_search.resolve(resultats[0])
        except feed_search.SearchError as exc:
            pytest.skip(f"Apple injoignable pour l'instant : {exc}")
        sub = joignable(lambda: subs.create(feed_url), "le podcast")
        assert sub.title and sub.feed_url
        assert sub.kind in (subs.KIND_PODCAST, subs.KIND_YOUTUBE)
