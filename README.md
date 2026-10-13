# MiniTaskManagerWSL

A small desktop system dashboard for WSL, built with PyQt6, `psutil`, and
`matplotlib`. It shows live CPU, memory, disk, and network usage, a rolling
usage chart, system information, and a table of the busiest processes with a
kill action.

## Features

- Live CPU, RAM, and disk usage with progress bars that change colour as
  usage climbs.
- Smoothed network download/upload speed.
- Rolling 60-second CPU/RAM chart.
- System information panel (OS, hostname, uptime, CPU cores, WSL kernel).
- Table of the top 10 processes by CPU, with per-row colour coding.
- Terminate a selected process (with confirmation).
- Light/dark theme toggle.
- Export the current readings and full process list to CSV.
- Keyboard shortcuts: `Ctrl+R` refresh now, `Ctrl+Q` quit.

## Requirements

- Python 3.10 or newer (developed against 3.13).
- Packages:
  - `PyQt6`
  - `psutil`
  - `matplotlib`

A virtual environment with these installed is included at `minitask-venv/`.

## Install

Using the bundled virtual environment:

```bash
minitask-venv/bin/python -m mini_task_manager
```

To set up a fresh environment instead:

```bash
python -m venv venv
source venv/bin/activate
pip install PyQt6 psutil matplotlib
python -m mini_task_manager
```

## Run

Either entry point works:

```bash
python -m mini_task_manager
```

```bash
python SystemDashboard.py
```

`SystemDashboard.py` is a thin compatibility launcher that delegates to the
package, so the original command keeps working.

## Project layout

```
mini_task_manager/
  __main__.py          # python -m mini_task_manager
  config.py            # Config: refresh interval, counts, intervals
  models.py            # StatsSnapshot and ProcessInfo dataclasses
  collector.py         # psutil sampling -> StatsSnapshot (no Qt)
  worker.py            # UpdateThread: emits stats_ready(snapshot)
  theme.py             # dark palette + light/dark stylesheets
  export.py            # CSV export of a snapshot
  app.py               # QApplication bootstrap
  ui/
    canvas.py          # embedded matplotlib canvas
    header.py          # title bar and action buttons
    overview_tab.py    # bars, chart, system info
    process_tab.py     # QTableWidget process list and kill action
    main_window.py     # SystemMonitor: wires signals to widgets
PHASES.md              # problem log and phased remediation plan
SystemDashboard.py     # compatibility launcher
```

Data flows one way: `app -> ui.main_window -> ui.*` for display, and
`ui.main_window -> worker -> collector -> models` for sampling. The worker
thread does all sampling and emits a finished snapshot over a queued Qt
signal; only the main thread touches widgets. `collector.py` and `models.py`
contain no Qt code and can be run or tested on their own.

## Configuration

Tune behaviour in `mini_task_manager/config.py`:

| Setting | Default | Meaning |
|---------|---------|---------|
| `REFRESH_INTERVAL` | `1.0` | Seconds between samples. |
| `PROCESS_COUNT` | `10` | Rows shown in the process table. |
| `CHART_POINTS` | `60` | Samples retained on the chart. |
| `NETWORK_HISTORY` | `5` | Samples averaged for network speed. |
| `SYSTEM_INFO_UPDATE_INTERVAL` | `30` | Seconds between system-info refreshes. |
| `DISK_UPDATE_INTERVAL` | `5` | Seconds between disk refreshes. |

## Usage notes

- **Export** writes the latest snapshot and the full process list to a CSV
  file you choose.
- **Kill Selected** sends `SIGTERM` to the selected process after a
  confirmation prompt showing its PID and name. Processes owned by other
  users require sufficient permissions.
- The dashboard reads `/proc/version` to detect the WSL kernel and shows it in
  the system information panel.

## Development

The package is split so the sampling layer stays free of Qt:

- `mini_task_manager/collector.py` takes no Qt imports and returns plain
  dataclasses, so it can be exercised directly:

  ```bash
  minitask-venv/bin/python -c "from mini_task_manager.collector import Collector; print(Collector().collect())"
  ```

- Compile-check every module:

  ```bash
  minitask-venv/bin/python -m compileall mini_task_manager
  ```

- Smoke-test the UI without a display:

  ```bash
  QT_QPA_PLATFORM=offscreen timeout 6 minitask-venv/bin/python -m mini_task_manager
  ```

See `PHASES.md` for the original problem list and remaining work.
