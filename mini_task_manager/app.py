"""Application bootstrap."""

import sys

from PyQt6.QtWidgets import QApplication

from .theme import apply_dark_palette
from .ui.main_window import SystemMonitor


def main() -> None:
    """Create the Qt application, show the dashboard, and run the loop."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_dark_palette(app)

    window = SystemMonitor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
