import wx
from app.core import logger as _logger
from app.core import settings as cfg
from app.core import i18n
from app.core import updater


def main():
    _logger.setup()

    # Installe la traduction AVANT d'importer/instancier les fenetres :
    # tout module qui utilise _() au niveau module-load doit voir _ injecte
    # dans builtins. MainWindow et ses imports declenchent ce chargement.
    settings = cfg.load()
    i18n.install_language(settings.get("language", "auto"))

    from app.ui.main_window import MainWindow

    app = wx.App(False)
    frame = MainWindow(None)
    frame.Show()

    updater.bootstrap(
        on_update_done=lambda status, info: wx.CallAfter(
            frame.on_ytdlp_update_done, status, info
        )
    )
    frame.check_app_update_at_startup()
    frame.check_announcement_at_startup()

    app.MainLoop()


if __name__ == "__main__":
    main()
