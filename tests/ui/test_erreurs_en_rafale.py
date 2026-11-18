"""Une meme panne sur toute la file n'ouvre qu'une fenetre.

`_on_dl_error` est appele une fois par telechargement. Quand la meme panne
frappe une file entiere — le controle anti-robot sur deux cents fictions audio
enfilees d'un coup — l'application ouvrait deux cents fenetres modales a la
suite, plus vite que l'utilisateur ne pouvait les fermer (rapport de Brad,
2026-09-02, sur 0.2.3).

L'item reste marque en erreur dans la liste : le retour visuel existe toujours,
c'est la repetition de la fenetre qui n'a pas lieu d'etre.
"""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core.downloader import bot_check_message, drm_locked_video_message
from app.core.settings import DEFAULTS
from app.ui.main_window import MainWindow

# Deux pannes qui ouvrent leur fenetre tout de suite, parce qu'elles demandent
# une action. Les echecs simples, eux, attendent le bilan de fin de file
# (cf. `TestBilanDeFinDeFile`).
PANNE = bot_check_message()
AUTRE_PANNE = drm_locked_video_message()


class FausseListe:
    def __init__(self):
        self.en_erreur = []

    def error_item(self, dl_id):
        self.en_erreur.append(dl_id)

    def SetFocus(self):
        pass

    def get_title(self, dl_id):
        return f"Titre {dl_id}"


class FausseFile:
    """La file tourne encore : la rafale n'est pas finie."""
    def __init__(self, idle=False):
        self.is_idle = idle


class FausseFenetre:
    """Juste ce qu'il faut pour traverser `_on_dl_error`."""

    def __init__(self, idle=False):
        self.settings = dict(DEFAULTS)
        self.download_list = FausseListe()
        self._progress = {}
        self._gauge_dl_id = None
        self._error_bursts = {}
        self._deferred_failures = []
        self.rapports = []
        self._queue = FausseFile(idle)
        self._dl_data = {}
        self.statuts = []
        self.dialogues = []

    def set_status(self, message):
        self.statuts.append(message)

    def _log_history(self, *a, **kw):
        pass

    # Chacun des trois parcours qui ouvrent une fenetre.
    def _on_login_required(self, dl_id):
        self.dialogues.append(("login", dl_id))

    def _login_failed_after_attempt(self, dl_id):
        self.dialogues.append(("login_failed", dl_id))

    def _start_error_report(self, dl_id, message, groups=None):
        self.rapports.append((dl_id, message, groups))

    def _redownload_as_audio(self, dl_id):
        pass

    _claim_error_dialog          = MainWindow._claim_error_dialog
    _error_burst_key             = MainWindow._error_burst_key
    _reset_error_bursts_if_idle  = MainWindow._reset_error_bursts_if_idle
    _clear_error_burst_for_site  = MainWindow._clear_error_burst_for_site
    _is_actionable_error         = MainWindow._is_actionable_error
    _show_error_dialog           = MainWindow._show_error_dialog
    _flush_failures_if_idle      = MainWindow._flush_failures_if_idle
    # `staticmethod` : sans le rehabiller, `self` partirait comme URL.
    _site_label                  = staticmethod(MainWindow._site_label)


def echouer(faux, dl_id, message, url="https://www.youtube.com/watch?v=a",
            login_required=False, use_cookies=False):
    faux._dl_data[dl_id] = {"url": url, "use_cookies": use_cookies}
    MainWindow._on_dl_error(faux, dl_id, message, login_required)


@pytest.fixture
def sans_fenetre_d_erreur(monkeypatch):
    """Compte les ouvertures de la fenetre d'erreur generique."""
    from app.ui import main_window as mw
    ouvertes = []

    class FauxDialogue:
        def __init__(self, parent, message, audio_offer=False):
            ouvertes.append(message)

        def ShowModal(self):
            return wx.ID_OK

        def wants_audio(self):
            return False

        def wants_report(self):
            return False

        def Destroy(self):
            pass

    monkeypatch.setattr(mw, "ErrorDialog", FauxDialogue)
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **kw: fn(*a, **kw))
    return ouvertes


class TestUneSeuleFenetre:

    def test_la_premiere_erreur_ouvre_bien_sa_fenetre(self, sans_fenetre_d_erreur):
        faux = FausseFenetre()
        echouer(faux, "d1", PANNE)
        assert len(sans_fenetre_d_erreur) == 1

    def test_les_suivantes_identiques_n_en_ouvrent_aucune(self, sans_fenetre_d_erreur):
        faux = FausseFenetre()
        for i in range(200):
            echouer(faux, f"d{i}", PANNE)
        assert len(sans_fenetre_d_erreur) == 1, "une seule fenetre pour 200 echecs"

    def test_les_items_restent_tous_marques_en_erreur(self, sans_fenetre_d_erreur):
        """Etouffer la fenetre ne doit pas etouffer le retour visuel."""
        faux = FausseFenetre()
        for i in range(200):
            echouer(faux, f"d{i}", PANNE)
        assert len(faux.download_list.en_erreur) == 200

    def test_la_barre_d_etat_donne_le_compte(self, sans_fenetre_d_erreur):
        faux = FausseFenetre()
        for i in range(5):
            echouer(faux, f"d{i}", PANNE)
        assert "5" in faux.statuts[-1]

    def test_une_autre_panne_a_droit_a_sa_fenetre(self, sans_fenetre_d_erreur):
        """Le garde-fou porte sur la repetition, pas sur les erreurs en general."""
        faux = FausseFenetre()
        echouer(faux, "d1", PANNE)
        echouer(faux, "d2", AUTRE_PANNE)
        assert len(sans_fenetre_d_erreur) == 2

    def test_un_autre_site_a_droit_a_sa_fenetre(self, sans_fenetre_d_erreur):
        faux = FausseFenetre()
        echouer(faux, "d1", PANNE)
        echouer(faux, "d2", PANNE, url="https://vimeo.com/1")
        assert len(sans_fenetre_d_erreur) == 2


class TestParcoursDeConnexion:

    def test_une_seule_fenetre_de_connexion_pour_toute_la_file(
            self, sans_fenetre_d_erreur):
        faux = FausseFenetre()
        for i in range(50):
            echouer(faux, f"d{i}", "Private video", login_required=True)
        assert faux.dialogues == [("login", "d0")]

    def test_une_seule_fenetre_de_connexion_insuffisante(self, sans_fenetre_d_erreur):
        """Le parcours qui a noye Brad : deja connecte, donc `use_cookies`."""
        faux = FausseFenetre()
        for i in range(50):
            echouer(faux, f"d{i}", "Private video",
                    login_required=True, use_cookies=True)
        assert faux.dialogues == [("login_failed", "d0")]

    def test_les_deux_parcours_restent_distincts(self, sans_fenetre_d_erreur):
        faux = FausseFenetre()
        echouer(faux, "d1", "Private video", login_required=True)
        echouer(faux, "d2", "Private video", login_required=True,
                use_cookies=True)
        assert [n for n, _ in faux.dialogues] == ["login", "login_failed"]


class TestRearmement:

    def test_la_file_retombee_a_vide_rearme(self, sans_fenetre_d_erreur):
        """La rafale est finie : une panne plus tard merite sa fenetre."""
        faux = FausseFenetre(idle=True)
        echouer(faux, "d1", PANNE)
        echouer(faux, "d2", PANNE)   # etouffee, puis rearmement
        echouer(faux, "d3", PANNE)
        assert len(sans_fenetre_d_erreur) == 2

    def test_un_telechargement_reussi_rearme_le_site(self, sans_fenetre_d_erreur):
        faux = FausseFenetre()
        echouer(faux, "d1", PANNE)
        faux._clear_error_burst_for_site("https://www.youtube.com/watch?v=b")
        echouer(faux, "d2", PANNE)
        assert len(sans_fenetre_d_erreur) == 2

    def test_la_reussite_d_un_autre_site_ne_rearme_rien(self, sans_fenetre_d_erreur):
        faux = FausseFenetre()
        echouer(faux, "d1", PANNE)
        faux._clear_error_burst_for_site("https://vimeo.com/1")
        echouer(faux, "d2", PANNE)
        assert len(sans_fenetre_d_erreur) == 1


# --- Bilan de fin de file (demande de Brad, 2026-11-16) ----------------------

@pytest.fixture
def bilans(monkeypatch):
    """Compte les bilans ouverts ; `bilans.clic = "report"` simule le bouton."""
    from app.ui import main_window as mw

    class Ouverts(list):
        clic = "close"

    ouverts = Ouverts()

    class FauxBilan:
        def __init__(self, parent, summary):
            ouverts.append(summary)

        def ShowModal(self):
            return wx.ID_CANCEL

        def wants_report(self):
            return ouverts.clic == "report"

        def Destroy(self):
            pass

    monkeypatch.setattr(mw, "FailureSummaryDialog", FauxBilan)
    return ouverts


class TestBilanDeFinDeFile:

    def test_aucune_fenetre_tant_que_la_file_tourne(self, sans_fenetre_d_erreur, bilans):
        faux = FausseFenetre()
        for i in range(20):
            echouer(faux, f"d{i}", "HTTP Error 403: Forbidden")
        assert sans_fenetre_d_erreur == [] and bilans == []
        assert len(faux.download_list.en_erreur) == 20, "le retour visuel reste"

    def test_un_seul_bilan_quand_la_file_est_vide(self, sans_fenetre_d_erreur, bilans):
        faux = FausseFenetre()
        for i in range(14):
            echouer(faux, f"a{i}", "Video retiree")
        for i in range(6):
            echouer(faux, f"b{i}", "HTTP Error 403: Forbidden")
        faux._queue.is_idle = True
        faux._flush_failures_if_idle()
        assert len(bilans) == 1 and sans_fenetre_d_erreur == []
        assert "20" in bilans[0]
        # La cause la plus frequente d'abord.
        assert bilans[0].index("Video retiree") < bilans[0].index("403")
        # Deja montre : un second signal de file vide ne le rouvre pas.
        faux._flush_failures_if_idle()
        assert len(bilans) == 1

    def test_un_seul_rapport_pour_tous(self, sans_fenetre_d_erreur, bilans):
        bilans.clic = "report"
        faux = FausseFenetre()
        for i in range(3):
            echouer(faux, f"d{i}", "HTTP Error 403: Forbidden")
        faux._queue.is_idle = True
        faux._flush_failures_if_idle()
        assert len(faux.rapports) == 1, "un rapport, donc un mail"
        _dl_id, _message, groupes = faux.rapports[0]
        assert sum(len(g.failures) for g in groupes) == 3

    def test_un_echec_isole_garde_sa_fenetre_habituelle(self, sans_fenetre_d_erreur, bilans):
        faux = FausseFenetre(idle=True)
        echouer(faux, "d1", "HTTP Error 403: Forbidden")
        assert sans_fenetre_d_erreur == ["HTTP Error 403: Forbidden"]
        assert bilans == []

    def test_une_panne_qui_demande_une_action_n_attend_pas(self, sans_fenetre_d_erreur, bilans):
        faux = FausseFenetre()
        echouer(faux, "d1", PANNE)
        assert sans_fenetre_d_erreur == [PANNE]
        assert faux._deferred_failures == []
