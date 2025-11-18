"""Analytics report generator using simulated board data."""

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy import ndimage


def generate_board(rows: int, cols: int, mines: int, rng: np.random.Generator):
    if mines < 0 or mines >= rows * cols:
        raise ValueError("mines must be in [0, rows*cols-1]")
    flat_idx = rng.choice(rows * cols, size=mines, replace=False)
    mine_mask = np.zeros(rows * cols, dtype=bool)
    mine_mask[flat_idx] = True
    mine_mask = mine_mask.reshape(rows, cols)

    kernel8 = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=int)
    numbers = ndimage.convolve(mine_mask.astype(int), kernel8, mode="constant", cval=0)
    return mine_mask, numbers.astype(np.int8)


def generate_report(rows: int, cols: int, mines: int, n_boards: int, output_path: str, seed: int | None = 42):
    rng = np.random.default_rng(seed)

    white_cells_per_board = []
    clusters_per_board = []
    value_counts = np.zeros(9, dtype=np.int64)
    heat_accum = np.zeros((rows, cols), dtype=np.float64)

    struct8 = np.ones((3, 3), dtype=int)
    kernel9 = np.ones((3, 3), dtype=int)

    for _ in range(n_boards):
        mines_mask, numbers = generate_board(rows, cols, mines, rng)
        whites = (~mines_mask) & (numbers == 0)
        white_cells_per_board.append(int(whites.sum()))

        non_mine_vals = numbers[~mines_mask].ravel()
        value_counts += np.bincount(non_mine_vals, minlength=9)

        _, num_clusters = ndimage.label(mines_mask, structure=struct8)
        clusters_per_board.append(int(num_clusters))

        heat_accum += ndimage.convolve(mines_mask.astype(int), kernel9, mode="constant", cval=0)

    heat_avg = heat_accum / float(n_boards)

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


if __name__ == "__main__":
    raise SystemExit("This module is intended to be imported by gui.py")
