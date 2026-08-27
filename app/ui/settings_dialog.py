import subprocess

import wx

from app.core import settings as cfg
from app.core import speech
from app.core import i18n
from app.core.browser import available_browsers
from app.core.ffmpeg_utils import get_ffmpeg_path
# Formats proposes pour un abonnement : meme liste que la fenetre Abonnements,
# pour qu'un ajout de format n'ait a se faire qu'a un seul endroit.
from app.ui.subscriptions_dialog import FORMAT_CODES as SUBSCRIPTION_FORMAT_CODES
from app.ui.subscriptions_dialog import _format_labels as _subscription_format_labels

# Cles internes (jamais traduites). Memes codes que add_url_dialog (format par
# defaut) ; « manual » et « subtitles_only » ne sont pas des defauts utiles.
POST_CHOICES = ["auto", "mp4", "mp3", "m4a", "amc_video", "amc_audio"]
SUBTITLE_FORMAT_CHOICES = ["srt", "vtt", "original"]
SUBTITLE_MODE_CHOICES = ["separate", "embed", "burn"]
LANGUAGE_CHOICES = ["auto", "fr", "en"]
ANNOUNCE_CHOICES = ["always", "foreground", "never"]
AD_MODE_CHOICES = ["ask", "ad_only", "original_and_ad", "original_only"]
PAGING_CHOICES = ["pages", "continuous"]
CHAPTERS_MODE_CHOICES = ["embed", "split", "ignore"]

# Limiteur de vitesse : valeurs en octets/sec. 0 = illimité.
RATELIMIT_VALUES = [
    0,
    256 * 1024,
    512 * 1024,
    1 * 1024 * 1024,
    2 * 1024 * 1024,
    5 * 1024 * 1024,
    10 * 1024 * 1024,
]


def _post_labels():
    return [
        _("Meilleure qualité automatique (fichier d'origine)"),
        _("Vidéo MP4 (H.264)"),
        _("Audio MP3"),
        _("Audio M4A"),
        _("Ouvrir avec Access Media Converter — vidéo"),
        _("Ouvrir avec Access Media Converter — audio seul"),
    ]


def _subtitle_format_labels():
    return [
        _("SRT"),
        _("VTT"),
        _("Original (sans conversion)"),
    ]


def _subtitle_mode_labels():
    return [
        _("Fichier séparé (.srt à côté de la vidéo)"),
        _("Inclus dans le conteneur (piste désactivable)"),
        _("Incrustés dans l'image (ré-encode la vidéo, plus lent)"),
    ]


def _ratelimit_labels():
    return [
        _("Illimité"),
        _("256 Ko/s"),
        _("512 Ko/s"),
        _("1 Mo/s"),
        _("2 Mo/s"),
        _("5 Mo/s"),
        _("10 Mo/s"),
    ]


def _announce_labels():
    return [
        _("Toujours"),
        _("Seulement quand DownAccess est au premier plan"),
        _("Jamais"),
    ]


def _ad_mode_labels():
    return [
        _("Demander à chaque fois"),
        _("Audiodescription seule"),
        _("Version originale + audiodescription"),
        _("Version originale seule"),
    ]


def _chapters_mode_labels():
    return [
        _("Garder un seul fichier, avec des repères de chapitres dedans"),
        _("Créer un fichier par chapitre"),
        _("Ignorer les chapitres"),
    ]


def _language_labels():
    detected = i18n.get_system_language_code()
    detected_msgid = i18n.get_language_name_msgid(detected) or detected
    return [
        _("Auto ({language})").format(language=_(detected_msgid)),
        _("Français"),
        _("English"),
    ]


class SettingsDialog(wx.Dialog):
    """
    Dialogue de préférences — 5 onglets.
    100 % accessible NVDA : labels associés, ordre Tab logique,
    focus sur le premier contrôle à l'ouverture.
    """

    def __init__(self, parent, settings: dict):
        super().__init__(
            parent,
            title=_("Préférences — DownAccess"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._settings = dict(settings)  # copie de travail
        self._initial_language = i18n.normalize_ui_language(
            self._settings.get("language", "auto")
        )
        self._restart_requested = False
        self._build_ui()
        self._load_values()
        self._bind_events()
        self.SetMinSize((540, 420))
        self.Fit()
        self.CentreOnParent()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.notebook = wx.Notebook(self)
        self.notebook.SetName(_("Onglets de préférences"))

        self._page_general   = self._build_page_general()
        self._page_formats   = self._build_page_formats()
        self._page_subs      = self._build_page_subscriptions()
        self._page_subtitles = self._build_page_subtitles()
        self._page_network   = self._build_page_network()
        self._page_advanced  = self._build_page_advanced()

        self.notebook.AddPage(self._page_general,   _("Général"))
        self.notebook.AddPage(self._page_formats,   _("Formats"))
        self.notebook.AddPage(self._page_subs,      _("Abonnements"))
        self.notebook.AddPage(self._page_subtitles, _("Sous-titres"))
        self.notebook.AddPage(self._page_network,   _("Réseau"))
        self.notebook.AddPage(self._page_advanced,  _("Avancé"))

        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 8)

        # Boutons OK / Annuler
        btn_sizer = wx.StdDialogButtonSizer()
        self.btn_ok     = wx.Button(self, wx.ID_OK,     label=_("Enregistrer"))
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL, label=_("Annuler"))
        self.btn_ok.SetDefault()
        btn_sizer.AddButton(self.btn_ok)
        btn_sizer.AddButton(self.btn_cancel)
        btn_sizer.Realize()
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.SetSizer(main_sizer)

        # Focus sur le premier champ du premier onglet
        self.txt_folder.SetFocus()

    # ---- Onglet Général ----

    def _build_page_general(self) -> wx.Panel:
        page = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Langue de l'interface
        lbl_language = wx.StaticText(page, label=_("Langue de l'interface :"))
        self.choice_language = wx.Choice(
            page,
            choices=_language_labels(),
            name=_("Langue de l'interface"),
        )
        self.choice_language.SetSelection(0)
        lbl_language_hint = wx.StaticText(
            page,
            label=_("Le changement de langue prendra effet au prochain démarrage."),
        )
        lbl_language_hint.SetForegroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        )

        # Dossier de destination
        lbl_folder = wx.StaticText(page, label=_("Dossier de destination :"))
        row_folder = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_folder = wx.TextCtrl(page, name=_("Dossier de destination"))
        self.btn_browse  = wx.Button(page, label=_("Parcourir…"))
        row_folder.Add(self.txt_folder, 1, wx.EXPAND | wx.RIGHT, 6)
        row_folder.Add(self.btn_browse, 0)

        # Téléchargements simultanés
        lbl_concurrent = wx.StaticText(page, label=_("Téléchargements simultanés :"))
        self.spin_concurrent = wx.SpinCtrl(page, min=1, max=10, initial=2,
                                           name=_("Téléchargements simultanés"))

        # Fragments en parallèle
        lbl_fragments = wx.StaticText(page, label=_("Fragments en parallèle par téléchargement :"))
        self.spin_fragments = wx.SpinCtrl(page, min=1, max=16, initial=1,
                                          name=_("Fragments en parallèle"))
        lbl_fragments_hint = wx.StaticText(
            page,
            label=_("Accélère le téléchargement en utilisant plusieurs connexions. 1 = désactivé."),
        )
        lbl_fragments_hint.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        # Action après téléchargement
        lbl_after = wx.StaticText(page, label=_("Action après téléchargement :"))
        self.chk_open_folder = wx.CheckBox(page,
            label=_("Ouvrir le dossier de destination quand tout est terminé"),
            name=_("Ouvrir le dossier de destination quand tout est terminé"))
        self.chk_organize = wx.CheckBox(page,
            label=_("Organiser dans des sous-dossiers par site"),
            name=_("Organiser dans des sous-dossiers par site"))
        self.chk_organize_playlist = wx.CheckBox(page,
            label=_("Organiser dans des sous-dossiers par playlist"),
            name=_("Organiser dans des sous-dossiers par playlist"))

        # Annonces vocales des téléchargements
        self.radio_announce = wx.RadioBox(
            page,
            label=_("Annoncer vocalement le début et la fin des téléchargements"),
            choices=_announce_labels(),
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
            name=_("Annonces vocales des téléchargements"),
        )
        lbl_announce_hint = wx.StaticText(
            page,
            label=_("L'information reste toujours visible dans la liste et la barre d'état."),
        )
        lbl_announce_hint.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        # Résultats de recherche
        lbl_results = wx.StaticText(page, label=_("Résultats de recherche :"))
        self.radio_paging = wx.RadioBox(
            page,
            label=_("Parcours des résultats"),
            choices=[
                _("Par pages (boutons Page précédente / Page suivante)"),
                _("En continu (la suite se charge en arrivant en bas de la liste)"),
            ],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
            name=_("Parcours des résultats"),
        )

        # Extraction guidée
        lbl_uge = wx.StaticText(page, label=_("Extraction guidée :"))
        lbl_browser = wx.StaticText(page, label=_("Navigateur à utiliser :"))
        installed = available_browsers()
        self._browser_codes = ["auto"] + [code for code, _n in installed]
        self.choice_browser = wx.Choice(
            page,
            choices=[_("Automatique")] + [name for _c, name in installed],
            name=_("Navigateur à utiliser"))
        lbl_browser_hint = wx.StaticText(page, label=_(
            "DownAccess ouvre le navigateur dans un profil séparé de votre "
            "navigation habituelle. Vous vous connectez aux sites une seule "
            "fois : la connexion est conservée pour les fois suivantes."))
        self.chk_intercept_title = wx.CheckBox(page,
            label=_("Utiliser le titre de la page comme nom de fichier (interception)"),
            name=_("Utiliser le titre de la page comme nom de fichier"))

        # Avertissements
        lbl_warn = wx.StaticText(page, label=_("Avertissements :"))
        self.btn_reset_warnings = wx.Button(page,
            label=_("Réinitialiser tous les avertissements"),
            name=_("Réinitialiser tous les avertissements"))

        sizer.Add(lbl_language,      0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.choice_language, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_language_hint, 0, wx.LEFT | wx.RIGHT | wx.TOP, 4)
        sizer.Add(lbl_folder,        0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(row_folder,        0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_concurrent,    0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.spin_concurrent, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_fragments,     0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.spin_fragments,  0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_fragments_hint,   0, wx.LEFT | wx.RIGHT | wx.TOP, 4)
        sizer.Add(lbl_after,         0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.chk_open_folder,       0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(self.chk_organize,          0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(self.chk_organize_playlist, 0, wx.LEFT | wx.RIGHT | wx.TOP, 4)
        sizer.Add(self.radio_announce,        0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(lbl_announce_hint,          0, wx.LEFT | wx.RIGHT | wx.TOP, 4)
        sizer.Add(lbl_results,                0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.radio_paging,          0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_uge,                    0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(lbl_browser,                0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(self.choice_browser,        0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_browser_hint,           0, wx.LEFT | wx.RIGHT | wx.TOP, 4)
        sizer.Add(self.chk_intercept_title,   0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_warn,                   0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.btn_reset_warnings,    0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        page.SetSizer(sizer)
        return page

    # ---- Onglet Abonnements ----

    def _build_page_subscriptions(self) -> wx.Panel:
        """Tout ce qui touche aux chaines, podcasts et collections suivis.

        Ces reglages vivaient dans l'onglet General, coinces entre le choix du
        navigateur et une option d'interception : personne ne les trouvait,
        alors qu'ils decident de ce qui se passe a chaque lancement.
        """
        page = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.chk_subs_start = wx.CheckBox(
            page,
            label=_("Relever les abonnements au lancement"),
            name=_("Relever les abonnements au lancement"))
        self.chk_subs_start.SetToolTip(_(
            "Vérifie discrètement vos chaînes, podcasts et collections suivis "
            "au démarrage. Décochez pour ne relever que sur demande, depuis la "
            "fenêtre Abonnements."))

        self.chk_subs_daily = wx.CheckBox(
            page,
            label=_("Au plus une fois par jour"),
            name=_("Au plus une fois par jour"))
        self.chk_subs_daily.SetToolTip(_(
            "Si vous ouvrez DownAccess plusieurs fois dans la journée, le "
            "relevé n'a lieu qu'au premier lancement."))

        self.radio_subs_new = wx.RadioBox(
            page,
            label=_("Quand il y a du nouveau au démarrage"),
            choices=[_("Ne rien afficher : le nombre apparaît dans le menu Fichier"),
                     _("Ouvrir la fenêtre des nouveautés")],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
            name=_("Quand il y a du nouveau au démarrage"))

        self.chk_subs_announce = wx.CheckBox(
            page,
            label=_("Annoncer vocalement les nouveautés"),
            name=_("Annoncer vocalement les nouveautés"))
        self.chk_subs_announce.SetToolTip(_(
            "Pour être prévenu sans regarder le menu. Sans effet si aucun "
            "lecteur d'écran n'est actif."))

        lbl_fmt = wx.StaticText(page, label=_(
            "Format des nouveaux abonnements :"))
        self.choice_subs_fmt = wx.Choice(
            page, choices=_subscription_format_labels(),
            name=_("Format des nouveaux abonnements"))
        lbl_fmt_hint = wx.StaticText(page, label=_(
            "Proposé par défaut quand vous suivez une nouvelle source. Chaque "
            "abonnement garde ensuite son propre format."))

        for widget, marge in ((self.chk_subs_start, 12),
                              (self.chk_subs_daily, 4),
                              (self.radio_subs_new, 12),
                              (self.chk_subs_announce, 12),
                              (lbl_fmt, 12),
                              (self.choice_subs_fmt, 6),
                              (lbl_fmt_hint, 4)):
            sizer.Add(widget, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, marge)

        # Ordre de tabulation explicite : le relevé d'abord, ses consequences
        # ensuite.
        self.chk_subs_daily.MoveAfterInTabOrder(self.chk_subs_start)
        self.radio_subs_new.MoveAfterInTabOrder(self.chk_subs_daily)
        self.chk_subs_announce.MoveAfterInTabOrder(self.radio_subs_new)
        self.choice_subs_fmt.MoveAfterInTabOrder(self.chk_subs_announce)

        page.SetSizer(sizer)
        return page

    # ---- Onglet Formats ----

    def _build_page_formats(self) -> wx.Panel:
        page = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.choice_post = wx.RadioBox(
            page,
            label=_("Format par défaut"),
            choices=_post_labels(),
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
            name=_("Format par défaut"),
        )

        sizer.Add(self.choice_post, 0, wx.EXPAND | wx.ALL, 12)

        lbl_ad = wx.StaticText(
            page,
            label=_("Audiodescription (france.tv, Arte) :"))
        self.choice_ad = wx.Choice(
            page,
            choices=_ad_mode_labels(),
            name=_("Mode audiodescription"),
        )
        self.choice_ad.SetToolTip(
            _("Sur les sites compatibles, choisit automatiquement la ou les "
              "pistes audio sans afficher de dialogue."))
        sizer.Add(lbl_ad, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.choice_ad, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.chk_metadata = wx.CheckBox(
            page,
            label=_("Renseigner les informations du fichier (titre, auteur, "
                    "pochette, chapitres)"),
            name=_("Renseigner les informations du fichier"),
        )
        self.chk_metadata.SetToolTip(
            _("Votre lecteur audio peut alors annoncer le titre et l'auteur, "
              "et classer le fichier dans votre bibliothèque."))
        sizer.Add(self.chk_metadata, 0, wx.EXPAND | wx.ALL, 12)

        lbl_chapters = wx.StaticText(
            page,
            label=_("Quand la vidéo propose des chapitres :"))
        self.choice_chapters = wx.Choice(
            page,
            choices=_chapters_mode_labels(),
            name=_("Traitement des chapitres"),
        )
        self.choice_chapters.SetToolTip(
            _("Les repères permettent à votre lecteur d'annoncer le chapitre en "
              "cours et d'y sauter directement. Un fichier par chapitre est plus "
              "pratique sur les très longs enregistrements, mais le fichier "
              "entier n'est alors pas conservé."))
        sizer.Add(lbl_chapters, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.choice_chapters, 0,
                  wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        page.SetSizer(sizer)
        return page

    # ---- Onglet Sous-titres ----

    def _build_page_subtitles(self) -> wx.Panel:
        page = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.chk_auto_subs = wx.CheckBox(page,
            label=_("Télécharger automatiquement les sous-titres"),
            name=_("Télécharger automatiquement les sous-titres"))

        lbl_langs = wx.StaticText(page, label=_("Langues préférées (codes séparés par des virgules) :"))
        self.txt_langs = wx.TextCtrl(page, name=_("Langues des sous-titres"))
        self.txt_langs.SetHint("fr, en")

        self.choice_subfmt = wx.RadioBox(
            page,
            label=_("Format des sous-titres"),
            choices=_subtitle_format_labels(),
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
            name=_("Format des sous-titres"),
        )

        self.choice_submode = wx.RadioBox(
            page,
            label=_("Mode des sous-titres"),
            choices=_subtitle_mode_labels(),
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
            name=_("Mode des sous-titres"),
        )

        sizer.Add(self.chk_auto_subs, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(lbl_langs,          0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.txt_langs,     0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(self.choice_subfmt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.choice_submode, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        page.SetSizer(sizer)
        return page

    # ---- Onglet Réseau ----

    def _build_page_network(self) -> wx.Panel:
        page = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl_proxy_http = wx.StaticText(page, label=_("Proxy HTTP/HTTPS :"))
        self.txt_proxy_http = wx.TextCtrl(page, name=_("Proxy HTTP"))
        self.txt_proxy_http.SetHint("http://proxy:8080")

        lbl_proxy_socks = wx.StaticText(page, label=_("Proxy SOCKS4/5 :"))
        self.txt_proxy_socks = wx.TextCtrl(page, name=_("Proxy SOCKS"))
        self.txt_proxy_socks.SetHint("socks5://127.0.0.1:1080")

        lbl_ua = wx.StaticText(page, label=_("User-Agent personnalisé (laisser vide = défaut) :"))
        self.txt_useragent = wx.TextCtrl(page, name=_("User-Agent"))

        lbl_ratelimit = wx.StaticText(page, label=_("Limite de vitesse de téléchargement :"))
        self.choice_ratelimit = wx.Choice(
            page,
            choices=_ratelimit_labels(),
            name=_("Limite de vitesse de téléchargement"),
        )
        self.choice_ratelimit.SetSelection(0)

        # Sites avec cookies
        lbl_cookie_sites = wx.StaticText(
            page,
            label=_("Sites utilisant les cookies du navigateur :"),
        )
        self.lst_cookie_sites = wx.ListBox(page, size=(-1, 80),
                                           name=_("Sites avec cookies"))
        lbl_cookies_hint = wx.StaticText(
            page,
            label=_("Sites où vous vous êtes connecté. Ils sont ajoutés automatiquement après une connexion, et vos identifiants y sont réutilisés pour les téléchargements."),
        )
        lbl_cookies_hint.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        self.btn_remove_cookie_site = wx.Button(page, label=_("Supprimer le site sélectionné"),
                                                name=_("Supprimer le site sélectionné"))
        self.btn_remove_cookie_site.Bind(wx.EVT_BUTTON, self._on_remove_cookie_site)

        sizer.Add(lbl_proxy_http,      0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.txt_proxy_http,  0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_proxy_socks,     0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.txt_proxy_socks, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_ua,              0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.txt_useragent,   0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_ratelimit,        0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.choice_ratelimit, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_cookie_sites,     0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.lst_cookie_sites, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_cookies_hint,     0, wx.LEFT | wx.RIGHT | wx.TOP, 4)
        sizer.Add(self.btn_remove_cookie_site, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        page.SetSizer(sizer)
        return page

    # ---- Onglet Avancé ----

    def _build_page_advanced(self) -> wx.Panel:
        page = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Chemin ffmpeg
        lbl_ffmpeg = wx.StaticText(page, label=_("Chemin vers ffmpeg :"))
        row_ffmpeg = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_ffmpeg = wx.TextCtrl(page, name=_("Chemin ffmpeg"))
        self.txt_ffmpeg.SetHint("ffmpeg")
        self.btn_ffmpeg_browse = wx.Button(page, label=_("Parcourir…"),
                                           name=_("Parcourir ffmpeg"))
        self.btn_ffmpeg_test   = wx.Button(page, label=_("Tester"),
                                           name=_("Tester ffmpeg"))
        row_ffmpeg.Add(self.txt_ffmpeg,       1, wx.EXPAND | wx.RIGHT, 6)
        row_ffmpeg.Add(self.btn_ffmpeg_browse, 0, wx.RIGHT, 4)
        row_ffmpeg.Add(self.btn_ffmpeg_test,   0)

        # Emplacement d'Access Media Converter
        lbl_amc = wx.StaticText(page,
            label=_("Emplacement d'Access Media Converter (vide = détection "
                    "automatique) :"))
        row_amc = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_amc = wx.TextCtrl(page, name=_("Emplacement d'Access Media Converter"))
        self.btn_amc_browse = wx.Button(page, label=_("Parcourir…"),
                                        name=_("Parcourir Access Media Converter"))
        row_amc.Add(self.txt_amc,       1, wx.EXPAND | wx.RIGHT, 6)
        row_amc.Add(self.btn_amc_browse, 0)

        # Options yt-dlp supplémentaires
        lbl_ytdlp_opts = wx.StaticText(page,
            label=_("Options yt-dlp supplémentaires (raw, une par ligne) :"))
        self.txt_ytdlp_opts = wx.TextCtrl(page,
            style=wx.TE_MULTILINE,
            size=(-1, 80),
            name=_("Options yt-dlp supplémentaires"),
        )
        self.txt_ytdlp_opts.SetHint("--no-playlist\n--restrict-filenames")

        sizer.Add(lbl_ffmpeg,         0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(row_ffmpeg,         0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_amc,            0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(row_amc,            0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        sizer.Add(lbl_ytdlp_opts,     0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        sizer.Add(self.txt_ytdlp_opts, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)

        page.SetSizer(sizer)
        return page

    # ------------------------------------------------------------------
    # Chargement / sauvegarde des valeurs
    # ------------------------------------------------------------------

    def _load_values(self) -> None:
        s = self._settings

        # Langue
        lang = i18n.normalize_ui_language(s.get("language", "auto"))
        lang_idx = LANGUAGE_CHOICES.index(lang) if lang in LANGUAGE_CHOICES else 0
        self.choice_language.SetSelection(lang_idx)

        # Général
        self.txt_folder.SetValue(s.get("download_folder", ""))
        self.spin_concurrent.SetValue(s.get("max_concurrent_downloads", 2))
        self.spin_fragments.SetValue(s.get("concurrent_fragments", 1))
        self.chk_open_folder.SetValue(s.get("open_folder_when_done", False))
        self.chk_organize.SetValue(s.get("organize_by_site", False))
        self.chk_organize_playlist.SetValue(s.get("organize_by_playlist", False))
        self.radio_paging.SetSelection(
            PAGING_CHOICES.index(s.get("results_paging", "pages"))
            if s.get("results_paging", "pages") in PAGING_CHOICES else 0)
        browser = s.get("browser_choice", "auto")
        self.choice_browser.SetSelection(
            self._browser_codes.index(browser) if browser in self._browser_codes else 0)
        self.chk_intercept_title.SetValue(s.get("intercept_use_page_title", True))
        self.chk_subs_start.SetValue(bool(s.get("subscriptions_check_on_start", True)))
        self.chk_subs_daily.SetValue(bool(s.get("subscriptions_daily_only", False)))
        self.radio_subs_new.SetSelection(
            1 if s.get("subscriptions_on_new") == "window" else 0)
        self.chk_subs_announce.SetValue(bool(s.get("subscriptions_announce", False)))
        fmt = s.get("subscriptions_default_format", "")
        self.choice_subs_fmt.SetSelection(
            SUBSCRIPTION_FORMAT_CODES.index(fmt)
            if fmt in SUBSCRIPTION_FORMAT_CODES else 0)
        announce = s.get("download_announcements", "always")
        ann_idx = ANNOUNCE_CHOICES.index(announce) if announce in ANNOUNCE_CHOICES else 0
        self.radio_announce.SetSelection(ann_idx)

        # Formats
        post = s.get("post_processing", "auto")
        idx = POST_CHOICES.index(post) if post in POST_CHOICES else 0
        self.choice_post.SetSelection(idx)
        ad_mode = s.get("audio_description_mode", "ask")
        self.chk_metadata.SetValue(bool(s.get("embed_metadata", True)))
        chap_mode = s.get("chapters_mode", "embed")
        chap_idx = (CHAPTERS_MODE_CHOICES.index(chap_mode)
                    if chap_mode in CHAPTERS_MODE_CHOICES else 0)
        self.choice_chapters.SetSelection(chap_idx)
        ad_idx = AD_MODE_CHOICES.index(ad_mode) if ad_mode in AD_MODE_CHOICES else 0
        self.choice_ad.SetSelection(ad_idx)

        # Sous-titres
        self.chk_auto_subs.SetValue(s.get("auto_subtitles", False))
        self.txt_langs.SetValue(", ".join(s.get("subtitle_langs", ["fr", "en"])))
        subfmt = s.get("subtitle_format", "srt")
        sfmt_idx = SUBTITLE_FORMAT_CHOICES.index(subfmt) if subfmt in SUBTITLE_FORMAT_CHOICES else 0
        self.choice_subfmt.SetSelection(sfmt_idx)
        submode = s.get("subtitle_mode", "separate")
        smode_idx = SUBTITLE_MODE_CHOICES.index(submode) if submode in SUBTITLE_MODE_CHOICES else 0
        self.choice_submode.SetSelection(smode_idx)

        # Réseau
        self.txt_proxy_http.SetValue(s.get("proxy_http", ""))
        self.txt_proxy_socks.SetValue(s.get("proxy_socks", ""))
        self.txt_useragent.SetValue(s.get("user_agent", ""))
        rl = s.get("ratelimit_bytes", 0)
        rl_idx = RATELIMIT_VALUES.index(rl) if rl in RATELIMIT_VALUES else 0
        self.choice_ratelimit.SetSelection(rl_idx)

        # Cookies
        # Sites avec cookies
        self.lst_cookie_sites.Clear()
        for site in s.get("cookie_sites", []):
            self.lst_cookie_sites.Append(site)

        # Avancé
        self.txt_ffmpeg.SetValue(s.get("ffmpeg_path", "ffmpeg"))
        self.txt_amc.SetValue(s.get("amc_path", ""))
        self.txt_ytdlp_opts.SetValue("\n".join(s.get("ytdlp_extra_opts", [])))

    def _collect_values(self) -> dict:
        s = dict(self._settings)

        # Langue
        s["language"] = LANGUAGE_CHOICES[self.choice_language.GetSelection()]

        # Général
        s["download_folder"]          = self.txt_folder.GetValue().strip()
        s["max_concurrent_downloads"] = self.spin_concurrent.GetValue()
        s["concurrent_fragments"]     = self.spin_fragments.GetValue()
        s["open_folder_when_done"]    = self.chk_open_folder.GetValue()
        s["organize_by_site"]         = self.chk_organize.GetValue()
        s["organize_by_playlist"]     = self.chk_organize_playlist.GetValue()
        s["results_paging"] = PAGING_CHOICES[max(0, self.radio_paging.GetSelection())]
        s["browser_choice"] = self._browser_codes[max(0, self.choice_browser.GetSelection())]
        s["intercept_use_page_title"] = self.chk_intercept_title.GetValue()
        s["subscriptions_check_on_start"] = self.chk_subs_start.GetValue()
        s["subscriptions_daily_only"] = self.chk_subs_daily.GetValue()
        s["subscriptions_on_new"] = ("window" if self.radio_subs_new.GetSelection() == 1
                                     else "counter")
        s["subscriptions_announce"] = self.chk_subs_announce.GetValue()
        idx = self.choice_subs_fmt.GetSelection()
        s["subscriptions_default_format"] = (
            SUBSCRIPTION_FORMAT_CODES[idx]
            if 0 <= idx < len(SUBSCRIPTION_FORMAT_CODES) else "")
        s["download_announcements"]   = ANNOUNCE_CHOICES[self.radio_announce.GetSelection()]

        # Formats
        s["post_processing"] = POST_CHOICES[self.choice_post.GetSelection()]
        s["audio_description_mode"] = AD_MODE_CHOICES[self.choice_ad.GetSelection()]
        s["embed_metadata"] = self.chk_metadata.GetValue()
        s["chapters_mode"] = CHAPTERS_MODE_CHOICES[
            self.choice_chapters.GetSelection()]

        # Sous-titres
        s["auto_subtitles"]  = self.chk_auto_subs.GetValue()
        langs_raw = self.txt_langs.GetValue()
        s["subtitle_langs"]  = [lg.strip() for lg in langs_raw.split(",") if lg.strip()]
        s["subtitle_format"] = SUBTITLE_FORMAT_CHOICES[self.choice_subfmt.GetSelection()]
        s["subtitle_mode"]   = SUBTITLE_MODE_CHOICES[self.choice_submode.GetSelection()]

        # Réseau
        s["proxy_http"]  = self.txt_proxy_http.GetValue().strip()
        s["proxy_socks"] = self.txt_proxy_socks.GetValue().strip()
        s["user_agent"]  = self.txt_useragent.GetValue().strip()
        s["ratelimit_bytes"] = RATELIMIT_VALUES[self.choice_ratelimit.GetSelection()]

        # Sites avec cookies
        s["cookie_sites"] = [self.lst_cookie_sites.GetString(i)
                             for i in range(self.lst_cookie_sites.GetCount())]

        # Avancé
        s["ffmpeg_path"] = self.txt_ffmpeg.GetValue().strip() or "ffmpeg"
        s["amc_path"] = self.txt_amc.GetValue().strip()
        opts_raw = self.txt_ytdlp_opts.GetValue()
        s["ytdlp_extra_opts"] = [opt.strip() for opt in opts_raw.splitlines() if opt.strip()]

        return s

    # ------------------------------------------------------------------
    # Événements
    # ------------------------------------------------------------------

    def _bind_events(self) -> None:
        self.btn_ok.Bind(wx.EVT_BUTTON,     self._on_ok)
        self.btn_browse.Bind(wx.EVT_BUTTON, self._on_browse_folder)
        self.btn_ffmpeg_browse.Bind(wx.EVT_BUTTON, self._on_browse_ffmpeg)
        self.btn_ffmpeg_test.Bind(wx.EVT_BUTTON,   self._on_test_ffmpeg)
        self.btn_amc_browse.Bind(wx.EVT_BUTTON,    self._on_browse_amc)
        self.btn_reset_warnings.Bind(wx.EVT_BUTTON, self._on_reset_warnings)

    def _on_reset_warnings(self, _event) -> None:
        n = len(self._settings.get("suppressed_warnings") or [])
        if n == 0:
            wx.MessageBox(
                _("Aucun avertissement n'est actuellement masqué."),
                _("Avertissements"),
                wx.OK | wx.ICON_INFORMATION, self,
            )
            return
        self._settings["suppressed_warnings"] = []
        cfg.save(self._settings)
        if n > 1:
            msg = _("{n} avertissements ont été réactivés.").format(n=n)
        else:
            msg = _("{n} avertissement a été réactivé.").format(n=n)
        wx.MessageBox(
            msg,
            _("Avertissements réinitialisés"),
            wx.OK | wx.ICON_INFORMATION, self,
        )

    def _on_remove_cookie_site(self, _event) -> None:
        sel = self.lst_cookie_sites.GetSelection()
        if sel == wx.NOT_FOUND:
            wx.MessageBox(
                _("Sélectionnez un site à supprimer."),
                _("Aucune sélection"), wx.OK | wx.ICON_INFORMATION, self,
            )
            return
        self.lst_cookie_sites.Delete(sel)

    def _on_ok(self, _event) -> None:
        s = self._collect_values()
        if not s.get("download_folder"):
            wx.MessageBox(
                _("Le dossier de destination ne peut pas être vide."),
                _("Champ requis"), wx.OK | wx.ICON_WARNING, self,
            )
            self.notebook.SetSelection(0)
            self.txt_folder.SetFocus()
            return
        # Si la langue effective change, proposer un redemarrage immediat.
        old_resolved = i18n.resolve_language(self._initial_language)
        new_resolved = i18n.resolve_language(
            i18n.normalize_ui_language(s.get("language", "auto"))
        )
        if old_resolved != new_resolved:
            with wx.MessageDialog(
                self,
                _("La langue a été modifiée. Voulez-vous redémarrer DownAccess maintenant pour appliquer le changement ?"),
                _("Redémarrer DownAccess ?"),
                wx.YES_NO | wx.ICON_QUESTION,
            ) as dlg:
                self._restart_requested = (dlg.ShowModal() == wx.ID_YES)
        self._settings = s
        self.EndModal(wx.ID_OK)

    def restart_requested(self) -> bool:
        return self._restart_requested

    def _on_browse_folder(self, _event) -> None:
        current = self.txt_folder.GetValue()
        with wx.DirDialog(
            self,
            _("Choisir le dossier de destination"),
            defaultPath=current,
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.txt_folder.SetValue(dlg.GetPath())

    def _on_browse_ffmpeg(self, _event) -> None:
        with wx.FileDialog(
            self,
            _("Chemin vers ffmpeg"),
            wildcard=_("Exécutable (*.exe)|*.exe|Tous les fichiers|*"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.txt_ffmpeg.SetValue(dlg.GetPath())

    def _on_browse_amc(self, _event) -> None:
        with wx.FileDialog(
            self,
            _("Emplacement d'Access Media Converter"),
            wildcard=_("Exécutable (*.exe)|*.exe|Tous les fichiers|*"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.txt_amc.SetValue(dlg.GetPath())

    def _on_test_ffmpeg(self, _event) -> None:
        path = get_ffmpeg_path({"ffmpeg_path": self.txt_ffmpeg.GetValue().strip()})
        try:
            result = subprocess.run(
                [path, "-version"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                first_line = result.stdout.splitlines()[0] if result.stdout else "OK"
                speech.speak(_("ffmpeg trouvé."))
                wx.MessageBox(
                    _("ffmpeg trouvé :\n{first_line}").format(first_line=first_line),
                    _("Test ffmpeg réussi"), wx.OK | wx.ICON_INFORMATION, self,
                )
            else:
                speech.speak(_("Test ffmpeg échoué."))
                wx.MessageBox(
                    _("ffmpeg a retourné une erreur :\n{stderr}").format(stderr=result.stderr[:200]),
                    _("Test ffmpeg échoué"), wx.OK | wx.ICON_ERROR, self,
                )
        except FileNotFoundError:
            speech.speak(_("ffmpeg introuvable."))
            wx.MessageBox(
                _("ffmpeg introuvable à : {path}\n\nVérifiez le chemin ou installez ffmpeg.").format(path=path),
                _("ffmpeg non trouvé"), wx.OK | wx.ICON_ERROR, self,
            )
        except Exception as exc:
            wx.MessageBox(str(exc), _("Erreur"), wx.OK | wx.ICON_ERROR, self)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def get_settings(self) -> dict:
        """Retourne le dict de settings modifié (après OK)."""
        return self._settings
