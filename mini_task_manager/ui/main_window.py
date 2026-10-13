"""Main window: wires the collector thread to the tab widgets."""

from datetime import datetime

from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..collector import Collector
from ..config import Config
from ..export import export_snapshot
from ..models import StatsSnapshot
from ..theme import light_stylesheet
from ..worker import UpdateThread
from .header import create_header
from .overview_tab import OverviewTab
from .process_tab import ProcessTab


class SystemMonitor(QMainWindow):
    """Top-level dashboard window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("🖥️ WSL System Dashboard")
        self.setGeometry(100, 100, 900, 750)
        self.setMinimumSize(800, 650)

        self.is_dark_theme = True
        self.collector = Collector()
        self.last_snapshot: StatsSnapshot | None = None

        self._build_ui()
        self._setup_shortcuts()
        self._start_worker()

    # -- construction -----------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 15, 20, 15)

        header, self.theme_btn = create_header(self.toggle_theme, self.export_data)
        layout.addWidget(header)

        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumHeight(550)
        layout.addWidget(self.tab_widget)

        self.overview_tab = OverviewTab()
        self.process_tab = ProcessTab(on_refresh=self.request_refresh)
        self.tab_widget.addTab(self.overview_tab, "📊 Overview")
        self.tab_widget.addTab(self.process_tab, "⚙️ Processes")

        self.status_label = QLabel(self._status_text())
        self.status_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(self.status_label)

    def _setup_shortcuts(self) -> None:
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)

        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut(QKeySequence("Ctrl+R"))
        refresh_action.triggered.connect(self.request_refresh)
        self.addAction(refresh_action)

    def _start_worker(self) -> None:
        self.update_thread = UpdateThread(self.collector)
        self.update_thread.stats_ready.connect(self._on_stats)
        self.update_thread.start()

    # -- slots ------------------------------------------------------------

    def _on_stats(self, snapshot: StatsSnapshot) -> None:
        """Receive a snapshot on the GUI thread and refresh every widget."""
        self.last_snapshot = snapshot
        self.overview_tab.apply_snapshot(snapshot)
        self.process_tab.apply_processes(snapshot.processes)
        self.status_label.setText(self._status_text())

    def request_refresh(self) -> None:
        """Ask the worker for an immediate sample (Ctrl+R, Refresh button)."""
        if self.update_thread.isRunning():
            self.update_thread.request_refresh()

    def toggle_theme(self) -> None:
        """Flip between the dark and light themes."""
        self.is_dark_theme = not self.is_dark_theme
        if self.is_dark_theme:
            self.theme_btn.setText("🌓 Theme")
            self.setStyleSheet("")
        else:
            self.theme_btn.setText("🌙 Dark")
            self.setStyleSheet(light_stylesheet())
        self.overview_tab.set_dark(self.is_dark_theme)

    def export_data(self) -> None:
        """Export the latest snapshot to a CSV file."""
        if self.last_snapshot is None:
            QMessageBox.information(self, "Export", "No data collected yet")
            return
        export_snapshot(self, self.last_snapshot)

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _status_text() -> str:
        return (
            f"🔄 Auto refreshing every {Config.REFRESH_INTERVAL}s | "
            f"Last update: {datetime.now().strftime('%H:%M:%S')}"
        )

    def closeEvent(self, event) -> None:
        if hasattr(self, "update_thread"):
            self.update_thread.stop()
            self.update_thread.wait()
        event.accept()
