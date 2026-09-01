import sys

# Mode hote WebView2 : DownAccess se relance lui-meme avec ce drapeau pour
# heberger le moteur de navigateur de Windows (extraction guidee). Le test doit
# rester ICI, avant `import wx` : ce processus-la n'ouvre aucune interface
# DownAccess, et `webview.start()` s'empare de la boucle de messages — les deux
# ne peuvent pas cohabiter. Voir app/core/webview_host.py.
if __name__ == "__main__" and "--da-webview-host" in sys.argv:
    from app.core.webview_host import run_host
    raise SystemExit(run_host())

import wx
from app.core import logger as _logger
from app.core import settings as cfg
from app.core import i18n
from app.core import updater
from app.core import browser


def main():
    _logger.setup()

    # Installe la traduction AVANT d'importer/instancier les fenetres :
    # tout module qui utilise _() au niveau module-load doit voir _ injecte
    # dans builtins. MainWindow et ses imports declenchent ce chargement.
    settings = cfg.load()
    i18n.install_language(settings.get("language", "auto"))
    browser.set_preferred_browser(settings.get("browser_choice", "auto"))

    # Rend la copie AppData de yt-dlp (canal nightly) prioritaire sur celle
    # embarquee au build. IMPERATIF ici : l'import de MainWindow declenche
    # `import yt_dlp` (downloader, lecteur), et un module deja charge ne peut
    # plus etre remplace. Sans cela, les mises a jour nightly etaient
    # telechargees mais jamais executees.
    updater.activate_appdata_ytdlp()

    from app.ui.main_window import MainWindow

    app = wx.App(False)
    frame = MainWindow(None)
    frame.Show()

    updater.bootstrap(
        on_update_done=lambda status, info: wx.CallAfter(
            frame.on_ytdlp_update_done, status, info
        )
    )
    # Annonce d'abord ; la verif MAJ est enchainee a la fin du traitement de
    # l'annonce (voir MainWindow._on_announcement_received) pour ne jamais ouvrir
    # deux modales en meme temps au demarrage.
    frame.check_announcement_at_startup()
    # Releve des abonnements : silencieux, sans fenetre, il alimente juste
    # le compteur du menu Abonnements (Ctrl+B).
    frame.check_subscriptions_at_startup()
    # Reprise de la file de la session precedente : silencieuse, elle remplit
    # simplement la liste et les telechargements repartent.
    frame.restore_queue_at_startup()

    app.MainLoop()


if __name__ == "__main__":
    main()
