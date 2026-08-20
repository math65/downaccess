"""Analyse des flux d'abonnement.

Les fixtures sont de **vrais** flux (chaine ARTE, podcast BBC) tronques a
quelques entrees : les tests restent fideles au terrain sans dependre du
reseau ni de ce que ces sources publient aujourd'hui.
"""

import pytest

from app.core.subscriptions import (
    KIND_PODCAST,
    KIND_YOUTUBE,
    FeedEntry,
    FeedError,
    _feed_from_html,
    _iso,
    _normalize_url,
    _youtube_feed_from_url,
    parse_feed,
)
from tests.conftest import read_fixture


class TestFluxYouTube:
    @pytest.fixture
    def flux(self):
        return parse_feed(read_fixture("youtube_channel.atom.xml"))

    def test_titre_de_la_chaine(self, flux):
        titre, _entries = flux
        assert titre == "ARTE"

    def test_entrees_completes(self, flux):
        _titre, entries = flux
        assert len(entries) == 3
        for entry in entries:
            assert entry.entry_id
            assert entry.title
            assert entry.url.startswith("https://www.youtube.com/")

    def test_identifiant_est_celui_de_la_video(self, flux):
        """Il sert de cle de deduplication : il doit etre stable, pas une URL
        qui pourrait changer de forme."""
        _titre, entries = flux
        assert all(len(e.entry_id) == 11 for e in entries)

    def test_date_lisible(self, flux):
        _titre, entries = flux
        assert entries[0].published_label().count("/") == 2


class TestFluxPodcast:
    @pytest.fixture
    def flux(self):
        return parse_feed(read_fixture("podcast.rss.xml"))

    def test_titre_du_podcast(self, flux):
        titre, _entries = flux
        assert titre == "Global News Podcast"

    def test_url_est_le_media_pas_la_page(self, flux):
        """Regression : le `<link>` d'un item pointe souvent vers une page web.
        Ce qu'il faut telecharger, c'est l'`<enclosure>`."""
        _titre, entries = flux
        assert all("bbc.co.uk" in e.url for e in entries)
        assert all(not e.url.endswith(".html") for e in entries)

    def test_resume_present(self, flux):
        _titre, entries = flux
        assert entries[0].summary


class TestFluxInvalides:
    def test_html_n_est_pas_un_flux(self):
        with pytest.raises(FeedError):
            parse_feed(b"<html><body>Bonjour</body></html>")

    def test_xml_casse(self):
        with pytest.raises(FeedError):
            parse_feed(b"<rss><channel>")

    def test_flux_vide(self):
        vide = b'<?xml version="1.0"?><rss version="2.0"><channel><title>Rien</title></channel></rss>'
        with pytest.raises(FeedError):
            parse_feed(vide)

    def test_declaration_d_entites_refusee(self):
        """Un flux n'a aucune raison de declarer une DTD. Les refuser coupe
        court aux bombes d'expansion d'entites sur du XML non controle."""
        bombe = (b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">]>'
                 b'<rss version="2.0"><channel><title>&lol;</title></channel></rss>')
        with pytest.raises(FeedError, match="claration non autoris"):
            parse_feed(bombe)


class TestDates:
    @pytest.mark.parametrize("brut", [
        "2026-08-19T10:00:00+00:00",       # Atom
        "2026-08-19T10:00:00Z",            # Atom avec Z
        "Tue, 19 Aug 2026 10:00:00 +0000",  # RSS
    ])
    def test_formats_acceptes(self, brut):
        assert _iso(brut).startswith("2026-08-19")

    @pytest.mark.parametrize("brut", ["", "   ", "pas une date"])
    def test_date_illisible_ne_casse_pas(self, brut):
        assert _iso(brut) == ""

    def test_entree_sans_date(self):
        assert FeedEntry(published="").published_label() == ""


class TestResolutionSansReseau:
    @pytest.mark.parametrize("url,attendu", [
        ("https://www.youtube.com/channel/UCwI-JbGNsojunnHbFAc0M4Q",
         "https://www.youtube.com/feeds/videos.xml?channel_id=UCwI-JbGNsojunnHbFAc0M4Q"),
        ("https://www.youtube.com/playlist?list=PLabcdefghijklmnopqr",
         "https://www.youtube.com/feeds/videos.xml?playlist_id=PLabcdefghijklmnopqr"),
        ("https://www.youtube.com/watch?v=x&list=UUabcdefghijklmnopqr",
         "https://www.youtube.com/feeds/videos.xml?playlist_id=UUabcdefghijklmnopqr"),
    ])
    def test_identifiant_deja_dans_l_url(self, url, attendu):
        """Aucune requete de decouverte n'est necessaire dans ces cas."""
        assert _youtube_feed_from_url(url) == attendu

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/@arte",     # handle : demande la page
        "https://example.org/podcast",       # autre site
    ])
    def test_decouverte_necessaire(self, url):
        assert _youtube_feed_from_url(url) == ""

    @pytest.mark.parametrize("html,base,attendu", [
        ('<link rel="alternate" type="application/rss+xml" href="https://a.org/f.xml">',
         "https://a.org", "https://a.org/f.xml"),
        ('<link type="application/atom+xml" rel="alternate" href="/flux.xml">',
         "https://a.org/page", "https://a.org/flux.xml"),
        ('<link rel="alternate" type="application/rss+xml" href="//cdn.a.org/f.xml">',
         "https://a.org", "https://cdn.a.org/f.xml"),
    ])
    def test_flux_declare_dans_la_page(self, html, base, attendu):
        assert _feed_from_html(html, base) == attendu

    def test_page_sans_flux(self):
        assert _feed_from_html("<html><head></head></html>", "https://a.org") == ""


class TestNormalisationUrl:
    def test_ajoute_le_schema(self):
        assert _normalize_url("youtube.com/@arte") == "https://youtube.com/@arte"

    def test_conserve_http(self):
        assert _normalize_url("http://a.org/f.xml") == "http://a.org/f.xml"

    @pytest.mark.parametrize("url", ["", "   "])
    def test_adresse_vide_refusee(self, url):
        with pytest.raises(FeedError):
            _normalize_url(url)

    @pytest.mark.parametrize("url", ["ftp://a.org/f.xml", "file:///etc/passwd"])
    def test_schema_non_web_refuse(self, url):
        with pytest.raises(FeedError):
            _normalize_url(url)


def test_types_exposes():
    assert KIND_YOUTUBE != KIND_PODCAST
