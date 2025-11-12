import tkinter as tk
from tkinter import messagebox
from game_logic import GameCore

class Minesweeper:
    NUMBER_COLORS = {
        1: "#1976D2", 
        2: "#388E3C", 
        3: "#D32F2F",
        4: "#7B1FA2",
        5: "#5D4037",
        6: "#00838F",
        7: "#000000",
        8: "#616161",
    }

    CELL_BG = "#E5E7EB"       
    CELL_BG_HOVER = "#D1D5DB" 
    REVEALED_BG = "#F3F4F6"
    BOARD_BG = "#F8FAFC"
    PANEL_BG = "#FFFFFF"
    PANEL_BORDER = "#E5E7EB"

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

        self.cell_font = ("Segoe UI", 10, "bold")
        self.counter_font = ("Consolas", 14, "bold")
        self.ui_font = ("Segoe UI", 11)

        self._build_ui()
        self._create_board()

    # ---------- UI Construction ----------
    def _build_ui(self):
        self.root.configure(bg=self.BOARD_BG)

        self.main_frame = tk.Frame(self.root, bg=self.BOARD_BG)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 10))

        self.side_panel = tk.Frame(self.main_frame, bg=self.PANEL_BG, bd=1, relief=tk.SOLID, highlightthickness=0)
        self.side_panel.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(
            self.side_panel, text="Minesweeper", bg=self.PANEL_BG, fg="#111827",
            font=("Segoe UI", 14, "bold")
        ).pack(fill=tk.X, padx=10, pady=(10, 6))

        self.mines_label = tk.Label(self.side_panel, text="Mines: 000", font=self.counter_font, bg=self.PANEL_BG, fg="#EF4444")
        self.mines_label.pack(fill=tk.X, padx=10, pady=(0, 10), anchor="w")

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
        self.difficulty_var = tk.StringVar(value="Medium")
        self.difficulty_map = {
            "Easy": (9, 9, 10),
            "Intermediate": (16, 16, 40),
            "Expert": (16, 30, 99),
        }
        self.difficulty_menu = tk.OptionMenu(self.side_panel, self.difficulty_var, *self.difficulty_map.keys(), command=self._on_change_difficulty)
        self.difficulty_menu.config(font=("Segoe UI Emoji", 12), width=10)
        self.difficulty_menu.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.board_frame = tk.Frame(self.main_frame, bg=self.PANEL_BG, bd=1, relief=tk.SOLID)
        self.board_frame.pack(side=tk.LEFT, padx=(10, 0))

        self.status = tk.Label(self.root, text="Left-click to reveal, right-click to flag.", bg=self.BOARD_BG, fg="#374151", font=self.ui_font)
        self.status.pack(padx=10, pady=(0, 6), anchor="w")

    def _create_board(self):
        for w in self.board_frame.winfo_children():
            w.destroy()
        self.buttons.clear()
        self.game.reset()
        self._stop_timer(reset_seconds=True)
        self._update_counters()
        self.reset_btn.config(text="Reset Game")

        # Responsive cell size to keep board tidy
        max_board_px = 520
        self.cell_px = max(18, min(48, min(max_board_px // max(1, self.cols), max_board_px // max(1, self.rows))))

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
            self.root.geometry("")
        except Exception:
            pass

    # ---------- Game Logic (UI Layer) ----------
    def reveal_cell(self, r, c):
        if self.game.is_game_over:
            return
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
                    elif cell.adjacent > 0:
                        btn.config(text=str(cell.adjacent), fg=self.NUMBER_COLORS.get(cell.adjacent, "#111827"))
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
        self.reset_btn.config(text="😎" if won else "😵")
        message = "You Win! 🎉" if won else "You hit a mine 💥"
        messagebox.showinfo("Game Over", message)

    # ---------- Helpers ----------
    def _update_counters(self):
        self.mines_label.config(text=f"Mines: {self.game.flags_left:03d}")

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
