"""Build ai.svg — a terminal-style card about how I work with Claude Code,
using real numbers from ~/.claude (stats-cache.json + session transcripts).

Run from the repo root on the machine where Claude Code is used:
    python -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
    .venv/bin/python scripts/ai_card.py ai.svg
The font is subset from a local JetBrains Mono install (override with FONT_DIR)."""
import base64, collections, datetime as dt, glob, html, io, json, math, os, sys
from fontTools import subset
from fontTools.ttLib import TTFont

OUT = sys.argv[1] if len(sys.argv) > 1 else 'ai.svg'
HOME = os.path.expanduser('~/.claude')
FONT_DIR = os.environ.get('FONT_DIR', '/usr/share/fonts/TTF/')
FONTS = {400: 'JetBrainsMonoNLNerdFontMono-Regular.ttf', 700: 'JetBrainsMonoNLNerdFontMono-Bold.ttf'}

# ---------- data ----------
cache = json.load(open(f'{HOME}/stats-cache.json'))
cutoff = cache['lastComputedDate']                      # cache covers dates <= cutoff
daily = collections.Counter()                           # date -> activity (tool calls + prompts)
days = set()
sessions = cache['totalSessions']
tool_calls = sum(d['toolCallCount'] for d in cache['dailyActivity'])
out_tokens = sum(m['outputTokens'] for m in cache['modelUsage'].values())
for d in cache['dailyActivity']:
    days.add(d['date']); daily[d['date']] += d['toolCallCount'] + d['messageCount'] // 10

tools = collections.Counter(); subagents = 0; late_sessions = set(); seen = set()
for f in glob.glob(f'{HOME}/projects/**/*.jsonl', recursive=True):
    if '/subagents/' in f and os.path.basename(f).startswith('agent-'):
        subagents += 1
    for line in open(f, errors='ignore'):
        try: r = json.loads(line)
        except ValueError: continue
        if r.get('type') not in ('user', 'assistant') or not r.get('timestamp'): continue
        day = r['timestamp'][:10]; m = r.get('message') or {}
        uses = [c for c in m.get('content') or [] if isinstance(c, dict) and c.get('type') == 'tool_use']
        for c in uses:
            n = c['name']
            tools['Browser · MCP' if 'claude-in-chrome' in n else
                  'Edit / Write' if n in ('Edit', 'Write', 'MultiEdit') else
                  'Web research' if n in ('WebSearch', 'WebFetch') else n] += 1
        if day <= cutoff: continue
        days.add(day)
        if '/subagents/' not in f: late_sessions.add(r.get('sessionId'))
        daily[day] += len(uses) + (r['type'] == 'user' and isinstance(m.get('content'), str))
        tool_calls += len(uses)
        if r['type'] == 'assistant' and m.get('id') not in seen:
            seen.add(m.get('id')); out_tokens += (m.get('usage') or {}).get('output_tokens', 0)
sessions += len(late_sessions)
# Claude Code deletes transcripts after 30 days; these were counted on 2026-10-29 before that cleanup
ARCHIVE_TOOLS = {'Bash': 4320, 'Read': 758, 'Browser · MCP': 215, 'Edit / Write': 162, 'Web research': 69}
subagents = max(subagents, 73)
# transcripts from 2026-09-06 on held 44 sessions, 25 active days and 5,682 tool calls at that count
pre = [d for d in cache['dailyActivity'] if d['date'] < '2026-09-06']
sessions = max(sessions, sum(d['sessionCount'] for d in pre) + 44)
active_days = max(len(days), len(pre) + 25)
tool_calls = max(tool_calls, sum(d['toolCallCount'] for d in pre) + 5682)
for k, v in ARCHIVE_TOOLS.items():
    tools[k] = max(tools[k], v)
first = dt.date.fromisoformat(cache['firstSessionDate'][:10])
today = dt.date.today()

def short(n):
    return f'{n/1e6:.1f}M' if n >= 1e6 else f'{n/1e3:.1f}k' if n >= 1e4 else f'{n:,}'

stats = [(str(active_days), 'active days', '#A78BFA'), (str(sessions), 'sessions', '#22D3EE'),
         (short(tool_calls), 'tool calls', '#34D399'), (str(subagents), 'subagents spawned', '#FACC15'),
         (short(out_tokens), 'tokens written', '#F472B6')]
top = [(k, tools[k]) for k in ('Bash', 'Read', 'Browser · MCP', 'Edit / Write', 'Web research')]

# ---------- svg ----------
W, H = 860, 616
o = []; a = o.append
esc = html.escape

a('<rect x="1" y="1" width="858" height="614" rx="16" fill="url(#bg)" stroke="#1E293B"/>')
a('<g clip-path="url(#win)"><rect x="1" y="1" width="858" height="40" fill="#fff" fill-opacity=".025"/>'
  '<rect x="1" y="41" width="858" height="1" fill="#1E293B"/><rect x="210" y="1" width="440" height="1" fill="url(#hl)"/></g>')
a('<circle cx="24" cy="21" r="6" fill="#FF5F57"/><circle cx="44" cy="21" r="6" fill="#FEBC2E"/><circle cx="64" cy="21" r="6" fill="#28C840"/>')
a('<text x="430" y="26" text-anchor="middle" class="dim" style="font-size:13px">claude — ~/projects</text>')

CHEV = '<path d="M56 {0}l6 5.5-6 5.5" fill="none" stroke="#34D399" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
a('<text x="40" y="76" fill="#C4B5FD">~</text>' + CHEV.format(66))
a('<text x="72" y="76" fill="#E2E8F0" clip-path="url(#typed)">claude</text>')
a('<text class="in dim" style="animation-delay:.95s" x="144" y="76"># how I build with AI agents</text>')

def label(x, y, txt, delay, extra=''):
    a(f'<g class="in" style="animation-delay:{delay}s"><text x="{x}" y="{y}" class="lbl">{esc(txt)}</text>'
      + (f'<text x="{x + len(txt) * 9.2 + 8}" y="{y}" class="dim" style="font-size:12px">{esc(extra)}</text>' if extra else '') + '</g>')

# workflow pipeline
label(40, 118, 'WORKFLOW', 1.1)
steps = [('01', 'PLAN', '#A78BFA', 'plan mode first', 'scope → spec'),
         ('02', 'DELEGATE', '#22D3EE', 'parallel subagents', 'explore · research'),
         ('03', 'BUILD', '#34D399', 'edit · run · test', 'in the real shell'),
         ('04', 'VERIFY', '#FACC15', 'review the diff', 'browser via MCP')]
BY, BW, BH = 132, 168, 88
for i, (num, title, col, d1, d2) in enumerate(steps):
    x = 40 + i * 204; delay = 1.2 + i * .18
    a(f'<g class="in" style="animation-delay:{delay:.2f}s">'
      f'<rect x="{x}" y="{BY}" width="{BW}" height="{BH}" rx="10" fill="{col}" fill-opacity=".06" stroke="{col}" stroke-opacity=".55"/>'
      f'<text x="{x + 14}" y="{BY + 28}"><tspan class="dim">{num}</tspan><tspan dx="9" fill="{col}" style="font-weight:700">{title}</tspan></text>'
      f'<text x="{x + 14}" y="{BY + 54}" class="sub">{esc(d1)}</text>'
      f'<text x="{x + 14}" y="{BY + 72}" class="sub">{esc(d2)}</text></g>')
    if i < 3:
        x0, y0 = x + BW + 4, BY + BH / 2
        a(f'<g class="in" style="animation-delay:{delay + .12:.2f}s"><path class="flow" d="M{x0} {y0}h24" stroke="{col}"/>'
          f'<path d="M{x0 + 22} {y0 - 4}l6 4-6 4" fill="none" stroke="{col}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></g>')
# iterate loop: VERIFY back to PLAN
lx1, lx0, ly = 652 + BW / 2, 40 + BW / 2, BY + BH + 26
a(f'<g class="in" style="animation-delay:2.0s"><path class="flow" d="M{lx1} {BY + BH + 4}V{ly - 8}q0 8-8 8H{lx0 + 8}q-8 0-8-8V{BY + BH + 10}" stroke="#64748B"/>'
  f'<path d="M{lx0 - 4} {BY + BH + 12}l4-6 4 6" fill="none" stroke="#64748B" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
  f'<rect x="{430 - 44}" y="{ly - 10}" width="88" height="20" rx="10" fill="#0B1020" stroke="#1E293B"/>'
  f'<text x="430" y="{ly + 4}" text-anchor="middle" class="sub">↻ iterate</text></g>')

# numbers
label(40, 296, 'BY THE NUMBERS', 2.15, f'since {first:%b %Y} · from my local Claude Code logs')
TW = 146.4
for i, (val, lab, col) in enumerate(stats):
    x = 40 + i * (TW + 12); delay = 2.25 + i * .08
    a(f'<g class="in" style="animation-delay:{delay:.2f}s">'
      f'<rect x="{x:.1f}" y="310" width="{TW}" height="74" rx="10" fill="#fff" fill-opacity=".03" stroke="#1E293B"/>'
      f'<rect x="{x + 14:.1f}" y="310" width="28" height="2" rx="1" fill="{col}"/>'
      f'<text x="{x + 14:.1f}" y="348" class="num">{esc(val)}</text>'
      f'<text x="{x + 14:.1f}" y="370" class="sub">{esc(lab)}</text></g>')

# tool usage bars (sqrt-scaled, real counts printed)
label(40, 420, 'TOOLS IT RUNS FOR ME', 2.7)
mx = math.sqrt(max(c for _, c in top))
for i, (name, cnt) in enumerate(top):
    y = 446 + i * 26; delay = 2.8 + i * .08; w = max(4, 190 * math.sqrt(cnt) / mx)
    a(f'<g class="in" style="animation-delay:{delay:.2f}s"><text x="40" y="{y + 10}" class="v" style="font-size:13px">{esc(name)}</text>'
      f'<rect x="168" y="{y}" width="190" height="12" rx="3" fill="#1E293B"/>'
      f'<rect class="grow" style="animation-delay:{delay + .1:.2f}s" x="168" y="{y}" width="{w:.1f}" height="12" rx="3" fill="url(#art)"/>'
      f'<text x="370" y="{y + 10}" class="dim" style="font-size:12px">{cnt:,}</text></g>')

# setup
label(448, 420, 'SETUP', 2.7)
for i, (k, v) in enumerate([('agent', 'Claude Code'), ('models', 'Opus · Sonnet'), ('mcp', 'Chrome · Docs'), ('mode', 'plan → auto')]):
    y = 456 + i * 26
    a(f'<g class="in" style="animation-delay:{2.85 + i * .08:.2f}s"><text x="448" y="{y}" class="k">{k}</text>'
      f'<text x="510" y="{y}" class="v" style="font-size:12px">{esc(v)}</text></g>')

# activity heatmap (weeks as columns, Mon..Sun as rows)
start = first - dt.timedelta(days=first.weekday())
weeks = (today - start).days // 7 + 1
CELL, GAP = 13, 4
hx = 820 - weeks * (CELL + GAP) + GAP
label(hx, 420, 'ACTIVITY', 2.7, f'{first:%b} → {today:%b}')
lv_col = ['#1E293B', '#3B2A73', '#6D28D9', '#A78BFA', '#67E8F9']
peak = max(daily.values())
def level(v):
    return 0 if not v else 1 + min(3, int(4 * math.sqrt(v / peak)))
for wk in range(weeks):
    for dow in range(7):
        day = start + dt.timedelta(days=wk * 7 + dow)
        if day > today: continue
        lv = level(daily.get(day.isoformat(), 0)) if day >= first else 0
        x = hx + wk * (CELL + GAP); y = 436 + dow * (CELL + GAP)
        a(f'<rect class="px" style="animation-delay:{2.8 + wk * .045 + dow * .012:.3f}s" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{lv_col[lv]}"/>')
lg = 820 - 5 * 15 - 36
a(f'<g class="in" style="animation-delay:3.4s"><text x="{lg - 8}" y="{564}" text-anchor="end" class="dim" style="font-size:11px">less</text>'
  + ''.join(f'<rect x="{lg + i * 15}" y="555" width="11" height="11" rx="2.5" fill="{c}"/>' for i, c in enumerate(lv_col))
  + f'<text x="{lg + 5 * 15 + 4}" y="564" class="dim" style="font-size:11px">more</text></g>')

a('<g class="in" style="animation-delay:3.6s"><text x="40" y="592" fill="#C4B5FD">~</text>' + CHEV.format(582)
  + '<rect class="cur" x="72" y="578" width="9" height="18" rx="1.5" fill="#67E8F9"/></g>')

body = '\n'.join(o)

# ---------- font subset ----------
import re
chars = set(re.sub(r'<[^>]+>', '', body)) | set('0123456789')
faces = ''
for weight, fname in FONTS.items():
    f = TTFont(FONT_DIR + fname)
    opts = subset.Options(); opts.flavor = 'woff2'; opts.layout_features = []; opts.name_IDs = []; opts.hinting = False
    s = subset.Subsetter(opts); s.populate(text=html.unescape(''.join(chars))); s.subset(f)
    buf = io.BytesIO(); f.flavor = 'woff2'; f.save(buf)
    faces += f"@font-face{{font-family:'CKMono';font-weight:{weight};src:url(data:font/woff2;base64,{base64.b64encode(buf.getvalue()).decode()}) format('woff2');}}"

style = faces + """
text{font-family:'CKMono','JetBrains Mono','Fira Code',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:15px}
.v{fill:#E2E8F0}
.dim{fill:#64748B}
.k{fill:#67E8F9;font-weight:700;font-size:13px}
.sub{fill:#94A3B8;font-size:12px}
.lbl{fill:#67E8F9;font-size:12px;font-weight:700;letter-spacing:2px}
.num{fill:#E2E8F0;font-size:26px;font-weight:700}
.flow{fill:none;stroke-width:1.8;stroke-dasharray:4 4;animation:flow 1s linear infinite}
@keyframes flow{to{stroke-dashoffset:-8}}
.in{animation:in .5s ease-out both}
@keyframes in{from{opacity:0;transform:translateX(-8px)}}
.grow{transform-box:fill-box;transform-origin:left;animation:grow .9s cubic-bezier(.2,.8,.2,1) both}
@keyframes grow{from{transform:scaleX(0)}}
.px{transform-box:fill-box;transform-origin:center;animation:pop .45s cubic-bezier(.3,1.6,.5,1) both}
@keyframes pop{from{opacity:0;transform:scale(.2)}}
.cur{animation:blink 1.1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}"""

defs = """<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0E1424"/><stop offset="1" stop-color="#070A13"/></linearGradient>
  <linearGradient id="art" gradientUnits="userSpaceOnUse" x1="168" y1="0" x2="358" y2="0" spreadMethod="reflect">
    <stop offset="0" stop-color="#A78BFA"/><stop offset=".5" stop-color="#22D3EE"/><stop offset="1" stop-color="#34D399"/>
    <animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="380 0" dur="6s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="hl" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#67E8F9" stop-opacity=".5"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <clipPath id="typed"><rect x="72" y="60" width="0" height="22">
    <animate attributeName="width" values="0;9;18;27;36;45;54" begin=".35s" dur=".4s" calcMode="discrete" fill="freeze"/>
  </rect></clipPath>
  <clipPath id="win"><rect x="1" y="1" width="858" height="614" rx="16"/></clipPath>
</defs>"""

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
       f'aria-label="How I build with AI: plan, delegate to subagents, build, verify — Claude Code usage stats">\n'
       f'<style>{style}</style>\n{defs}\n{body}\n</svg>\n')
open(OUT, 'w').write(svg)
print(OUT, len(svg), 'bytes'); print(stats); print(top); print('weeks', weeks, 'peak', peak)
