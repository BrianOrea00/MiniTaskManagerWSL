"""System sampling with psutil.

The collector holds the small amount of state that makes readings meaningful
(network deltas, cached disk and system-info blocks) and returns a single
:class:`StatsSnapshot` per call. It contains no Qt code so it can run on any
thread and be tested in isolation.
"""

import logging
import platform
import time
from datetime import datetime, timedelta

import psutil

from .config import Config
from .models import ProcessInfo, StatsSnapshot


class Collector:
    """Gathers one :class:`StatsSnapshot` per call."""

    def __init__(self) -> None:
        self._prev_net = psutil.net_io_counters()
        self._last_time = time.time()
        self._net_history: list[tuple[float, float]] = []
        self._disk_cache = None
        self._last_disk_update = 0.0
        self._info_cache = ""
        self._last_info_update = 0.0
        # Prime the CPU counter so the first real sample is not zero.
        psutil.cpu_percent(interval=None)

    def collect(self) -> StatsSnapshot:
        """Read the current system state and return a snapshot."""
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        disk = self._disk()
        down, up = self._network()

        return StatsSnapshot(
            cpu_percent=cpu,
            ram_percent=ram.percent,
            ram_used_mb=ram.used // (1024 ** 2),
            ram_total_mb=ram.total // (1024 ** 2),
            disk_percent=disk.percent,
            disk_used_gb=disk.used // (1024 ** 3),
            disk_total_gb=disk.total // (1024 ** 3),
            download_kbps=down,
            upload_kbps=up,
            system_info=self._system_info(),
            processes=self._processes(),
        )

    def _disk(self):
        """Disk usage, refreshed at most every DISK_UPDATE_INTERVAL seconds."""
        now = time.time()
        if self._disk_cache is None or now - self._last_disk_update > Config.DISK_UPDATE_INTERVAL:
            self._disk_cache = psutil.disk_usage("/")
            self._last_disk_update = now
        return self._disk_cache

    def _network(self) -> tuple[float, float]:
        """Average download/upload speed in KB/s over the recent history."""
        current = psutil.net_io_counters()
        now = time.time()
        delta = now - self._last_time
        if delta < 0.1:
            delta = 1.0

        down = (current.bytes_recv - self._prev_net.bytes_recv) / 1024 / delta
        up = (current.bytes_sent - self._prev_net.bytes_sent) / 1024 / delta

        self._prev_net = current
        self._last_time = now
        self._net_history.append((down, up))
        if len(self._net_history) > Config.NETWORK_HISTORY:
            self._net_history.pop(0)

        avg_down = sum(sample[0] for sample in self._net_history) / len(self._net_history)
        avg_up = sum(sample[1] for sample in self._net_history) / len(self._net_history)
        return avg_down, avg_up

    def _processes(self) -> list[ProcessInfo]:
        """All processes, sorted by CPU usage (highest first)."""
        result: list[ProcessInfo] = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                with proc.oneshot():
                    name = (proc.info.get("name") or "?")[:28]
                    cpu = proc.info.get("cpu_percent") or 0.0
                    mem = proc.info.get("memory_percent") or 0.0
                    result.append(ProcessInfo(proc.info["pid"], name, cpu, mem))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        result.sort(key=lambda info: info.cpu_percent, reverse=True)
        return result

    def _system_info(self) -> str:
        """Static system information, refreshed at most every 30 seconds."""
        now = time.time()
        if self._info_cache and now - self._last_info_update < Config.SYSTEM_INFO_UPDATE_INTERVAL:
            return self._info_cache

        wsl = self._wsl_info()
        uptime = str(timedelta(seconds=int(now - psutil.boot_time())))
        self._info_cache = (
            "System Information\n"
            "════════════════════\n"
            f"OS          : {platform.system()} {platform.release()}\n"
            f"Hostname    : {platform.node()}\n"
            f"Uptime      : {uptime}\n"
            f"CPU Cores   : {psutil.cpu_count()} (Physical: {psutil.cpu_count(logical=False)})\n"
            f"{'' if not wsl else f'WSL Info    : {wsl}'}\n"
            f"Last Update : {datetime.now().strftime('%H:%M:%S')}\n"
        )
        self._last_info_update = now
        return self._info_cache

    @staticmethod
    def _wsl_info() -> str | None:
        """Return the kernel version when running under WSL, else None."""
        try:
            with open("/proc/version", "r") as handle:
                version = handle.read().strip()
            if "Microsoft" in version:
                parts = version.split()
                if len(parts) > 2:
                    return parts[2]
        except OSError as exc:
            logging.debug("Could not read /proc/version: %s", exc)
        return None
