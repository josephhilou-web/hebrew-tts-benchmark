"""Build report/index.html (fully offline: system fonts, local mp3 files)."""
import html, json, math, subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REP = ROOT / "report"
TEXTS = json.loads((ROOT / "texts.json").read_text())
timing = [json.loads(l) for l in (ROOT / "results/timing.jsonl").read_text().splitlines()]
import sys, jiwer
sys.path.insert(0, str(ROOT / "scripts"))
from score import norm
REFS = {t["id"]: t["text"] for t in TEXTS}
asr = [json.loads(l) for f in sorted((ROOT / "results").glob("asr*.jsonl")) for l in f.read_text().splitlines()]
for r in asr:  # recompute with the current normalizer
    a, b = norm(REFS[r["id"]]), norm(r["hyp"])
    r["wer"], r["cer"] = jiwer.wer(a, b), jiwer.cer(a, b)
NOTES = json.loads((ROOT / "results/notes.json").read_text())

ENGINES = NOTES["engines"]  # ordered dict: key -> {name, offline, license, verdict, ...}

# ---------- metrics ----------
by = defaultdict(dict)
for r in asr:
    by[r["engine"]][r["id"]] = r
tim = defaultdict(dict)
for r in timing:
    tim[r["engine"]][r["id"]] = r


def speed_score(rtf):
    # RTF 0.03 -> 100, 1.0 -> 0, log scale
    return max(0, min(100, 100 * (math.log10(1 / rtf)) / math.log10(1 / 0.03)))


stats = {}
for e in ENGINES:
    rows = [by[e][t["id"]] for t in TEXTS if t["id"] in by[e]]
    if not rows:
        continue
    wer = sum(r["wer"] for r in rows) / len(rows)
    cer = sum(r["cer"] for r in rows) / len(rows)
    trs = [tim[e][t["id"]] for t in TEXTS if t["id"] in tim[e]]
    rtf = sum(r["gen_s"] for r in trs) / sum(r["audio_s"] for r in trs)
    lat = tim[e].get("00_latency", {})
    acc = max(0.0, 100 * (1 - wer))
    spd = speed_score(rtf)
    stats[e] = dict(wer=wer, cer=cer, rtf=rtf, lat=lat.get("first_audio_s") or lat.get("gen_s"),
                    acc=acc, spd=spd, total=0.75 * acc + 0.25 * spd)

(ROOT / "results/summary.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False))

# ---------- audio: wav -> mp3 for the page ----------
(REP / "audio").mkdir(parents=True, exist_ok=True)
for e in ENGINES:
    for t in TEXTS + [{"id": "00_latency"}]:
        src = ROOT / "samples" / e / f"{t['id']}.wav"
        dst = REP / "audio" / e / f"{t['id']}.mp3"
        if src.exists() and (not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime):
            dst.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-b:a", "64k", str(dst)], check=True)

# ---------- html ----------
esc = html.escape


def chip(ok, yes, no):
    return f'<span class="chip {"good" if ok else "bad"}">{yes if ok else no}</span>'


order = sorted(stats, key=lambda e: (not ENGINES[e]["offline"], -stats[e]["total"]))

rows_html = []
for rank, e in enumerate(order, 1):
    s, m = stats[e], ENGINES[e]
    rows_html.append(f"""
<tr class="{'' if m['offline'] else 'cloud'}">
  <td class="eng"><b>{esc(m['name'])}</b><small>{esc(m['tech'])}</small></td>
  <td>{chip(m['offline'], 'אופליין', 'דורש אינטרנט')}</td>
  <td>{chip(m['commercial'], esc(m['license']), esc(m['license']))}</td>
  <td class="num">{s['acc']:.0f}<small>WER {s['wer']*100:.0f}%</small></td>
  <td class="num">{s['rtf']:.2f}<small>{s['lat']:.2f} שנ׳ למשפט קצר</small></td>
  <td class="num score">{s['total']:.0f}</td>
  <td class="verdict">{esc(m['verdict'])}</td>
</tr>""")

sections = []
for t in TEXTS:
    players = []
    for e in order:
        r = by[e].get(t["id"])
        if not r:
            continue
        note = NOTES.get("sample_notes", {}).get(f"{e}/{t['id']}", "")
        players.append(f"""
<div class="player {'' if ENGINES[e]['offline'] else 'cloud'}">
  <div class="phead"><b>{esc(ENGINES[e]['name'])}</b><span class="num">WER {r['wer']*100:.0f}%</span></div>
  <audio controls preload="none" src="audio/{e}/{t['id']}.mp3"></audio>
  {f'<p class="note">{esc(note)}</p>' if note else ''}
  <details><summary>מה המודל "אמר" (תמלול חוזר)</summary><p class="hyp">{esc(r['hyp'])}</p></details>
</div>""")
    sections.append(f"""
<section class="test" id="{t['id']}">
  <h3>{esc(t['title'])}</h3>
  <blockquote>{esc(t['text'])}</blockquote>
  <div class="players">{''.join(players)}</div>
</section>""")

page = f"""<!doctype html>
<html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>מבחן TTS עברית אופליין</title>
<style>
/* Layout: one reading column; scoreboard table up top, then one block per test text with players in a grid. */
:root {{
  --bg: #f6f7f9; --surface: #ffffff; --fg: #17202b; --muted: #5b6675; --line: #dde2e8;
  --accent: #1d5fd0; --good: #18794e; --good-bg: #e3f4ea; --bad: #b4232f; --bad-bg: #fbe7e8;
  --font: "SF Hebrew", "Arial Hebrew", "Segoe UI", Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #11161d; --surface: #19202a; --fg: #e6ebf1; --muted: #9aa6b4; --line: #2b3542;
  --accent: #7fa8ff; --good: #5fd39a; --good-bg: #133326; --bad: #ff8a8f; --bad-bg: #3a1a1d; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #11161d; --surface: #19202a; --fg: #e6ebf1; --muted: #9aa6b4; --line: #2b3542;
  --accent: #7fa8ff; --good: #5fd39a; --good-bg: #133326; --bad: #ff8a8f; --bad-bg: #3a1a1d; color-scheme: dark; }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--font); font-size: 16px; line-height: 1.6; margin: 0; }}
main {{ max-width: 1100px; margin: 0 auto; padding-block: 32px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 40px; }}
h1 {{ font-size: 2rem; margin: 0; text-wrap: balance; }}
h2 {{ font-size: 1.35rem; margin: 0 0 12px; }}
h3 {{ font-size: 1.1rem; margin: 0; }}
p {{ margin: 0; max-width: 70ch; }}
.lede {{ color: var(--muted); }}
.reco {{ background: var(--surface); border: 1px solid var(--line); border-inline-start: 4px solid var(--good);
  border-radius: 8px; padding: 20px; display: grid; gap: 10px; }}
.reco ul {{ margin: 0; padding-inline-start: 20px; display: grid; gap: 6px; }}
.tablewrap {{ overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; }}
table {{ border-collapse: collapse; width: 100%; min-width: 860px; }}
th, td {{ text-align: start; padding: 12px; border-bottom: 1px solid var(--line); vertical-align: top; }}
th {{ font-size: .8rem; color: var(--muted); font-weight: 600; letter-spacing: .02em; }}
tr:last-child td {{ border-bottom: 0; }}
tr.cloud td {{ opacity: .62; }}
td small {{ display: block; color: var(--muted); font-size: .78rem; }}
.num {{ font-variant-numeric: tabular-nums; font-family: var(--mono); }}
.score {{ font-size: 1.4rem; font-weight: 700; color: var(--accent); }}
.verdict {{ max-width: 34ch; font-size: .9rem; }}
.chip {{ display: inline-block; font-size: .78rem; padding: 2px 8px; border-radius: 99px; white-space: nowrap; }}
.chip.good {{ background: var(--good-bg); color: var(--good); }}
.chip.bad {{ background: var(--bad-bg); color: var(--bad); }}
.test {{ display: grid; gap: 12px; }}
blockquote {{ margin: 0; padding: 14px 16px; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; }}
.players {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }}
.player {{ min-width: 0; display: grid; gap: 8px; padding: 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }}
.player.cloud {{ border-style: dashed; }}
.phead {{ display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; }}
.phead .num {{ color: var(--muted); font-size: .85rem; }}
audio {{ width: 100%; }}
.note {{ font-size: .88rem; color: var(--bad); }}
details summary {{ cursor: pointer; color: var(--muted); font-size: .85rem; }}
.hyp {{ font-size: .9rem; padding-top: 6px; }}
.method {{ color: var(--muted); font-size: .92rem; display: grid; gap: 8px; }}
a {{ color: var(--accent); }}
:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
</style></head><body><main>
<header style="display:grid;gap:8px">
  <h1>מבחן TTS עברית לסביבה סגורה</h1>
  <p class="lede">{esc(NOTES['lede'])}</p>
</header>
<section class="reco">{NOTES['recommendation_html']}</section>
<section>
  <h2>טבלת ציונים</h2>
  <div class="tablewrap"><table>
    <thead><tr><th>מנוע</th><th>אינטרנט</th><th>רישיון</th><th>דיוק (0–100)</th><th>מהירות (RTF)</th><th>ציון</th><th>שורה תחתונה</th></tr></thead>
    <tbody>{''.join(rows_html)}</tbody>
  </table></div>
</section>
<section style="display:grid;gap:32px">
  <h2>הדגימות: 8 טקסטים קשים</h2>
  {''.join(sections)}
</section>
<section class="method"><h2>איך נמדד</h2>{NOTES['method_html']}</section>
</main></body></html>"""
(REP / "index.html").write_text(page)
print("wrote", REP / "index.html")
for e in order:
    s = stats[e]
    print(f"{e:18s} acc {s['acc']:5.1f}  wer {s['wer']:.3f} cer {s['cer']:.3f}  rtf {s['rtf']:.3f}  lat {s['lat']}  total {s['total']:.1f}")
