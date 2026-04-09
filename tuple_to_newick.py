"""
Core parser and Newick converter for the nested-tuple lineage tree format.

Format: a list of timepoints ordered latest-first, root-last.
  - Each timepoint's nested structure mirrors the previous one positionally.
  - A leaf becoming a tuple means that node splits into those children.
  - A leaf to leaf means continuation (single child, possibly renamed).

Example:
  [((G,H),(I,(J,K))),(D,(E,F)),(B,C),(A)]
  → (((G,H)D)B,((I)E,(J,K)F)C)A;
"""

import sys


# ---------------------------------------------------------------------------
# Tokenizer / Parser
# ---------------------------------------------------------------------------

def tokenize(s):
    tokens = []
    i = 0
    while i < len(s):
        c = s[i]
        if c in "()[],":
            tokens.append(c)
            i += 1
        elif c.isalnum() or c in "_-.":
            j = i
            while j < len(s) and (s[j].isalnum() or s[j] in "_-."):
                j += 1
            tokens.append(s[i:j])
            i = j
        elif c.isspace():
            i += 1
        else:
            raise ValueError(f"Unexpected character: '{c}' at position {i}")
    return tokens


def parse_expr(tokens, pos):
    if tokens[pos] == "[":
        return parse_list(tokens, pos)
    elif tokens[pos] == "(":
        return parse_tuple(tokens, pos)
    else:
        return tokens[pos], pos + 1


def parse_list(tokens, pos):
    pos += 1  # skip '['
    items = []
    while tokens[pos] != "]":
        item, pos = parse_expr(tokens, pos)
        items.append(item)
        if pos < len(tokens) and tokens[pos] == ",":
            pos += 1
    return items, pos + 1


def parse_tuple(tokens, pos):
    pos += 1  # skip '('
    items = []
    while tokens[pos] != ")":
        item, pos = parse_expr(tokens, pos)
        items.append(item)
        if pos < len(tokens) and tokens[pos] == ",":
            pos += 1
    pos += 1  # skip ')'
    if len(items) == 1:
        return items[0], pos  # unwrap single-element tuple → plain leaf
    return tuple(items), pos


# ---------------------------------------------------------------------------
# Tree node
# ---------------------------------------------------------------------------

class TreeNode:
    """A single node in the lineage tree.

    Uses object identity as its key, so two nodes with the same name
    (e.g. a lineage that stays '1' across several timepoints) remain
    distinct and do not overwrite each other in any dict.
    """
    __slots__ = ("name", "children")

    def __init__(self, name: str):
        self.name = str(name)
        self.children: list["TreeNode"] = []

    def __repr__(self):
        return f"TreeNode({self.name!r}, children={len(self.children)})"


# ---------------------------------------------------------------------------
# Tree builder
# ---------------------------------------------------------------------------

def _expand(current, next_parsed):
    """Attach the next generation to the current node structure.

    Args:
        current:      A TreeNode (leaf) or a tuple of TreeNodes / sub-structures
                      produced by a previous call.
        next_parsed:  The parsed name-structure for the next timepoint,
                      positionally aligned with *current*.

    Returns the new "current structure" (a TreeNode or nested tuple of
    TreeNodes) ready for the following timepoint.
    """
    if isinstance(current, TreeNode):
        if isinstance(next_parsed, str):
            # Continuation: one child with a (possibly new) name
            child = TreeNode(next_parsed)
            current.children.append(child)
            return child

        elif isinstance(next_parsed, tuple):
            # Split: all elements must be plain names
            for x in next_parsed:
                if not isinstance(x, str):
                    raise ValueError(
                        f"Node '{current.name}' splits but a child is a nested "
                        f"structure {x!r}. Children must be plain names."
                    )
            children = [TreeNode(x) for x in next_parsed]
            current.children.extend(children)
            return tuple(children)

        else:
            raise TypeError(f"Unexpected next_parsed type: {type(next_parsed)}")

    elif isinstance(current, tuple):
        # Structural group: recurse element-wise
        if not isinstance(next_parsed, tuple) or len(current) != len(next_parsed):
            raise ValueError(
                f"Structure mismatch between consecutive timepoints:\n"
                f"  current : {current}\n"
                f"  next    : {next_parsed}"
            )
        return tuple(_expand(c, n) for c, n in zip(current, next_parsed))

    else:
        raise TypeError(f"Unexpected current type: {type(current)}")


def build_tree(timepoints) -> TreeNode:
    """Return the root TreeNode built from a parsed timepoint list (latest-first).

    Every node is a distinct TreeNode object, so repeated names along a
    lineage (e.g. a cell that stays '1' for several timepoints) are kept
    as separate nodes and not collapsed.
    """
    tps = list(reversed(timepoints))   # root-first

    if not isinstance(tps[0], str):
        raise ValueError(f"Root timepoint must be a single node name, got: {tps[0]!r}")

    root = TreeNode(tps[0])
    current = root                      # tracks the "frontier" node-structure

    for t in range(len(tps) - 1):
        current = _expand(current, tps[t + 1])

    return root


# ---------------------------------------------------------------------------
# Newick serialiser
# ---------------------------------------------------------------------------

def to_newick(node: TreeNode) -> str:
    if node.children:
        child_strs = [to_newick(c) for c in node.children]
        return f"({','.join(child_strs)}){node.name}"
    return node.name


def convert(input_str: str) -> str:
    """Full pipeline: parse input string → Newick string (with trailing ';')."""
    tokens = tokenize(input_str.strip())
    parsed, _ = parse_expr(tokens, 0)
    if not isinstance(parsed, list):
        raise ValueError("Input must be a list [...] of timepoints")
    root = build_tree(parsed)
    return to_newick(root) + ";"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read().strip()
    print(convert(src))
