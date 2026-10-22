"""Command line: ``python -m dallal_parser "message"`` or pipe the message on stdin."""

import json
import sys

from . import parse_order


def main() -> None:
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    print(json.dumps(parse_order(text), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
