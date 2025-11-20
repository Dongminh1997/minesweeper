import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def neighbors(rows: int, cols: int, r: int, c: int):
    for nr in range(max(0, r - 1), min(rows, r + 2)):
        for nc in range(max(0, c - 1), min(cols, c + 2)):
            if (nr, nc) != (r, c):
                yield nr, nc


def count_neighbor_mines(mine_mask: np.ndarray) -> np.ndarray:
    rows, cols = mine_mask.shape
    numbers = np.zeros((rows, cols), dtype=np.int8)
    for r in range(rows):
        for c in range(cols):
            if mine_mask[r, c]:
                continue
            numbers[r, c] = sum(mine_mask[nr, nc] for nr, nc in neighbors(rows, cols, r, c))
    return numbers


def count_mine_clusters(mine_mask: np.ndarray) -> int:
    rows, cols = mine_mask.shape
    visited = np.zeros_like(mine_mask, dtype=bool)
    clusters = 0

    for r in range(rows):
        for c in range(cols):
            if not mine_mask[r, c] or visited[r, c]:
                continue
            clusters += 1
            stack = [(r, c)]
            visited[r, c] = True

            while stack:
                cr, cc = stack.pop()
                for nr, nc in neighbors(rows, cols, cr, cc):
                    if mine_mask[nr, nc] and not visited[nr, nc]:
                        visited[nr, nc] = True
                        stack.append((nr, nc))

    return clusters


def mines_in_local_region(mine_mask: np.ndarray) -> np.ndarray:
    rows, cols = mine_mask.shape
    heat = np.zeros((rows, cols), dtype=np.int8)
    for r in range(rows):
        for c in range(cols):
            count = int(mine_mask[r, c])
            for nr, nc in neighbors(rows, cols, r, c):
                if mine_mask[nr, nc]:
                    count += 1
            heat[r, c] = count
    return heat


def generate_board(rows: int, cols: int, mines: int, rng: np.random.Generator):
    if mines < 0 or mines >= rows * cols:
        raise ValueError("mines must be in [0, rows*cols-1]")
    flat_idx = rng.choice(rows * cols, size=mines, replace=False)
    mine_mask = np.zeros(rows * cols, dtype=bool)
    mine_mask[flat_idx] = True
    mine_mask = mine_mask.reshape(rows, cols)

    numbers = count_neighbor_mines(mine_mask)
    return mine_mask, numbers


def generate_report(rows: int, cols: int, mines: int, boards: int, output_path: str, seed: int | None = 42):
    rng = np.random.default_rng(seed)
    white_cells_per_board = []
    clusters_per_board = []
    value_counts = np.zeros(9, dtype=np.int64)
    heat_accum = np.zeros((rows, cols), dtype=np.float64)

    for _ in range(boards):
        mines_mask, numbers = generate_board(rows, cols, mines, rng)
        whites = (~mines_mask) & (numbers == 0)
        white_cells_per_board.append(int(whites.sum()))
        non_mine_vals = numbers[~mines_mask].ravel()
        value_counts += np.bincount(non_mine_vals, minlength=9)
        num_clusters = count_mine_clusters(mines_mask)
        clusters_per_board.append(num_clusters)
        heat_accum += mines_in_local_region(mines_mask)

    heat_avg = heat_accum / float(boards)

    sns.set(style="whitegrid")
    fig = plt.figure(figsize=(12, 9))
    axes = fig.subplots(2, 2)

    axes[0, 0].hist(white_cells_per_board, bins="auto", color="#4C78A8", edgecolor="black")
    axes[0, 0].set_title("Histogram of White Cells per Board")
    axes[0, 0].set_xlabel("White cells (value 0, non-mine)")
    axes[0, 0].set_ylabel("Count of boards")

    xs = np.arange(9)
    axes[0, 1].bar(xs, value_counts, color="#F58518", edgecolor="black")
    axes[0, 1].set_title("Distribution of Numbers in Cells (non-mine)")
    axes[0, 1].set_xlabel("Number shown (0-8)")
    axes[0, 1].set_xticks(xs)
    axes[0, 1].set_ylabel("Cell count")

    axes[1, 0].hist(clusters_per_board, bins="auto", color="#54A24B", edgecolor="black")
    axes[1, 0].set_title("Number of Mine Clusters per Board (8-connected)")
    axes[1, 0].set_xlabel("Clusters per board")
    axes[1, 0].set_ylabel("Count of boards")

    sns.heatmap(
        heat_avg,
        ax=axes[1, 1],
        cmap="magma",
        square=True,
        cbar_kws={"label": "Avg mines in 3x3 region"},
    )
    axes[1, 1].set_title("Average Mines in 3x3 Region (across boards)")
    axes[1, 1].set_xlabel("Column")
    axes[1, 1].set_ylabel("Row")

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
