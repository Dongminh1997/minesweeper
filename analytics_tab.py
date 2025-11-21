"""Simple analytics log viewer used inside the GUI."""

import csv
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

FIELDNAMES = [
    "created_at",
    "boards",
    "rows",
    "cols",
    "mines",
    "pdf_path",
]


class AnalyticsLog:
    def __init__(self, path: str):
        self.path = path
        self.ensure_file()

    def ensure_file(self):
        if not os.path.exists(self.path):
            self.write_header()
            return
        with open(self.path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            header = reader.fieldnames or []
        if not header:
            self.write_header()
            return
        if header == FIELDNAMES:
            return
        converted = [self.convert_row(row) for row in rows]
        with open(self.path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(converted)

    def write_header(self):
        with open(self.path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()

    def convert_row(self, row: dict):
        return {
            "created_at": row.get("created_at") or row.get("timestamp") or "",
            "boards": self.to_int(row.get("boards")),
            "rows": self.to_int(row.get("rows")),
            "cols": self.to_int(row.get("cols")),
            "mines": self.to_int(row.get("mines")),
            "pdf_path": row.get("pdf_path") or row.get("pdf") or "",
        }

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
                row["boards"] = self.to_int(row.get("boards"))
                row["rows"] = self.to_int(row.get("rows"))
                row["cols"] = self.to_int(row.get("cols"))
                row["mines"] = self.to_int(row.get("mines"))
                rows.append(row)
        rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return rows

    @staticmethod
    def to_int(value):
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
        self.build_ui()
        self.refresh()

    def build_ui(self):
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

        columns = ("timestamp", "boards", "rows", "columns", "mines", "pdf")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("boards", text="Boards")
        self.tree.heading("rows", text="Rows")
        self.tree.heading("columns", text="Columns")
        self.tree.heading("mines", text="Mines")
        self.tree.heading("pdf", text="PDF File")

        self.tree.column("timestamp", width=170, anchor=tk.W)
        self.tree.column("boards", width=90, anchor=tk.CENTER)
        self.tree.column("rows", width=90, anchor=tk.CENTER)
        self.tree.column("columns", width=90, anchor=tk.CENTER)
        self.tree.column("mines", width=90, anchor=tk.CENTER)
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
            command=self.open_selected,
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
                    record.get("created_at", ""),
                    record.get("boards", 0),
                    record.get("rows", 0),
                    record.get("cols", 0),
                    record.get("mines", 0),
                    display_pdf,
                ),
            )
            self._item_paths[item] = record.get("pdf_path", "")
        self.status_var.set(f"Showing {len(records)} analytics report(s).")

    def add_record(self, record: dict):
        self.refresh()
        self.highlight_pdf(record.get("pdf_path", ""))

    def highlight_pdf(self, pdf_path: str):
        if not pdf_path:
            return
        target = os.path.abspath(pdf_path)
        for item, path in self._item_paths.items():
            if os.path.abspath(path) == target:
                try:
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    self.tree.see(item)
                except Exception:
                    pass
                break

    def open_selected(self):
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
            target = pdf_path
            if sys.platform == "darwin":
                target = f"file://{os.path.abspath(pdf_path)}"
            webbrowser.open_new(target)
        except Exception as exc:
            messagebox.showwarning("Analytics", f"Could not open file:\n{exc}")
