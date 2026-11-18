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
