"""Fenetres d'abonnement et de nouveautes."""

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.gui

from app.core.subscriptions import FeedEntry, Subscription
from app.ui.new_items_dialog import NewItemsDialog
from app.ui.subscriptions_dialog import (
    FORMAT_CODES,
    AddSubscriptionDialog,
    SubscriptionsDialog,
)


def entree(n=1):
    return FeedEntry(entry_id=f"id{n}", title=f"Episode {n}",
                     url=f"https://a/{n}", published="2026-08-19T10:00:00+00:00",
                     summary=f"Resume {n}")


def abonnement(**kw):
    base = {"sub_id": "s1", "title": "ARTE", "url": "https://youtube.com/@arte",
            "feed_url": "https://youtube.com/feed", "kind": "youtube"}
    base.update(kw)
    return Subscription(**base)


class TestAjoutAbonnement:
    def test_focus_sur_l_adresse(self, frame):
        dlg = AddSubscriptionDialog(frame)
        assert dlg.FindFocus() is dlg.txt_url
        dlg.Destroy()

    def test_format_par_defaut_delegue_aux_preferences(self, frame):
        """Une chaine vide veut dire « suivre le reglage general » : changer
        ses preferences ne doit pas obliger a reprendre chaque abonnement."""
        dlg = AddSubscriptionDialog(frame)
        assert dlg.get_format() == ""
        dlg.Destroy()

    def test_choix_d_un_format_explicite(self, frame):
        dlg = AddSubscriptionDialog(frame)
        dlg.choice_fmt.SetSelection(FORMAT_CODES.index("mp3"))
        assert dlg.get_format() == "mp3"
        dlg.Destroy()

    def test_telechargement_automatique_desactive_par_defaut(self, frame):
        dlg = AddSubscriptionDialog(frame)
        assert dlg.get_auto_download() is False
        dlg.Destroy()

    def test_adresse_nettoyee(self, frame):
        dlg = AddSubscriptionDialog(frame)
        dlg.txt_url.SetValue("  https://a/f.xml  ")
        assert dlg.get_url() == "https://a/f.xml"
        dlg.Destroy()


class TestListeAbonnements:
    def test_liste_vide_le_dit(self, frame, appdata):
        dlg = SubscriptionsDialog(frame)
        assert "aucune" in dlg.lbl.GetLabel().lower()
        assert dlg.lst.GetItemCount() == 0
        dlg.Destroy()

    def test_affiche_les_colonnes_utiles(self, frame, appdata, monkeypatch):
        from app.core import subscriptions as subs
        monkeypatch.setattr(subs, "load", lambda: [
            abonnement(format_spec="mp3", auto_download=True)])
        dlg = SubscriptionsDialog(frame)
        assert dlg.lst.GetItemCount() == 1
        assert dlg.lst.GetItemText(0, 0) == "ARTE"
        assert dlg.lst.GetItemText(0, 3) in ("oui", "yes")
        assert dlg.lst.GetItemText(0, 4)          # derniere verification
        dlg.Destroy()

    def test_bouton_nouveautes_inactif_sans_rien(self, frame, appdata, monkeypatch):
        from app.core import subscriptions as subs
        monkeypatch.setattr(subs, "load", lambda: [abonnement()])
        dlg = SubscriptionsDialog(frame)
        assert dlg.btn_new.IsEnabled() is False
        dlg.Destroy()

    def test_bouton_nouveautes_compte_ce_qui_attend(self, frame, appdata, monkeypatch):
        from app.core import subscriptions as subs
        monkeypatch.setattr(subs, "load", lambda: [abonnement()])
        dlg = SubscriptionsDialog(frame, on_new_items=lambda f, s: None,
                                  pending={"s1": [entree(1), entree(2)]})
        assert dlg.btn_new.IsEnabled() is True
        assert "2" in dlg.btn_new.GetLabel()
        dlg.Destroy()


class TestNouveautes:
    def test_focus_sur_la_liste(self, frame):
        dlg = NewItemsDialog(frame, [("ARTE", entree(1), "")])
        assert dlg.FindFocus() is dlg.lst
        dlg.Destroy()

    def test_tout_coche_par_defaut(self, frame):
        items = [("ARTE", entree(i), "") for i in range(3)]
        dlg = NewItemsDialog(frame, items)
        assert len(dlg.get_selected()) == 3
        dlg.Destroy()

    def test_selection_reflete_les_cases(self, frame):
        items = [("ARTE", entree(i), "") for i in range(3)]
        dlg = NewItemsDialog(frame, items)
        dlg.lst.CheckItem(1, False)
        choisis = dlg.get_selected()
        assert len(choisis) == 2
        assert all(e.entry_id != "id1" for _s, e, _f in choisis)
        dlg.Destroy()

    def test_tout_decocher_puis_tout_cocher(self, frame):
        items = [("ARTE", entree(i), "") for i in range(3)]
        dlg = NewItemsDialog(frame, items)
        dlg._check_all(False)
        assert dlg.get_selected() == []
        dlg._check_all(True)
        assert len(dlg.get_selected()) == 3
        dlg.Destroy()

    def test_colonnes_titre_source_date(self, frame):
        dlg = NewItemsDialog(frame, [("Global News", entree(7), "mp3")])
        assert dlg.lst.GetItemText(0, 0) == "Episode 7"
        assert dlg.lst.GetItemText(0, 1) == "Global News"
        assert dlg.lst.GetItemText(0, 2) == "19/08/2026"
        dlg.Destroy()

    def test_resume_de_l_element_courant(self, frame):
        dlg = NewItemsDialog(frame, [("ARTE", entree(1), "")])
        assert dlg.txt_summary.GetValue() == "Resume 1"
        dlg.Destroy()

    def test_element_sans_resume(self, frame):
        vide = FeedEntry(entry_id="x", title="T", url="https://a/x")
        dlg = NewItemsDialog(frame, [("ARTE", vide, "")])
        assert dlg.txt_summary.GetValue()      # message de repli, jamais vide
        dlg.Destroy()

    def test_format_de_l_abonnement_conserve(self, frame):
        """Chaque nouveaute repart avec le format choisi pour sa source."""
        dlg = NewItemsDialog(frame, [("Podcast", entree(1), "mp3")])
        assert dlg.get_selected()[0][2] == "mp3"
        dlg.Destroy()
