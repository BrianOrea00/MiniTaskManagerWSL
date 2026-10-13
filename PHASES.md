# PHASES — MiniTaskManagerWSL restructure plan

## Scope

`SystemDashboard.py` is a single 671-line file that mixes four concerns:

1. Qt UI construction (`setup_ui`, `setup_overview_tab`, `setup_process_tab`, `toggle_theme`).
2. Data sampling with `psutil` (`update_all_stats`, `update_network_speed`, `update_processes`, `get_wsl_info`).
3. Threading (`UpdateThread` calling methods directly on the window).
4. I/O and side effects (`export_data`, `kill_process`).

Verified at runtime against the bundled `minitask-venv`
(Python 3.13, PyQt6 6.11, matplotlib 3.11, psutil 7.2.2).

## Problems observed

| ID | Severity | Location | Problem | Fix |
|----|----------|----------|---------|-----|
| C1 | Critical | `SystemDashboard.py:288`, `:434` | CPU sampled twice per tick. Blocking `cpu_percent(interval=0.2)` at :288, then non-blocking `cpu_percent()` at :434 microseconds later returns `0.0`. Confirmed at runtime. Chart CPU line is always flat zero. | Sample once, pass the value to the chart. |
| C2 | Critical | `SystemDashboard.py:447` | `QTimer.singleShot(0, self._update_chart_ui)` is called from the worker thread. `UpdateThread.run` never runs an event loop, so the timer never fires and the chart never redraws. | Worker emits a signal; the window redraws on the main thread. |
| C3 | Critical | `SystemDashboard.py:278`, `:50-67` | `manual_refresh` spawns a raw `threading.Thread` running `update_all_stats` alongside `UpdateThread`. Both mutate `cpu_history`, `ram_history`, `prev_net`, `last_time` with no lock. | Single updater thread; manual refresh only wakes it early. |
| H1 | High | `SystemDashboard.py:519-530` | Kill path parses the PID out of `QTextEdit` selection text. Selecting mid-row yields a non-digit first token and silently returns with no message. | Use a `QTableWidget` and read the PID/name from the selected row. |
| H2 | High | `SystemDashboard.py:482` | `proc.info['name'][:28]` raises `TypeError` when the name is `None`. Inner `try` only catches `NoSuchProcess`/`AccessDenied`; the outer bare `except: pass` then blanks the whole list. | Coerce with `(name or "?")[:28]`. |
| H3 | High | `SystemDashboard.py:319-324` | The whole `update_all_stats` body shares one exception handler. A single `AccessDenied` on one process aborts disk, network, chart, and info too. | Per-section error isolation. |
| M1 | Medium | `SystemDashboard.py:606-609` | Export divides by a hard-coded `time_diff = 1` and reads `self.prev_net` that is never refreshed in this path. Reported network speed is meaningless. | Export the latest collected snapshot. |
| M2 | Medium | `SystemDashboard.py:406` | Uptime uses `time.gmtime`, which wraps at 24h and shows the wrong value. | Format a `timedelta`. |
| M3 | Medium | `SystemDashboard.py:439` | `time_history.append(len(self.cpu_history))` then pop saturates the X axis at 60/61 after one minute; the chart squashes horizontally. | Use a monotonic sample counter. |
| M4 | Medium | `SystemDashboard.py:345-357` | `setStyleSheet` is invoked on every bar every tick, forcing a full style re-polish each second. | Cache the last style per bar, set only on change. |
| M5 | Medium | `SystemDashboard.py:278`, `:633-641` | Raw daemon threads from `manual_refresh` are never joined on close; they can touch widgets after teardown. | Remove the extra thread. |
| M6 | Medium | `SystemDashboard.py:13` | Imports legacy `matplotlib.backends.backend_qt5agg`. Works only because PyQt6 is imported first; fails in isolation with matplotlib 3.11. | Use `matplotlib.backends.backend_qtagg`. |
| L1 | Low | `SystemDashboard.py:28` | `Config.THEME` is never read. | Remove. |
| L2 | Low | `SystemDashboard.py:428`, `:488`, `:639` | Bare `except: pass` hides real errors. | Narrow or log. |
| L3 | Low | `SystemDashboard.py:477` | Rebuilds the entire process list and format string every second even when unchanged. | Refresh on a table model. |
| L4 | Low | `SystemDashboard.py:638` | `plt.close('all')` closes unrelated matplotlib figures globally. | Drop pyplot; close owned figures only. |
| L5 | Low | `SystemDashboard.py:596` | Export writes directly to the target path; a mid-write failure leaves a partial file. | Write to a temp file and rename. |

## Phases

### Phase 1 — Modularize (structure only)

Split the file into a package with an explicit dependency direction; no behavioural
change intended. Target layout:

```
mini_task_manager/
  __init__.py
  __main__.py          # python -m mini_task_manager
  config.py            # Config
  models.py            # StatsSnapshot, ProcessInfo (no Qt)
  collector.py         # psutil -> models (no Qt)
  worker.py            # UpdateThread emits stats_ready(snapshot)
  theme.py             # palette + light/dark stylesheets
  export.py            # CSV writer from a snapshot
  app.py               # QApplication bootstrap
  ui/
    __init__.py
    canvas.py          # MplCanvas
    header.py          # header frame builder
    overview_tab.py    # stats bars + chart + info
    process_tab.py     # QTableWidget + kill/refresh
    main_window.py     # SystemMonitor, wires signals only
```

Dependency direction: `app -> ui.main_window -> ui.* , worker -> collector -> models, config`.
Nothing below `ui` imports Qt.

### Phase 2 — Threading and sampling correctness

Resolve C1, C2, C3, H3, M2, M3. This is folded into Phase 1 because the
signal-based worker removes the shared-state hazard by construction.

- Worker owns all sampling; emits one `stats_ready(StatsSnapshot)` per tick.
- Main-thread slot updates every widget and redraws the chart.
- Manual refresh sets an event to wake the worker early.

### Phase 3 — Process tab

Resolve H1, H2. Replace `QTextEdit` with a `QTableWidget`; kill reads the
selected row's PID and name.

### Phase 4 — Export

Resolve M1. Export the last snapshot instead of recomputing from stale state.
Deferred: atomic temp-file write (L5) and exporting the full history rather
than a single snapshot.

### Phase 5 — Theme and polish

Resolve M4, L1, L2, L4. Keep light/dark toggle behaviour.

### Phase 6 — Tests

Collector is pure and Qt-free, so it is unit-testable with a stubbed `psutil`.
Add tests for: speed formatting, network averaging, process name coercion,
and snapshot assembly.

## Verification

```
minitask-venv/bin/python -m py_compile mini_task_manager/**/*.py
QT_QPA_PLATFORM=offscreen timeout 6 minitask-venv/bin/python -m mini_task_manager
```

## Status

- [x] Phase 1 — package extracted
- [x] Phase 2 — signal-based worker; single sample per tick; uptime fixed
- [x] Phase 3 — `QTableWidget` process list; row-based kill
- [x] Phase 4 — snapshot-based export (atomic write still deferred)
- [x] Phase 5 — style cache, THEME removed, pyplot dropped
- [ ] Phase 6 — tests (collector has no coverage yet)
- [ ] Deferred — L5 atomic export write; full-history export
