import sys
import psutil
import platform
import time
from datetime import datetime
import threading
import logging
import csv
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration Class
class Config:
    REFRESH_INTERVAL = 1.0
    PROCESS_COUNT = 10
    CHART_POINTS = 60
    NETWORK_HISTORY = 5
    THEME = "dark"
    SYSTEM_INFO_UPDATE_INTERVAL = 30
    DISK_UPDATE_INTERVAL = 5


class MplCanvas(FigureCanvas):
    """Matplotlib canvas for embedding in PyQt"""
    def __init__(self, parent=None, width=8, height=2.5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Set dark theme
        self.fig.patch.set_facecolor('#2b2b2b')
        self.ax.set_facecolor('#2b2b2b')
        self.ax.set_xlabel('Time (seconds)', color='white', fontsize=9)
        self.ax.set_ylabel('Usage %', color='white', fontsize=9)
        self.ax.tick_params(colors='white', labelsize=8)
        self.ax.grid(True, alpha=0.3, color='gray')


class UpdateThread(QThread):
    """Thread for updating system stats"""
    update_signal = pyqtSignal()
    
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor
        self.running = True
        
    def run(self):
        while self.running:
            try:
                self.monitor.update_all_stats()
                # Emit signal to update UI in main thread
                self.update_signal.emit()
            except Exception as e:
                logging.error(f"Refresh loop error: {e}")
            time.sleep(Config.REFRESH_INTERVAL)
    
    def stop(self):
        self.running = False


class SystemMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🖥️ WSL System Dashboard")
        self.setGeometry(100, 100, 900, 750)
        self.setMinimumSize(800, 650)
        
        # Data variables
        self.prev_net = psutil.net_io_counters()
        self.last_time = time.time()
        self.net_history = []
        self.cpu_history = []
        self.ram_history = []
        self.time_history = []
        self.last_info_update = 0
        self.last_disk_update = 0
        self.disk_cache = {}
        self.is_dark_theme = True
        
        # Setup UI
        self.setup_ui()
        
        # Keyboard shortcuts
        self.quit_action = QAction("Quit", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.close)
        self.addAction(self.quit_action)
        
        self.refresh_action = QAction("Refresh", self)
        self.refresh_action.setShortcut(QKeySequence("Ctrl+R"))
        self.refresh_action.triggered.connect(self.manual_refresh)
        self.addAction(self.refresh_action)
        
        # Start monitoring thread
        self.update_thread = UpdateThread(self)
        self.update_thread.update_signal.connect(self.on_update_complete)
        self.update_thread.start()

    def setup_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumHeight(550)
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.overview_tab = QWidget()
        self.process_tab = QWidget()
        self.tab_widget.addTab(self.overview_tab, "📊 Overview")
        self.tab_widget.addTab(self.process_tab, "⚙️ Processes")
        
        # Setup tabs
        self.setup_overview_tab()
        self.setup_process_tab()
        
        # Status bar
        self.status_label = QLabel(f"🔄 Auto refreshing every {Config.REFRESH_INTERVAL}s | Last update: {datetime.now().strftime('%H:%M:%S')}")
        self.status_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(self.status_label)

    def create_header(self):
        header = QFrame()
        header_layout = QHBoxLayout(header)
        
        # Title
        title = QLabel("WSL System Dashboard")
        title.setStyleSheet("font-size: 26px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Buttons
        self.theme_btn = QPushButton("🌓 Theme")
        self.theme_btn.setFixedWidth(80)
        self.theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_btn)
        
        self.export_btn = QPushButton("📊 Export")
        self.export_btn.setFixedWidth(80)
        self.export_btn.clicked.connect(self.export_data)
        header_layout.addWidget(self.export_btn)
        
        return header

    def setup_overview_tab(self):
        layout = QVBoxLayout(self.overview_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Stats frame
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        stats_layout = QVBoxLayout(stats_frame)
        
        # CPU
        cpu_layout = QVBoxLayout()
        self.cpu_label = QLabel("CPU: --%")
        self.cpu_label.setStyleSheet("font-size: 16px;")
        cpu_layout.addWidget(self.cpu_label)
        
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setTextVisible(False)
        self.cpu_bar.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
        cpu_layout.addWidget(self.cpu_bar)
        stats_layout.addLayout(cpu_layout)
        
        # RAM
        ram_layout = QVBoxLayout()
        self.ram_label = QLabel("RAM: --%")
        self.ram_label.setStyleSheet("font-size: 16px;")
        ram_layout.addWidget(self.ram_label)
        
        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        self.ram_bar.setTextVisible(False)
        self.ram_bar.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
        ram_layout.addWidget(self.ram_bar)
        stats_layout.addLayout(ram_layout)
        
        # Disk
        disk_layout = QVBoxLayout()
        self.disk_label = QLabel("Disk: --%")
        self.disk_label.setStyleSheet("font-size: 16px;")
        disk_layout.addWidget(self.disk_label)
        
        self.disk_bar = QProgressBar()
        self.disk_bar.setRange(0, 100)
        self.disk_bar.setTextVisible(False)
        self.disk_bar.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
        disk_layout.addWidget(self.disk_bar)
        stats_layout.addLayout(disk_layout)
        
        # Network
        self.net_label = QLabel("↓ 0.0 KB/s     ↑ 0.0 KB/s")
        self.net_label.setStyleSheet("font-size: 15px;")
        stats_layout.addWidget(self.net_label)
        
        layout.addWidget(stats_frame)
        
        # Chart
        self.canvas = MplCanvas(self.overview_tab)
        layout.addWidget(self.canvas)
        
        # System info
        self.info_box = QTextEdit()
        self.info_box.setMaximumHeight(120)
        self.info_box.setReadOnly(True)
        self.info_box.setStyleSheet("font-size: 12px; font-family: monospace;")
        layout.addWidget(self.info_box)

    def setup_process_tab(self):
        layout = QVBoxLayout(self.process_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Controls
        controls = QFrame()
        controls_layout = QHBoxLayout(controls)
        
        title = QLabel("Top Processes")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        controls_layout.addWidget(title)
        
        controls_layout.addStretch()
        
        self.kill_btn = QPushButton("🗑️ Kill Selected")
        self.kill_btn.setStyleSheet("background-color: #c0392b; color: white;")
        self.kill_btn.clicked.connect(self.kill_process)
        self.kill_btn.setFixedWidth(120)
        controls_layout.addWidget(self.kill_btn)
        
        self.refresh_process_btn = QPushButton("🔄 Refresh")
        self.refresh_process_btn.clicked.connect(self.manual_refresh_processes)
        self.refresh_process_btn.setFixedWidth(100)
        controls_layout.addWidget(self.refresh_process_btn)
        
        layout.addWidget(controls)
        
        # Process list
        self.process_text = QTextEdit()
        self.process_text.setReadOnly(True)
        self.process_text.setStyleSheet("font-size: 13px; font-family: monospace;")
        layout.addWidget(self.process_text)

    def on_update_complete(self):
        """Called when update thread signals completion"""
        self.update_status_label()

    def update_status_label(self):
        """Update status bar - called from main thread via signal"""
        self.status_label.setText(
            f"🔄 Auto refreshing every {Config.REFRESH_INTERVAL}s | Last update: {datetime.now().strftime('%H:%M:%S')}"
        )

    def manual_refresh(self):
        """Manual refresh on Ctrl+R - updates in background"""
        threading.Thread(target=self.update_all_stats, daemon=True).start()

    def manual_refresh_processes(self):
        """Refresh only processes"""
        self.update_processes()

    def update_all_stats(self):
        """Update all stats - runs in background thread"""
        try:
            # CPU
            cpu = psutil.cpu_percent(interval=0.2)
            self.update_progress_bar(self.cpu_bar, cpu, f"CPU: {cpu:.1f}%", self.cpu_label)

            # RAM
            ram = psutil.virtual_memory()
            self.update_progress_bar(
                self.ram_bar, ram.percent,
                f"RAM: {ram.percent:.1f}% ({ram.used//(1024**2)}MB / {ram.total//(1024**2)}MB)",
                self.ram_label
            )

            # Disk (cached)
            if time.time() - self.last_disk_update > Config.DISK_UPDATE_INTERVAL:
                disk = psutil.disk_usage('/')
                self.disk_cache = disk
                self.last_disk_update = time.time()
            else:
                disk = self.disk_cache
            
            if disk:
                self.update_progress_bar(
                    self.disk_bar, disk.percent,
                    f"Disk: {disk.percent:.1f}% ({disk.used//(1024**3)}GB / {disk.total//(1024**3)}GB)",
                    self.disk_label
                )

            self.update_network_speed()
            self.update_system_info()
            self.update_processes()
            self.update_chart()

        except psutil.NoSuchProcess:
            logging.warning("Process disappeared during update")
        except psutil.AccessDenied:
            logging.warning("Access denied during update")
        except Exception as e:
            logging.error(f"Update failed: {e}")

    def update_progress_bar(self, bar, value, text, label):
        """Update progress bar - thread-safe using QMetaObject.invokeMethod"""
        # Update value
        QMetaObject.invokeMethod(
            bar,
            "setValue",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, int(value))
        )
        
        # Update label text
        QMetaObject.invokeMethod(
            label,
            "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, text)
        )
        
        # Update style based on value (safe to do directly as it's a simple operation)
        if value > 80:
            style = "QProgressBar::chunk { background-color: #e74c3c; }"
        elif value > 60:
            style = "QProgressBar::chunk { background-color: #f39c12; }"
        else:
            style = "QProgressBar::chunk { background-color: #2ecc71; }"
        
        QMetaObject.invokeMethod(
            bar,
            "setStyleSheet",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, style)
        )

    def update_network_speed(self):
        current_net = psutil.net_io_counters()
        current_time = time.time()
        
        time_diff = current_time - self.last_time
        if time_diff < 0.1:
            time_diff = 1

        down_speed = (current_net.bytes_recv - self.prev_net.bytes_recv) / 1024 / time_diff
        up_speed = (current_net.bytes_sent - self.prev_net.bytes_sent) / 1024 / time_diff

        self.prev_net = current_net
        self.last_time = current_time

        self.net_history.append((down_speed, up_speed))
        if len(self.net_history) > Config.NETWORK_HISTORY:
            self.net_history.pop(0)
        
        avg_down = sum(s[0] for s in self.net_history) / len(self.net_history)
        avg_up = sum(s[1] for s in self.net_history) / len(self.net_history)

        down_str = self.format_speed(avg_down)
        up_str = self.format_speed(avg_up)
        
        # Update UI in main thread
        QMetaObject.invokeMethod(
            self.net_label,
            "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, f"↓ Download: {down_str}     ↑ Upload: {up_str}")
        )

    def format_speed(self, speed_kb):
        if speed_kb >= 1024:
            return f"{speed_kb/1024:.1f} MB/s"
        else:
            return f"{speed_kb:.1f} KB/s"

    def update_system_info(self):
        if time.time() - self.last_info_update < Config.SYSTEM_INFO_UPDATE_INTERVAL:
            return
        
        wsl_info = self.get_wsl_info()
        info = f"""System Information
════════════════════
OS          : {platform.system()} {platform.release()}
Hostname    : {platform.node()}
Uptime      : {time.strftime('%H:%M:%S', time.gmtime(time.time() - psutil.boot_time()))}
CPU Cores   : {psutil.cpu_count()} (Physical: {psutil.cpu_count(logical=False)})
{'' if not wsl_info else f'WSL Info    : {wsl_info}'}
Last Update : {datetime.now().strftime('%H:%M:%S')}
"""
        # Update UI in main thread
        QMetaObject.invokeMethod(
            self.info_box,
            "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, info)
        )
        self.last_info_update = time.time()

    def get_wsl_info(self):
        try:
            with open('/proc/version', 'r') as f:
                version = f.read().strip()
                if 'Microsoft' in version:
                    parts = version.split()
                    if len(parts) > 2:
                        return parts[2]
        except:
            pass
        return None

    def update_chart(self):
        """Update chart data - schedule UI update in main thread"""
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        
        self.cpu_history.append(cpu)
        self.ram_history.append(ram)
        self.time_history.append(len(self.cpu_history))
        
        if len(self.cpu_history) > Config.CHART_POINTS:
            self.cpu_history.pop(0)
            self.ram_history.pop(0)
            self.time_history.pop(0)
        
        # Schedule chart update in main thread
        QTimer.singleShot(0, self._update_chart_ui)

    def _update_chart_ui(self):
        """Update chart UI - must be called from main thread"""
        try:
            self.canvas.ax.clear()
            self.canvas.ax.plot(self.time_history, self.cpu_history, '#3498db', 
                               label='CPU', linewidth=2)
            self.canvas.ax.plot(self.time_history, self.ram_history, '#2ecc71', 
                               label='RAM', linewidth=2)
            self.canvas.ax.set_ylim(0, 100)
            
            # Set colors based on theme
            text_color = 'white' if self.is_dark_theme else 'black'
            bg_color = '#2b2b2b' if self.is_dark_theme else '#ffffff'
            
            self.canvas.ax.set_xlabel('Time (seconds)', color=text_color, fontsize=9)
            self.canvas.ax.set_ylabel('Usage %', color=text_color, fontsize=9)
            self.canvas.ax.legend(loc='upper left', labelcolor=text_color)
            self.canvas.ax.tick_params(colors=text_color, labelsize=8)
            self.canvas.ax.grid(True, alpha=0.3, color='gray')
            self.canvas.ax.set_facecolor(bg_color)
            self.canvas.fig.patch.set_facecolor(bg_color)
            
            self.canvas.draw_idle()  # Use draw_idle() instead of draw()
        except Exception as e:
            logging.error(f"Chart update error: {e}")

    def update_processes(self):
        """Update the process list with top CPU processes"""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                with proc.oneshot():
                    try:
                        name = proc.info['name'][:28]
                        cpu = proc.info.get('cpu_percent') or 0
                        mem = proc.info.get('memory_percent') or 0
                        processes.append((proc.info['pid'], name, cpu, mem))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        except:
            pass
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x[2], reverse=True)
        processes = processes[:Config.PROCESS_COUNT]

        text = " PID     Process Name" + " "*18 + "CPU      Memory\n"
        text += "═" * 80 + "\n"
        
        for pid, name, cpu, mem in processes:
            cpu_str = f"{cpu:5.1f}%"
            if cpu > 50:
                cpu_str = f"🔴 {cpu_str}"
            elif cpu > 25:
                cpu_str = f"🟡 {cpu_str}"
            else:
                cpu_str = f"🟢 {cpu_str}"
            
            text += f"{pid:6d}   {name:<30}  {cpu_str}   {mem:5.1f}%\n"

        # Update UI in main thread
        QMetaObject.invokeMethod(
            self.process_text,
            "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, text)
        )

    def kill_process(self):
        try:
            cursor = self.process_text.textCursor()
            selection = cursor.selectedText()
            
            if not selection:
                QMessageBox.warning(self, "Warning", "No process selected")
                return
            
            pid_str = selection.split()[0]
            if not pid_str.isdigit():
                return
            
            pid = int(pid_str)
            
            reply = QMessageBox.question(
                self, "Confirm Kill",
                f"Are you sure you want to terminate process {pid}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
            
            process = psutil.Process(pid)
            process.terminate()
            QMessageBox.information(self, "Success", f"Process {pid} terminated successfully")
            self.update_processes()
            
        except psutil.NoSuchProcess:
            QMessageBox.critical(self, "Error", "Process no longer exists")
        except psutil.AccessDenied:
            QMessageBox.critical(self, "Error", "Access denied. Insufficient permissions")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to kill process: {e}")

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        
        if self.is_dark_theme:
            self.theme_btn.setText("🌓 Theme")
            self.setStyleSheet("")
            # Reset to dark
            self.canvas.fig.patch.set_facecolor('#2b2b2b')
            self.canvas.ax.set_facecolor('#2b2b2b')
            self.canvas.ax.tick_params(colors='white')
            self.canvas.ax.set_xlabel('Time (seconds)', color='white')
            self.canvas.ax.set_ylabel('Usage %', color='white')
        else:
            self.theme_btn.setText("🌙 Dark")
            self.setStyleSheet("""
                QMainWindow { background-color: #ffffff; }
                QLabel { color: #000000; }
                QFrame { background-color: #f0f0f0; }
                QTextEdit { background-color: #ffffff; color: #000000; }
                QProgressBar { background-color: #e0e0e0; border: 1px solid #cccccc; }
                QProgressBar::chunk { background-color: #2ecc71; }
            """)
            # Update chart for light theme
            self.canvas.fig.patch.set_facecolor('#ffffff')
            self.canvas.ax.set_facecolor('#ffffff')
            self.canvas.ax.tick_params(colors='black')
            self.canvas.ax.set_xlabel('Time (seconds)', color='black')
            self.canvas.ax.set_ylabel('Usage %', color='black')
        
        self.canvas.draw_idle()  # Use draw_idle() instead of draw()

    def export_data(self):
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save System Data",
                "",
                "CSV files (*.csv);;All files (*.*)"
            )
            
            if not filename:
                return
            
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Timestamp', 'CPU %', 'RAM %', 'Disk %', 
                               'Download (KB/s)', 'Upload (KB/s)'])
                
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                
                current_net = psutil.net_io_counters()
                time_diff = 1
                down_speed = (current_net.bytes_recv - self.prev_net.bytes_recv) / 1024 / time_diff
                up_speed = (current_net.bytes_sent - self.prev_net.bytes_sent) / 1024 / time_diff
                
                writer.writerow([now, f"{cpu:.1f}", f"{ram:.1f}", 
                               f"{disk:.1f}", f"{down_speed:.1f}", f"{up_speed:.1f}"])
                
                writer.writerow([])
                writer.writerow(['Process PID', 'Process Name', 'CPU %', 'Memory %'])
                
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        writer.writerow([
                            proc.info['pid'],
                            proc.info['name'],
                            f"{proc.info.get('cpu_percent') or 0:.1f}",
                            f"{proc.info.get('memory_percent') or 0:.1f}"
                        ])
                    except:
                        continue
            
            QMessageBox.information(self, "Export Complete", f"Data exported to:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def closeEvent(self, event):
        if hasattr(self, 'update_thread'):
            self.update_thread.stop()
            self.update_thread.wait()
        try:
            plt.close('all')
        except:
            pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set dark theme by default
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)
    
    window = SystemMonitor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
