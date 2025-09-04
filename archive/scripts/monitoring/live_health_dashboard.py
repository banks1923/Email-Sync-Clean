#!/usr/bin/env python3
"""
Live System Health Dashboard Real-time updating dashboard with web interface.
"""

import sqlite3
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import requests
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class LiveHealthDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Email Sync System - Live Health Dashboard")
        self.root.geometry("1200x800")

        # Data storage
        self.current_data = {}
        self.data_history = []
        self.max_history = 100

        # Create matplotlib figure
        self.fig, self.axes = plt.subplots(2, 3, figsize=(12, 8))
        self.fig.suptitle("Live System Health Dashboard", fontsize=16, fontweight="bold")

        # Embed matplotlib in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Control panel
        self.create_control_panel()

        # Start data collection thread
        self.running = True
        self.data_thread = threading.Thread(target=self.data_collector, daemon=True)
        self.data_thread.start()

        # Start animation
        self.ani = animation.FuncAnimation(self.fig, self.update_plots, interval=5000, blit=False)

    def create_control_panel(self):
        """
        Create control panel with buttons and status.
        """
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Status label
        self.status_label = ttk.Label(control_frame, text="Status: Starting...")
        self.status_label.pack(side=tk.LEFT)

        # Refresh button
        ttk.Button(control_frame, text="Force Refresh", command=self.force_refresh).pack(
            side=tk.RIGHT, padx=5
        )

        # Auto-refresh toggle
        self.auto_refresh = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Auto Refresh", variable=self.auto_refresh).pack(
            side=tk.RIGHT, padx=5
        )

        # Update interval
        ttk.Label(control_frame, text="Interval (s):").pack(side=tk.RIGHT)
        self.interval_var = tk.StringVar(value="5")
        interval_spinbox = ttk.Spinbox(
            control_frame, from_=1, to=60, width=5, textvariable=self.interval_var
        )
        interval_spinbox.pack(side=tk.RIGHT, padx=5)

    def get_db_path(self):
        """
        Get database path consistently.
        """
        return Path(__file__).parent.parent / "data" / "system_data" / "emails.db"

    def collect_system_data(self):
        """
        Collect current system data.
        """
        data = {"timestamp": datetime.now(), "services": {}, "database": {}, "filesystem": {}}

        # Check services
        try:
            response = requests.get("http://localhost:6333/health", timeout=2)
            data["services"]["qdrant"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            data["services"]["qdrant"] = "offline"

        # Check database
        try:
            db_path = self.get_db_path()
            conn = sqlite3.connect(str(db_path), timeout=1)

            # Get record counts
            tables = ["content_unified", "documents", "embeddings", "consolidated_entities"]
            for table in tables:
                try:
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    data["database"][table] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    data["database"][table] = 0

            # Get database size
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            data["database"]["size_mb"] = (page_size * page_count) / (1024 * 1024)

            conn.close()
            data["services"]["database"] = "healthy"
        except Exception as e:
            data["services"]["database"] = "unhealthy"
            data["database"] = {"error": str(e)}

        # File system stats
        base_path = Path(__file__).parent.parent / "data"
        if base_path.exists():
            data["services"]["filesystem"] = "healthy"
            # Quick file count
            try:
                user_data_path = base_path / "Stoneman_dispute" / "user_data"
                if user_data_path.exists():
                    data["filesystem"]["user_files"] = len(list(user_data_path.glob("*")))
                else:
                    data["filesystem"]["user_files"] = 0
            except:
                data["filesystem"]["user_files"] = 0
        else:
            data["services"]["filesystem"] = "unhealthy"
            data["filesystem"] = {}

        return data

    def data_collector(self):
        """
        Background thread to collect data.
        """
        while self.running:
            try:
                if self.auto_refresh.get():
                    new_data = self.collect_system_data()
                    self.current_data = new_data

                    # Add to history
                    self.data_history.append(new_data)
                    if len(self.data_history) > self.max_history:
                        self.data_history.pop(0)

                    # Update status
                    healthy_services = sum(
                        1 for status in new_data["services"].values() if status == "healthy"
                    )
                    total_services = len(new_data["services"])
                    self.status_label.config(
                        text=f"Status: {healthy_services}/{total_services} services healthy - "
                        f"Last update: {new_data['timestamp'].strftime('%H:%M:%S')}"
                    )

                interval = int(self.interval_var.get())
                time.sleep(interval)

            except Exception as e:
                print(f"Data collection error: {e}")
                time.sleep(5)

    def force_refresh(self):
        """
        Force immediate data refresh.
        """
        try:
            new_data = self.collect_system_data()
            self.current_data = new_data
            self.data_history.append(new_data)
            if len(self.data_history) > self.max_history:
                self.data_history.pop(0)
        except Exception as e:
            print(f"Force refresh error: {e}")

    def update_plots(self, _):
        """
        Update all plots with current data.
        """
        if not self.current_data:
            return []

        # Clear all axes
        for ax in self.axes.flat:
            ax.clear()

        data = self.current_data

        # Colors
        colors = {
            "healthy": "#2ecc71",
            "warning": "#f39c12",
            "unhealthy": "#e74c3c",
            "offline": "#95a5a6",
            "primary": "#3498db",
        }

        # 1. Service Status
        ax1 = self.axes[0, 0]
        services = list(data["services"].keys())
        statuses = list(data["services"].values())
        status_colors = [colors.get(status, colors["offline"]) for status in statuses]

        bars = ax1.barh(services, [1] * len(services), color=status_colors, alpha=0.8)
        ax1.set_xlim(0, 1)
        ax1.set_title("Service Status")
        ax1.set_xticks([])

        for i, (bar, status) in enumerate(zip(bars, statuses)):
            ax1.text(
                0.5,
                i,
                status.upper(),
                ha="center",
                va="center",
                fontweight="bold",
                color="white",
                fontsize=8,
            )

        # 2. Database Records
        ax2 = self.axes[0, 1]
        if "database" in data and isinstance(data["database"], dict):
            db_data = {
                k: v for k, v in data["database"].items() if k != "size_mb" and isinstance(v, int)
            }
            if db_data:
                tables = list(db_data.keys())
                counts = list(db_data.values())
                ax2.bar(tables, counts, color=colors["primary"], alpha=0.7)
                ax2.set_title("Database Records")
                ax2.set_ylabel("Count")
                plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")

                # Add value labels
                for i, (table, count) in enumerate(zip(tables, counts)):
                    ax2.text(
                        i,
                        count + max(counts) * 0.01,
                        f"{count:,}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )
        ax2.set_title("Database Records")

        # 3. Historical trend (if we have history)
        ax3 = self.axes[0, 2]
        if len(self.data_history) > 1:
            timestamps = [d["timestamp"] for d in self.data_history]
            if "content_unified" in data.get("database", {}):
                content_counts = [
                    d.get("database", {}).get("content_unified", 0) for d in self.data_history
                ]
                ax3.plot(timestamps, content_counts, marker="o", color=colors["primary"])
                ax3.set_title("Content Unified Trend")
                ax3.set_ylabel("Count")
                plt.setp(ax3.get_xticklabels(), rotation=45, ha="right")
        ax3.set_title("Historical Trends")

        # 4. Service Health Over Time
        ax4 = self.axes[1, 0]
        if len(self.data_history) > 1:
            timestamps = [d["timestamp"] for d in self.data_history[-20:]]  # Last 20 points
            for service in ["qdrant", "database", "filesystem"]:
                health_scores = []
                for d in self.data_history[-20:]:
                    status = d.get("services", {}).get(service, "offline")
                    score = {"healthy": 1, "warning": 0.5, "unhealthy": 0.2, "offline": 0}
                    health_scores.append(score.get(status, 0))

                ax4.plot(timestamps, health_scores, marker="o", label=service, linewidth=2)

            ax4.set_ylim(-0.1, 1.1)
            ax4.set_ylabel("Health Score")
            ax4.set_title("Service Health Trends")
            ax4.legend()
            plt.setp(ax4.get_xticklabels(), rotation=45, ha="right")
        ax4.set_title("Service Health Trends")

        # 5. Database Size Trend
        ax5 = self.axes[1, 1]
        if len(self.data_history) > 1:
            timestamps = [d["timestamp"] for d in self.data_history]
            sizes = [d.get("database", {}).get("size_mb", 0) for d in self.data_history]
            if any(sizes):
                ax5.plot(timestamps, sizes, marker="o", color=colors["warning"])
                ax5.set_title("Database Size (MB)")
                ax5.set_ylabel("Size (MB)")
                plt.setp(ax5.get_xticklabels(), rotation=45, ha="right")
        ax5.set_title("Database Size Trend")

        # 6. Current Summary
        ax6 = self.axes[1, 2]
        ax6.axis("off")

        summary_text = []
        summary_text.append("LIVE SYSTEM STATUS")
        summary_text.append("=" * 18)
        summary_text.append("")

        # Current status
        healthy_services = sum(1 for status in data["services"].values() if status == "healthy")
        total_services = len(data["services"])
        summary_text.append(f"Services: {healthy_services}/{total_services} Healthy")

        if "database" in data and isinstance(data["database"], dict):
            total_records = sum(
                v for k, v in data["database"].items() if isinstance(v, int) and k != "size_mb"
            )
            summary_text.append(f"Records: {total_records:,}")

            size = data["database"].get("size_mb", 0)
            summary_text.append(f"DB Size: {size:.1f} MB")

        summary_text.append("")
        summary_text.append(f"Updates: {len(self.data_history)}")
        summary_text.append(f"Last: {data['timestamp'].strftime('%H:%M:%S')}")

        ax6.text(
            0.05,
            0.95,
            "\n".join(summary_text),
            transform=ax6.transAxes,
            fontsize=10,
            verticalalignment="top",
            fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8),
        )

        plt.tight_layout()

        return []

    def run(self):
        """
        Start the live dashboard.
        """
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()

    def on_closing(self):
        """
        Cleanup when closing.
        """
        self.running = False
        self.root.quit()
        self.root.destroy()


def main():
    """
    Run the live dashboard.
    """
    print("Starting Live Health Dashboard...")
    print("Close the window to stop.")

    dashboard = LiveHealthDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
