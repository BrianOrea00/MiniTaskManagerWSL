"""CSV export of the most recent snapshot."""

import csv
from datetime import datetime

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from .models import StatsSnapshot


def export_snapshot(parent, snapshot: StatsSnapshot) -> None:
    """Prompt for a path and write the snapshot to a CSV file."""
    try:
        filename, _ = QFileDialog.getSaveFileName(
            parent,
            "Save System Data",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        if not filename:
            return

        with open(filename, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                ["Timestamp", "CPU %", "RAM %", "Disk %", "Download (KB/s)", "Upload (KB/s)"]
            )
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow(
                [
                    now,
                    f"{snapshot.cpu_percent:.1f}",
                    f"{snapshot.ram_percent:.1f}",
                    f"{snapshot.disk_percent:.1f}",
                    f"{snapshot.download_kbps:.1f}",
                    f"{snapshot.upload_kbps:.1f}",
                ]
            )

            writer.writerow([])
            writer.writerow(["Process PID", "Process Name", "CPU %", "Memory %"])
            for proc in snapshot.processes:
                writer.writerow(
                    [
                        proc.pid,
                        proc.name,
                        f"{proc.cpu_percent:.1f}",
                        f"{proc.memory_percent:.1f}",
                    ]
                )

        QMessageBox.information(parent, "Export Complete", f"Data exported to:\n{filename}")
    except Exception as exc:
        QMessageBox.critical(parent, "Export Error", f"Failed to export: {exc}")
