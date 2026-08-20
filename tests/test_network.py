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

from app.core import subscriptions as subs
from app.core.transcript import TranscriptError, fetch_transcript

pytestmark = pytest.mark.network

CHAINE_YOUTUBE = "https://www.youtube.com/@Arte"
PODCAST = "https://podcasts.files.bbci.co.uk/p02nq0gn.rss"
VIDEO_AVEC_SOUS_TITRES = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


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
