"""Simplified high score storage and UI panel."""

import csv
import os
import tkinter as tk
from tkinter import messagebox, ttk

FIELDNAMES = [
    "name",
    "time_seconds",
    "white_cells",
    "won",
    "difficulty",
    "rows",
    "cols",
    "mines",
    "created_at",
]



class ScoreStore:
    def __init__(self, path: str):
        self.path = path
        self.ensure_file()

    def ensure_file(self):
        if os.path.exists(self.path):
            return
        with open(self.path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
            writer.writeheader()

    def save(self, record: dict):
        needs_header = not os.path.exists(self.path) or os.path.getsize(self.path) == 0
        try:
            with open(self.path, "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
                if needs_header:
                    writer.writeheader()
                writer.writerow(record)
        except OSError as exc:
            raise Exception(f"Could not save score: {exc}") from exc
        return record

    def load_scores(self):
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                return [self.normalise(row) for row in reader if row]
        except OSError as exc:
            raise Exception(f"Could not read leaderboard: {exc}") from exc

    def normalise(self, row):
        def to_int(value, default=0):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        return {
            "name": row.get("name", "Player"),
            "time_seconds": to_int(row.get("time_seconds")),
            "white_cells": to_int(row.get("white_cells")),
            "won": str(row.get("won", "0")).lower() in ("1", "true", "yes"),
            "difficulty": row.get("difficulty", ""),
            "rows": row.get("rows", ""),
            "cols": row.get("cols", ""),
            "mines": row.get("mines", ""),
            "created_at": row.get("created_at", ""),
        }


def score_key(entry):
    return (
        entry.get("name", ""),
        int(entry.get("time_seconds", 0) or 0),
        entry.get("difficulty", ""),
        entry.get("created_at", ""),
    )


class HighScorePanel:
    def __init__(self, parent, panel_bg, ui_font, score_store, max_rows=25):
        self.score_store = score_store
        self.panel_bg = panel_bg
        self.ui_font = ui_font
        self.max_rows = max_rows
        self.frame = tk.Frame(parent, bg=self.panel_bg)
        self.info_label = None
        self.tree = None
        self.build_widgets()

    def build_widgets(self):
        tk.Label(
            self.frame,
            text="High Scores",
            bg=self.panel_bg,
            fg="#111827",
            font=("Segoe UI", 14, "bold"),
        ).pack(fill=tk.X, padx=12, pady=(12, 6))

        table_frame = tk.Frame(self.frame, bg=self.panel_bg)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        columns = ("rank", "name", "time", "difficulty", "created")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        headings = {
            "rank": "#",
            "name": "Name",
            "time": "Time (s)",
            "difficulty": "Difficulty",
            "created": "Timestamp",
        }
        widths = {"rank": 50, "name": 140, "time": 80, "difficulty": 120, "created": 160}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            anchor = tk.CENTER if col in ("rank", "time") else tk.W
            self.tree.column(col, width=widths[col], anchor=anchor)
        self.tree.tag_configure("highlight", background="#FEF3C7")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        self.info_label = tk.Label(
            self.frame,
            text="No scores yet.",
            bg=self.panel_bg,
            fg="#6B7280",
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.info_label.pack(fill=tk.X, padx=12, pady=(0, 6))

    def refresh(self, highlight_key=None):
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            scores = self.score_store.load_scores()
        except Exception as exc:
            messagebox.showwarning("Leaderboard", str(exc))
            return

        wins = [s for s in scores if s.get("won")]
        if not wins:
            self.tree.insert("", "end", values=("", "No winning games yet", "", "", ""))
            self.info_label.config(text="No winning games tracked yet.")
            return

        wins.sort(key=lambda s: (s["time_seconds"], s["name"].lower()))
        rows_displayed = 0
        highlight_item = None
        for idx, entry in enumerate(wins[: max(self.max_rows, len(wins))], start=1):
            if idx > self.max_rows and (not highlight_key or score_key(entry) != highlight_key):
                break
            tags = ("highlight",) if highlight_key and score_key(entry) == highlight_key else ()
            item = self.tree.insert(
                "",
                "end",
                values=(idx, entry["name"], entry["time_seconds"], entry["difficulty"], entry["created_at"]),
                tags=tags,
            )
            if tags:
                highlight_item = item
            rows_displayed += 1

        self.info_label.config(text=f"Showing top {rows_displayed} of {len(wins)} winning games.")
        if highlight_item:
            self.tree.see(highlight_item)

    def add_record(self, record, highlight=False):
        highlight_key = score_key(record) if highlight else None
        self.refresh(highlight_key)
