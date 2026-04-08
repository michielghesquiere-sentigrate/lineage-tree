"""
Core parser and Newick converter for the nested-tuple lineage tree format.

Format: a list of timepoints ordered latest-first, root-last.
  - Each timepoint's nested structure mirrors the previous one positionally.
  - A leaf becoming a tuple means that node splits into those children.
  - A leaf to leaf means continuation (single child, possibly renamed).

Example:
  [((G,H),(I,(J,K))),(D,(E,F)),(B,C),(A)]
  → ((((G,H)D)B,(((I)E),(J,K)F)C)A);
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
# Tree builder
# ---------------------------------------------------------------------------

def _map_structure(current, next_tp, children):
    """Walk current and next_tp in parallel to record parent→children edges.

    Rules:
      - leaf → leaf  : continuation (single child)
      - leaf → tuple : node splits; tuple elements must all be leaf names
      - tuple → tuple: recurse element-wise (same length required)
    """
    if isinstance(current, str):
        if isinstance(next_tp, str):
            children[current] = [next_tp]
        elif isinstance(next_tp, tuple):
            for x in next_tp:
                if not isinstance(x, str):
                    raise ValueError(
                        f"Node '{current}' splits but got nested structure as "
                        f"child: {x!r}. Children must be plain names."
                    )
            children[current] = list(next_tp)
    elif isinstance(current, tuple):
        if not isinstance(next_tp, tuple) or len(current) != len(next_tp):
            raise ValueError(
                f"Structure mismatch between consecutive timepoints:\n"
                f"  current : {current}\n"
                f"  next    : {next_tp}"
            )
        for c, n in zip(current, next_tp):
            _map_structure(c, n, children)


def build_tree(timepoints):
    """Return (root, children_dict) from a parsed timepoint list (latest-first)."""
    tps = list(reversed(timepoints))   # root-first
    children = {}
    for t in range(len(tps) - 1):
        _map_structure(tps[t], tps[t + 1], children)
    root = tps[0]
    if not isinstance(root, str):
        raise ValueError(f"Root timepoint must be a single node name, got: {root!r}")
    return root, children


# ---------------------------------------------------------------------------
# Newick serializer
# ---------------------------------------------------------------------------

def to_newick(node, children):
    if node in children:
        child_strs = [to_newick(c, children) for c in children[node]]
        return f"({','.join(child_strs)}){node}"
    return node


def convert(input_str):
    """Full pipeline: parse input string → Newick string."""
    tokens = tokenize(input_str.strip())
    parsed, _ = parse_expr(tokens, 0)
    if not isinstance(parsed, list):
        raise ValueError("Input must be a list [...] of timepoints")
    root, children = build_tree(parsed)
    return to_newick(root, children) + ";"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read().strip()
    print(convert(src))
