"""Simple analytics log viewer used inside the GUI."""

import csv
import os
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

FIELDNAMES = [
    "created_at",
    "name",
    "pdf_path",
    "time_seconds",
    "rows",
    "cols",
    "mines",
    "won",
]


class AnalyticsLog:
    def __init__(self, path: str):
        self.path = path
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.path):
            with open(self.path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
                writer.writeheader()
            return
        with open(self.path, newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
        if not rows:
            with open(self.path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
                writer.writeheader()
            return
        header = rows[0]
        if header == FIELDNAMES:
            return
        converted = []
        for row in rows:
            if len(row) < len(FIELDNAMES):
                continue
            converted.append(
                {
                    "created_at": row[0],
                    "name": row[1],
                    "pdf_path": row[2],
                    "time_seconds": row[3],
                    "rows": row[4],
                    "cols": row[5],
                    "mines": row[6],
                    "won": row[7],
                }
            )
        with open(self.path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(converted)

    def append(self, record: dict):
        with open(self.path, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writerow(record)

    def read_all(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = []
            for row in reader:
                row["time_seconds"] = self._to_int(row.get("time_seconds"))
                rows.append(row)
        rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return rows

    @staticmethod
    def _to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


class AnalyticsTab:
    def __init__(self, parent, panel_bg, ui_font, analytics_log: AnalyticsLog):
        self.log = analytics_log
        self.panel_bg = panel_bg
        self.ui_font = ui_font
        self.frame = tk.Frame(parent, bg=self.panel_bg)
        self.status_var = tk.StringVar(value="Analytics reports will appear here.")
        self.tree = None
        self._item_paths = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        tk.Label(
            self.frame,
            text="Analytics Reports",
            bg=self.panel_bg,
            fg="#111827",
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=12, pady=(12, 6))

        table_frame = tk.Frame(self.frame, bg=self.panel_bg)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        columns = ("name", "timestamp", "time", "pdf")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        self.tree.heading("name", text="Player")
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("time", text="Time (s)")
        self.tree.heading("pdf", text="Analytics PDF")
        self.tree.column("name", width=150, anchor=tk.W)
        self.tree.column("timestamp", width=160, anchor=tk.W)
        self.tree.column("time", width=80, anchor=tk.CENTER)
        self.tree.column("pdf", width=320, anchor=tk.W)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        controls = tk.Frame(self.frame, bg=self.panel_bg)
        controls.pack(fill=tk.X, padx=12, pady=(0, 8))

        tk.Button(
            controls,
            text="Open Selected Report",
            command=self._open_selected,
            font=self.ui_font,
            width=20,
        ).pack(side=tk.LEFT)

        tk.Label(
            self.frame,
            textvariable=self.status_var,
            bg=self.panel_bg,
            fg="#374151",
            anchor="w",
            font=("Segoe UI", 10),
        ).pack(fill=tk.X, padx=12, pady=(0, 10))

    def refresh(self):
        self._item_paths.clear()
        for row in self.tree.get_children():
            self.tree.delete(row)
        records = self.log.read_all()
        if not records:
            self.status_var.set("No analytics reports yet.")
            return
        for record in records:
            display_pdf = os.path.basename(record.get("pdf_path", "")) if record.get("pdf_path") else ""
            item = self.tree.insert(
                "",
                "end",
                values=(
                    record.get("name", "Player"),
                    record.get("created_at", ""),
                    record.get("time_seconds", 0),
                    display_pdf,
                ),
            )
            self._item_paths[item] = record.get("pdf_path", "")
        self.status_var.set(f"Showing {len(records)} analytics report(s).")

    def add_record(self, record: dict):
        self.refresh()

    def _open_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Analytics", "Select a report to open.")
            return
        pdf_path = self._item_paths.get(selected[0], "")
        if not pdf_path:
            messagebox.showwarning("Analytics", "No PDF path recorded for this entry.")
            return
        if not os.path.exists(pdf_path):
            messagebox.showwarning("Analytics", f"File not found:\n{pdf_path}")
            return
        try:
            webbrowser.open_new(pdf_path)
        except Exception as exc:
            messagebox.showwarning("Analytics", f"Could not open file:\n{exc}")
