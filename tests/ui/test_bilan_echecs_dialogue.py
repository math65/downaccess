"""Fenetre du bilan de fin de file : regles d'accessibilite du projet."""
import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.ui.failure_summary_dialog import FailureSummaryDialog

BILAN = "20 téléchargements ont échoué.\n\n14 téléchargements — Vidéo retirée"


def test_le_bilan_est_dans_une_zone_de_texte_etiquetee(frame):
    """NVDA lit une zone de texte en lecture seule, pas un StaticText."""
    dlg = FailureSummaryDialog(frame, BILAN)
    assert dlg.txt_summary.GetValue() == BILAN
    assert not dlg.txt_summary.IsEditable()
    assert dlg.txt_summary.GetName()
    dlg.Destroy()


def test_le_focus_arrive_sur_le_contenu(frame):
    dlg = FailureSummaryDialog(frame, BILAN)
    assert dlg.FindFocus() is dlg.txt_summary
    dlg.Destroy()


def test_boutons_etiquetes_et_echap_ferme_sans_rapport(frame):
    dlg = FailureSummaryDialog(frame, BILAN)
    for bouton in (dlg.btn_report, dlg.btn_close):
        assert bouton.GetLabel() and bouton.GetName()
    assert dlg.GetEscapeId() == wx.ID_CANCEL
    assert dlg.wants_report() is False
    dlg.Destroy()
