"""Background update thread.

The worker owns *all* sampling and hands finished snapshots to the UI through
a queued signal, so no widget is ever touched from a non-GUI thread.
"""

import logging
import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal

from .collector import Collector
from .config import Config
from .models import StatsSnapshot


class UpdateThread(QThread):
    """Emits :attr:`stats_ready` with a fresh :class:`StatsSnapshot` each tick."""

    stats_ready = pyqtSignal(object)

    def __init__(self, collector: Collector, parent=None) -> None:
        super().__init__(parent)
        self._collector = collector
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()

    def run(self) -> None:
        while not self._stop_event.is_set():
            started = time.time()
            try:
                self.stats_ready.emit(self._collector.collect())
            except Exception as exc:  # keep the loop alive on transient errors
                logging.error("Refresh loop error: %s", exc)

            remaining = Config.REFRESH_INTERVAL - (time.time() - started)
            if remaining > 0:
                # Returns early when a manual refresh or stop is requested.
                self._wake_event.wait(remaining)
                self._wake_event.clear()

    def request_refresh(self) -> None:
        """Wake the worker so the next sample happens immediately."""
        self._wake_event.set()

    def stop(self) -> None:
        """Ask the loop to finish; pair with :meth:`wait`."""
        self._stop_event.set()
        self._wake_event.set()
