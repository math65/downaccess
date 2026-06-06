"""
Dialogue de mise à jour de DownAccess.
Affiche la nouvelle version, les notes de release en texte brut
et propose de mettre à jour.

100 % accessible NVDA : contrôles natifs uniquement.
"""
import re

import wx



def _md_to_plain(md: str) -> str:
    """Convertit du Markdown basique en texte lisible."""
    text = md
    # Commentaires HTML (ex. marqueurs de langue <!-- notes:fr -->) → supprimes
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    # Titres : ## Titre → Titre
    text = re.sub(r'^#{1,3}\s+', '', text, flags=re.MULTILINE)
    # Gras : **texte** → texte
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Italique : *texte* → texte
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Liens : [texte](url) → texte
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    # Listes à puces : - texte → • texte
    text = re.sub(r'^[-*]\s+', '• ', text, flags=re.MULTILINE)
    # Supprimer les lignes vides multiples
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class UpdateDialog(wx.Dialog):
    """
    Dialogue affiché quand une nouvelle version est disponible.
    Les release notes sont affichées en texte brut dans un TextCtrl.
    """

    def __init__(self, parent, new_version: str, release_notes: str):
        super().__init__(
            parent,
            title=_("Mise à jour disponible — DownAccess {version}").format(version=new_version),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(600, 480),
        )
        self._notes_text = _md_to_plain(release_notes or _("Aucune note disponible."))
        self._build_ui(new_version)
        self.CentreOnParent()

        # Focus sur les notes (contenu avant bouton — règle projet)
        self._txt_notes.SetInsertionPoint(0)
        self._txt_notes.SetFocus()

    def _build_ui(self, new_version: str) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        # En-tête
        lbl_title = wx.StaticText(
            self,
            label=_("DownAccess {version} est disponible !").format(version=new_version),
        )
        font = lbl_title.GetFont()
        font.SetPointSize(font.GetPointSize() + 2)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        lbl_title.SetFont(font)
        sizer.Add(lbl_title, 0, wx.ALL, 12)

        # Label pour le champ de notes
        lbl_notes = wx.StaticText(self, label=_("Notes de version :"))
        sizer.Add(lbl_notes, 0, wx.LEFT | wx.RIGHT, 12)

        # Notes en texte brut (lecture seule, multi-ligne)
        self._txt_notes = wx.TextCtrl(
            self,
            value=self._notes_text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.BORDER_SUNKEN,
            name=_("Notes de version"),
        )
        sizer.Add(self._txt_notes, 1, wx.EXPAND | wx.ALL, 8)

        # Boutons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_update = wx.Button(
            self, wx.ID_OK,
            label=_("Mettre à jour maintenant"),
            name=_("Mettre à jour maintenant"),
        )
        self.btn_later = wx.Button(
            self, wx.ID_CANCEL,
            label=_("Plus tard"),
            name=_("Reporter la mise à jour"),
        )
        self.btn_update.SetDefault()
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self.btn_update, 0, wx.RIGHT, 8)
        btn_sizer.Add(self.btn_later,  0, wx.RIGHT, 8)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.SetSizer(sizer)
