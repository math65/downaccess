"""Extracteurs maison : ici.fr (demande de Seb, 2026-11-17).

yt-dlp repondait « Unsupported URL » alors que la page donne le MP3. Ces tests
passent par un VRAI `YoutubeDL` : ils cassent aussi si yt-dlp change la forme
de son registre interne d'extracteurs (cf. `extra_extractors.register`).
"""
from pathlib import Path

import pytest
import yt_dlp

from app.core import downloader, extra_extractors

URL = "https://www.ici.fr/emissions/nom-de-la-serie/titre-de-l-emission-6800523"
FIXTURE = Path(__file__).parent.parent / "fixtures" / "ici_fr_emission.html"


@pytest.fixture
def page(monkeypatch):
    contenu = {"html": FIXTURE.read_text(encoding="utf-8")}
    monkeypatch.setattr(extra_extractors.IciFrIE, "_download_webpage",
                        lambda self, url, video_id, *a, **kw: contenu["html"])
    return contenu


def test_emission_ici_fr_reconnue(page):
    with downloader._open_ydl({"quiet": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(URL, download=False)
    assert info["extractor_key"] == "IciFr"
    assert info["title"] == "Titre de l'émission : un exemple"
    assert info["url"].endswith("ITEMA_EXEMPLE.mp3")
    assert info["ext"] == "mp3"
    assert info["duration"] == 45 * 60 + 12
    assert info["series"] == "Nom de la série"
    assert info["upload_date"] == "20261116"


def test_page_sans_emission_erreur_sans_appel_a_github(page):
    page["html"] = "<html><head></head><body></body></html>"
    with downloader._open_ydl({"quiet": True, "skip_download": True}) as ydl:
        with pytest.raises(yt_dlp.utils.DownloadError) as err:
            ydl.extract_info(URL, download=False)
    assert "github" not in str(err.value).lower()
    # Le message clair « aucune vidéo sur cette page » doit prendre le relais.
    assert downloader.is_no_formats_error(str(err.value))


def test_les_autres_sites_gardent_leur_extracteur():
    with downloader._open_ydl({"quiet": True}) as ydl:
        cles = list(ydl._ies)
    assert cles[0] == "IciFr"
    assert "Youtube" in cles and cles[-1] == "Generic"
    assert not extra_extractors.IciFrIE.suitable("https://www.youtube.com/watch?v=x")
    # La page d'un programme (liste d'emissions) n'est pas une emission.
    assert not extra_extractors.IciFrIE.suitable("https://www.ici.fr/emissions/nom-de-la-serie")


# --- Programme entier : la liste complete, pas seulement les liens de la page ---

PROGRAMME = "https://www.ici.fr/emissions/nom-de-la-serie"


def _emission(n, path="", title=None):
    return {
        "id": f"id-{n}",
        "path": path,
        "title": title if title is not None else f"Émission\xa0{n}",
        "standFirst": "",
        "media": {
            "sources": [{"broadcastType": "aod", "url": f"https://media.exemple/{n}.mp3"}],
            "startTime": 1794816600 + n * 86400,
            "duration": 2700 + n,
        },
    }


@pytest.fixture
def programme(monkeypatch):
    """Deux pages d'API : une emission avec sa page, trois sans (dont une au
    titre generique et une sans fichier audio)."""
    pages = {
        1: {"hasNextPage": True, "results": [
            _emission(1, path="emissions/nom-de-la-serie/premiere-emission-1000001"),
            _emission(2)]},
        2: {"hasNextPage": False, "results": [
            _emission(3, title="Nom de la série"),
            {"id": "id-4", "path": "", "title": "Sans audio", "media": {"sources": []}}]},
    }
    demandes = []

    def faux_json(self, url, video_id, *a, query=None, **kw):
        demandes.append(query["pageNumber"])
        return pages.get(query["pageNumber"], {})

    html = (FIXTURE.parent / "ici_fr_programme.html").read_text(encoding="utf-8")
    monkeypatch.setattr(extra_extractors.IciFrProgrammeIE, "_download_webpage",
                        lambda self, url, video_id, *a, **kw: html)
    monkeypatch.setattr(extra_extractors.IciFrProgrammeIE, "_download_json", faux_json)
    return demandes


def _analyser(url, **opts):
    with downloader._open_ydl({"quiet": True, "skip_download": True, **opts}) as ydl:
        return ydl.extract_info(url, download=False)


def test_programme_liste_toutes_les_emissions(programme):
    """Plus de la moitie des emissions n'ont pas de page : elles ne sont pas
    dans les liens de la page du programme, seulement dans son API."""
    info = _analyser(PROGRAMME, extract_flat=True)
    assert info["extractor_key"] == "IciFrProgramme"
    assert info["title"] == "Nom de la série"
    entrees = list(info["entries"])
    assert [e["title"] for e in entrees][:2] == ["Émission 1", "Émission 2"]
    assert len(entrees) == 3, "l'emission sans fichier audio est ecartee"
    assert programme == [1, 2], "on s'arrete a la derniere page annoncee"
    # Celle qui a sa page garde une adresse propre.
    assert entrees[0]["url"] == PROGRAMME + "/premiere-emission-1000001"
    assert len({e["url"] for e in entrees}) == 3


def test_titre_generique_complete_par_la_date(programme):
    """Sans cela, toutes ces emissions porteraient le meme nom de fichier."""
    entrees = list(_analyser(PROGRAMME, extract_flat=True)["entries"])
    assert entrees[2]["title"].startswith("Nom de la série - ")
    assert entrees[2]["title"] != "Nom de la série"


def test_emission_sans_page_se_telecharge_depuis_son_adresse(programme):
    """L'adresse fabriquee suffit : aucun nouvel appel au site."""
    entree = list(_analyser(PROGRAMME, extract_flat=True)["entries"])[1]
    del programme[:]
    info = _analyser(entree["url"])
    assert info.get("_type", "video") == "video"
    assert info["title"] == "Émission 2"
    assert info["url"] == "https://media.exemple/2.mp3"
    assert info["duration"] == 2702 and info["series"] == "Nom de la série"
    assert programme == [], "tout etait deja dans l'adresse"


def test_programme_sans_liste_erreur_claire(programme, monkeypatch):
    monkeypatch.setattr(extra_extractors.IciFrProgrammeIE, "_download_webpage",
                        lambda self, url, video_id, *a, **kw: "<h1>Vide</h1>")
    with pytest.raises(yt_dlp.utils.DownloadError) as err:
        _analyser(PROGRAMME, extract_flat=True)
    assert downloader.is_no_formats_error(str(err.value))
    assert "github" not in str(err.value).lower()
