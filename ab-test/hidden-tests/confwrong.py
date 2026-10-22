"""Confidently-wrong rate: a core field (phone/governorate/name/address) wrong while the parser says no review needed."""
import sys, os, json, subprocess
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import importlib
pkg = sys.argv[1]; sys.path.insert(0, pkg)
from dallal_parser import parse_order
tot = {}
for setname, script in [('A', 'grade.py'), ('B', 'grade_b.py'), ('C', 'grade_c.py')]:
    d = json.loads(subprocess.run([sys.executable, os.path.join(here, script), pkg], capture_output=True, text=True).stdout)
    mod = importlib.import_module({'A': 'cases', 'B': 'cases_b', 'C': 'cases_c'}[setname])
    wrong = cw = flagged_right = right = 0
    for c in d['cases']:
        text = mod.CASES[c['case'] - 1][0]
        out = parse_order(text)
        flag = bool(out.get('needs_review') or out.get('needs_followup'))
        ok = all(c.get(k, False) for k in ('phone_ok', 'gov_ok', 'name_ok', 'addr_ok'))
        if ok: right += 1; flagged_right += flag
        else: wrong += 1; cw += (not flag)
    tot[setname] = dict(n=len(d['cases']), wrong=wrong, confidently_wrong=cw, right_but_flagged=flagged_right)
print(json.dumps(tot))
