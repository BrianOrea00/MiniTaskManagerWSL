"""Process tab: a sortable-looking table of top processes with a kill action."""

import psutil
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import Config
from ..models import ProcessInfo

_CPU_HIGH = QColor("#e74c3c")
_CPU_MED = QColor("#f39c12")
_CPU_LOW = QColor("#2ecc71")


class ProcessTab(QWidget):
    """Table of the busiest processes; supports terminating a selection."""

    def __init__(self, on_refresh, parent=None) -> None:
        super().__init__(parent)
        self._on_refresh = on_refresh
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        controls = QFrame()
        controls_layout = QHBoxLayout(controls)

        title = QLabel("Top Processes")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        controls_layout.addWidget(title)
        controls_layout.addStretch()

        self.kill_btn = QPushButton("🗑️ Kill Selected")
        self.kill_btn.setStyleSheet("background-color: #c0392b; color: white;")
        self.kill_btn.setFixedWidth(120)
        self.kill_btn.clicked.connect(self.kill_selected)
        controls_layout.addWidget(self.kill_btn)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setFixedWidth(100)
        self.refresh_btn.clicked.connect(self._on_refresh)
        controls_layout.addWidget(self.refresh_btn)

        layout.addWidget(controls)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["PID", "Process Name", "CPU %", "Memory %"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("font-size: 13px; font-family: monospace;")
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 340)
        self.table.setColumnWidth(2, 90)
        layout.addWidget(self.table)

    # -- updates ----------------------------------------------------------

    def apply_processes(self, processes: list[ProcessInfo]) -> None:
        """Fill the table with the top processes. Must run on the GUI thread."""
        shown = processes[: Config.PROCESS_COUNT]
        self.table.setRowCount(len(shown))
        for row, proc in enumerate(shown):
            pid_item = QTableWidgetItem(str(proc.pid))
            pid_item.setData(Qt.ItemDataRole.UserRole, proc.pid)
            self.table.setItem(row, 0, pid_item)
            self.table.setItem(row, 1, QTableWidgetItem(proc.name))

            cpu_item = QTableWidgetItem(f"{proc.cpu_percent:5.1f}")
            cpu_item.setForeground(self._cpu_color(proc.cpu_percent))
            self.table.setItem(row, 2, cpu_item)

            self.table.setItem(row, 3, QTableWidgetItem(f"{proc.memory_percent:5.1f}"))

    @staticmethod
    def _cpu_color(value: float) -> QColor:
        if value > 50:
            return _CPU_HIGH
        if value > 25:
            return _CPU_MED
        return _CPU_LOW

    # -- actions ----------------------------------------------------------

    def kill_selected(self) -> None:
        """Terminate the process in the selected row after confirmation."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "No process selected")
            return

        pid_item = self.table.item(row, 0)
        if pid_item is None:
            return
        pid = pid_item.data(Qt.ItemDataRole.UserRole)
        name_item = self.table.item(row, 1)
        name = name_item.text() if name_item is not None else "?"

        reply = QMessageBox.question(
            self,
            "Confirm Kill",
            f"Terminate process {pid} ({name})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            psutil.Process(pid).terminate()
            QMessageBox.information(self, "Success", f"Process {pid} terminated successfully")
            self._on_refresh()
        except psutil.NoSuchProcess:
            QMessageBox.critical(self, "Error", "Process no longer exists")
        except psutil.AccessDenied:
            QMessageBox.critical(self, "Error", "Access denied. Insufficient permissions")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to kill process: {exc}")
