import json, sys, os
f = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
ev = []
for line in open(f, errors='ignore'):
    try: ev.append(json.loads(line))
    except: pass
tools = 0; texts = []
for e in ev:
    if e.get('type') == 'assistant':
        for c in e['message'].get('content', []):
            if c.get('type') == 'tool_use':
                tools += 1
                inp = c.get('input', {})
                desc = inp.get('description') or inp.get('command', '')[:100] or inp.get('file_path', '') or inp.get('skill', '') or inp.get('prompt', '')[:80]
                texts.append(f"TOOL {c['name']}: {str(desc)[:140]}")
            elif c.get('type') == 'text' and c['text'].strip():
                texts.append('TEXT ' + c['text'].strip().replace('\n', ' ')[:200])
    if e.get('type') == 'result':
        texts.append(f"RESULT: {e.get('subtype')} turns={e.get('num_turns')} cost={e.get('total_cost_usd')} dur={e.get('duration_ms')}")
print(f"{os.path.dirname(f)}: {len(ev)} events, {tools} tool calls")
for t in texts[-n:]: print('  ' + t)
