import random
# from dataclasses import dataclass

class Cell:
    def __init__(self):
        self.is_mine: bool = False
        self.is_revealed: bool = False
        self.is_flagged: bool = False
        self.neighbor_mines: int = 0


class GameCore:
    def __init__(self, rows=10, cols=10, mines=10):
        self.rows = rows
        self.cols = cols
        self.mines = mines

        self.is_game_over = False
        self.mines_placed = False
        self.flags_left = mines

        self.grid = [[Cell() for _ in range(self.cols)] for _ in range(self.rows)]

    def neighbors(self, r, c):
        neighbors_list = []
        for nr in range(max(0, r - 1), min(self.rows, r + 2)):
            for nc in range(max(0, c - 1), min(self.cols, c + 2)):
                if (nr, nc) != (r, c):
                    neighbors_list.append((nr, nc))

        return neighbors_list
    
    def count_neighbor_mines(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c].is_mine:
                    self.grid[r][c].neighbor_mines = 0
                    continue

                count = 0
                for nr, nc in self.neighbors(r, c):
                    if self.grid[nr][nc].is_mine:
                        count += 1
                self.grid[r][c].neighbor_mines = count

    def place_mines(self, first_click=None, safe_first=True):
        all_cells = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        if safe_first and first_click and first_click in all_cells:
            all_cells.remove(first_click)

        for (r, c) in random.sample(all_cells, self.mines):
            self.grid[r][c].is_mine = True

        self.count_neighbor_mines()
        self.mines_placed = True

    def reveal(self, r, c):
        if self.is_game_over:
            return True

        if not self.mines_placed:
            self.place_mines(first_click=(r, c))

        return self.large_area_reveal(r, c)

    def large_area_reveal(self, r, c):
        start = self.grid[r][c]
        if start.is_revealed or start.is_flagged:
            return True

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

            if cell.neighbor_mines == 0:
                for nr, nc in self.neighbors(cr, cc):
                    ncell = self.grid[nr][nc]
                    if not ncell.is_revealed and not ncell.is_flagged and not ncell.is_mine:
                        stack.append((nr, nc))
        return True

    def toggle_flag(self, r, c):
        cell = self.grid[r][c]
        if cell.is_revealed:
            return None
        cell.is_flagged = not cell.is_flagged
        flag = -1 if cell.is_flagged else 1
        self.flags_left += flag

    def check_win(self):
        for row in self.grid:
            for cell in row:
                if not cell.is_mine and not cell.is_revealed:
                    return False
        self.is_game_over = True
        return True

    def reset(self):
        self.is_game_over = False
        self.mines_placed = False
        self.flags_left = self.mines
        self.grid = [[Cell() for _ in range(self.cols)] for _ in range(self.rows)]
