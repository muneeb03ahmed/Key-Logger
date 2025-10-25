from __future__ import annotations
import sys
from PySide6 import QtWidgets
from kdyn.logging_conf import configure_logging
from kdyn.settings import AppSettings
from kdyn.gui import MainWindow


def main() -> int:
    configure_logging()
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("KDyn")
    settings = AppSettings.load()
    win = MainWindow(settings)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())