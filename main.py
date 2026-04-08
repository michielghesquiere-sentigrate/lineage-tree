"""
lineage-tree CLI

Usage:
  python main.py TREE [options]

Arguments:
  TREE    Nested-tuple tree string, e.g. '[((G,H),(I,(J,K))),(D,(E,F)),(B,C),(A)]'
          Omit to read from stdin.

Options:
  --newick          Print Newick string to stdout (default when no --save/--show)
  --save PATH       Save visualisation to PATH (.png / .pdf / .svg)
  --show            Open interactive matplotlib window
  --title TEXT      Title for the figure
  -h, --help        Show this help and exit

Examples:
  python main.py '[((G,H),(I,(J,K))),(D,(E,F)),(B,C),(A)]'
  python main.py '[((G,H),(I,(J,K))),(D,(E,F)),(B,C),(A)]' --save outputs/example.png
  echo '[((1,2),(3,(4,5))),(6,(7,8)),(9,10),(11)]' | python main.py --save out.png
"""

import argparse
import sys

from tuple_to_newick import convert
from visualize import visualize


def main():
    parser = argparse.ArgumentParser(
        prog="lineage-tree",
        description="Convert / visualise nested-tuple lineage trees.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "tree", nargs="?", default=None,
        help="Nested-tuple tree string (reads stdin if omitted)",
    )
    parser.add_argument(
        "--newick", action="store_true",
        help="Print Newick string to stdout",
    )
    parser.add_argument(
        "--save", metavar="PATH",
        help="Save visualisation image to PATH",
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Open interactive plot window",
    )
    parser.add_argument(
        "--title", metavar="TEXT", default=None,
        help="Figure title",
    )

    args = parser.parse_args()

    # Read tree string
    if args.tree:
        src = args.tree
    else:
        src = sys.stdin.read().strip()
        if not src:
            parser.print_help()
            sys.exit(1)

    # Default: print Newick unless a visual action was requested
    want_visual = args.save or args.show
    if args.newick or not want_visual:
        print(convert(src))

    if want_visual:
        visualize(src, output_path=args.save, title=args.title, show=args.show)


if __name__ == "__main__":
    main()
