"""Runtime configuration for the dashboard."""


class Config:
    """Central tuning knobs for the dashboard."""

    REFRESH_INTERVAL = 1.0
    PROCESS_COUNT = 10
    CHART_POINTS = 60
    NETWORK_HISTORY = 5
    SYSTEM_INFO_UPDATE_INTERVAL = 30
    DISK_UPDATE_INTERVAL = 5
