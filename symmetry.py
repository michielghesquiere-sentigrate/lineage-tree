"""
Tree symmetry metrics.

Balance ratio per branching node:
  score = min_child_leaves / max_child_leaves  ∈ [0, 1]

Overall symmetry score = mean balance ratio over all branching nodes
  (nodes with exactly 1 child — "continuations" — are excluded).

  1.0 = perfectly symmetric
  0.0 = maximally asymmetric (caterpillar)
"""

from tuple_to_newick import TreeNode


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def leaf_count(node: TreeNode) -> int:
    """Number of leaf descendants (including self if leaf)."""
    if not node.children:
        return 1
    return sum(leaf_count(c) for c in node.children)


def node_balance(node: TreeNode) -> "float | None":
    """min/max leaf-count ratio for a branching node (≥2 children).

    Returns None for continuation nodes (single child) — they have no
    meaningful balance since there is no split.
    """
    if len(node.children) < 2:
        return None
    counts = [leaf_count(c) for c in node.children]
    return min(counts) / max(counts)


def symmetry_score(root: TreeNode) -> "tuple[float, dict[TreeNode, float]]":
    """Compute tree symmetry.

    Returns:
        score      – mean balance ratio over all branching nodes, ∈ [0, 1]
        node_ratios – {TreeNode: ratio} for every branching node
    """
    node_ratios: dict = {}

    def walk(node):
        r = node_balance(node)
        if r is not None:
            node_ratios[node] = r
        for c in node.children:
            walk(c)

    walk(root)
    score = sum(node_ratios.values()) / len(node_ratios) if node_ratios else 1.0
    return score, node_ratios


def symmetry_label(score: float) -> str:
    """Human-readable description of a symmetry score."""
    if score >= 0.90:
        return "highly symmetric"
    if score >= 0.70:
        return "moderately symmetric"
    if score >= 0.50:
        return "moderately asymmetric"
    return "highly asymmetric"
