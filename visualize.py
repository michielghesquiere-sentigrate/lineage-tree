"""
Visualize a nested-tuple lineage tree as a cladogram-style figure.

The figure has three panels:
  ┌─────────────────────────────────────────┐
  │  INPUT  [((G,H),(I,(J,K))),(D,(E,F)),…] │  ← green box
  │                                         │
  │            cladogram diagram            │  ← tree
  │                                         │
  │  NEWICK  (((G,H)D)B,((I)E,(J,K)F)C)A;  │  ← blue box
  └─────────────────────────────────────────┘
"""

import textwrap

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
    """Return {node: (x, y)} with y = depth and x centred over leaves.

    Uses object identity as the dict key so nodes with duplicate names
    remain distinct.
    """
    # DFS leaf order (left-to-right)
    leaves = [n for n in _all_nodes(root) if not n.children]
    leaf_x = {id(n): float(i) for i, n in enumerate(leaves)}

    # Depth by recursion
    depth: dict[int, int] = {}
    def assign_depth(node, d):
        depth[id(node)] = d
        for c in node.children:
            assign_depth(c, d + 1)
    assign_depth(root, 0)

    # X position: post-order mean of children
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

def _draw_edges(ax, pos, root: TreeNode, color="#444444", lw=1.8):
    """Dendrogram step edges: stem → horizontal bar → legs."""
    for parent in _all_nodes(root):
        if not parent.children:
            continue
        px, py = pos[parent]
        child_positions = [pos[c] for c in parent.children]
        cy = child_positions[0][1]          # all children at same depth
        child_xs = [cp[0] for cp in child_positions]
        mid_y = (py + cy) / 2.0

        ax.plot([px, px], [py, mid_y], color=color, lw=lw,
                solid_capstyle="round", zorder=1)
        ax.plot([min(child_xs), max(child_xs)], [mid_y, mid_y],
                color=color, lw=lw, solid_capstyle="round", zorder=1)
        for cx, _ in child_positions:
            ax.plot([cx, cx], [mid_y, cy], color=color, lw=lw,
                    solid_capstyle="round", zorder=1)


def _text_panel(ax, label, code_str, bg_color, border_color, wrap_width=72):
    """Draw a labelled monospace code box inside axes *ax*."""
    ax.axis("off")

    # Wrap long strings
    wrapped = "\n".join(textwrap.wrap(code_str, width=wrap_width))

    # Background rectangle (axes-fraction coords)
    rect = mpatches.FancyBboxPatch(
        (0.01, 0.05), 0.98, 0.90,
        boxstyle="round,pad=0.02",
        facecolor=bg_color, edgecolor=border_color,
        linewidth=1.2, transform=ax.transAxes, zorder=0
    )
    ax.add_patch(rect)

    # Bold label on the left
    ax.text(
        0.03, 0.52, label,
        transform=ax.transAxes,
        ha="left", va="center",
        fontsize=9, fontweight="bold", color=border_color,
        zorder=2
    )

    # Code text
    ax.text(
        0.5, 0.52, wrapped,
        transform=ax.transAxes,
        ha="center", va="center",
        fontsize=8.5, fontfamily="monospace", color="#1a1a1a",
        zorder=2
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def visualize(input_str, output_path=None, title=None, show=False):
    """Parse *input_str* and produce the three-panel figure.

    Args:
        input_str:   Nested-tuple format string.
        output_path: Save image to this path if given (.png / .pdf / .svg).
        title:       Optional figure title.
        show:        Open interactive window when True.
    """
    input_str = input_str.strip()

    # ---- parse tree -------------------------------------------------------
    tokens = tokenize(input_str)
    parsed, _ = parse_expr(tokens, 0)
    root = build_tree(parsed)
    newick_str = _to_newick(root) + ";"

    pos = layout_tree(root)
    all_xs = [x for x, _ in pos.values()]
    all_ys = [y for _, y in pos.values()]
    n_leaves  = sum(1 for n in pos if not n.children)
    max_depth = int(max(all_ys))
    max_lbl   = max(len(n.name) for n in pos)

    # ---- figure / grid ----------------------------------------------------
    fig_w = max(8, n_leaves * 1.15)
    tree_h = max(3.5, (max_depth + 1) * 1.35)
    panel_h = 0.55                          # height of each text panel (inches)

    fig = plt.figure(figsize=(fig_w, tree_h + 2 * panel_h + 0.6))
    fig.patch.set_facecolor("#fafafa")

    gs = GridSpec(
        3, 1,
        figure=fig,
        height_ratios=[panel_h, tree_h, panel_h],
        hspace=0.08,
    )

    ax_input  = fig.add_subplot(gs[0])
    ax_tree   = fig.add_subplot(gs[1])
    ax_newick = fig.add_subplot(gs[2])

    # ---- input panel ------------------------------------------------------
    _text_panel(
        ax_input,
        label="INPUT",
        code_str=input_str,
        bg_color="#eef7ee",
        border_color="#4a9a4a",
    )

    # ---- newick panel -----------------------------------------------------
    _text_panel(
        ax_newick,
        label="NEWICK",
        code_str=newick_str,
        bg_color="#eeeef8",
        border_color="#5555aa",
    )

    # ---- tree panel -------------------------------------------------------
    ax = ax_tree
    cmap = plt.cm.viridis
    node_colors = {
        node: cmap(0.1 + 0.75 * (y / max(max_depth, 1)))
        for node, (_, y) in pos.items()
    }

    # Guide lines
    for d in range(max_depth + 1):
        ax.axhline(d, color="#eeeeee", lw=0.8, zorder=0)

    _draw_edges(ax, pos, root)

    # Node circles + labels
    radius = 0.18 + max_lbl * 0.025
    for node, (x, y) in pos.items():
        circle = mpatches.Circle(
            (x, y), radius=radius,
            facecolor=node_colors[node],
            edgecolor="white", linewidth=1.5,
            zorder=3,
        )
        ax.add_patch(circle)
        ax.text(
            x, y, node.name,
            ha="center", va="center",
            fontsize=9, fontweight="bold", color="white",
            zorder=4,
        )

    # Timepoint labels
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

    # ---- title ------------------------------------------------------------
    if title:
        fig.suptitle(title, fontsize=12, fontweight="bold", y=0.995, va="top")

    plt.tight_layout()

    # ---- output -----------------------------------------------------------
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"  saved → {output_path}")
    if show:
        matplotlib.use("TkAgg")
        plt.show()
    plt.close(fig)
