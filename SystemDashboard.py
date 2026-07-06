import customtkinter as ctk
import psutil
import platform
import time
from datetime import datetime
import threading
import logging
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
from tkinter import filedialog, messagebox

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
    SYSTEM_INFO_UPDATE_INTERVAL = 30  # seconds
    DISK_UPDATE_INTERVAL = 5  # seconds

ctk.set_appearance_mode(Config.THEME)
ctk.set_default_color_theme("blue")

class WSL_SystemDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🖥️ WSL System Dashboard")
        self.geometry("900x750")
        self.minsize(800, 650)
        self.resizable(True, True)
        
        self.running = True
        self.prev_net = psutil.net_io_counters()
        self.last_time = time.time()
        self.net_history = []
        self.cpu_history = []
        self.ram_history = []
        self.time_history = []
        self.last_info_update = 0
        self.last_disk_update = 0
        self.disk_cache = {}
        
        # Keyboard shortcuts
        self.bind('<Control-q>', lambda e: self.on_closing())
        self.bind('<Control-r>', lambda e: self.manual_refresh())
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.create_widgets()
        self.start_auto_refresh()

    def create_widgets(self):
        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)
        
        ctk.CTkLabel(header_frame, text="WSL System Dashboard", 
                    font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, sticky="w", padx=10)
        
        # Controls
        control_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        control_frame.grid(row=0, column=1, sticky="e")
        
        self.theme_btn = ctk.CTkButton(control_frame, text="🌓 Theme", 
                                      width=80, command=self.toggle_theme)
        self.theme_btn.pack(side="left", padx=5)
        
        self.export_btn = ctk.CTkButton(control_frame, text="📊 Export", 
                                       width=80, command=self.export_data)
        self.export_btn.pack(side="left", padx=5)

        # Tabview
        self.tabview = ctk.CTkTabview(self, width=840, height=550)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        # Overview Tab
        self.overview = self.tabview.add("📊 Overview")
        self.create_overview_tab()

        # Processes Tab
        self.process_tab = self.tabview.add("⚙️ Processes")
        self.create_process_tab()

        # Status Bar
        status_frame = ctk.CTkFrame(self)
        status_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        self.status_label = ctk.CTkLabel(status_frame, 
                                        text=f"🔄 Auto refreshing every {Config.REFRESH_INTERVAL}s | Last update: {datetime.now().strftime('%H:%M:%S')}", 
                                        font=ctk.CTkFont(size=12), text_color="gray")
        self.status_label.pack()

    def create_overview_tab(self):
        # Main frame with grid
        main_frame = ctk.CTkFrame(self.overview)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=0)
        main_frame.grid_rowconfigure(1, weight=1)

        # Stats Frame (left side)
        stats_frame = ctk.CTkFrame(main_frame)
        stats_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        stats_frame.grid_columnconfigure(0, weight=1)
        
        # CPU
        cpu_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        cpu_frame.pack(fill="x", padx=10, pady=5)
        
        self.cpu_label = ctk.CTkLabel(cpu_frame, text="CPU: --%", font=ctk.CTkFont(size=16))
        self.cpu_label.pack(anchor="w")
        self.cpu_bar = ctk.CTkProgressBar(cpu_frame, width=600, height=15)
        self.cpu_bar.pack(fill="x", pady=2)
        self.cpu_bar.set(0)

        # RAM
        ram_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        ram_frame.pack(fill="x", padx=10, pady=5)
        
        self.ram_label = ctk.CTkLabel(ram_frame, text="RAM: --%", font=ctk.CTkFont(size=16))
        self.ram_label.pack(anchor="w")
        self.ram_bar = ctk.CTkProgressBar(ram_frame, width=600, height=15)
        self.ram_bar.pack(fill="x", pady=2)
        self.ram_bar.set(0)

        # Disk
        disk_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        disk_frame.pack(fill="x", padx=10, pady=5)
        
        self.disk_label = ctk.CTkLabel(disk_frame, text="Disk: --%", font=ctk.CTkFont(size=16))
        self.disk_label.pack(anchor="w")
        self.disk_bar = ctk.CTkProgressBar(disk_frame, width=600, height=15)
        self.disk_bar.pack(fill="x", pady=2)
        self.disk_bar.set(0)

        # Network
        net_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        net_frame.pack(fill="x", padx=10, pady=5)
        
        self.net_label = ctk.CTkLabel(net_frame, text="↓ 0.0 KB/s     ↑ 0.0 KB/s", 
                                    font=ctk.CTkFont(size=15))
        self.net_label.pack(anchor="w")

        # Chart Frame (bottom)
        chart_frame = ctk.CTkFrame(main_frame)
        chart_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Setup matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(8, 2.5), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.ax.set_facecolor('#2b2b2b')
        self.ax.set_xlabel('Time (seconds)', color='white', fontsize=9)
        self.ax.set_ylabel('Usage %', color='white', fontsize=9)
        self.ax.tick_params(colors='white', labelsize=8)
        
        # Embed in Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Info Box
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        self.info_box = ctk.CTkTextbox(info_frame, height=120, font=ctk.CTkFont(size=12))
        self.info_box.pack(fill="both", expand=True, padx=5, pady=5)

    def create_process_tab(self):
        frame = ctk.CTkFrame(self.process_tab)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=0)
        frame.grid_rowconfigure(1, weight=1)

        # Controls
        control_frame = ctk.CTkFrame(frame, fg_color="transparent")
        control_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        ctk.CTkLabel(control_frame, text="Top Processes", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=5)
        
        self.kill_btn = ctk.CTkButton(control_frame, text="🗑️ Kill Selected", 
                                     command=self.kill_process, fg_color="#c0392b",
                                     hover_color="#e74c3c", width=120)
        self.kill_btn.pack(side="right", padx=5)

        self.refresh_process_btn = ctk.CTkButton(control_frame, text="🔄 Refresh", 
                                                command=self.manual_refresh_processes, width=100)
        self.refresh_process_btn.pack(side="right", padx=5)

        # Process list
        self.process_text = ctk.CTkTextbox(frame, font=ctk.CTkFont(size=13), height=350)
        self.process_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def start_auto_refresh(self):
        def refresh_loop():
            while self.running:
                try:
                    self.update_all_stats()
                    self.after(0, self.update_status_label)
                except Exception as e:
                    logging.error(f"Refresh loop error: {e}")
                time.sleep(Config.REFRESH_INTERVAL)
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()

    def manual_refresh(self):
        """Manual refresh on Ctrl+R"""
        threading.Thread(target=self.update_all_stats, daemon=True).start()

    def manual_refresh_processes(self):
        """Refresh only processes"""
        self.update_processes()

    def update_status_label(self):
        """Update status bar with last update time"""
        self.status_label.configure(
            text=f"🔄 Auto refreshing every {Config.REFRESH_INTERVAL}s | Last update: {datetime.now().strftime('%H:%M:%S')}"
        )

    def update_all_stats(self):
        try:
            # CPU
            cpu = psutil.cpu_percent(interval=0.2)
            self.update_progress_bar(self.cpu_bar, cpu, 
                                    f"CPU Usage: {cpu:.1f}%",
                                    self.cpu_label)

            # RAM
            ram = psutil.virtual_memory()
            self.update_progress_bar(self.ram_bar, ram.percent,
                                   f"RAM: {ram.percent:.1f}% ({ram.used//(1024**2)}MB / {ram.total//(1024**2)}MB)",
                                   self.ram_label)

            # Disk (cached)
            if time.time() - self.last_disk_update > Config.DISK_UPDATE_INTERVAL:
                disk = psutil.disk_usage('/')
                self.disk_cache = disk
                self.last_disk_update = time.time()
            else:
                disk = self.disk_cache
            
            if disk:
                self.update_progress_bar(self.disk_bar, disk.percent,
                                       f"Disk: {disk.percent:.1f}% ({disk.used//(1024**3)}GB / {disk.total//(1024**3)}GB)",
                                       self.disk_label)

            # Network with smoothing
            self.update_network_speed()

            # System info (cached)
            self.update_system_info()

            # Processes
            self.update_processes()

            # Chart
            self.update_chart()

        except psutil.NoSuchProcess:
            logging.warning("Process disappeared during update")
        except psutil.AccessDenied:
            logging.warning("Access denied during update")
        except Exception as e:
            logging.error(f"Update failed: {e}")

    def update_progress_bar(self, bar, value, text, label):
        """Update a progress bar with color coding"""
        bar.set(value / 100)
        label.configure(text=text)
        
        # Color coding
        if value > 80:
            bar.configure(progress_color="#e74c3c")  # Red
        elif value > 60:
            bar.configure(progress_color="#f39c12")  # Orange
        else:
            bar.configure(progress_color="#2ecc71")  # Green

    def update_network_speed(self):
        current_net = psutil.net_io_counters()
        current_time = time.time()
        
        time_diff = current_time - self.last_time
        if time_diff < 0.1:
            time_diff = 1

        # Calculate speed in KB/s
        down_speed = (current_net.bytes_recv - self.prev_net.bytes_recv) / 1024 / time_diff
        up_speed = (current_net.bytes_sent - self.prev_net.bytes_sent) / 1024 / time_diff

        self.prev_net = current_net
        self.last_time = current_time

        # Moving average smoothing
        self.net_history.append((down_speed, up_speed))
        if len(self.net_history) > Config.NETWORK_HISTORY:
            self.net_history.pop(0)
        
        avg_down = sum(s[0] for s in self.net_history) / len(self.net_history)
        avg_up = sum(s[1] for s in self.net_history) / len(self.net_history)

        # Format with units
        down_str = self.format_speed(avg_down)
        up_str = self.format_speed(avg_up)
        
        self.net_label.configure(
            text=f"↓ Download: {down_str}     ↑ Upload: {up_str}"
        )

    def format_speed(self, speed_kb):
        """Format speed with appropriate units"""
        if speed_kb >= 1024:
            return f"{speed_kb/1024:.1f} MB/s"
        else:
            return f"{speed_kb:.1f} KB/s"

    def update_system_info(self):
        """Update system info with caching"""
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
        self.info_box.delete("1.0", "end")
        self.info_box.insert("1.0", info)
        self.last_info_update = time.time()

    def get_wsl_info(self):
        """Get WSL-specific information"""
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
        """Update the CPU/RAM history chart"""
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        
        self.cpu_history.append(cpu)
        self.ram_history.append(ram)
        self.time_history.append(len(self.cpu_history))
        
        if len(self.cpu_history) > Config.CHART_POINTS:
            self.cpu_history.pop(0)
            self.ram_history.pop(0)
            self.time_history.pop(0)
        
        self.ax.clear()
        self.ax.plot(self.time_history, self.cpu_history, '#3498db', 
                    label='CPU', linewidth=2)
        self.ax.plot(self.time_history, self.ram_history, '#2ecc71', 
                    label='RAM', linewidth=2)
        self.ax.set_ylim(0, 100)
        self.ax.set_xlabel('Time (seconds)', color='white', fontsize=9)
        self.ax.set_ylabel('Usage %', color='white', fontsize=9)
        self.ax.legend(loc='upper left', labelcolor='white')
        self.ax.tick_params(colors='white', labelsize=8)
        self.ax.grid(True, alpha=0.3, color='gray')
        self.ax.set_facecolor('#2b2b2b')
        self.fig.canvas.draw()

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
            # Color code for high CPU
            cpu_str = f"{cpu:5.1f}%"
            if cpu > 50:
                cpu_str = f"🔴 {cpu_str}"
            elif cpu > 25:
                cpu_str = f"🟡 {cpu_str}"
            else:
                cpu_str = f"🟢 {cpu_str}"
            
            text += f"{pid:6d}   {name:<30}  {cpu_str}   {mem:5.1f}%\n"

        self.process_text.delete("1.0", "end")
        self.process_text.insert("1.0", text)

    def kill_process(self):
        """Kill the selected process"""
        try:
            selection = self.process_text.get("sel.first", "sel.last")
            if not selection:
                return
            
            # Extract PID from selection
            pid_str = selection.split()[0]
            if not pid_str.isdigit():
                return
            
            pid = int(pid_str)
            
            # Confirm
            if not messagebox.askyesno("Confirm Kill", 
                                      f"Are you sure you want to terminate process {pid}?"):
                return
            
            process = psutil.Process(pid)
            process.terminate()
            messagebox.showinfo("Success", f"Process {pid} terminated successfully")
            
            # Refresh process list
            self.update_processes()
            
        except psutil.NoSuchProcess:
            messagebox.showerror("Error", "Process no longer exists")
        except psutil.AccessDenied:
            messagebox.showerror("Error", "Access denied. Insufficient permissions")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to kill process: {e}")

    def toggle_theme(self):
        """Toggle between dark and light theme"""
        current = ctk.get_appearance_mode()
        new_theme = "Light" if current == "dark" else "Dark"
        ctk.set_appearance_mode(new_theme.lower())
        self.theme_btn.configure(text="🌙 Dark" if new_theme == "Light" else "☀️ Light")
        
        # Update chart colors
        bg_color = '#2b2b2b' if new_theme == "Dark" else '#ffffff'
        self.fig.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)
        self.ax.tick_params(colors='white' if new_theme == "Dark" else 'black')
        self.ax.set_xlabel('Time (seconds)', color='white' if new_theme == "Dark" else 'black')
        self.ax.set_ylabel('Usage %', color='white' if new_theme == "Dark" else 'black')
        self.fig.canvas.draw()

    def export_data(self):
        """Export current data to CSV"""
        try:
            # Get save location
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Save System Data"
            )
            if not filename:
                return
            
            # Collect data
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Timestamp', 'CPU %', 'RAM %', 'Disk %', 
                               'Download (KB/s)', 'Upload (KB/s)'])
                
                # Current snapshot
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                
                # Network speed
                current_net = psutil.net_io_counters()
                time_diff = 1
                down_speed = (current_net.bytes_recv - self.prev_net.bytes_recv) / 1024 / time_diff
                up_speed = (current_net.bytes_sent - self.prev_net.bytes_sent) / 1024 / time_diff
                
                writer.writerow([now, f"{cpu:.1f}", f"{ram:.1f}", 
                               f"{disk:.1f}", f"{down_speed:.1f}", f"{up_speed:.1f}"])
                
                # Also write process data
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
            
            messagebox.showinfo("Export Complete", f"Data exported to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")

    def on_closing(self):
        """Clean shutdown"""
        self.running = False
        try:
            plt.close('all')
        except:
            pass
        self.destroy()

if __name__ == "__main__":
    app = WSL_SystemDashboard()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
