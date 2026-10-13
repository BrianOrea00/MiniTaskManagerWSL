"""Header bar with the title and action buttons."""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


def create_header(on_toggle_theme, on_export):
    """Build the header frame.

    Returns ``(header, theme_button)`` so the caller can update the button
    label when the theme changes.
    """
    header = QFrame()
    layout = QHBoxLayout(header)

    title = QLabel("WSL System Dashboard")
    title.setStyleSheet("font-size: 26px; font-weight: bold;")
    layout.addWidget(title)

    layout.addStretch()

    theme_button = QPushButton("🌓 Theme")
    theme_button.setFixedWidth(80)
    theme_button.clicked.connect(on_toggle_theme)
    layout.addWidget(theme_button)

    export_button = QPushButton("📊 Export")
    export_button.setFixedWidth(80)
    export_button.clicked.connect(on_export)
    layout.addWidget(export_button)

    return header, theme_button
