"""Transcribe every sample with ivrit.ai Hebrew Whisper and compute WER/CER vs. the source text.

Usage: python scripts/score.py [engine ...]   (default: all engines under samples/)
Writes results/asr.jsonl (one line per sample; existing engine rows are replaced).
"""
import json, os, re, subprocess, sys, unicodedata
from pathlib import Path

import jiwer
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
TEXTS = {t["id"]: t["text"] for t in json.loads((ROOT / "texts.json").read_text())}

try:
    from num2words import num2words
except ImportError:
    num2words = None


def norm(s: str) -> str:
    from he_normalize import normalize
    s = normalize(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not ("֑" <= c <= "ׇ"))  # strip nikud/cantillation
    s = s.replace("%", " אחוז ").replace("₪", " שקלים ")
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)  # 3,450,000 -> 3450000
    if num2words:
        def w(m):
            try:
                return " " + num2words(float(m.group()) if "." in m.group() else int(m.group()), lang="he") + " "
            except Exception:
                return m.group()
        s = re.sub(r"\d+(?:\.\d+)?", w, s)
    s = s.lower()
    s = re.sub(r"[\"'׳״`’‘“”]", "", s)  # geresh/gershayim/quotes
    s = re.sub(r"[^\w\s]", " ", s)       # punctuation, hyphens
    s = re.sub(r"\bאחוזים\b", "אחוז", s)
    s = re.sub(r"\bשקלים חדשים\b", "שקלים", s)
    s = re.sub(r"\bש\s?ח\b", "שקלים", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    from faster_whisper import WhisperModel
    engines = sys.argv[1:] or sorted(p.name for p in (ROOT / "samples").iterdir() if p.is_dir())
    model = WhisperModel("ivrit-ai/whisper-large-v3-turbo-ct2", device="cpu", compute_type="int8")
    out = ROOT / "results" / os.environ.get("ASR_OUT", "asr.jsonl")
    rows = [json.loads(l) for l in out.read_text().splitlines()] if out.exists() else []
    rows = [r for r in rows if r["engine"] not in engines]
    for eng in engines:
        for tid, ref in TEXTS.items():
            wav = ROOT / "samples" / eng / f"{tid}.wav"
            if not wav.exists():
                continue
            pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                 check=True, capture_output=True).stdout
            audio = np.frombuffer(pcm, dtype=np.float32)
            segs, _ = model.transcribe(audio, language="he", beam_size=5, vad_filter=False)
            hyp = " ".join(s.text.strip() for s in segs)
            r, h = norm(ref), norm(hyp)
            row = dict(engine=eng, id=tid, hyp=hyp,
                       wer=round(jiwer.wer(r, h), 4), cer=round(jiwer.cer(r, h), 4))
            rows.append(row)
            print(eng, tid, row["wer"], row["cer"], flush=True)
            out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


if __name__ == "__main__":
    main()
