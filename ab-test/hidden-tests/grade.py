"""usage: python3 grade.py <dir containing the dallal_parser package>  -> prints JSON score"""
import sys, os, re, json, importlib, traceback, signal, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cases import CASES, GOV_VARIANTS
root = os.path.abspath(sys.argv[1]); sys.path.insert(0, root)
mod = importlib.import_module('dallal_parser')
parse = getattr(mod, 'parse_order')
AR = str.maketrans({'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ى': 'ي', 'ة': 'ه', 'ؤ': 'و', 'ئ': 'ي', 'ـ': ''})
def norm(s): s = re.sub(r'[ً-ْ]', '', str(s or '')).translate(AR).lower(); return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', s)).strip()
def gov_key(v):
    if not v: return None
    s = re.sub(r'[^a-z]', '', re.sub(r'\b(al|as|ad|an|ar|governorate|province|muhafazat|muhafazah)\b', '', str(v).lower().replace('-', ' ')))
    for k, vs in GOV_VARIANTS.items():
        if s in [re.sub(r'[^a-z]', '', x) for x in vs]: return k
    return 'other:' + s
res = []; tot = 0; mx = 0
for i, (text, phone, gov, name, addr) in enumerate(CASES):
    r = {'case': i + 1}
    try:
        signal.alarm(5); out = parse(text); signal.alarm(0)
        if not isinstance(out, dict): raise TypeError('not a dict')
    except Exception as e:
        signal.alarm(0); r['error'] = f'{type(e).__name__}: {e}'[:160]; out = None
    if out is None:
        sc = 0.0
    else:
        p_ok = (out.get('phone') or None) == phone if phone else not out.get('phone')
        g_ok = gov_key(out.get('governorate')) == gov if gov else not out.get('governorate')
        if name:
            on = norm(out.get('name')); en = norm(name)
            n_ok = bool(on) and (on == en or (en in on and len(on) <= len(en) + 12) or (on in en and len(on) >= 3))
        else: n_ok = not out.get('name') if (phone is None and gov is None) else True
        if addr:
            skip = re.compile(r'raw|orig|input|text|message|source|note|warn|issue|error|flag|review|reason', re.I)
            others = ' '.join(str(v) for k, v in out.items() if k not in ('name', 'phone', 'governorate', 'address') and not skip.search(str(k))
                              and isinstance(v, (str, int, float)) and norm(v) != norm(text))
            D = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')
            adigits = re.sub(r'\D', '', (str(out.get('address') or '') + ' ' + others).translate(D))
            leak = bool(phone) and phone[-7:] in adigits      # the address must not just be the whole message
            a_ok = norm(addr) in norm(str(out.get('address') or '') + ' ' + others) and not leak
        else: a_ok = True
        sc = 0.35 * p_ok + 0.35 * g_ok + 0.15 * n_ok + 0.15 * a_ok
        r.update(phone_ok=p_ok, gov_ok=g_ok, name_ok=n_ok, addr_ok=a_ok, got={k: out.get(k) for k in ('name', 'phone', 'governorate', 'address')})
    r['score'] = round(sc, 3); tot += sc; mx += 1; res.append(r)
summary = dict(score=round(100 * tot / mx, 1), n=mx,
               phone=sum(1 for r in res if r.get('phone_ok')), gov=sum(1 for r in res if r.get('gov_ok')), name=sum(1 for r in res if r.get('name_ok')), addr=sum(1 for r in res if r.get('addr_ok')),
               errors=sum(1 for r in res if 'error' in r))
print(json.dumps(dict(summary=summary, cases=res), ensure_ascii=False, indent=1))
