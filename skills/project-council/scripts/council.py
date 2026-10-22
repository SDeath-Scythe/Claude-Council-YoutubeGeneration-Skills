#!/usr/bin/env python3
"""
council.py — the ledger for a project council: state on disk, briefs for every seat, schema checks, objection
tracking, mechanical convergence, findings triage and the final quality gate. Standard library only.

  python3 council.py init "<goal>" [--type code|product|content|business|research|general] [--stakes lite|standard|critical]
  python3 council.py seats [--suggest] [--set skeptic,user,builder,domain:"school timetabling",quality]
  python3 council.py brief <seat> --phase propose|debate|review|redteam [--round N]   # print the exact prompt for that seat
  python3 council.py record <seat> --phase propose|debate|review|redteam [--round N] [--file out.json]
  python3 council.py digest --phase propose|debate [--round N]   # merge positions -> .council/digest_<phase><N>.md
  python3 council.py plan [--version N]                          # register plan_vN.md (decisions = lines "D1: ...")
  python3 council.py resolve O3 --how "D3 now does X"           # mark an objection answered in the plan (seat may still maintain it)
  python3 council.py status                                     # convergence verdict + what blocks it
  python3 council.py decide --note "chair's ruling on remaining dissent"   # end debate (after max rounds / stalemate)
  python3 council.py cases split [--sealed 0.6]                 # seats' cases -> dev set (builder sees) + sealed holdout (builder never sees)
  python3 council.py cases score --set sealed|dev|fresh-K --run "<cmd {cases}>"   # run the system on a case set and score it
  python3 council.py cases score --set sealed --results judged.json             # non-code: a judge's pass/fail per case
  python3 council.py cases list|drop C7 --note "..."|target 0.95|waive --note "..."
  python3 council.py brief build                                # the builder agent's prompt (dev cases only)
  python3 council.py findings merge --pass K | list [--open] | set F4 verified|dismissed|fixed|wontfix --note "..."
  python3 council.py accept --run "<shell command>" --name AT1   # run an acceptance check, record pass/fail + output
  python3 council.py accept --name AT2 --result pass --evidence "..."  # manual check (non-code deliverables)
  python3 council.py gate                                       # exit 0 only if the work may ship
  python3 council.py report                                     # DECISIONS.md + REPORT.md

State lives in ./.council (override with COUNCIL_DIR). Every command prints the next step.
"""
import json, os, re, subprocess, sys, time, textwrap, hashlib, unicodedata
import signal
if hasattr(signal, 'SIGPIPE'): signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # quiet when piped into head

D = os.environ.get('COUNCIL_DIR', '.council')
HERE = os.path.dirname(os.path.abspath(__file__))
SEV = ['blocker', 'major', 'minor', 'nit']
TYPE = 'general'  # project type, set by load()

# ------------------------------------------------------------------ roster
ROSTER = {
    'architect': ('Architect', 'the shape of the whole: components, interfaces, data flow, and how cheap it stays to change',
                  ['boundaries and interfaces', 'data model and its invariants', 'simplest structure that meets the definition of done', 'what is hard to change later']),
    'skeptic': ('Skeptic (red team)', 'finding how this fails: wrong assumptions, edge cases, the input nobody planned for, what breaks in production',
                ['the riskiest assumption and how to test it cheaply', 'adversarial and malformed inputs', 'silent failure modes', 'the strongest alternative approach']),
    'user': ('User advocate', 'the real people who will use the result: their actual inputs, language, habits, devices and the job they hire it for',
             ['real-world inputs and messy data', 'language, locale and accessibility', 'error messages and recovery', 'the first five minutes of use']),
    'builder': ('Builder (pragmatist)', 'shipping the smallest thing that fully meets the definition of done, on time, with few moving parts',
                ['scope: what to cut or defer', 'dependencies and their risk', 'order of work', 'what can be verified quickly']),
    'quality': ('Quality engineer', 'proof that it works and keeps working: acceptance tests, test design, error handling, observability, docs',
                ['acceptance tests that map to the definition of done', 'unit tests for invariants and edge cases', 'error handling and logging', 'readability and docs']),
    'security': ('Security & privacy', 'what could be abused or leaked: personal data, money, secrets, injection, permissions, compliance',
                 ['personal and payment data handling', 'injection and untrusted input', 'secrets and permissions', 'abuse cases and rate limits']),
    'ops': ('Reliability & cost', 'how it behaves at scale and under failure: performance, recovery, monitoring, running cost',
            ['performance on realistic volumes', 'failure recovery and idempotency', 'monitoring and alerts', 'cost to run']),
    'money': ('Business & money', 'whether it pays off: value to the customer, pricing, unit economics, competitors, go-to-market',
              ['who pays and why', 'unit economics', 'competitive alternatives', 'the cheapest test of demand']),
    'audience': ('Audience', 'whether people will watch/read/use it to the end: hook, clarity, pacing, platform norms, retention',
                 ['the first 10 seconds / first screen', 'where attention drops', 'clarity for a newcomer', 'platform fit']),
    'editor': ('Editor', 'clarity and structure of anything written: argument, order, cuts, voice, consistency',
               ['structure and flow', 'what to cut', 'consistency of terms and voice', 'claims that need support']),
    'researcher': ('Researcher', 'facts and prior art: verify claims with sources, find what already exists, quantify unknowns',
                   ['claims that need a source', 'prior art and existing tools', 'numbers that drive decisions', 'what evidence would change the plan']),
    'domain': ('Domain expert', 'the specifics of this domain that outsiders get wrong: conventions, regulations, local facts, jargon',
               ['domain conventions and terminology', 'local/regulatory facts', 'what practitioners would immediately notice is wrong', 'domain-specific edge cases']),
}
PRESETS = {
    'code': ['architect', 'skeptic', 'user', 'builder', 'quality', 'domain', 'security'],
    'product': ['user', 'builder', 'architect', 'skeptic', 'money', 'domain', 'quality'],
    'content': ['audience', 'editor', 'domain', 'skeptic', 'builder', 'researcher'],
    'business': ['money', 'skeptic', 'domain', 'user', 'researcher', 'builder'],
    'research': ['researcher', 'skeptic', 'domain', 'editor', 'builder'],
    'general': ['skeptic', 'user', 'builder', 'domain', 'quality', 'architect'],
}
STAKES = {'lite': dict(seats=3, debate_rounds=1, review_passes=1), 'standard': dict(seats=5, debate_rounds=1, review_passes=2), 'critical': dict(seats=6, debate_rounds=2, review_passes=3)}
MIN_CASES = {'code': 8, 'product': 4, 'research': 4, 'business': 3, 'content': 3, 'general': 4}

# ------------------------------------------------------------------ io
def p(*a): return os.path.join(D, *a)
def load():
    global TYPE
    if not os.path.exists(p('state.json')): die('no council here — run: council.py init "<goal>"')
    st = json.load(open(p('state.json')))
    TYPE = st.get('type', 'general'); st.setdefault('scores', []); st.setdefault('cases_meta', {})
    return st
def save(st): json.dump(st, open(p('state.json'), 'w'), indent=1, ensure_ascii=False)
def die(msg, code=2): print(msg, file=sys.stderr); sys.exit(code)
def nxt(msg): print('\nNEXT: ' + msg)
def arg(k, d=None):
    a = sys.argv
    return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d
def words(s): return set(w for w in re.findall(r'[a-z0-9؀-ۿ]+', (s or '').lower()) if len(w) > 2)
def similar(a, b):
    A, B = words(a), words(b)
    return len(A & B) / max(1, len(A | B))

# ------------------------------------------------------------------ schemas
def check(obj, phase):
    errs = []
    def need(k, typ):
        if k not in obj: errs.append(f'missing "{k}"'); return False
        if not isinstance(obj[k], typ): errs.append(f'"{k}" should be {typ.__name__ if not isinstance(typ, tuple) else "/".join(t.__name__ for t in typ)}'); return False
        return True
    def sev_ok(x, where, allowed=SEV):
        if x.get('severity') not in allowed: errs.append(f'{where}: severity must be one of {allowed}')
    if phase == 'propose':
        need('summary', str)
        if need('proposals', list):
            for i, x in enumerate(obj['proposals']):
                if not isinstance(x, dict) or not x.get('title'): errs.append(f'proposals[{i}] needs a title')
        if need('risks', list):
            for i, x in enumerate(obj['risks']):
                if not isinstance(x, dict) or not x.get('title'): errs.append(f'risks[{i}] needs a title')
                else: sev_ok(x, f'risks[{i}]', SEV[:3])
        need('acceptance_tests', list)
        errs.extend(check_cases(obj.get('cases'), 'cases', MIN_CASES.get(TYPE, 4)))
    elif phase in ('debate', 'redteam'):
        if need('votes', list):
            for i, v in enumerate(obj['votes']):
                if not isinstance(v, dict) or not re.match(r'^D\d+$', str(v.get('decision', ''))): errs.append(f'votes[{i}].decision must look like "D3"')
                elif v.get('vote') not in ('accept', 'amend', 'reject'): errs.append(f'votes[{i}].vote must be accept|amend|reject')
                elif v['vote'] != 'accept' and not v.get('reason'): errs.append(f'votes[{i}] ({v["decision"]} {v["vote"]}) needs a reason')
        if need('objections', list):
            for i, o in enumerate(obj['objections']):
                if not isinstance(o, dict) or not o.get('claim'): errs.append(f'objections[{i}] needs a claim'); continue
                sev_ok(o, f'objections[{i}]', SEV[:3])
                if o.get('severity') in ('blocker', 'major') and not o.get('evidence'): errs.append(f'objections[{i}] is {o["severity"]} but has no evidence (no evidence -> minor at most)')
                if o.get('status', 'new') not in ('new', 'maintained', 'withdrawn'): errs.append(f'objections[{i}].status must be new|maintained|withdrawn')
                if o.get('status') == 'withdrawn' and not o.get('changed_by'): errs.append(f'objections[{i}] withdrawn without changed_by (say what convinced you)')
        if phase == 'debate': need('steelman', str)
    elif phase == 'review':
        if obj.get('verdict') not in ('ship', 'ship-with-fixes', 'do-not-ship'): errs.append('verdict must be ship|ship-with-fixes|do-not-ship')
        if need('findings', list):
            for i, f in enumerate(obj['findings']):
                if not isinstance(f, dict) or not f.get('title'): errs.append(f'findings[{i}] needs a title'); continue
                sev_ok(f, f'findings[{i}]')
                if f.get('severity') in ('blocker', 'major') and not f.get('evidence'): errs.append(f'findings[{i}] is {f["severity"]} without evidence (a reproducible input/command and the actual result)')
            if len(obj['findings']) > 15: errs.append('more than 15 findings — rank and keep the 15 that matter')
        errs.extend(check_cases(obj.get('new_cases'), 'new_cases', 3))
    return errs

def check_cases(cs, key, minimum):
    errs = []
    if not isinstance(cs, list): return [f'missing "{key}" (a list of {{"input", "expected", "why"}})']
    if len(cs) < minimum: errs.append(f'"{key}" has {len(cs)} cases; write at least {minimum} — the hardest realistic ones from your angle')
    for i, c in enumerate(cs):
        if not isinstance(c, dict) or 'input' not in c or 'expected' not in c: errs.append(f'{key}[{i}] needs "input" and "expected"'); continue
        if c['input'] in (None, '') and not c.get('why'): errs.append(f'{key}[{i}]: an empty input needs a "why"')
    return errs

# ------------------------------------------------------------------ briefs
SCHEMA_TXT = {
    'propose': '''{
  "seat": "<your seat id>",
  "summary": "your recommended approach in one paragraph",
  "proposals": [{"id": "P1", "title": "...", "detail": "...", "why": "..."}],
  "risks": [{"id": "R1", "title": "...", "severity": "blocker|major|minor", "likelihood": "high|med|low", "evidence": "what you saw/ran/read", "mitigation": "..."}],
  "acceptance_tests": ["Given ... when ... then ... (concrete, checkable)"],
  "questions": ["only questions whose answer would change the plan"],
  "cases": [{"input": "<exactly what the system receives>", "expected": "<the exact correct result, in the charter's case format>", "why": "what this case tests"}],
  "confidence": 0.0
}''',
    'debate': '''{
  "seat": "<your seat id>",
  "steelman": "the strongest case FOR the decision you most disagree with",
  "votes": [{"decision": "D1", "vote": "accept|amend|reject", "reason": "...", "amendment": "exact change you want (for amend)"}],
  "objections": [{"id": "O4 if continuing an existing objection, else new", "decision": "D3", "severity": "blocker|major|minor",
                  "claim": "...", "evidence": "file:line, command + output, calculation or source", "fix": "concrete change",
                  "status": "new|maintained|withdrawn", "changed_by": "what convinced you (required when withdrawn)"}],
  "confidence": 0.0
}''',
    'review': '''{
  "seat": "<your seat id>",
  "verdict": "ship|ship-with-fixes|do-not-ship",
  "findings": [{"title": "...", "severity": "blocker|major|minor|nit", "location": "file:line / section / screen",
                "evidence": "exact input or command AND the actual result you observed", "expected": "...", "fix": "...", "confidence": 0.0}],
  "acceptance": [{"test": "AT2", "result": "pass|fail|not-run", "evidence": "..."}],
  "new_cases": [{"input": "...", "expected": "...", "why": "..."}],
  "keep": "what is good and must not be broken by the fixes"
}''',
}
SCHEMA_TXT['redteam'] = SCHEMA_TXT['debate']

def seat_card(st, sid):
    s = st['seats'][sid]
    must = '\n'.join(f'  - {m}' for m in s['must_check'])
    return f"You are the **{s['name']}** on a council of {len(st['seats'])} specialists reviewing one project. You care about {s['mandate']}.\nAlways check:\n{must}"

def brief(st, sid, phase, rnd):
    if sid not in st['seats']: die(f'unknown seat {sid}; seats: {", ".join(st["seats"])}')
    out = p(f'{phase}{"" if phase == "propose" else "-" + str(rnd)}', f'{sid}.json')
    charter = p('charter.md')
    common = textwrap.dedent(f"""
    {seat_card(st, sid)}

    PROJECT GOAL: {st['goal']}
    Charter (objective, definition of done, constraints, assumptions): {os.path.abspath(charter)}
    Working directory: {os.path.abspath('.')}
    """).strip()
    rules = {
        'propose': f"""
PHASE: independent proposal. Nobody else's view is visible to you on purpose — think for yourself.
1. Read the charter. Look at the real material (files, data, existing code, the user's examples) before proposing; run small experiments if they settle a question.
2. Propose how to do this well from your seat's angle: what must be in it, how it should work, what will go wrong, how we will know it is done.
3. Add acceptance tests a stranger could check (Given/When/Then with concrete values).
4. Be specific. "Handle edge cases" is useless; "invoice dates arrive as 03/04/26 in both US and EU order" is useful.
5. Write test cases in the charter's case format: realistic inputs a real user would send, from your seat's angle, with the exact expected result. Include the hard ones you expect a first version to get wrong, and a few ordinary ones. Most of these are SEALED: the builder never sees them, so they measure whether the work generalises. Don't invent impossible inputs; be sure each expected result is actually correct.""",
        'debate': f"""
PHASE: debate, round {rnd}. Read the current plan {os.path.abspath(p(f"plan_v{st.get('plan_version', 1)}.md"))} and the digest of everyone's positions {os.path.abspath(p(f"digest_{st.get('last_digest', 'propose1')}.md"))}.
Rules:
- Vote on EVERY decision D1..Dn: accept, amend (give the exact change) or reject (give the reason).
- Agreement is not the goal; being right is. Keep an objection the plan has not actually fixed, even if others disagree.
- Change your position only when shown a specific error in your reasoning; say what convinced you in changed_by.
- No evidence -> it is at most minor. Evidence = file:line, a command and its output, a calculation, or a source.
- Severity: blocker = the definition of done cannot be met or real harm; major = likely to bite users/money/time; minor = worth doing.
- Spend your words on disagreements. Do not restate what you accept.""",
        'redteam': f"""
PHASE: red team. The council converged suspiciously easily. Your only job: find the strongest reason this plan ({os.path.abspath(p(f"plan_v{st.get('plan_version', 1)}.md"))}) will fail or disappoint the user. Attack its riskiest assumption with evidence. Propose the best alternative. Vote on every decision.""",
        'review': f"""
PHASE: review pass {rnd} of the REAL artifact (not the plan). Decisions: {os.path.abspath(p('DECISIONS.md'))}. The work: {st.get('artifact', '(see charter / working directory)')}.
1. Use it for real: run it, run the tests, feed it the inputs your seat cares about, read the code/text closely.
2. Each finding must be reproducible by a stranger: the exact input/command and the actual result. Without that, set confidence low and severity minor/nit.
3. Check every acceptance test you can and report pass/fail with evidence.
4. Rank by impact; at most 15 findings. Do not pad with nits. Say what must be kept.
5. new_cases: 3–8 NEW realistic cases (charter's case format, exact expected result) that you have NOT run through the system yet — write them first, then test. They measure how well the work handles inputs nobody tuned it on, so pick realistic ones from your angle, not tricks.""",
    }[phase]
    return f"""{common}
{rules}

OUTPUT: write ONLY this JSON (valid, UTF-8) to {os.path.abspath(out)} — create the folder if needed — then reply with one line saying it's done:
{SCHEMA_TXT[phase]}
Then the orchestrator runs: python3 {os.path.abspath(__file__)} record {sid} --phase {phase}{'' if phase == 'propose' else ' --round ' + str(rnd)}
"""

# ------------------------------------------------------------------ commands
def cmd_init():
    toks, skip = [], False
    for a in sys.argv[2:]:
        if skip: skip = False; continue
        if a in ('--type', '--stakes'): skip = True; continue
        toks.append(a)
    goal = ' '.join(toks).strip()
    if not goal: die('usage: council.py init "<goal>" [--type code] [--stakes standard]')
    typ, stakes = arg('--type', 'general'), arg('--stakes', 'standard')
    if typ not in PRESETS: die(f'--type must be one of {list(PRESETS)}')
    if stakes not in STAKES: die(f'--stakes must be one of {list(STAKES)}')
    os.makedirs(D, exist_ok=True)
    st = dict(goal=goal, type=typ, stakes=stakes, limits=STAKES[stakes], seats={}, created=time.strftime('%Y-%m-%d %H:%M'),
              phase='charter', plan_version=0, objections={}, next_obj=1, decisions={}, rounds=[], findings={}, next_finding=1,
              acceptance={}, chair_notes=[], log=[])
    save(st)
    if not os.path.exists(p('charter.md')):
        open(p('charter.md'), 'w').write(f"""# Charter

**Goal (as the user said it):** {goal}

## Objective
<what success looks like for the user, in one paragraph>

## Deliverables
- <files / features / documents, where they go>

## Definition of done (acceptance criteria — each one checkable)
- AT1: <Given … when … then …>
- AT2:

## Case format (how seats write test cases and how they are scored)
- input: <what the system receives, e.g. one raw message string>
- expected: <the result, e.g. {{"name": ..., "phone": ...}} — only the fields that matter; "~text" = must contain text; null = must be empty>
- target: sealed holdout pass rate ≥ 90% (council.py cases target 0.9)

## Constraints
- <stack, budget, deadline, interfaces that are fixed, things not to touch>

## Users and context
- <who uses it, where, with what inputs>

## Assumptions made without asking (and why)
-

## Out of scope
-
""")
    print(f'council initialised in {D}/ — type {typ}, stakes {stakes} ({STAKES[stakes]})')
    nxt(f'write {p("charter.md")} (turn the goal into a checkable definition of done), then: council.py seats --suggest')

def cmd_seats():
    st = load()
    if '--set' in sys.argv:
        st['seats'] = {}
        spec_str, items, cur, q = arg('--set'), [], '', False
        for ch in spec_str:  # split on commas outside quotes
            if ch == '"': q = not q; cur += ch
            elif ch == ',' and not q: items.append(cur); cur = ''
            else: cur += ch
        items.append(cur)
        for item in items:
            item = item.strip()
            if not item: continue
            sid, _, spec = item.partition(':')
            sid = sid.strip()
            base = ROSTER.get(sid) or ROSTER['domain']
            name, mandate, must = base
            if spec:
                spec = spec.strip().strip('"')
                if sid == 'domain' or sid not in ROSTER: name = f'Domain expert — {spec}'; mandate = f'what someone with years in {spec} knows that outsiders get wrong'
                else: mandate += f' (focus: {spec})'
            st['seats'][sid] = dict(name=name, mandate=mandate, must_check=list(must))
        st['phase'] = 'propose'; save(st)
        print('seats:', ', '.join(f'{k} ({v["name"]})' for k, v in st['seats'].items()))
        nxt('spawn every seat IN PARALLEL with its brief: council.py brief <seat> --phase propose  (one subagent per seat, same message)')
        return
    n = STAKES[st['stakes']]['seats']
    pick = PRESETS[st['type']][:n]
    print(f'suggested for a {st["type"]} project at {st["stakes"]} stakes ({n} seats):')
    for s in pick: print(f'  {s:10} {ROSTER[s][0]} — {ROSTER[s][1]}')
    print('\nother seats:', ', '.join(s for s in ROSTER if s not in pick))
    print('\nAlways give the domain seat a concrete field, e.g. domain:"hospital pharmacy inventory". Add security for money/personal data, ops for services.')
    nxt(f'council.py seats --set {",".join(s if s != "domain" else "domain:<field>" for s in pick)}')

def build_brief(st):
    dev = os.path.abspath(p('dev_cases.json'))
    return f"""You are the BUILDER for a project a council of specialists has planned. Build it completely and well.

PROJECT GOAL: {st['goal']}
Charter (objective, definition of done, case format, constraints): {os.path.abspath(p('charter.md'))}
Decisions to implement — the council argued these out; follow them, and if one turns out wrong, say so in your reply rather than silently deviating: {os.path.abspath(p('DECISIONS.md'))}
Development cases (input + expected result) you may use and turn into tests: {dev}
Working directory: {os.path.abspath('.')}

Rules:
- There is also a SEALED holdout written by the council that you will never see; you are scored on it. Don't look for it: never open anything under {os.path.abspath(p('sealed'))} or other .council files beyond the three above. Build for the real inputs the charter describes, not for the dev cases alone — overfitting to them will show up in the sealed score.
- Write the acceptance tests from the charter first, then the work, then run everything.
- Work in stages and save as you go: after each stage (roughly every 8–10 minutes of work) stop and reply with what is done, what is next and the test status. Some harnesses cut long agent calls off; the orchestrator continues you with a message.
- {"Provide an evaluation entry point: a shell command that takes a path to a JSON file [{\"id\": ..., \"input\": ...}] and prints to stdout a JSON list [{\"id\": ..., \"output\": <result in the case format>}]. Put the exact command (with {cases} where the file path goes) in your final reply." if st.get('type') == 'code' else "Write the result where the charter says."}
- Finish with a short reply: what you built, how to run it, test results, the eval command, and any decision you think is wrong.
"""

def cmd_brief():
    st = load(); sid = sys.argv[2]
    if sid == 'build': print(build_brief(st)); return
    phase = arg('--phase', 'propose'); rnd = int(arg('--round', 1))
    if phase not in ('propose', 'debate', 'review', 'redteam'): die('--phase must be propose|debate|review|redteam')
    print(brief(st, sid, phase, rnd))

def cmd_record():
    st = load(); sid = sys.argv[2]; phase = arg('--phase', 'propose'); rnd = int(arg('--round', 1))
    folder = p(f'{phase}{"" if phase == "propose" else "-" + str(rnd)}')
    f = arg('--file', os.path.join(folder, f'{sid}.json'))
    if not os.path.exists(f): die(f'{f} not found — the seat must write its JSON there')
    raw = open(f).read().strip()
    m = re.search(r'\{.*\}', raw, re.S)
    try: obj = json.loads(m.group(0) if m else raw)
    except Exception as e: die(f'{f}: invalid JSON ({e}). Ask the seat to rewrite it.', 1)
    errs = check(obj, phase)
    if errs:
        print(f'{sid} {phase}: INVALID'); [print('  - ' + e) for e in errs]
        nxt(f'send these errors back to the {sid} seat (SendMessage to the same agent if possible) and record again'); sys.exit(1)
    os.makedirs(folder, exist_ok=True)
    obj['seat'] = sid
    json.dump(obj, open(os.path.join(folder, f'{sid}.json'), 'w'), indent=1, ensure_ascii=False)
    if phase == 'propose' and obj.get('cases'):
        os.makedirs(p('cases'), exist_ok=True)
        json.dump([dict(c, source=sid) for c in obj['cases']], open(p('cases', f'{sid}.json'), 'w'), indent=1, ensure_ascii=False)
    have = [x[:-5] for x in os.listdir(folder) if x.endswith('.json')]
    missing = [s for s in st['seats'] if s not in have]
    print(f'{sid} {phase}{"" if phase == "propose" else " " + str(rnd)}: recorded ({len(have)}/{len(st["seats"])} seats)')
    if missing: nxt('waiting for: ' + ', '.join(missing))
    elif phase == 'review': nxt(f'council.py findings merge --pass {rnd}')
    else: nxt(f'council.py digest --phase {phase}' + ('' if phase == 'propose' else f' --round {rnd}'))

def parse_decisions(st):
    v = st.get('plan_version', 0)
    if not v or not os.path.exists(p(f'plan_v{v}.md')): return {}
    dec = {}
    for line in open(p(f'plan_v{v}.md'), encoding='utf-8'):
        m = re.match(r'^\s*(?:[-*]\s*)?(?:#+\s*)?\**\s*(D\d+)\s*\**\s*[:.)\-—]\s*(.+)', line)
        if m: dec[m.group(1)] = m.group(2).strip().strip('*').strip()
    return dec

def cmd_digest():
    st = load(); phase = arg('--phase', 'propose'); rnd = int(arg('--round', 1))
    folder = p(f'{phase}{"" if phase == "propose" else "-" + str(rnd)}')
    files = sorted(x for x in os.listdir(folder) if x.endswith('.json')) if os.path.isdir(folder) else []
    if not files: die(f'nothing recorded in {folder}')
    pos = {}
    for x in files:
        if x[:-5] not in st['seats']: print(f'  (skipping {x}: not a seat of this council)'); continue
        pos[x[:-5]] = json.load(open(os.path.join(folder, x)))
    if not pos: die('no seat files to digest')
    letters = {sid: chr(65 + i) for i, sid in enumerate(sorted(pos))}
    out = [f'# Digest — {phase} {rnd}', '', f'Seats: {len(pos)}. Positions are labelled by letter so arguments are weighed on their merits.', '']
    if phase == 'propose':
        for sid, o in pos.items():
            out.append(f"## Position {letters[sid]} ({st['seats'][sid]['name']})")
            out.append(o.get('summary', ''))
            for x in o.get('proposals', []): out.append(f"- proposal: **{x.get('title')}** — {x.get('detail', '')} _(why: {x.get('why', '')})_")
            for x in o.get('risks', []): out.append(f"- risk [{x.get('severity')}]: **{x.get('title')}** — {x.get('evidence', '')} → {x.get('mitigation', '')}")
            out.append('')
        # cluster risks across seats (independent agreement is a strong signal)
        allr = [(sid, r) for sid, o in pos.items() for r in o.get('risks', [])]
        clusters = []
        for sid, r in allr:
            for c in clusters:
                if similar(r.get('title', '') + ' ' + r.get('evidence', ''), c['text']) > 0.28: c['seats'].add(sid); c['sev'] = min(c['sev'], SEV.index(r.get('severity', 'minor'))); break
            else: clusters.append(dict(text=r.get('title', '') + ' ' + r.get('evidence', ''), title=r.get('title', ''), seats={sid}, sev=SEV.index(r.get('severity', 'minor'))))
        clusters.sort(key=lambda c: (-len(c['seats']), c['sev']))
        out.append('## Risks raised independently by several seats (strongest signal first)')
        for c in clusters[:25]: out.append(f"- [{SEV[c['sev']]}] {c['title']} — raised by {len(c['seats'])}: {', '.join(letters[s] for s in sorted(c['seats']))}")
        out.append(''); out.append('## Acceptance tests proposed')
        seen = []
        for sid, o in pos.items():
            for a in o.get('acceptance_tests', []):
                if all(similar(a, b) < 0.5 for b in seen): seen.append(a); out.append(f'- {a}')
        q = [x for o in pos.values() for x in o.get('questions', [])]
        if q: out.append(''); out.append('## Open questions'); out += [f'- {x}' for x in q]
        ncase = sum(len(o.get('cases', [])) for o in pos.values())
        out.append(''); out.append(f'## Cases: {ncase} written by the seats (run council.py cases split; the sealed part is not shown here on purpose)')
        st['last_digest'] = f'propose{rnd}'
        st['phase'] = 'plan'
        nxt(f'council.py cases split; then write {p("plan_v1.md")}: numbered decisions as lines "D1: ...", each answering the risks above (or saying why not); include the acceptance tests. Then: council.py plan --version 1')
    else:
        dec = parse_decisions(st)
        tally = {d: {'accept': [], 'amend': [], 'reject': []} for d in dec}
        for sid, o in pos.items():
            for v in o.get('votes', []):
                tally.setdefault(v['decision'], {'accept': [], 'amend': [], 'reject': []})[v['vote']].append((sid, v))
        # objections: merge into ledger
        new_majors = 0
        for sid, o in pos.items():
            for ob in o.get('objections', []):
                oid = str(ob.get('id', '')).strip()
                if oid in st['objections']:
                    e = st['objections'][oid]
                    e['history'].append(dict(round=rnd, seat=sid, status=ob.get('status', 'maintained'), claim=ob.get('claim'), changed_by=ob.get('changed_by')))
                    if ob.get('status') == 'withdrawn' and sid == e['seat']: e['status'] = 'withdrawn'
                    elif ob.get('status') != 'withdrawn': e['status'] = 'open'; e['severity'] = ob.get('severity', e['severity']); e['resolved_how'] = None if e.get('resolved_how') and sid == e['seat'] else e.get('resolved_how')
                    continue
                # dedupe against existing open objections on the same decision
                match = next((k for k, e in st['objections'].items() if e['status'] == 'open' and e.get('decision') == ob.get('decision') and similar(e['claim'], ob.get('claim', '')) > 0.35), None)
                if match:
                    st['objections'][match]['also'] = sorted(set(st['objections'][match].get('also', [])) | {sid}); continue
                k = f'O{st["next_obj"]}'; st['next_obj'] += 1
                st['objections'][k] = dict(id=k, seat=sid, decision=ob.get('decision'), severity=ob.get('severity', 'minor'), claim=ob.get('claim'), evidence=ob.get('evidence'), fix=ob.get('fix'), status='open', round=rnd, history=[], also=[])
                if ob.get('severity') in ('blocker', 'major'): new_majors += 1
        st['rounds'].append(dict(phase=phase, round=rnd, seats=list(pos), new_majors=new_majors, tally={d: {k: [s for s, _ in v] for k, v in t.items()} for d, t in tally.items()}))
        out.append('## Votes per decision')
        for d, t in sorted(tally.items(), key=lambda x: int(x[0][1:])):
            n = sum(len(v) for v in t.values()); sup = len(t['accept']) + len(t['amend'])
            out.append(f"- **{d}** {dec.get(d, '(not in current plan)')[:110]} — accept {len(t['accept'])}, amend {len(t['amend'])}, reject {len(t['reject'])} ({sup}/{n} support)")
            for s, v in t['amend'] + t['reject']: out.append(f"    - {v['vote']} ({letters[s]}): {v.get('reason', '')} {('→ ' + v['amendment']) if v.get('amendment') else ''}")
        out.append(''); out.append('## Objection ledger')
        for k, e in st['objections'].items():
            if e['status'] == 'withdrawn': continue
            out.append(f"- **{k}** [{e['severity']}] on {e.get('decision')} — {e['claim']} (evidence: {e.get('evidence') or 'none'}; fix: {e.get('fix') or '-'}){' — answered: ' + e['resolved_how'] if e.get('resolved_how') else ''}{' — also raised by ' + ', '.join(letters.get(a, a) for a in e['also']) if e.get('also') else ''}")
        stl = [(letters[sid], o.get('steelman')) for sid, o in pos.items() if o.get('steelman')]
        if stl: out.append(''); out.append('## Steelmen'); out += [f'- {a}: {b}' for a, b in stl]
        st['last_digest'] = f'{phase}{rnd}'
    open(p(f'digest_{phase}{rnd}.md'), 'w').write('\n'.join(out) + '\n')
    save(st)
    print(f'wrote {p(f"digest_{phase}{rnd}.md")}')
    if phase != 'propose': cmd_status(quiet=False)

def cmd_plan():
    st = load(); v = int(arg('--version', st.get('plan_version', 0) + 1))
    if not os.path.exists(p(f'plan_v{v}.md')): die(f'write {p(f"plan_v{v}.md")} first (lines "D1: ..." for each decision)')
    st['plan_version'] = v
    dec = parse_decisions(st)
    if not dec: die(f'no decisions found in plan_v{v}.md — write each as a line starting "D1: ", "D2: " ...')
    st['decisions'] = dec; st['phase'] = 'debate'; save(st)
    done = [r for r in st['rounds'] if r['phase'] == 'debate']
    print(f'plan v{v}: {len(dec)} decisions ({", ".join(dec)})')
    nxt(f'spawn every seat in parallel with: council.py brief <seat> --phase debate --round {len(done) + 2}')

def convergence(st):
    dec = st.get('decisions') or parse_decisions(st)
    deb = [r for r in st['rounds'] if r['phase'] in ('debate', 'redteam')]
    if not deb: return dict(verdict='NO_DEBATE', reasons=['no debate round recorded yet'])
    last = deb[-1]; n = max(1, len(last['seats']))
    need = -(-2 * n // 3)  # ceil(2n/3)
    weak = []
    for d in dec:
        t = last['tally'].get(d)
        if not t: weak.append(f'{d}: no votes'); continue
        sup = len(t.get('accept', [])) + len(t.get('amend', []))
        if sup < need: weak.append(f'{d}: {sup}/{n} support (need {need})')
    blockers = [k for k, e in st['objections'].items() if e['status'] == 'open' and e['severity'] == 'blocker' and not e.get('resolved_how')]
    unresolved_majors = [k for k, e in st['objections'].items() if e['status'] == 'open' and e['severity'] == 'major' and not e.get('resolved_how')]
    reasons = []
    if blockers: reasons.append('open blockers: ' + ', '.join(blockers))
    if weak: reasons.append('weak support: ' + '; '.join(weak))
    if last['new_majors']: reasons.append(f"{last['new_majors']} new blocker/major objections this round")
    if unresolved_majors: reasons.append('unanswered majors: ' + ', '.join(unresolved_majors))
    unanimous = all(len(t.get('reject', [])) == 0 and len(t.get('amend', [])) == 0 for t in last['tally'].values()) and not any(e['round'] == last['round'] for e in st['objections'].values())
    max_r = st['limits']['debate_rounds']
    if not reasons:
        if unanimous and not any(r['phase'] == 'redteam' for r in st['rounds']):
            return dict(verdict='RED_TEAM', reasons=['unanimous with no objections on the first try — run one red-team pass before trusting it'])
        return dict(verdict='CONVERGED', reasons=[])
    if len([r for r in deb if r['phase'] == 'debate']) >= max_r: return dict(verdict='STALEMATE', reasons=reasons)
    return dict(verdict='CONTINUE', reasons=reasons)

def cmd_status(quiet=False):
    st = load(); c = convergence(st)
    print(f"phase: {st['phase']} · plan v{st.get('plan_version', 0)} · debate rounds {len([r for r in st['rounds'] if r['phase'] == 'debate'])}/{st['limits']['debate_rounds']} · objections open {sum(1 for e in st['objections'].values() if e['status'] == 'open')}")
    print('verdict:', c['verdict']); [print('  - ' + r) for r in c['reasons']]
    if st['phase'] in ('review', 'build', 'done'):
        fs = st['findings']
        print(f"findings: {sum(1 for f in fs.values() if f['status'] in ('open', 'verified') and f['severity'] in ('blocker', 'major'))} open blocker/major, {sum(1 for f in fs.values() if f['status'] == 'fixed')} fixed, {sum(1 for f in fs.values() if f['status'] == 'dismissed')} dismissed")
    v = c['verdict']
    if v == 'CONTINUE': nxt(f'answer each objection in plan_v{st.get("plan_version", 1) + 1}.md (change the decision or say why not), mark them with council.py resolve <Oid> --how "...", run council.py plan, then debate again')
    elif v == 'RED_TEAM': nxt('spawn the skeptic (and one more seat) with: council.py brief skeptic --phase redteam --round <next>; record; digest --phase redteam --round <n>')
    elif v == 'STALEMATE': nxt('you are the chair: rule on what remains with council.py decide --note "...", recording the dissent; then write DECISIONS.md via council.py report and build')
    elif v == 'CONVERGED': nxt('council.py report (writes DECISIONS.md), then spawn ONE builder agent with: council.py brief build. Then score: council.py cases score --set sealed --run "<eval cmd>", then review pass 1 (all seats in parallel)')

def cmd_resolve():
    st = load(); oid = sys.argv[2]; how = arg('--how')
    if oid not in st['objections']: die(f'unknown objection {oid}')
    if not how: die('--how "what changed in the plan (or why the objection is rejected)" is required')
    st['objections'][oid]['resolved_how'] = how; save(st); print(f'{oid} answered: {how}')

def cmd_decide():
    st = load(); note = arg('--note')
    if not note: die('--note "the ruling and the dissent you are overriding" is required')
    st['chair_notes'].append(dict(at=time.strftime('%H:%M'), note=note))
    for e in st['objections'].values():
        if e['status'] == 'open' and not e.get('resolved_how'): e['resolved_how'] = 'chair ruling (dissent recorded): ' + note[:200]; e['dissent'] = True
    st['phase'] = 'build'; save(st); print('ruling recorded; remaining objections kept as dissent')
    nxt('council.py report, then spawn ONE builder agent with: council.py brief build')

def cmd_findings():
    st = load(); sub = sys.argv[2] if len(sys.argv) > 2 else 'list'
    if sub == 'merge':
        k = int(arg('--pass', 1)); folder = p(f'review-{k}')
        if not os.path.isdir(folder): die(f'no {folder}')
        added = 0; fresh = []
        for x in sorted(os.listdir(folder)):
            if not x.endswith('.json'): continue
            o = json.load(open(os.path.join(folder, x))); sid = x[:-5]
            for f in o.get('findings', []):
                key = f.get('title', '') + ' ' + f.get('location', '')
                dup = next((fid for fid, e in st['findings'].items() if e['status'] in ('open', 'verified') and (similar(e['title'] + ' ' + e.get('location', ''), key) > 0.4 or (f.get('location') and f.get('location') == e.get('location') and similar(e['title'], f.get('title', '')) > 0.2))), None)
                if dup:
                    e = st['findings'][dup]; e['seats'] = sorted(set(e['seats']) | {sid})
                    if SEV.index(f.get('severity', 'nit')) < SEV.index(e['severity']): e['severity'] = f['severity']
                    continue
                fid = f'F{st["next_finding"]}'; st['next_finding'] += 1
                st['findings'][fid] = dict(id=fid, title=f.get('title'), severity=f.get('severity', 'minor'), location=f.get('location', ''), evidence=f.get('evidence', ''), expected=f.get('expected', ''), fix=f.get('fix', ''), confidence=f.get('confidence'), seats=[sid], status='open', pass_=k, notes=[])
                added += 1
            for a in o.get('acceptance', []):
                st['acceptance'].setdefault(a.get('test', '?'), []).append(dict(seat=sid, result=a.get('result'), evidence=a.get('evidence', ''), pass_=k))
            fresh.extend(dict(c, source=sid) for c in o.get('new_cases', []) if isinstance(c, dict) and 'input' in c)
        if fresh:
            base = len(load_cases(f'fresh-{k}'))
            for i, c in enumerate(fresh): c['id'] = f'R{k}.{base + i + 1}'
            save_cases(f'fresh-{k}', load_cases(f'fresh-{k}') + fresh)
        st['phase'] = 'review'; save(st)
        print(f'merged pass {k}: {added} new findings, {len(fresh)} fresh cases')
        if fresh: print(f'  score the fresh cases BEFORE fixing anything: council.py cases score --set fresh-{k} --run "<eval command>"')
        sub = 'list'
    if sub == 'set':
        fid, status = sys.argv[3], sys.argv[4]
        if fid not in st['findings']: die(f'unknown finding {fid}')
        if status not in ('verified', 'dismissed', 'fixed', 'wontfix', 'open'): die('status: verified|dismissed|fixed|wontfix|open')
        note = arg('--note', '')
        if status in ('dismissed', 'wontfix', 'fixed') and not note: die(f'{status} needs --note (dismissed: why it is not real; wontfix: why acceptable; fixed: what changed + how verified)')
        st['findings'][fid]['status'] = status; st['findings'][fid]['notes'].append(note); save(st)
        print(f'{fid} -> {status}'); return
    only_open = '--open' in sys.argv
    rows = sorted(st['findings'].values(), key=lambda f: (SEV.index(f['severity']), f['id']))
    for f in rows:
        if only_open and f['status'] not in ('open', 'verified'): continue
        print(f"{f['id']:4} [{f['severity']:7}] {f['status']:9} {f['title']}  ({', '.join(f['seats'])}; {f.get('location', '')})")
        if f['status'] == 'open' and f['severity'] in ('blocker', 'major'): print(f"      evidence: {str(f['evidence'])[:220]}")
    opn = [f for f in rows if f['status'] == 'open' and f['severity'] in ('blocker', 'major')]
    if opn: nxt('reproduce each open blocker/major yourself (or with a verifier agent) — then council.py findings set <F> verified|dismissed --note "..."; fix verified ones')
    else: nxt('fix the verified findings, re-run the acceptance checks (council.py accept ...), then run another review pass or council.py gate')

# ------------------------------------------------------------------ cases (sealed holdout + fresh review cases)
def case_path(name): return p('sealed', 'holdout.json') if name == 'sealed' else p('dev_cases.json') if name == 'dev' else p(f'cases_{name}.json')
def load_cases(name):
    f = case_path(name)
    return json.load(open(f)) if os.path.exists(f) else []
def save_cases(name, cs):
    os.makedirs(os.path.dirname(case_path(name)) or '.', exist_ok=True)
    json.dump(cs, open(case_path(name), 'w'), indent=1, ensure_ascii=False)

def canon(v):
    """Normalise for comparison: NFKC, drop combining marks/tatweel, casefold, collapse whitespace, trim edge punctuation."""
    if isinstance(v, str):
        t = ''.join(ch for ch in unicodedata.normalize('NFKD', v) if not unicodedata.combining(ch)).replace('ـ', '')
        t = unicodedata.normalize('NFKC', t).casefold()
        return re.sub(r'\s+', ' ', t).strip(' \t\n.,;:!?-–—"\'')
    return v

def unjson(v):
    """Seats sometimes write the expected result as a JSON string; read it as the object it describes."""
    if isinstance(v, str) and v.strip()[:1] in '{[':
        try: return json.loads(v)
        except Exception: return v
    return v

def match(expected, actual):
    expected, actual = unjson(expected), unjson(actual)
    """expected: exact value | "~text" (actual must contain text) | null/"" (actual must be empty) | list (same items, any order) | dict (each key matched)."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict): return {k: False for k in expected}
        return {k: match_value(v, actual.get(k)) for k, v in expected.items()}
    return {'_': match_value(expected, actual)}

def match_value(e, a):
    if e is None or e == '' or e == []: return a in (None, '', [], {}, False)
    if isinstance(e, str) and e.startswith('~'): return canon(e[1:]) in canon(json.dumps(a, ensure_ascii=False) if not isinstance(a, str) else a)
    if isinstance(e, bool) or isinstance(a, bool): return e is a or e == a
    if isinstance(e, (int, float)) and isinstance(a, (int, float)): return abs(e - a) <= 1e-6 * max(1, abs(e))
    if isinstance(e, list): return isinstance(a, list) and sorted(map(lambda x: json.dumps(canon(x), ensure_ascii=False), e)) == sorted(map(lambda x: json.dumps(canon(x), ensure_ascii=False), a))
    if isinstance(e, dict): return all(match(e, a).values())
    return canon(e) == canon(a if not isinstance(a, (int, float)) else str(a)) or canon(str(e)) == canon(str(a))

def cmd_cases():
    st = load(); sub = sys.argv[2] if len(sys.argv) > 2 else 'list'
    if sub == 'split':
        frac = float(arg('--sealed', 0.6)); dev, sealed = [], []
        files = sorted(x for x in os.listdir(p('cases')) if x.endswith('.json')) if os.path.isdir(p('cases')) else []
        if not files: die('no seat cases recorded (the propose phase writes them)')
        n = 0
        for x in files:  # stratified per seat, deterministic order by content hash
            cs = sorted(json.load(open(p('cases', x))), key=lambda c: hashlib.sha1(json.dumps(c['input'], ensure_ascii=False).encode()).hexdigest())
            k = round(len(cs) * frac)
            for i, c in enumerate(cs):
                n += 1; c['id'] = f'C{n}'
                (sealed if i < k else dev).append(c)
        save_cases('dev', dev); save_cases('sealed', sealed)
        st['cases_meta'].update(dev=len(dev), sealed=len(sealed), target=st['cases_meta'].get('target', 0.9)); save(st)
        print(f'{len(dev)} dev cases -> {p("dev_cases.json")} (the builder gets these)\n{len(sealed)} sealed cases -> {p("sealed/holdout.json")} (never shown to the builder; you may read them only to check a disputed case)')
        nxt('write the plan; after the build: council.py cases score --set sealed --run "<eval command with {cases}>"'); return
    if sub == 'target':
        st['cases_meta']['target'] = float(sys.argv[3]); save(st); print('target', sys.argv[3]); return
    if sub == 'waive':
        note = arg('--note') or die('--note "why shipping below target is acceptable" is required')
        st['cases_meta']['waiver'] = note; save(st); print('waiver recorded'); return
    if sub == 'drop':
        cid, note = sys.argv[3], arg('--note') or die('--note "why this case is wrong" is required')
        for name in ['sealed', 'dev'] + [x[6:-5] for x in os.listdir(D) if x.startswith('cases_fresh-')]:
            cs = load_cases(name); keep = [c for c in cs if c.get('id') != cid]
            if len(keep) != len(cs): save_cases(name, keep); st['cases_meta'].setdefault('dropped', []).append(dict(id=cid, set=name, note=note)); save(st); print(f'dropped {cid} from {name}'); return
        die(f'no case {cid}')
    if sub == 'list':
        print(f"dev {len(load_cases('dev'))} · sealed {len(load_cases('sealed'))} · target {st['cases_meta'].get('target', 0.9):.0%}")
        for sc in st['scores']: print(f"  {sc['at']} {sc['set']:9} {sc['passed']}/{sc['n']} cases ({sc['rate']:.0%}) · fields {sc['field_acc']:.0%} · {sc.get('label', '')}")
        return
    if sub == 'score':
        name = arg('--set', 'sealed'); cs = load_cases(name)
        if not cs: die(f'no cases in set {name}')
        if arg('--results'):  # judged manually (non-code work)
            res = {str(r['id']): r for r in json.load(open(arg('--results')))}
            rows = [dict(id=c['id'], source=c.get('source'), ok=bool(res.get(str(c['id']), {}).get('pass')), fields={'_': bool(res.get(str(c['id']), {}).get('pass'))}, note=res.get(str(c['id']), {}).get('note', '')) for c in cs]
        else:
            cmd = arg('--run') or die('--run "<command with {cases}>" or --results judged.json')
            tmp = p(f'_run_{name}.json'); json.dump([dict(id=c['id'], input=c['input']) for c in cs], open(tmp, 'w'), ensure_ascii=False)
            r = subprocess.run(cmd.replace('{cases}', tmp), shell=True, capture_output=True, text=True, timeout=int(arg('--timeout', 900)))
            os.remove(tmp)
            try: outs = {str(o['id']): o.get('output') for o in json.loads(r.stdout[r.stdout.find('['):])}
            except Exception: die(f'eval command must print a JSON list [{{"id","output"}}] (exit {r.returncode}):\n{(r.stdout + r.stderr)[-1200:]}')
            rows = []
            for c in cs:
                m = match(c['expected'], outs.get(str(c['id'])))
                rows.append(dict(id=c['id'], source=c.get('source'), ok=all(m.values()), fields=m, got=outs.get(str(c['id']))))
        nf = sum(len(x['fields']) for x in rows); okf = sum(sum(x['fields'].values()) for x in rows)
        sc = dict(set=name, n=len(rows), passed=sum(x['ok'] for x in rows), rate=sum(x['ok'] for x in rows) / len(rows), field_acc=okf / max(1, nf), at=time.strftime('%m-%d %H:%M'), label=arg('--label', ''))
        st['scores'].append(sc)
        byfield, bysrc = {}, {}
        for x in rows:
            for k, v in x['fields'].items():
                if not v: byfield[k] = byfield.get(k, 0) + 1
            if not x['ok']: bysrc[x['source']] = bysrc.get(x['source'], 0) + 1
        os.makedirs(p('scores'), exist_ok=True)
        json.dump(rows, open(p('scores', f"{name}_{len(st['scores'])}.json"), 'w'), indent=1, ensure_ascii=False)
        print(f"{name}: {sc['passed']}/{sc['n']} cases pass ({sc['rate']:.0%}), field accuracy {sc['field_acc']:.0%}")
        print('  misses by field:', ', '.join(f'{k} {v}' for k, v in sorted(byfield.items(), key=lambda x: -x[1])) or 'none')
        print('  misses by author seat:', ', '.join(f'{k} {v}' for k, v in sorted(bysrc.items(), key=lambda x: -x[1])) or 'none')
        if name == 'sealed':
            print(f'  (per-case detail in {p("scores")}/ — for YOU only: tell the builder field/seat counts and patterns in your own words, never the sealed inputs)')
        else:
            for x in [x for x in rows if not x['ok']][:12]: print(f"  ✗ {x['id']} ({x['source']}): got {json.dumps(x.get('got'), ensure_ascii=False)[:160]}")
        if name.startswith('fresh-') and not st['cases_meta'].get(f'{name}_merged'):
            save_cases('dev', load_cases('dev') + cs); st['cases_meta'][f'{name}_merged'] = True
            print(f'  {len(cs)} fresh cases now added to the dev set (they are no longer unseen) — fix the misses with the builder')
        save(st); return
    die('cases split|score|list|drop|target|waive')

def cmd_accept():
    st = load(); cmd = arg('--run'); name = arg('--name', 'AT')
    if not cmd:  # manual check for non-code work: --result pass|fail --evidence "what you checked"
        res, ev = arg('--result'), arg('--evidence')
        if res not in ('pass', 'fail') or not ev: die('use --run "<command>", or --result pass|fail --evidence "what you checked and saw"')
        st['acceptance'].setdefault(name, []).append(dict(seat='orchestrator', result=res, evidence=ev, at=time.strftime('%H:%M'), pass_='manual'))
        save(st); print(f'{name}: {res.upper()} (manual)'); return
    t0 = time.time()
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=int(arg('--timeout', 900)))
    tail = (r.stdout + r.stderr)[-1500:]
    st['acceptance'].setdefault(name, []).append(dict(seat='orchestrator', result='pass' if r.returncode == 0 else 'fail', evidence=f'$ {cmd}\n(exit {r.returncode}, {time.time() - t0:.1f}s)\n{tail}', at=time.strftime('%H:%M'), pass_='run'))
    save(st); print(f'{name}: {"PASS" if r.returncode == 0 else "FAIL"} (exit {r.returncode})'); print(tail[-600:])
    sys.exit(0 if r.returncode == 0 else 1)

def cmd_gate():
    st = load(); problems = []
    if not st['seats']: problems.append('no seats')
    if not os.path.exists(p('DECISIONS.md')): problems.append('no DECISIONS.md (council.py report)')
    reviews = sorted(int(x.split('-')[1]) for x in os.listdir(D) if x.startswith('review-') and os.path.isdir(p(x)))
    if not reviews: problems.append('no review pass recorded')
    opn = [f['id'] for f in st['findings'].values() if f['status'] in ('open', 'verified') and f['severity'] in ('blocker', 'major')]
    if opn: problems.append('open blocker/major findings: ' + ', '.join(opn))
    runs = {k: v[-1] for k, v in st['acceptance'].items() if any(x.get('seat') == 'orchestrator' for x in v)}
    if not runs: problems.append('no acceptance check executed by the orchestrator (council.py accept --run ...)')
    failed = [k for k, v in runs.items() if v['result'] != 'pass']
    if failed: problems.append('failing acceptance checks: ' + ', '.join(failed))
    if load_cases('sealed'):
        sealed = [x for x in st['scores'] if x['set'] == 'sealed']
        tgt = st['cases_meta'].get('target', 0.9)
        if not sealed: problems.append('sealed holdout never scored (council.py cases score --set sealed --run ...)')
        elif sealed[-1]['rate'] < tgt and not st['cases_meta'].get('waiver'): problems.append(f"sealed holdout {sealed[-1]['rate']:.0%} < target {tgt:.0%} — fix the patterns behind the misses, or council.py cases waive --note \"why\"")
        devs = [x for x in st['scores'] if x['set'] == 'dev']
        if devs and devs[-1]['rate'] < 1 and devs[-1]['n'] - devs[-1]['passed'] > max(1, 0.05 * devs[-1]['n']): problems.append(f"dev cases: {devs[-1]['n'] - devs[-1]['passed']} still failing")
    fixed_after = [f for f in st['findings'].values() if f['status'] == 'fixed' and f['severity'] in ('blocker', 'major')]
    if fixed_after and reviews and max(f['pass_'] for f in fixed_after) >= reviews[-1] and st['limits']['review_passes'] > len(reviews):
        problems.append(f'blocker/major fixes since review pass {reviews[-1]} have not been re-reviewed (passes used {len(reviews)}/{st["limits"]["review_passes"]})')
    if problems:
        print('GATE: NOT READY'); [print('  - ' + x) for x in problems]; sys.exit(1)
    st['phase'] = 'done'; save(st); print('GATE: READY TO SHIP'); nxt('council.py report, then deliver REPORT.md with the work')

def cmd_report():
    st = load(); dec = st.get('decisions') or parse_decisions(st)
    lines = [f"# Decisions — {st['goal']}", '', f"Council: {', '.join(v['name'] for v in st['seats'].values())} · stakes {st['stakes']} · plan v{st.get('plan_version', 0)}", '']
    for d, text in sorted(dec.items(), key=lambda x: int(x[0][1:])):
        lines.append(f'- **{d}** {text}')
    objs = [e for e in st['objections'].values()]
    if objs:
        lines += ['', '## How objections were handled']
        for e in objs: lines.append(f"- {e['id']} [{e['severity']}] ({st['seats'].get(e['seat'], {}).get('name', e['seat'])}) {e['claim']} → {e.get('resolved_how') or e['status']}{' (dissent recorded)' if e.get('dissent') else ''}")
    if st['chair_notes']: lines += ['', '## Chair rulings'] + [f"- {n['note']}" for n in st['chair_notes']]
    open(p('DECISIONS.md'), 'w').write('\n'.join(lines) + '\n')
    rep = ['# Council report', '', f"**Goal:** {st['goal']}", '', '## Process', f"- seats: {', '.join(st['seats'])}", f"- rounds: " + ', '.join(f"{r['phase']} {r['round']}" for r in st['rounds']) or '- rounds: proposals only']
    rp = sorted(x for x in os.listdir(D) if x.startswith('review-'))
    rep.append(f'- review passes: {len(rp)}')
    rep += ['', '## Findings']
    for f in sorted(st['findings'].values(), key=lambda f: (SEV.index(f['severity']), f['id'])):
        rep.append(f"- {f['id']} [{f['severity']}] {f['status']}: {f['title']}" + (f" — {f['notes'][-1]}" if f['notes'] else ''))
    if st['scores']:
        rep += ['', '## Case scores (sealed = never seen by the builder; fresh-K = written by reviewers in pass K, scored before fixes)']
        rep += [f"- {x['at']} {x['set']}: {x['passed']}/{x['n']} cases ({x['rate']:.0%}), fields {x['field_acc']:.0%} {x.get('label', '')}" for x in st['scores']]
        if st['cases_meta'].get('waiver'): rep.append(f"- waiver: {st['cases_meta']['waiver']}")
    rep += ['', '## Acceptance checks']
    for k, v in st['acceptance'].items():
        last = v[-1]; rep.append(f"- {k}: {last['result']} ({last['seat']})")
    open(p('REPORT.md'), 'w').write('\n'.join(rep) + '\n')
    if st['phase'] in ('plan', 'debate'): st['phase'] = 'build'; save(st)
    print(f'wrote {p("DECISIONS.md")} and {p("REPORT.md")}')

CMDS = dict(init=cmd_init, seats=cmd_seats, brief=cmd_brief, record=cmd_record, digest=cmd_digest, plan=cmd_plan, status=cmd_status,
            resolve=cmd_resolve, decide=cmd_decide, findings=cmd_findings, cases=cmd_cases, accept=cmd_accept, gate=cmd_gate, report=cmd_report)
if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS: print(__doc__); sys.exit(2)
    CMDS[sys.argv[1]]()
