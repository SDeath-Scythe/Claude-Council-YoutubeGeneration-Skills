#!/usr/bin/env python3
"""Eval CLI (D11).

  python3 eval_cases.py CASES.json          # raw mode if any case lacks "expected"
  python3 eval_cases.py --raw CASES.json    # always raw mode

Raw mode prints ONLY a JSON list [{"id": ..., "output": parse_order(input)}] on
stdout.  Scored mode (every case has "expected") prints per-case diffs and a
summary, exiting 1 if any case fails.  Diagnostics go to stderr.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dallal_parser import parse_order  # noqa: E402
from dallal_parser.evalcases import check_case  # noqa: E402


def main(argv):
    raw = "--raw" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if len(paths) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        with open(paths[0], encoding="utf-8") as fh:
            cases = json.load(fh)
    except OSError as e:
        print("error: cannot read %s: %s" % (paths[0], e), file=sys.stderr)
        return 2
    except ValueError as e:
        print("error: %s is not valid JSON: %s" % (paths[0], e), file=sys.stderr)
        return 2
    if isinstance(cases, dict):
        cases = cases.get("cases", [])
    if not isinstance(cases, list) or not all(isinstance(c, dict) for c in cases):
        print("error: expected a JSON list of objects [{\"id\": ..., \"input\": ...}]", file=sys.stderr)
        return 2
    if not cases:
        print("warning: no cases in %s" % paths[0], file=sys.stderr)
    for c in cases:
        if "input" not in c:
            print("warning: case %r has no 'input'; parsing ''" % c.get("id"), file=sys.stderr)
    if raw or any("expected" not in c for c in cases):
        out = [{"id": c.get("id"), "output": parse_order(c.get("input", ""))} for c in cases]
        sys.stdout.write(json.dumps(out, ensure_ascii=False))
        sys.stdout.write("\n")
        return 0
    failed = 0
    for c in cases:
        res = parse_order(c.get("input", ""))
        bad = check_case(res, c["expected"])
        if bad:
            failed += 1
            print("FAIL %s: %r" % (c.get("id"), c.get("input")))
            for f, exp, act in bad:
                print("   %-12s expected %r, got %r" % (f, exp, act))
    total = len(cases)
    print("%d/%d passed (%.1f%%)" % (total - failed, total, 100.0 * (total - failed) / max(total, 1)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
