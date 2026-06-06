"""
Dialogue de rapport d'erreur DownAccess.
Explique le processus de diagnostic, collecte un commentaire utilisateur,
affiche la progression et le résultat de l'envoi.
"""
import re

import wx
from app.core import speech

# Validation simple : un local, un @, un domaine avec au moins un point,
# sans espace. Suffisant pour écarter les champs vides ou manifestement faux.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ReportDialog(wx.Dialog):
    """
    Étape 1 : présente le formulaire (commentaire + bouton Lancer).
    Étape 2 : affiche "Diagnostic en cours…" pendant le re-run.
    Étape 3 : affiche le résultat (succès ou erreur).
    """

    def __init__(self, parent, url: str, site: str, error_message: str,
                 on_confirmed=None, saved_email: str = ""):
        super().__init__(
            parent,
            title=_("Envoyer un rapport d'erreur"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(560, 420),
        )
        self._url           = url
        self._site          = site
        self._error_message = error_message
        self._on_confirmed  = on_confirmed  # Callable[[str, str], None] | None
        self._saved_email   = saved_email
        self._build_ui()
        self.txt_email.SetFocus()
        self.Centre()
        speech.speak(
            _("Rapport d'erreur. URL : {url}. Site : {site}.").format(
                url=self._url or _("inconnue"),
                site=self._site or _("inconnu"),
            )
        )

    # ------------------------------------------------------------------
    # Construction de l'UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._sizer = wx.BoxSizer(wx.VERTICAL)

        # Explication
        intro = _(
            "Pour générer un rapport complet, DownAccess va relancer le "
            "téléchargement en mode diagnostic afin de capturer les logs "
            "détaillés de yt-dlp.\n\n"
            "URL : {url}\n"
            "Site : {site}"
        ).format(url=self._url or "—", site=self._site or "—")
        lbl_intro = wx.StaticText(self, label=intro)
        lbl_intro.Wrap(520)
        self._sizer.Add(lbl_intro, 0, wx.ALL, 12)

        # Champ email
        lbl_email = wx.StaticText(
            self, label=_("Votre email (obligatoire, pour qu'on puisse vous répondre) :")
        )
        self._sizer.Add(lbl_email, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.txt_email = wx.TextCtrl(self, name=_("Adresse email"), value=self._saved_email)
        self._sizer.Add(self.txt_email, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        # Champ commentaire
        lbl_comment = wx.StaticText(self, label=_("Commentaire (optionnel) :"))
        self._sizer.Add(lbl_comment, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        self.txt_comment = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE,
            name=_("Commentaire"),
        )
        self._sizer.Add(self.txt_comment, 1, wx.EXPAND | wx.ALL, 8)

        # Zone de statut (cachée au départ)
        self.lbl_status = wx.StaticText(self, label="")
        self._sizer.Add(self.lbl_status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        # Boutons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_send   = wx.Button(self, wx.ID_OK,
                                    label=_("Lancer le diagnostic et envoyer"),
                                    name=_("Lancer le diagnostic et envoyer"))
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL, label=_("Annuler"),
                                    name=_("Annuler"))
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.btn_send,   0, wx.RIGHT, 8)
        btn_sizer.Add(self.btn_cancel, 0, wx.RIGHT, 8)
        self._sizer.Add(btn_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.btn_send.Bind(wx.EVT_BUTTON,   self._on_send)
        self.btn_cancel.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_CANCEL))

        self.SetSizer(self._sizer)

    # ------------------------------------------------------------------
    # Transitions d'état
    # ------------------------------------------------------------------

    def set_running(self) -> None:
        """Passe en mode "diagnostic en cours"."""
        self.btn_send.Enable(False)
        self.btn_cancel.Enable(False)
        self.txt_email.Enable(False)
        self.txt_comment.Enable(False)
        self.lbl_status.SetLabel(_("Diagnostic en cours…"))
        speech.speak(_("Diagnostic en cours."))
        speech.braille(_("Diagnostic en cours…"))
        self.Layout()

    def set_done(self, success: bool, message: str) -> None:
        """Affiche le résultat et réactive le bouton Fermer."""
        self.lbl_status.SetLabel(message)
        self.btn_cancel.SetLabel(_("Fermer"))
        self.btn_cancel.Enable(True)
        self.btn_cancel.SetFocus()
        speech.speak(message)
        speech.braille(message)
        self.Layout()

    # ------------------------------------------------------------------
    # Accesseurs
    # ------------------------------------------------------------------

    def get_email(self) -> str:
        return self.txt_email.GetValue().strip()

    def get_comment(self) -> str:
        return self.txt_comment.GetValue().strip()

    # ------------------------------------------------------------------
    # Événements
    # ------------------------------------------------------------------

    def _on_send(self, _event) -> None:
        """Valide l'email (obligatoire), lance le diagnostic et appelle le callback."""
        comment = self.get_comment()
        email   = self.get_email()
        if not _EMAIL_RE.match(email):
            dlg = wx.MessageDialog(
                self,
                _("Veuillez saisir une adresse email valide pour que nous "
                  "puissions vous répondre.\n\n"
                  "Sans adresse, nous ne pouvons pas vous aider sur ce "
                  "problème.\n\n"
                  "Exemple : prenom@exemple.com"),
                _("Adresse email requise"),
                wx.OK | wx.ICON_WARNING,
            )
            dlg.ShowModal()
            dlg.Destroy()
            self.txt_email.SetFocus()
            return
        self.set_running()
        if self._on_confirmed:
            self._on_confirmed(comment, email)
