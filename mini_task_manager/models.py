"""Plain data containers shared between the collector and the UI.

This module must not import Qt or psutil so it stays cheap to import and
trivial to unit-test.
"""

from dataclasses import dataclass, field


@dataclass
class ProcessInfo:
    """A single process sample."""

    pid: int
    name: str
    cpu_percent: float
    memory_percent: float


@dataclass
class StatsSnapshot:
    """One immutable set of system readings taken at a point in time."""

    cpu_percent: float
    ram_percent: float
    ram_used_mb: int
    ram_total_mb: int
    disk_percent: float
    disk_used_gb: int
    disk_total_gb: int
    download_kbps: float
    upload_kbps: float
    system_info: str
    processes: list[ProcessInfo] = field(default_factory=list)
