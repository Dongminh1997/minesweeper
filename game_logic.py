import random
from dataclasses import dataclass

@dataclass
class Cell:
    is_mine: bool = False
    is_revealed: bool = False
    is_flagged: bool = False
    adjacent: int = 0


class GameCore:
    """Handles core Minesweeper game logic (no UI)."""

    def __init__(self, rows=10, cols=10, mines=10):
        self.rows = rows
        self.cols = cols
        self.mines = mines

        self.is_game_over = False
        self.mines_placed = False
        self.flags_left = mines

        self.grid = [[Cell() for _ in range(cols)] for _ in range(rows)]

    # ---------- Utilities ----------
    def neighbors(self, r, c):
        """Yield valid neighboring coordinates around (r, c)."""
        for nr in range(max(0, r - 1), min(self.rows, r + 2)):
            for nc in range(max(0, c - 1), min(self.cols, c + 2)):
                if (nr, nc) != (r, c):
                    yield nr, nc

    # ---------- Mine Placement ----------
    def place_mines(self, first_click=None, safe_first=True):
        """Randomly place mines, optionally avoiding the first clicked cell."""
        all_positions = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        if safe_first and first_click and first_click in all_positions:
            all_positions.remove(first_click)

        for (r, c) in random.sample(all_positions, self.mines):
            self.grid[r][c].is_mine = True

        self._calculate_adjacent_counts()
        self.mines_placed = True

    def _calculate_adjacent_counts(self):
        """Count how many mines surround each cell."""
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c].is_mine:
                    self.grid[r][c].adjacent = 0
                    continue

                count = 0
                for nr, nc in self.neighbors(r, c):
                    if self.grid[nr][nc].is_mine:
                        count += 1
                self.grid[r][c].adjacent = count

    # ---------- Gameplay ----------
    def reveal(self, r, c):
        """Reveal a cell; False if a mine, True otherwise."""
        if self.is_game_over:
            return True

        # Lazy mine placement on first click
        if not self.mines_placed:
            self.place_mines(first_click=(r, c))

        return self._flood_reveal(r, c)

    def _flood_reveal(self, r, c):
        """Iterative flood-fill reveal starting at (r, c)."""
        start = self.grid[r][c]
        if start.is_revealed or start.is_flagged:
            return True

        # Hitting a mine on the clicked cell ends the game
        if start.is_mine:
            start.is_revealed = True
            self.is_game_over = True
            return False

        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            cell = self.grid[cr][cc]
            if cell.is_revealed or cell.is_flagged:
                continue
            cell.is_revealed = True

            # Only expand zeros; never push mines
            if cell.adjacent == 0:
                for nr, nc in self.neighbors(cr, cc):
                    ncell = self.grid[nr][nc]
                    if not ncell.is_revealed and not ncell.is_flagged and not ncell.is_mine:
                        stack.append((nr, nc))

        return True

    def toggle_flag(self, r, c):
        """Toggles a flag on a cell."""
        cell = self.grid[r][c]
        if cell.is_revealed:
            return
        cell.is_flagged = not cell.is_flagged
        self.flags_left += -1 if cell.is_flagged else 1

    def chord(self, r, c):
        """If flags around a revealed number match its count, reveal neighbors.
        Returns False if a mine gets revealed (misflag), True otherwise.
        """
        if self.is_game_over:
            return True
        cell = self.grid[r][c]
        if not cell.is_revealed or cell.adjacent == 0:
            return True

        flagged = 0
        for nr, nc in self.neighbors(r, c):
            if self.grid[nr][nc].is_flagged:
                flagged += 1

        if flagged != cell.adjacent:
            return True

        # Reveal all unflagged neighbors; if a mine is unflagged, it's a loss
        for nr, nc in list(self.neighbors(r, c)):
            ncell = self.grid[nr][nc]
            if ncell.is_flagged or ncell.is_revealed:
                continue
            if ncell.is_mine:
                ncell.is_revealed = True
                self.is_game_over = True
                return False
            self._flood_reveal(nr, nc)

        return True

    def check_win(self):
        """Checks if all non-mine cells are revealed."""
        for row in self.grid:
            for cell in row:
                if not cell.is_mine and not cell.is_revealed:
                    return False
        self.is_game_over = True
        return True

    # ---------- Reset ----------
    def reset(self):
        """Reset the game state."""
        self.is_game_over = False
        self.mines_placed = False
        self.flags_left = self.mines
        self.grid = [[Cell() for _ in range(self.cols)] for _ in range(self.rows)]
