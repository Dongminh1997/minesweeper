import os
import re
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from analytics_tab import AnalyticsLog, AnalyticsTab
from analytics import generate_report
from game_logic import GameCore
from highscore import HighScorePanel, ScoreStore, score_key


class Minesweeper:
    NUMBER_COLORS = {1: "blue", 2: "green", 3: "red", 4: "purple", 5: "brown", 6: "teal", 7: "black", 8: "gray"}

    CELL_BG = "#E5E7EB"       
    CELL_BG_HOVER = "#D1D5DB" 
    REVEALED_BG = "#F3F4F6"
    BOARD_BG = "#F8FAFC"
    PANEL_BG = "#FFFFFF"
    PANEL_BORDER = "#E5E7EB"
    BOARD_MAX_WIDTH = 920
    BOARD_MAX_HEIGHT = 640

    def __init__(self, root, rows=10, cols=10, mines=10):
        self.root = root
        self.rows = rows
        self.cols = cols
        self.mines = mines

        self.game = GameCore(self.rows, self.cols, self.mines)
        self.buttons = {}
        self.timer_seconds = 0
        self.timer_job = None
        self.username = "Player"
        scores_path = os.path.join(os.path.dirname(__file__), "user.csv")

        self.score_store = ScoreStore(scores_path)
        self.last_win_key = None
        base_dir = os.path.dirname(__file__)
        self.analytics_reports_dir = os.path.join(base_dir, "analytics_reports")
        os.makedirs(self.analytics_reports_dir, exist_ok=True)
        analytics_log_path = os.path.join(base_dir, "analytic.csv")

        self.analytics_log = AnalyticsLog(analytics_log_path)
        self.analytics_boards = 100
        self.analytics_mode_var = tk.BooleanVar(value=False)
        self.analytics_rows_var = tk.StringVar(value=str(rows))
        self.analytics_cols_var = tk.StringVar(value=str(cols))
        self.analytics_mines_var = tk.StringVar(value=str(mines))
        self.analytics_config_frame = None

        self.cell_font = ("Segoe UI", 10, "bold")
        self.counter_font = ("Consolas", 14, "bold")
        self.ui_font = ("Segoe UI", 11)

        self._build_ui()
        self._create_board()
        self._refresh_leaderboard_tab()

    # ---------- UI Construction ----------
    def _build_ui(self):
        # Compose the main layout: left control column + right notebook (game + scores).
        self.root.configure(bg=self.BOARD_BG)
        self.root.geometry("1200x720")
        self.root.resizable(False, False)

        self.main_frame = tk.Frame(self.root, bg=self.BOARD_BG)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 10))

        self.side_panel = tk.Frame(self.main_frame, bg=self.PANEL_BG, bd=1, relief=tk.SOLID, highlightthickness=0, width=220)
        self.side_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.side_panel.pack_propagate(False)

        tk.Label(
            self.side_panel, text="Minesweeper", bg=self.PANEL_BG, fg="#111827",
            font=("Segoe UI", 14, "bold")
        ).pack(fill=tk.X, padx=10, pady=(10, 6))

        self.mines_label = tk.Label(self.side_panel, text="Mines: 000", font=self.counter_font, bg=self.PANEL_BG, fg="#EF4444")
        self.mines_label.pack(fill=tk.X, padx=10, pady=(0, 10), anchor="w")

        self.timer_label = tk.Label(self.side_panel, text="Time: 000", font=self.counter_font, bg=self.PANEL_BG, fg="#111827")
        self.timer_label.pack(fill=tk.X, padx=10, pady=(0, 10), anchor="w")

        # Safe-first toggle
        self.safe_first_var = tk.BooleanVar(value=True)
        self.safe_first_chk = tk.Checkbutton(
            self.side_panel,
            text="Safe first",
            variable=self.safe_first_var,
            onvalue=True,
            offvalue=False,
            command=self.reset,
            bg=self.PANEL_BG,
            font=self.ui_font,
            highlightthickness=0,
            activebackground=self.PANEL_BG,
            anchor="w",
            justify=tk.LEFT,
        )
        self.safe_first_chk.pack(fill=tk.X, padx=12, pady=(0, 8))

        self.reset_btn = tk.Button(self.side_panel, text="Reset Game", width=10, font=("Segoe UI Emoji", 12), command=self.reset)
        self.reset_btn.pack(fill=tk.X, padx=10, pady=(0, 8))

        # Difficulty selector
        # Default to a valid key in the map
        self.difficulty_var = tk.StringVar(value="Intermediate")
        self.difficulty_map = {
            "Easy": (9, 9, 5),
            "Intermediate": (16, 16, 40),
            "Expert": (16, 30, 99),
        }
        self.difficulty_menu = tk.OptionMenu(self.side_panel, self.difficulty_var, *self.difficulty_map.keys(), command=self._on_change_difficulty)
        self.difficulty_menu.config(font=("Segoe UI Emoji", 12), width=10)
        self.difficulty_menu.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.analytics_toggle = tk.Checkbutton(
            self.side_panel,
            text="Analytics mode",
            variable=self.analytics_mode_var,
            onvalue=True,
            offvalue=False,
            command=self._toggle_analytics_mode,
            bg=self.PANEL_BG,
            font=self.ui_font,
            anchor="w",
            justify=tk.LEFT,
        )
        self.analytics_toggle.pack(fill=tk.X, padx=12, pady=(0, 6))

        self.analytics_config_frame = tk.LabelFrame(
            self.side_panel,
            text="Analytics settings",
            bg=self.PANEL_BG,
            fg="#111827",
            font=self.ui_font,
            labelanchor="n",
            padx=8,
            pady=4,
        )
        self._build_analytics_inputs()

        # Notebook keeps the playable board and the leaderboard in two tabs.
        self.content_notebook = ttk.Notebook(self.main_frame)
        self.content_notebook.pack(side=tk.LEFT, padx=(10, 0), fill=tk.BOTH, expand=True)

        self.game_tab = tk.Frame(self.content_notebook, bg=self.BOARD_BG)
        self.content_notebook.add(self.game_tab, text="Game")
        self.board_frame = tk.Frame(self.game_tab, bg=self.PANEL_BG, bd=1, relief=tk.SOLID)
        self.board_frame.pack(padx=0, pady=0)

        self.highscore_panel = HighScorePanel(self.content_notebook, self.PANEL_BG, self.ui_font, self.score_store)
        self.content_notebook.add(self.highscore_panel.frame, text="High Scores")

        self.analytics_tab = AnalyticsTab(
            self.content_notebook,
            self.PANEL_BG,
            self.ui_font,
            self.analytics_log,
        )
        self.content_notebook.add(self.analytics_tab.frame, text="Analytics")

        self.status = tk.Label(self.root, text="Left-click to reveal, right-click to flag. Press R to reset.", bg=self.BOARD_BG, fg="#374151", font=self.ui_font)
        self.status.pack(padx=10, pady=(0, 6), anchor="w")

        # Keyboard shortcuts
        try:
            self.root.bind("<r>", lambda e: self.reset())
            self.root.bind("<R>", lambda e: self.reset())
        except Exception:
            pass

    def _build_analytics_inputs(self):
        tk.Label(
            self.analytics_config_frame,
            text="Rows / Columns / Mines",
            wraplength=180,
            justify=tk.LEFT,
            bg=self.PANEL_BG,
            fg="#374151",
            font=("Segoe UI", 9),
        ).pack(fill=tk.X, pady=(0, 6))

        inputs_frame = tk.Frame(self.analytics_config_frame, bg=self.PANEL_BG)
        inputs_frame.pack(fill=tk.X)

        def bind_entry(var):
            def on_change(*_):
                settings = self._get_analytics_settings(show_errors=False)
                if settings:
                    rows, cols, mines = settings
                    self.analytics_rows_var.set(str(rows))
                    self.analytics_cols_var.set(str(cols))
                    self.analytics_mines_var.set(str(mines))
            var.trace_add("write", on_change)

        for label, var in (
            ("Rows", self.analytics_rows_var),
            ("Columns", self.analytics_cols_var),
            ("Mines", self.analytics_mines_var),
        ):
            wrapper = tk.Frame(inputs_frame, bg=self.PANEL_BG)
            tk.Label(wrapper, text=label, bg=self.PANEL_BG, font=("Segoe UI", 10)).pack(anchor="w")
            bind_entry(var)
            entry = tk.Entry(wrapper, textvariable=var, width=6, justify="center")
            entry.pack(anchor="w")
            wrapper.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(
            self.analytics_config_frame,
            text="Mines must be less than cells",
            bg=self.PANEL_BG,
            fg="#6B7280",
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill=tk.X, pady=(4, 0))

        # Start hidden until the toggle is enabled.
        self.analytics_config_frame.pack_forget()

    def _toggle_analytics_mode(self):
        if self.analytics_mode_var.get():
            self.analytics_rows_var.set(str(self.rows))
            self.analytics_cols_var.set(str(self.cols))
            self.analytics_mines_var.set(str(self.mines))
            self.analytics_config_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
        else:
            self.analytics_config_frame.pack_forget()


    def _create_board(self):
        for w in self.board_frame.winfo_children():
            w.destroy()
        self.buttons.clear()
        self.game.reset()
        if self.last_win_key is not None:
            self.last_win_key = None
            self._refresh_leaderboard_tab()
        if hasattr(self, "content_notebook"):
            # Reset always returns focus to the Game tab.
            self.content_notebook.select(self.game_tab)
        self._stop_timer(reset_seconds=True)
        self._update_counters()
        self.reset_btn.config(text="Reset Game")

        # Responsive cell size so the board fits within the fixed window bounds
        width_limit = self.BOARD_MAX_WIDTH // max(1, self.cols)
        height_limit = self.BOARD_MAX_HEIGHT // max(1, self.rows)
        self.cell_px = max(18, min(48, width_limit, height_limit))

        # Set board frame size and prevent shrinking
        try:
            self.board_frame.config(width=self.cell_px * self.cols, height=self.cell_px * self.rows)
            self.board_frame.grid_propagate(False)
        except Exception:
            pass

        # Configure grid sizes
        for r in range(self.rows):
            self.board_frame.grid_rowconfigure(r, weight=1, uniform="row", minsize=self.cell_px)
        for c in range(self.cols):
            self.board_frame.grid_columnconfigure(c, weight=1, uniform="col", minsize=self.cell_px)

        for r in range(self.rows):
            for c in range(self.cols):
                font_size = max(8, int(self.cell_px * 0.45))
                b = tk.Button(
                    self.board_frame,
                    text="",
                    bg=self.CELL_BG,
                    activebackground=self.CELL_BG_HOVER,
                    font=("Segoe UI", font_size, "bold"),
                    relief=tk.RAISED,
                    command=lambda r=r, c=c: self.reveal_cell(r, c),
                )
                # Right-click for flag (and middle-click as fallback)
                b.bind("<Button-3>", lambda e, r=r, c=c: self.toggle_flag(r, c)) #Window
                b.bind("<Button-2>", lambda e, r=r, c=c: self.toggle_flag(r, c)) #Mac
                
                # Hover effects
                b.bind("<Enter>", lambda e, r=r, c=c: self._hover(r, c, True))
                b.bind("<Leave>", lambda e, r=r, c=c: self._hover(r, c, False))
                b.grid(row=r, column=c, sticky="nsew")
                self.buttons[(r, c)] = b

        # If safe-first is disabled, place mines immediately so first click can hit a mine
        if not getattr(self, "safe_first_var", None) or not self.safe_first_var.get():
            try:
                self.game.place_mines(first_click=None, safe_first=False)
            except TypeError:
                # Fallback for older GameCore signature
                self.game.place_mines(first_click=None)

        # Let window recompute size based on new content
        try:
            self.root.update_idletasks()
        except Exception:
            pass

    # ---------- Game Logic (UI Layer) ----------
    def reveal_cell(self, r, c):
        if self.game.is_game_over:
            return
        # Start timer on first reveal
        if self.timer_job is None and self.timer_seconds == 0:
            self._start_timer()
        ok = self.game.reveal(r, c)
        self._refresh_ui()
        if not ok:
            self._show_mines()
            self.game_over(False)
        elif self.game.check_win():
            self.game_over(True)

    def toggle_flag(self, r, c):
        if self.game.is_game_over:
            return
        self.game.toggle_flag(r, c)
        self._refresh_ui()

    def _refresh_ui(self):
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.game.grid[r][c]
                btn = self.buttons[(r, c)]
                if cell.is_flagged:
                    btn.config(text="🚩", fg="#EF4444", bg=self.CELL_BG)
                elif cell.is_revealed:
                    btn.config(state="disabled", relief=tk.SUNKEN, bg=self.REVEALED_BG, disabledforeground="#111827")
                    if cell.is_mine:
                        btn.config(text="💣", bg="#FCA5A5")
                    elif cell.neighbor_mines > 0:
                        btn.config(text=str(cell.neighbor_mines), fg=self.NUMBER_COLORS.get(cell.neighbor_mines, "#111827"))
                    else:
                        btn.config(text="")
                else:
                    btn.config(text="", bg=self.CELL_BG)

        self._update_counters()

    def _show_mines(self):
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.game.grid[r][c]
                if cell.is_mine:
                    self.buttons[(r, c)].config(text="💣", bg="#FEE2E2")

    def game_over(self, won):
        self.game.is_game_over = True
        self._stop_timer()
        message = "You Win! 🎉" if won else "Game over! 😵"
        messagebox.showinfo("Game Over", message)
        player_name = self._prompt_for_name()
        if player_name:
            self.username = player_name
        else:
            player_name = self.username or "Player"
        record = self._save_score(player_name, won)
        self.last_win_key = score_key(record) if (won and record) else None
        self._refresh_leaderboard_tab()
        if won and hasattr(self, "content_notebook") and hasattr(self, "highscore_panel"):
            # After a win and confirmation, jump straight to the leaderboard tab.
            self.content_notebook.select(self.highscore_panel.frame)
        self._generate_analytics_report(player_name, won)

    def _prompt_for_name(self):
        try:
            name = simpledialog.askstring(
                "Leaderboard Entry",
                "Enter your name for the leaderboard:",
                parent=self.root,
                initialvalue=self.username,
            )
            if name is None:
                return None
            name = name.strip()
            return name or None
        except Exception:
            return None

    def _get_board_config(self):
        return {"rows": self.rows, "cols": self.cols, "mines": self.mines}

    def _get_analytics_settings(self, show_errors=True):
        if not self.analytics_mode_var.get():
            return None
        try:
            rows = int(self.analytics_rows_var.get())
            cols = int(self.analytics_cols_var.get())
            mines = int(self.analytics_mines_var.get())
        except ValueError:
            if show_errors:
                messagebox.showwarning("Analytics", "Analytics settings must be integers.")
            return None
        if rows <= 0 or cols <= 0:
            if show_errors:
                messagebox.showwarning("Analytics", "Rows and columns must be positive.")
            return None
        if mines < 0:
            if show_errors:
                messagebox.showwarning("Analytics", "Mines must be zero or positive.")
            return None
        if mines >= rows * cols:
            if show_errors:
                messagebox.showwarning("Analytics", "Mines must be less than the number of cells.")
            return None
        return rows, cols, mines

    def _generate_analytics_report(self, player_name, won):
        settings = self._get_analytics_settings()
        if not settings:
            return None
        rows, cols, mines = settings
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        unix_suffix = str(int(now.timestamp()))
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", player_name or "Player").strip("_") or "Player"
        filename = f"{safe_name}_{unix_suffix}.pdf"
        pdf_path = os.path.join(self.analytics_reports_dir, filename)
        try:
            generate_report(rows, cols, mines, self.analytics_boards, pdf_path)
        except Exception as exc:
            messagebox.showwarning("Analytics", f"Failed to build analytics report:\n{exc}")
            return None
        record = {
            "created_at": timestamp,
            "name": player_name,
            "pdf_path": pdf_path,
            "time_seconds": self.timer_seconds,
            "rows": rows,
            "cols": cols,
            "mines": mines,
            "won": bool(won),
        }
        try:
            self.analytics_log.append(record)
        except OSError as exc:
            messagebox.showwarning("Analytics", f"Could not store analytics record:\n{exc}")
        if hasattr(self, "analytics_tab"):
            self.analytics_tab.add_record(record)
        return record

    def _build_score_record(self, name, won):
        # Normalize the payload that is persisted to CSV (and reflected in the Treeview).
        difficulty = getattr(self, "difficulty_var", None)
        difficulty_label = difficulty.get() if difficulty else f"{self.rows}x{self.cols}"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "name": name,
            "time_seconds": self.timer_seconds,
            "white_cells": self._count_white_cells(),
            "won": "1" if won else "0",
            "difficulty": difficulty_label,
            "rows": self.rows,
            "cols": self.cols,
            "mines": self.mines,
            "created_at": created_at,
        }

    def _count_white_cells(self):
        count = 0
        for row in self.game.grid:
            for cell in row:
                if not cell.is_mine and cell.neighbor_mines == 0:
                    count += 1
        return count

    def _save_score(self, name, won):
        record = self._build_score_record(name, won)
        try:
            return self.score_store.save(record)
        except Exception as exc:
            messagebox.showwarning("Leaderboard", str(exc))
            return None

    def _refresh_leaderboard_tab(self):
        if hasattr(self, "highscore_panel"):
            self.highscore_panel.refresh(self.last_win_key)

    # ---------- Helpers ----------
    def _update_counters(self):
        self.mines_label.config(text=f"Mines: {self.game.flags_left:03d}")
        self.timer_label.config(text=f"Time: {self.timer_seconds:03d}")

    def _hover(self, r, c, is_enter):
        cell = self.game.grid[r][c]
        btn = self.buttons[(r, c)]
        if cell.is_revealed or cell.is_flagged:
            return
        btn.config(bg=self.CELL_BG_HOVER if is_enter else self.CELL_BG)

    def _stop_timer(self, reset_seconds=False):
        if self.timer_job is not None:
            try:
                self.root.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None
        if reset_seconds:
            self.timer_seconds = 0

    def _start_timer(self):
        def tick():
            self.timer_seconds += 1
            try:
                self.timer_label.config(text=f"Time: {self.timer_seconds:03d}")
            except Exception:
                pass
            self.timer_job = self.root.after(1000, tick)

        # ensure only one timer
        if self.timer_job is None:
            self.timer_job = self.root.after(1000, tick)

    def _on_change_difficulty(self, *_):
        rows, cols, mines = self.difficulty_map[self.difficulty_var.get()]
        self.rows, self.cols, self.mines = rows, cols, mines
        # Recreate game core with new dimensions
        self.game = GameCore(self.rows, self.cols, self.mines)
        self.reset()

    def reset(self):
        self._create_board()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Minesweeper")
    Minesweeper(root, rows=10, cols=10, mines=10)
    root.mainloop()
