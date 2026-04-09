"""
Visualize a nested-tuple lineage tree as a cladogram-style figure.

Default (3-panel) layout:
  ┌─────────────────────────────────────────┐
  │  INPUT  [((G,H),(I,(J,K))),(D,(E,F)),…] │  ← green box
  │            cladogram diagram            │  ← tree
  │  NEWICK  (((G,H)D)B,((I)E,(J,K)F)C)A;  │  ← blue box
  └─────────────────────────────────────────┘

With show_symmetry=True a symmetry gauge panel is inserted:
  ┌─────────────────────────────────────────┐
  │  INPUT  [...]                           │
  │  SYMMETRY  0.73  [red ──── green bar]   │  ← gauge
  │            cladogram (edges coloured)   │
  │  NEWICK  [...]                          │
  └─────────────────────────────────────────┘
"""

import textwrap
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

from tuple_to_newick import tokenize, parse_expr, build_tree, to_newick as _to_newick, TreeNode


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _all_nodes(root: TreeNode):
    """Yield every node in DFS order."""
    yield root
    for c in root.children:
        yield from _all_nodes(c)


def layout_tree(root: TreeNode):
    """Return {node: (x, y)} with y = depth and x centred over leaves."""
    leaves = [n for n in _all_nodes(root) if not n.children]
    leaf_x = {id(n): float(i) for i, n in enumerate(leaves)}

    depth: dict[int, int] = {}
    def assign_depth(node, d):
        depth[id(node)] = d
        for c in node.children:
            assign_depth(c, d + 1)
    assign_depth(root, 0)

    x_pos: dict[int, float] = {}
    def assign_x(node):
        if not node.children:
            x_pos[id(node)] = leaf_x[id(node)]
        else:
            xs = [assign_x(c) for c in node.children]
            x_pos[id(node)] = sum(xs) / len(xs)
        return x_pos[id(node)]
    assign_x(root)

    return {node: (x_pos[id(node)], float(depth[id(node)])) for node in _all_nodes(root)}


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _draw_edges(ax, pos, root: TreeNode, node_ratios=None, lw=1.8):
    """Dendrogram step edges: stem → horizontal bar → legs.

    When node_ratios is provided, the horizontal split bar and legs are
    coloured by the balance ratio (RdYlGn: red = asymmetric, green = symmetric).
    Continuation edges (single child) and stems remain dark grey.
    """
    sym_cmap = plt.cm.RdYlGn
    default_color = "#444444"

    for parent in _all_nodes(root):
        if not parent.children:
            continue
        px, py = pos[parent]
        child_positions = [pos[c] for c in parent.children]
        cy = child_positions[0][1]
        child_xs = [cp[0] for cp in child_positions]
        mid_y = (py + cy) / 2.0

        # Colour for the split bar (only meaningful when ≥2 children)
        ratio = (node_ratios or {}).get(parent)
        split_color = sym_cmap(ratio) if ratio is not None else default_color

        # Stem: parent node down to elbow (neutral grey)
        ax.plot([px, px], [py, mid_y], color=default_color, lw=lw,
                solid_capstyle="round", zorder=1)
        # Horizontal bar (coloured by balance ratio, slightly thicker)
        ax.plot([min(child_xs), max(child_xs)], [mid_y, mid_y],
                color=split_color, lw=lw * 1.3,
                solid_capstyle="round", zorder=2)
        # Legs: elbow down to each child
        for cx, _ in child_positions:
            ax.plot([cx, cx], [mid_y, cy], color=split_color, lw=lw,
                    solid_capstyle="round", zorder=1)


def _draw_symmetry_gauge(ax, score: float, descriptor: str):
    """Draw the symmetry gauge panel.

    Shows a red→green gradient bar with the score value marked on it,
    plus a short text label (e.g. 'moderately asymmetric').
    """
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Panel background
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.01, 0.04), 0.98, 0.92,
        boxstyle="round,pad=0.02",
        facecolor="#f7f7f7", edgecolor="#cccccc",
        linewidth=1.0, transform=ax.transAxes, zorder=0,
    ))

    # Gradient bar coordinates (data space, since xlim/ylim = [0,1])
    bx0, bx1 = 0.22, 0.86
    by0, by1 = 0.20, 0.78

    gradient = np.linspace(0, 1, 512).reshape(1, -1)
    ax.imshow(gradient, aspect="auto", cmap="RdYlGn",
              extent=[bx0, bx1, by0, by1], zorder=1)
    ax.add_patch(mpatches.Rectangle(
        (bx0, by0), bx1 - bx0, by1 - by0,
        facecolor="none", edgecolor="#888888", lw=0.8, zorder=2,
    ))

    # Tick marks at 0, 0.5, 1
    for tick in [0.0, 0.5, 1.0]:
        tx = bx0 + tick * (bx1 - bx0)
        ax.plot([tx, tx], [by0 - 0.04, by0], color="#888888", lw=0.8, zorder=2)
        ax.text(tx, by0 - 0.06, f"{tick:.1f}", ha="center", va="top",
                fontsize=7, color="#888888")

    # Score marker
    mx = bx0 + score * (bx1 - bx0)
    ax.plot([mx, mx], [by0, by1], color="black", lw=2.5, zorder=3)
    ax.plot([mx], [(by0 + by1) / 2], marker="v", color="black",
            markersize=6, zorder=4, clip_on=False,
            transform=ax.transData)
    ax.text(mx, by1 + 0.08, f"{score:.2f}",
            ha="center", va="bottom",
            fontsize=9, fontweight="bold", color="black", zorder=4)

    # End labels
    ax.text(bx0 - 0.015, (by0 + by1) / 2, "asymmetric",
            ha="right", va="center", fontsize=7.5, color="#cc4444")
    ax.text(bx1 + 0.015, (by0 + by1) / 2, "symmetric",
            ha="left", va="center", fontsize=7.5, color="#33aa33")

    # Panel label + descriptor
    ax.text(0.025, 0.52, "SYMMETRY",
            transform=ax.transAxes, ha="left", va="center",
            fontsize=9, fontweight="bold", color="#555555", zorder=2)
    ax.text(0.885, 0.52, descriptor,
            transform=ax.transAxes, ha="left", va="center",
            fontsize=8, style="italic", color="#444444", zorder=2)


def _text_panel(ax, label, code_str, bg_color, border_color, wrap_width=72,
                 compact=False):
    """Draw a labelled monospace code box inside axes *ax*.

    If compact=True, use smaller font and narrower wrap for space-constrained layouts.
    """
    ax.axis("off")
    if compact:
        wrap_width = 35
        fontsize_label = 7.5
        fontsize_code = 6.5
    else:
        fontsize_label = 9
        fontsize_code = 8.5

    wrapped = "\n".join(textwrap.wrap(code_str, width=wrap_width))

    ax.add_patch(mpatches.FancyBboxPatch(
        (0.01, 0.05), 0.98, 0.90,
        boxstyle="round,pad=0.02",
        facecolor=bg_color, edgecolor=border_color,
        linewidth=1.2, transform=ax.transAxes, zorder=0,
    ))
    ax.text(0.03, 0.52, label,
            transform=ax.transAxes, ha="left", va="center",
            fontsize=fontsize_label, fontweight="bold", color=border_color, zorder=2)
    ax.text(0.5, 0.52, wrapped,
            transform=ax.transAxes, ha="center", va="center",
            fontsize=fontsize_code, fontfamily="monospace", color="#1a1a1a", zorder=2)


def _draw_tree_panel(ax, root, pos, max_depth, max_lbl, node_ratios=None):
    """Render the cladogram into *ax*. Shared between single and comparison figures."""
    all_xs = [x for x, _ in pos.values()]

    cmap = plt.cm.viridis
    node_colors = {
        node: cmap(0.1 + 0.75 * (y / max(max_depth, 1)))
        for node, (_, y) in pos.items()
    }

    for d in range(max_depth + 1):
        ax.axhline(d, color="#eeeeee", lw=0.8, zorder=0)

    _draw_edges(ax, pos, root, node_ratios=node_ratios)

    radius = 0.18 + max_lbl * 0.025
    for node, (x, y) in pos.items():
        ax.add_patch(mpatches.Circle(
            (x, y), radius=radius,
            facecolor=node_colors[node], edgecolor="white", linewidth=1.5,
            zorder=3,
        ))
        ax.text(x, y, node.name, ha="center", va="center",
                fontsize=9, fontweight="bold", color="white", zorder=4)

    x_min = min(all_xs) - 0.8
    for d in range(max_depth + 1):
        ax.text(x_min, d, f"t{d}", ha="right", va="center",
                fontsize=9, color="#999999")

    pad = 0.6
    ax.set_xlim(x_min - 0.3, max(all_xs) + pad)
    ax.set_ylim(-pad, max_depth + pad)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("#fafafa")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def visualize(input_str, output_path=None, title=None, show=False,
              show_symmetry=False):
    """Parse *input_str* and produce a figure.

    Args:
        input_str:      Nested-tuple format string.
        output_path:    Save image to this path (.png / .pdf / .svg).
        title:          Optional figure title.
        show:           Open interactive window when True.
        show_symmetry:  Add symmetry gauge panel and colour split edges.
    """
    from symmetry import symmetry_score, symmetry_label

    input_str = input_str.strip()

    tokens = tokenize(input_str)
    parsed, _ = parse_expr(tokens, 0)
    root = build_tree(parsed)
    newick_str = _to_newick(root) + ";"

    pos = layout_tree(root)
    all_ys = [y for _, y in pos.values()]
    n_leaves  = sum(1 for n in pos if not n.children)
    max_depth = int(max(all_ys))
    max_lbl   = max(len(n.name) for n in pos)

    score, node_ratios = symmetry_score(root)
    descriptor = symmetry_label(score)

    # ---- figure layout ----------------------------------------------------
    fig_w   = max(8, n_leaves * 1.15)
    tree_h  = max(3.5, (max_depth + 1) * 1.35)
    panel_h = 0.55

    n_rows = 4 if show_symmetry else 3
    height_ratios = (
        [panel_h, panel_h, tree_h, panel_h] if show_symmetry
        else [panel_h, tree_h, panel_h]
    )
    fig_h = tree_h + (3 if show_symmetry else 2) * panel_h + 0.6

    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor("#fafafa")

    gs = GridSpec(n_rows, 1, figure=fig,
                  height_ratios=height_ratios, hspace=0.08)

    if show_symmetry:
        ax_input, ax_sym, ax_tree, ax_newick = (
            fig.add_subplot(gs[0]), fig.add_subplot(gs[1]),
            fig.add_subplot(gs[2]), fig.add_subplot(gs[3]),
        )
    else:
        ax_input, ax_tree, ax_newick = (
            fig.add_subplot(gs[0]), fig.add_subplot(gs[1]),
            fig.add_subplot(gs[2]),
        )

    # ---- panels -----------------------------------------------------------
    _text_panel(ax_input, "INPUT", input_str, "#eef7ee", "#4a9a4a")

    if show_symmetry:
        _draw_symmetry_gauge(ax_sym, score, descriptor)

    _draw_tree_panel(ax_tree, root, pos, max_depth, max_lbl,
                     node_ratios=node_ratios if show_symmetry else None)

    _text_panel(ax_newick, "NEWICK", newick_str, "#eeeef8", "#5555aa")

    full_title = title or ""
    if show_symmetry:
        sym_part = f"symmetry score: {score:.2f}  ({descriptor})"
        full_title = f"{full_title}  —  {sym_part}" if full_title else sym_part
    if full_title:
        fig.suptitle(full_title, fontsize=11, fontweight="bold",
                     y=0.995, va="top")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"  saved → {output_path}")
    if show:
        matplotlib.use("TkAgg")
        plt.show()
    plt.close(fig)
