"""Overview tab: usage bars, live chart, and system information."""

import logging

from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import Config
from ..models import StatsSnapshot
from ..theme import chart_colors
from .canvas import MplCanvas

_CPU_COLORS = (
    (80, "#e74c3c"),
    (60, "#f39c12"),
    (0, "#2ecc71"),
)


class OverviewTab(QWidget):
    """Read-only view of CPU, RAM, disk, network, chart, and system info."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cpu_history: list[float] = []
        self._ram_history: list[float] = []
        self._time_history: list[int] = []
        self._tick = 0
        self._is_dark = True
        self._bar_styles: dict[str, str] = {}
        self._build()

    # -- construction -----------------------------------------------------

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        stats_layout = QVBoxLayout(stats_frame)

        self.cpu_label = QLabel("CPU: --%")
        self.cpu_bar = self._make_bar()
        stats_layout.addWidget(self.cpu_label)
        stats_layout.addWidget(self.cpu_bar)

        self.ram_label = QLabel("RAM: --%")
        self.ram_bar = self._make_bar()
        stats_layout.addWidget(self.ram_label)
        stats_layout.addWidget(self.ram_bar)

        self.disk_label = QLabel("Disk: --%")
        self.disk_bar = self._make_bar()
        stats_layout.addWidget(self.disk_label)
        stats_layout.addWidget(self.disk_bar)

        self.net_label = QLabel("↓ 0.0 KB/s     ↑ 0.0 KB/s")
        self.net_label.setStyleSheet("font-size: 15px;")
        stats_layout.addWidget(self.net_label)

        layout.addWidget(stats_frame)

        self.canvas = MplCanvas(self)
        layout.addWidget(self.canvas)

        self.info_box = QTextEdit()
        self.info_box.setMaximumHeight(120)
        self.info_box.setReadOnly(True)
        self.info_box.setStyleSheet("font-size: 12px; font-family: monospace;")
        layout.addWidget(self.info_box)

    def _make_bar(self) -> QProgressBar:
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setTextVisible(False)
        bar.setStyleSheet(self._style_for(0))
        return bar

    # -- updates ----------------------------------------------------------

    def apply_snapshot(self, snapshot: StatsSnapshot) -> None:
        """Render a fresh snapshot. Must run on the GUI thread."""
        self._set_bar(self.cpu_bar, self.cpu_label, "cpu", snapshot.cpu_percent,
                      f"CPU: {snapshot.cpu_percent:.1f}%")
        self._set_bar(
            self.ram_bar, self.ram_label, "ram", snapshot.ram_percent,
            f"RAM: {snapshot.ram_percent:.1f}% "
            f"({snapshot.ram_used_mb}MB / {snapshot.ram_total_mb}MB)",
        )
        self._set_bar(
            self.disk_bar, self.disk_label, "disk", snapshot.disk_percent,
            f"Disk: {snapshot.disk_percent:.1f}% "
            f"({snapshot.disk_used_gb}GB / {snapshot.disk_total_gb}GB)",
        )

        down = self.format_speed(snapshot.download_kbps)
        up = self.format_speed(snapshot.upload_kbps)
        self.net_label.setText(f"↓ Download: {down}     ↑ Upload: {up}")
        self.info_box.setText(snapshot.system_info)

        self._append_history(snapshot.cpu_percent, snapshot.ram_percent)
        self._draw_chart()

    def set_dark(self, is_dark: bool) -> None:
        """Switch chart colours between the dark and light theme."""
        self._is_dark = is_dark
        self._draw_chart()

    # -- helpers ----------------------------------------------------------

    def _set_bar(self, bar: QProgressBar, label: QLabel, key: str,
                 value: float, text: str) -> None:
        bar.setValue(int(value))
        label.setText(text)
        style = self._style_for(value)
        if self._bar_styles.get(key) != style:
            bar.setStyleSheet(style)
            self._bar_styles[key] = style

    @staticmethod
    def _style_for(value: float) -> str:
        for threshold, color in _CPU_COLORS:
            if value > threshold:
                return f"QProgressBar::chunk {{ background-color: {color}; }}"
        return "QProgressBar::chunk { background-color: #2ecc71; }"

    @staticmethod
    def format_speed(speed_kb: float) -> str:
        if speed_kb >= 1024:
            return f"{speed_kb / 1024:.1f} MB/s"
        return f"{speed_kb:.1f} KB/s"

    def _append_history(self, cpu: float, ram: float) -> None:
        self._tick += 1
        self._cpu_history.append(cpu)
        self._ram_history.append(ram)
        self._time_history.append(self._tick)
        while len(self._cpu_history) > Config.CHART_POINTS:
            self._cpu_history.pop(0)
            self._ram_history.pop(0)
            self._time_history.pop(0)

    def _draw_chart(self) -> None:
        try:
            text_color, bg_color = chart_colors(self._is_dark)
            ax = self.canvas.ax
            ax.clear()
            ax.plot(self._time_history, self._cpu_history, "#3498db",
                    label="CPU", linewidth=2)
            ax.plot(self._time_history, self._ram_history, "#2ecc71",
                    label="RAM", linewidth=2)
            ax.set_ylim(0, 100)
            ax.set_xlabel("Time (seconds)", color=text_color, fontsize=9)
            ax.set_ylabel("Usage %", color=text_color, fontsize=9)
            ax.legend(loc="upper left", labelcolor=text_color)
            ax.tick_params(colors=text_color, labelsize=8)
            ax.grid(True, alpha=0.3, color="gray")
            ax.set_facecolor(bg_color)
            self.canvas.fig.patch.set_facecolor(bg_color)
            self.canvas.draw_idle()
        except Exception as exc:
            logging.error("Chart update error: %s", exc)
