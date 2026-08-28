"""Recherche d'une source a suivre : ce qu'on retient, et ce qu'on ecarte.

Le point sensible est l'adresse du flux d'un podcast. Apple ne la donne pas
dans son API pour une bonne partie du catalogue francais : on la lit dans la
page publique du podcast, ou figurent aussi les podcasts suggeres, chacun avec
son propre `feedUrl`. Prendre le premier venu abonnerait a l'emission du
voisin — c'est ce que verifient les tests d'extraction ci-dessous.
"""

import pytest

from app.core import feed_search as fs


class TestAiguillage:
    def test_source_inconnue_ne_pretend_rien(self):
        assert fs.search("gopher", "arte") == []

    def test_recherche_vide_ne_sort_pas_sur_le_reseau(self, monkeypatch):
        def interdit(*_a, **_kw):
            raise AssertionError("aucune requete ne doit partir")

        monkeypatch.setattr(fs, "_open", interdit)
        assert fs.search(fs.SOURCE_PODCAST, "   ") == []

    def test_un_libelle_par_source(self):
        assert len(fs.source_labels()) == len(fs.SOURCE_CODES)


class TestChainesYouTube:
    def _faux_ytdlp(self, monkeypatch, entries):
        class FauxYDL:
            def __init__(self, _opts):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

            def extract_info(self, _url, download=False):
                return {"entries": entries}

        import yt_dlp
        monkeypatch.setattr(yt_dlp, "YoutubeDL", FauxYDL)

    def test_une_chaine_devient_un_resultat_suivable(self, monkeypatch):
        self._faux_ytdlp(monkeypatch, [{
            "title": "ARTE",
            "uploader": "ARTE",
            "channel_follower_count": 5020000,
            "url": "https://www.youtube.com/channel/UCwI-JbGNsojunnHbFAc0M4Q",
        }])
        resultats = fs.search(fs.SOURCE_YOUTUBE, "arte")
        assert len(resultats) == 1
        entree = resultats[0]
        assert entree["title"] == "ARTE"
        assert entree["url"].endswith("UCwI-JbGNsojunnHbFAc0M4Q")
        assert entree["source"] == fs.SOURCE_YOUTUBE
        # L'adresse est deja la : aucun appel reseau au moment du choix.
        assert fs.resolve(entree) == entree["url"]

    def test_le_nombre_d_abonnes_distingue_la_vraie_chaine(self, monkeypatch):
        """Les copies pullulent sur YouTube : sans ce reperage, impossible de
        choisir entre deux chaines du meme nom."""
        self._faux_ytdlp(monkeypatch, [
            {"title": "ARTE", "url": "https://x/1", "channel_follower_count": 5020000},
            {"title": "ARTE", "url": "https://x/2", "channel_follower_count": 12},
        ])
        detail = [e["detail"] for e in fs.search(fs.SOURCE_YOUTUBE, "arte")]
        assert "5 020 000" in detail[0]
        assert "12" in detail[1]

    def test_une_entree_sans_adresse_est_ecartee(self, monkeypatch):
        self._faux_ytdlp(monkeypatch, [None, {"title": "Sans adresse"},
                                       {"title": "Bonne", "url": "https://x/1"}])
        assert [e["title"] for e in fs.search(fs.SOURCE_YOUTUBE, "x")] == ["Bonne"]

    def test_une_panne_ressort_en_message_lisible(self, monkeypatch):
        class FauxYDL:
            def __init__(self, _opts):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

            def extract_info(self, _url, download=False):
                raise RuntimeError("HTTP Error 429")

        import yt_dlp
        monkeypatch.setattr(yt_dlp, "YoutubeDL", FauxYDL)
        with pytest.raises(fs.SearchError):
            fs.search(fs.SOURCE_YOUTUBE, "arte")


class TestCollectionsArte:
    def test_seules_les_collections_se_suivent(self, monkeypatch):
        """Une video seule n'a pas de suite : s'y abonner n'aurait aucun sens."""
        from app.core import site_search

        monkeypatch.setattr(site_search, "search", lambda *a, **kw: {"entries": [
            {"title": "Un documentaire", "_dl_type": "video",
             "webpage_url": "https://www.arte.tv/fr/videos/123-000-A/x/"},
            {"title": "Karambolage", "_dl_type": "playlist",
             "_summary": "Les Europeens decryptes",
             "webpage_url": "https://www.arte.tv/fr/videos/RC-014034/karambolage/"},
        ]})
        resultats = fs.search(fs.SOURCE_ARTE, "karambolage")
        assert [e["title"] for e in resultats] == ["Karambolage"]
        assert resultats[0]["url"].endswith("RC-014034/karambolage/")

    def test_une_collection_sans_adresse_est_ecartee(self, monkeypatch):
        from app.core import site_search

        monkeypatch.setattr(site_search, "search", lambda *a, **kw: {"entries": [
            {"title": "Sans adresse", "_dl_type": "playlist"},
        ]})
        assert fs.search(fs.SOURCE_ARTE, "x") == []


FEED_VOISIN = "https://exemple.test/voisin.xml"
FEED_VOULU = "https://radiofrance-podcast.net/podcast09/rss_13940.xml"

# Page Apple simplifiee : un podcast suggere AVANT celui qu'on a choisi. Les
# deux portent un `feedUrl` ; seul le second est le bon.
PAGE_APPLE = (
    '{"id":"111111","name":"Un autre podcast",'
    '"feedUrl":"' + FEED_VOISIN + '"}'
    + "," * 50 +
    '{"id":"912451024","name":"Affaires sensibles",'
    '"feedUrl":"' + FEED_VOULU + '"}'
)


class TestPodcasts:
    def _faux_itunes(self, monkeypatch, results):
        monkeypatch.setattr(fs, "_json_get", lambda _url: {"results": results})

    def test_l_adresse_n_est_pas_cherchee_pendant_la_recherche(self, monkeypatch):
        """Une page Apple pese pres d'un mega-octet : la lire pour chacun des
        vingt resultats rendrait la recherche interminable."""
        self._faux_itunes(monkeypatch, [{
            "collectionName": "Affaires sensibles", "artistName": "France Inter",
            "trackCount": 138, "collectionId": 912451024,
            "collectionViewUrl": "https://podcasts.apple.com/fr/podcast/x/id912451024",
        }])
        monkeypatch.setattr(fs, "_text_get", lambda _url: (_ for _ in ()).throw(
            AssertionError("la page ne doit pas etre lue ici")))
        resultats = fs.search(fs.SOURCE_PODCAST, "affaires sensibles")
        assert resultats[0]["title"] == "Affaires sensibles"
        assert resultats[0]["url"] == "", "l'adresse est resolue au choix"

    def test_l_adresse_donnee_par_apple_est_gardee(self, monkeypatch):
        self._faux_itunes(monkeypatch, [{
            "collectionName": "The Daily", "artistName": "The New York Times",
            "feedUrl": "https://feeds.simplecast.com/Sl5CSM3S",
            "collectionId": 1200361736, "collectionViewUrl": "https://apple/x",
        }])
        entree = fs.search(fs.SOURCE_PODCAST, "the daily")[0]
        assert entree["url"] == "https://feeds.simplecast.com/Sl5CSM3S"
        assert fs.resolve(entree) == entree["url"]

    def test_l_adresse_est_lue_dans_la_page_du_bon_podcast(self, monkeypatch):
        """Le coeur du sujet : la page contient aussi des podcasts suggeres."""
        monkeypatch.setattr(fs, "_text_get", lambda _url: PAGE_APPLE)
        entree = {"source": fs.SOURCE_PODCAST, "url": "",
                  "_apple_id": 912451024,
                  "_apple_page": "https://podcasts.apple.com/fr/podcast/x/id912451024"}
        assert fs.resolve(entree) == FEED_VOULU

    def test_les_barres_echappees_sont_retablies(self, monkeypatch):
        monkeypatch.setattr(fs, "_text_get", lambda _url: (
            '{"id":"42","feedUrl":"https:\\/\\/exemple.test\\/flux.xml"}'))
        entree = {"source": fs.SOURCE_PODCAST, "url": "", "_apple_id": 42,
                  "_apple_page": "https://apple/x"}
        assert fs.resolve(entree) == "https://exemple.test/flux.xml"

    def test_adresse_introuvable_le_dit_sans_jargon(self, monkeypatch):
        monkeypatch.setattr(fs, "_text_get", lambda _url: "<html>rien ici</html>")
        entree = {"source": fs.SOURCE_PODCAST, "url": "", "_apple_id": 42,
                  "_apple_page": "https://apple/x"}
        with pytest.raises(fs.SearchError) as exc:
            fs.resolve(entree)
        assert "saisir" in str(exc.value), "le repli manuel doit etre indique"

    def test_sans_page_apple_on_n_invente_pas(self, monkeypatch):
        entree = {"source": fs.SOURCE_PODCAST, "url": "", "_apple_id": None,
                  "_apple_page": ""}
        with pytest.raises(fs.SearchError):
            fs.resolve(entree)

    def test_un_resultat_sans_titre_est_ecarte(self, monkeypatch):
        self._faux_itunes(monkeypatch, [{"artistName": "Personne"},
                                        {"collectionName": "Bon", "trackCount": 3}])
        assert [e["title"] for e in fs.search(fs.SOURCE_PODCAST, "x")] == ["Bon"]
