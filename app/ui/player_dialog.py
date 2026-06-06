"""
PlayerDialog — fenêtre dédiée pour l'aperçu audio d'un résultat de recherche.

Utilise wx.media.MediaCtrl (backend Media Foundation natif Windows) — aucune
dépendance externe.

Raccourcis clavier :
    Espace            Lecture / Pause
    Flèche gauche     Reculer 10 s
    Flèche droite     Avancer 10 s
    Flèche haut       Volume +5 %
    Flèche bas        Volume -5 %
    Échap             Fermer
"""
import threading
import wx
import wx.media
import yt_dlp

from app.core import speech


_SEEK_STEP_MS  = 10_000   # 10 secondes
_VOLUME_STEP   = 5         # 5 %
_DEFAULT_VOL   = 80
_TIMER_MS      = 500


class PlayerDialog(wx.Dialog):
    """Lecteur audio modal avec contrôles natifs et raccourcis clavier."""

    def __init__(self, parent, web_url: str, title: str):
        super().__init__(
            parent,
            title=_("Aperçu — {title}").format(title=title),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(560, 280),
        )
        self._web_url = web_url
        self._title   = title
        self._is_playing = False
        self._duration_ms = 0
        self._seeking_user = False  # True quand l'utilisateur manipule le slider
        self._closing = False

        self._build_ui()
        self._bind_events()
        self.Centre()

        # Timer pour rafraîchir la position pendant la lecture
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_tick, self._timer)

        # Lancer l'extraction de l'URL de stream en arrière-plan
        threading.Thread(target=self._fetch_stream_url, daemon=True).start()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._lbl_title = wx.StaticText(self, label=self._title)
        font = self._lbl_title.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self._lbl_title.SetFont(font)
        sizer.Add(self._lbl_title, 0, wx.ALL, 10)

        self._lbl_status = wx.StaticText(self, label=_("Chargement…"))
        sizer.Add(self._lbl_status, 0, wx.LEFT | wx.RIGHT, 10)

        # MediaCtrl (audio seul → 1x1 px, pas affiché). Backend WMP10 pour
        # streaming HTTP fiable sur Windows ; fallback automatique sinon.
        try:
            self._media = wx.media.MediaCtrl(
                self,
                style=wx.SIMPLE_BORDER,
                szBackend=wx.media.MEDIABACKEND_WMP10,
                name=_("Lecteur audio"),
            )
        except Exception:
            self._media = wx.media.MediaCtrl(
                self,
                style=wx.SIMPLE_BORDER,
                name=_("Lecteur audio"),
            )
        self._media.SetMinSize((1, 1))
        sizer.Add(self._media, 0, wx.LEFT | wx.RIGHT, 10)

        # Position
        lbl_pos = wx.StaticText(self, label=_("Position :"))
        sizer.Add(lbl_pos, 0, wx.LEFT | wx.TOP, 10)
        self._slider_pos = wx.Slider(
            self, value=0, minValue=0, maxValue=1000,
            style=wx.SL_HORIZONTAL,
            name=_("Position de lecture"),
        )
        self._slider_pos.Disable()
        sizer.Add(self._slider_pos, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._lbl_time = wx.StaticText(self, label="0:00 / 0:00")
        sizer.Add(self._lbl_time, 0, wx.LEFT | wx.BOTTOM, 10)

        # Volume
        lbl_vol = wx.StaticText(self, label=_("Volume :"))
        sizer.Add(lbl_vol, 0, wx.LEFT, 10)
        self._slider_vol = wx.Slider(
            self, value=_DEFAULT_VOL, minValue=0, maxValue=100,
            style=wx.SL_HORIZONTAL,
            name=_("Volume"),
        )
        sizer.Add(self._slider_vol, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Boutons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_back  = wx.Button(self, label=_("Reculer 10 s"),  name=_("Reculer 10 secondes"))
        self._btn_play  = wx.Button(self, label=_("Lecture"),       name=_("Lecture / Pause"))
        self._btn_fwd   = wx.Button(self, label=_("Avancer 10 s"),  name=_("Avancer 10 secondes"))
        self._btn_close = wx.Button(self, wx.ID_CANCEL, label=_("Fermer"))
        self._btn_back.Disable()
        self._btn_play.Disable()
        self._btn_fwd.Disable()
        btn_sizer.Add(self._btn_back, 0, wx.RIGHT, 6)
        btn_sizer.Add(self._btn_play, 0, wx.RIGHT, 6)
        btn_sizer.Add(self._btn_fwd,  0, wx.RIGHT, 6)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(self._btn_close, 0)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)

    def _bind_events(self) -> None:
        self.Bind(wx.media.EVT_MEDIA_LOADED,   self._on_media_loaded)
        self.Bind(wx.media.EVT_MEDIA_FINISHED, self._on_media_finished)

        self._slider_pos.Bind(wx.EVT_SLIDER, self._on_seek)
        self._slider_vol.Bind(wx.EVT_SLIDER, self._on_volume)

        self._btn_back.Bind(wx.EVT_BUTTON, lambda e: self._seek_relative(-_SEEK_STEP_MS))
        self._btn_play.Bind(wx.EVT_BUTTON, lambda e: self._toggle_play())
        self._btn_fwd.Bind(wx.EVT_BUTTON,  lambda e: self._seek_relative(+_SEEK_STEP_MS))
        self.Bind(wx.EVT_BUTTON, self._on_close, id=wx.ID_CANCEL)

        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Bind(wx.EVT_CLOSE, self._on_close)

    # ------------------------------------------------------------------
    # Extraction URL stream
    # ------------------------------------------------------------------

    def _fetch_stream_url(self) -> None:
        try:
            opts = {
                "quiet": True,
                "no_warnings": True,
                "format": "bestaudio/best",
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self._web_url, download=False)
            stream_url = info.get("url")
            if not stream_url:
                wx.CallAfter(self._fail, _("Impossible d'extraire l'URL de streaming."))
                return
            wx.CallAfter(self._load_stream, stream_url)
        except Exception as e:
            wx.CallAfter(self._fail, str(e))

    def _load_stream(self, stream_url: str) -> None:
        if self._closing:
            return
        self._lbl_status.SetLabel(_("Préparation de la lecture…"))
        if not self._media.LoadURI(stream_url):
            self._fail(_("Le lecteur média n'a pas pu charger ce flux."))

    def _fail(self, message: str) -> None:
        if self._closing:
            return
        wx.MessageBox(message, _("Erreur d'aperçu"), wx.OK | wx.ICON_ERROR, self)
        self._on_close(None)

    # ------------------------------------------------------------------
    # Callbacks media
    # ------------------------------------------------------------------

    def _on_media_loaded(self, _event) -> None:
        if self._closing:
            return
        self._duration_ms = max(self._media.Length(), 1)
        self._slider_pos.SetMax(self._duration_ms)
        self._slider_pos.Enable()
        self._btn_back.Enable()
        self._btn_play.Enable()
        self._btn_fwd.Enable()
        self._media.SetVolume(_DEFAULT_VOL / 100.0)
        self._lbl_status.SetLabel(_("Lecture en cours."))
        self._update_time_label(0)
        if self._media.Play():
            self._is_playing = True
            self._btn_play.SetLabel(_("Pause"))
            self._timer.Start(_TIMER_MS)
            self._btn_play.SetFocus()
            speech.speak(_("Lecture."))
        else:
            self._fail(_("Le lecteur média n'a pas pu démarrer la lecture."))

    def _on_media_finished(self, _event) -> None:
        if self._closing:
            return
        self._is_playing = False
        self._btn_play.SetLabel(_("Lecture"))
        self._timer.Stop()
        self._slider_pos.SetValue(0)
        self._update_time_label(0)
        speech.speak(_("Aperçu terminé."))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _toggle_play(self) -> None:
        if self._duration_ms <= 0:
            return
        state = self._media.GetState()
        if state == wx.media.MEDIASTATE_PLAYING:
            self._media.Pause()
            self._is_playing = False
            self._btn_play.SetLabel(_("Lecture"))
            self._timer.Stop()
            speech.speak(_("Pause."))
        else:
            if self._media.Play():
                self._is_playing = True
                self._btn_play.SetLabel(_("Pause"))
                self._timer.Start(_TIMER_MS)
                speech.speak(_("Lecture."))

    def _seek_relative(self, delta_ms: int) -> None:
        if self._duration_ms <= 0:
            return
        new_pos = max(0, min(self._media.Tell() + delta_ms, self._duration_ms))
        self._media.Seek(new_pos)
        self._slider_pos.SetValue(new_pos)
        self._update_time_label(new_pos)

    def _change_volume(self, delta: int) -> None:
        new_vol = max(0, min(self._slider_vol.GetValue() + delta, 100))
        self._slider_vol.SetValue(new_vol)
        self._media.SetVolume(new_vol / 100.0)
        speech.speak(_("Volume {volume} pour cent.").format(volume=new_vol))

    def _on_seek(self, _event) -> None:
        pos = self._slider_pos.GetValue()
        self._media.Seek(pos)
        self._update_time_label(pos)

    def _on_volume(self, _event) -> None:
        self._media.SetVolume(self._slider_vol.GetValue() / 100.0)

    def _on_tick(self, _event) -> None:
        if not self._is_playing or self._closing:
            return
        pos = self._media.Tell()
        # Ne pas écraser le slider si l'utilisateur le manipule activement
        self._slider_pos.SetValue(min(pos, self._slider_pos.GetMax()))
        self._update_time_label(pos)

    def _update_time_label(self, pos_ms: int) -> None:
        self._lbl_time.SetLabel(f"{_fmt_ms(pos_ms)} / {_fmt_ms(self._duration_ms)}")

    # ------------------------------------------------------------------
    # Clavier
    # ------------------------------------------------------------------

    def _on_char_hook(self, event: wx.KeyEvent) -> None:
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self._on_close(None)
            return
        if key == wx.WXK_SPACE:
            # N'absorbe Espace que si la cible n'est pas un slider (qui s'en sert)
            self._toggle_play()
            return
        if key == wx.WXK_LEFT:
            self._seek_relative(-_SEEK_STEP_MS)
            return
        if key == wx.WXK_RIGHT:
            self._seek_relative(+_SEEK_STEP_MS)
            return
        if key == wx.WXK_UP:
            self._change_volume(+_VOLUME_STEP)
            return
        if key == wx.WXK_DOWN:
            self._change_volume(-_VOLUME_STEP)
            return
        event.Skip()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _on_close(self, _event) -> None:
        if self._closing:
            return
        self._closing = True
        try:
            self._timer.Stop()
        except Exception:
            pass
        try:
            self._media.Stop()
        except Exception:
            pass
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)
        else:
            self.Destroy()


def _fmt_ms(ms: int) -> str:
    s = max(0, int(ms // 1000))
    h, m = divmod(s, 3600)
    m, s = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
