"""
Generate symmetry example figures.

Outputs:
  outputs/symmetry/symmetric.png      — almost-perfectly symmetric tree
  outputs/symmetry/asymmetric.png     — clearly (but realistically) asymmetric
  outputs/symmetry/comparison.png     — both trees side by side

Tree design
-----------
SYMMETRIC  (score ≈ 0.92)
  Root trifurcates into A, B, C.
  A produces 3 daughter cells (a1,a2,a3), B and C produce 2 each (b1/b2, c1/c2).
  All splits happen at t2 → 7 leaves total.
  The only imbalance: A has one extra daughter vs B and C (3 vs 2).

  [((a1,a2,a3),(b1,b2),(c1,c2)),(A,B,C),(root)]

ASYMMETRIC (score ≈ 0.46)
  Stem-cell-like caterpillar: the stem always self-renews (sheds one
  differentiated cell per timepoint) before making a symmetric terminal split.

  stem → (d1, stem1)
  stem1 → (d2, stem2)
  stem2 → (d3, stem3)
  stem3 → (d4, stem4)
  stem4 → (d5, d6)          ← one balanced split at the very tip

  [(d1,(d2,(d3,(d4,(d5,d6))))),(d1,(d2,(d3,(d4,stem4)))),(d1,(d2,(d3,stem3))),(d1,(d2,stem2)),(d1,stem1),(stem)]
"""

import os
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

from tuple_to_newick import tokenize, parse_expr, build_tree, to_newick as _to_newick
from symmetry import symmetry_score, symmetry_label
from visualize import (
    layout_tree, _draw_tree_panel, _draw_symmetry_gauge,
    _text_panel, _all_nodes,
)

# ---------------------------------------------------------------------------
# Example trees
# ---------------------------------------------------------------------------

SYMMETRIC = "[((a1,a2,a3),(b1,b2),(c1,c2)),(A,B,C),(root)]"

ASYMMETRIC = (
    "[(d1,(d2,(d3,(d4,(d5,d6))))),"
    "(d1,(d2,(d3,(d4,stem4)))),"
    "(d1,(d2,(d3,stem3))),"
    "(d1,(d2,stem2)),"
    "(d1,stem1),"
    "(stem)]"
)

EXAMPLES = [
    (SYMMETRIC,  "Symmetric tree"),
    (ASYMMETRIC, "Asymmetric tree (stem-cell caterpillar)"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_tree(input_str):
    tokens = tokenize(input_str.strip())
    parsed, _ = parse_expr(tokens, 0)
    return build_tree(parsed)


def _tree_metrics(root):
    pos       = layout_tree(root)
    n_leaves  = sum(1 for n in pos if not n.children)
    max_depth = int(max(y for _, y in pos.values()))
    max_lbl   = max(len(n.name) for n in pos)
    score, ratios = symmetry_score(root)
    newick    = _to_newick(root) + ";"
    return pos, n_leaves, max_depth, max_lbl, score, ratios, newick


# ---------------------------------------------------------------------------
# Individual figures
# ---------------------------------------------------------------------------

def save_individual(input_str, label, path):
    """Save a single tree with symmetry panel."""
    from visualize import visualize
    visualize(input_str, output_path=path, title=label, show_symmetry=True)


# ---------------------------------------------------------------------------
# Comparison figure
# ---------------------------------------------------------------------------

def save_comparison(examples, path, title="Symmetry comparison"):
    """Side-by-side comparison of multiple trees in one figure."""
    trees = []
    for inp, label in examples:
        root = _parse_tree(inp)
        pos, n_leaves, max_depth, max_lbl, score, ratios, newick = _tree_metrics(root)
        trees.append(dict(
            input=inp, label=label, root=root,
            pos=pos, n_leaves=n_leaves, max_depth=max_depth,
            max_lbl=max_lbl, score=score, ratios=ratios, newick=newick,
        ))

    n = len(trees)
    panel_h   = 0.65          # slightly taller for readability
    col_w     = [max(10, t["n_leaves"] * 1.4) for t in trees]  # wider columns
    tree_hs   = [max(3.5, (t["max_depth"] + 1) * 1.35) for t in trees]
    main_tree_h = max(tree_hs)

    fig_w = sum(col_w) + 1.2 * (n - 1)        # more space between columns
    fig_h = main_tree_h + 3 * panel_h + 1.2

    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor("#fafafa")
    if title:
        fig.suptitle(title, fontsize=13, fontweight="bold", y=0.995, va="top")

    gs = GridSpec(
        4, n,
        figure=fig,
        height_ratios=[panel_h, panel_h, main_tree_h, panel_h],
        width_ratios=col_w,
        hspace=0.10,
        wspace=0.15,
    )

    for col, t in enumerate(trees):
        ax_input  = fig.add_subplot(gs[0, col])
        ax_gauge  = fig.add_subplot(gs[1, col])
        ax_tree   = fig.add_subplot(gs[2, col])
        ax_newick = fig.add_subplot(gs[3, col])

        # Use compact mode for text panels in comparison
        _text_panel(ax_input, "INPUT", t["input"], "#eef7ee", "#4a9a4a",
                    compact=True)
        _text_panel(ax_newick, "NEWICK", t["newick"], "#eeeef8", "#5555aa",
                    compact=True)

        # Gauge without labels (just the color bar)
        _draw_symmetry_gauge(ax_gauge, t["score"], show_labels=False)

        _draw_tree_panel(ax_tree, t["root"], t["pos"],
                         t["max_depth"], t["max_lbl"],
                         node_ratios=t["ratios"])

        # Column subtitle showing the label + score
        ax_input.set_title(
            f'{t["label"]}   (score = {t["score"]:.2f})',
            fontsize=10, fontweight="bold", pad=8,
        )

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    print(f"  saved → {path}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs("outputs/symmetry", exist_ok=True)

    print("Generating individual figures…")
    save_individual(SYMMETRIC,  "Symmetric tree",
                    "outputs/symmetry/symmetric.png")
    save_individual(ASYMMETRIC, "Asymmetric tree (stem-cell caterpillar)",
                    "outputs/symmetry/asymmetric.png")

    print("Generating comparison figure…")
    save_comparison(EXAMPLES, "outputs/symmetry/comparison.png")

    print("Done.")
