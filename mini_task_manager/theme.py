"""Palette and stylesheet helpers for the light and dark themes."""

from PyQt6.QtGui import QColor, QPalette

DARK_BG = "#2b2b2b"
LIGHT_BG = "#ffffff"


def apply_dark_palette(app) -> None:
    """Apply the default dark palette to a :class:`QApplication`."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("white"))
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("black"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("white"))
    palette.setColor(QPalette.ColorRole.Text, QColor("white"))
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("white"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("red"))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("black"))
    app.setPalette(palette)


def light_stylesheet() -> str:
    """Stylesheet that switches the window to the light theme."""
    return """
        QMainWindow { background-color: #ffffff; }
        QLabel { color: #000000; }
        QFrame { background-color: #f0f0f0; }
        QTextEdit { background-color: #ffffff; color: #000000; }
        QTableWidget { background-color: #ffffff; color: #000000; }
        QProgressBar { background-color: #e0e0e0; border: 1px solid #cccccc; }
        QProgressBar::chunk { background-color: #2ecc71; }
    """


def chart_colors(is_dark: bool) -> tuple[str, str]:
    """Return ``(text_color, background_color)`` for the active theme."""
    if is_dark:
        return "white", DARK_BG
    return "black", LIGHT_BG
