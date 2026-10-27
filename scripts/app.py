"""Local Hebrew TTS studio: listen to the benchmark, inspect homographs, try your own text, keep recordings.

Runs fully offline:  .venv/bin/python scripts/app.py   ->  http://localhost:8800
"""
import json, re, sys, time, uuid
from collections import defaultdict
from pathlib import Path

import jiwer
import soundfile as sf
from flask import Flask, abort, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines_local as eng
from score import norm

ROOT = Path(__file__).resolve().parent.parent
SAMPLES, TMP, SAVED = ROOT / "samples", ROOT / "studio" / "tmp", ROOT / "studio" / "saved"
for d in (TMP, SAVED):
    d.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=str(ROOT / "web"), static_url_path="")

# order shown on the listening page: local engines first, cloud references last
LISTEN_ORDER = ["f5_he_norm", "kokoro_he_norm", "phonikud_shaul_norm", "phonikud_michael_norm",
                "phonikud_default_norm", "mms_heb_norm", "mac_carmit", "chatterbox_mtl", "phonikud_michael",
                "edge_hila", "edge_avri", "google_gtts"]


def catalog():
    notes = json.loads((ROOT / "results/notes.json").read_text())
    texts = json.loads((ROOT / "texts.json").read_text())
    refs = {t["id"]: t["text"] for t in texts}
    wer = defaultdict(dict)
    for f in sorted((ROOT / "results").glob("asr*.jsonl")):
        for line in f.read_text().splitlines():
            r = json.loads(line)
            wer[r["engine"]][r["id"]] = round(jiwer.wer(norm(refs[r["id"]]), norm(r["hyp"])), 3)
    timing = defaultdict(dict)
    for line in (ROOT / "results/timing.jsonl").read_text().splitlines():
        r = json.loads(line)
        if not r.get("error"):
            timing[r["engine"]][r["id"]] = r
    engines = []
    for e in LISTEN_ORDER:
        if not (SAMPLES / e).exists():
            continue
        m = dict(notes["engines"].get(e, {"name": e}), key=e)
        ws = [wer[e][t["id"]] for t in texts if t["id"] in wer[e]]
        trs = [timing[e][t["id"]] for t in texts if t["id"] in timing[e]]
        m["accuracy"] = round(100 * (1 - sum(ws) / len(ws))) if ws else None
        m["rtf"] = round(sum(r["gen_s"] for r in trs) / sum(r["audio_s"] for r in trs), 3) if trs else None
        lat = timing[e].get("00_latency", {})
        m["latency"] = lat.get("first_audio_s") or lat.get("gen_s")
        m["n_texts"] = len(ws)
        engines.append(m)
    hg = json.loads((ROOT / "results/homographs.json").read_text())
    hg_engines = [e for e in ["f5_he_norm", "kokoro_he_norm", "phonikud_shaul_norm", "phonikud_michael_norm"]
                  if (SAMPLES / e / "hg_01.wav").exists()]
    return dict(texts=texts, engines=engines, wer=wer, notes=notes.get("sample_notes", {}),
                homographs=hg, hg_engines=hg_engines,
                live=[dict(key=k, name=v["name"], note=v["note"]) for k, v in eng.ENGINES.items()])


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/catalog")
def api_catalog():
    return jsonify(catalog())


@app.get("/samples/<engine>/<name>")
def sample(engine, name):
    return send_from_directory(SAMPLES / engine, name)


@app.post("/api/prepare")
def api_prepare():
    """Text -> normalized text -> nikud, so the user can review/correct before speaking."""
    b = request.get_json()
    text = (b.get("text") or "").strip()[:2000]
    if not text:
        return jsonify(error="כתבו טקסט קודם"), 400
    normalized = eng.normalize(text) if b.get("normalize", True) else text
    return jsonify(normalized=normalized, vocalized=eng.vocalize(normalized))


@app.post("/api/speak")
def api_speak():
    b = request.get_json()
    vtext = (b.get("vocalized") or "").strip()[:3000]
    engine = b.get("engine")
    if not vtext or engine not in eng.ENGINES:
        return jsonify(error="חסר טקסט או מנוע"), 400
    speed = min(1.5, max(0.6, float(b.get("speed", 1.0))))
    t0 = time.perf_counter()
    wav, sr = eng.speak(vtext, engine, speed)
    gen = time.perf_counter() - t0
    fid = f"{uuid.uuid4().hex[:10]}.wav"
    sf.write(TMP / fid, wav, sr)
    return jsonify(file=fid, url=f"/tmp/{fid}", gen_s=round(gen, 2), audio_s=round(len(wav) / sr, 2))


@app.get("/tmp/<name>")
def tmp_file(name):
    return send_from_directory(TMP, name)


def _index():
    p = SAVED / "index.json"
    return json.loads(p.read_text()) if p.exists() else []


@app.get("/api/saved")
def api_saved():
    return jsonify(_index())


@app.post("/api/save")
def api_save():
    b = request.get_json()
    src = TMP / Path(b.get("file", "")).name
    if not src.exists():
        return jsonify(error="ההקלטה כבר לא קיימת, הקריאו שוב"), 404
    title = (b.get("title") or "").strip()[:80] or (b.get("text") or "")[:40]
    slug = re.sub(r"[^\w֐-׿-]+", "_", title)[:40].strip("_") or "recording"
    name = f"{time.strftime('%Y%m%d-%H%M%S')}_{slug}.wav"
    (SAVED / name).write_bytes(src.read_bytes())
    items = _index()
    items.insert(0, dict(file=name, title=title, text=b.get("text", ""), vocalized=b.get("vocalized", ""),
                         engine=b.get("engine"), speed=b.get("speed"), saved_at=time.strftime("%Y-%m-%d %H:%M")))
    (SAVED / "index.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
    return jsonify(ok=True, item=items[0])


@app.delete("/api/saved/<name>")
def api_delete(name):
    items = [i for i in _index() if i["file"] != name]
    (SAVED / "index.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
    (SAVED / Path(name).name).unlink(missing_ok=True)
    return jsonify(ok=True)


@app.get("/saved/<name>")
def saved_file(name):
    if not (SAVED / name).exists():
        abort(404)
    return send_from_directory(SAVED, name)


if __name__ == "__main__":
    import os
    # HOST=0.0.0.0 exposes the studio to the internal network (e.g. on the GPU server)
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8800)), debug=False, threaded=True)
