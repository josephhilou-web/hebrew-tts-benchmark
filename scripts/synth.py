"""Synthesize every test text with every engine; record timing.

Usage: python scripts/synth.py engine [engine ...]
Writes samples/<engine>/<text_id>.wav and appends to results/timing.jsonl
"""
import asyncio, json, os, subprocess, sys, tempfile, time
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
TEXTS = json.loads((ROOT / "texts.json").read_text())
LATENCY_TEXT = "שלום, איך אפשר לעזור לך היום?"
MODELS = ROOT / "models"


def ffmpeg_to_wav(src, dst):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "24000", str(dst)], check=True)


# ---------- engines: each returns (first_audio_seconds or None) and writes dst wav ----------

def mac_say(text, dst, voice="Carmit"):
    with tempfile.NamedTemporaryFile(suffix=".aiff") as tmp:
        subprocess.run(["say", "-v", voice, "-o", tmp.name, text], check=True)
        ffmpeg_to_wav(tmp.name, dst)


def gtts(text, dst):
    from gtts import gTTS
    with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
        gTTS(text, lang="iw").save(tmp.name)
        ffmpeg_to_wav(tmp.name, dst)


def make_edge(voice):
    def run(text, dst):
        import edge_tts

        async def go():
            t0 = time.perf_counter()
            first = None
            buf = bytearray()
            async for chunk in edge_tts.Communicate(text, voice).stream():
                if chunk["type"] == "audio":
                    if first is None:
                        first = time.perf_counter() - t0
                    buf += chunk["data"]
            return first, bytes(buf)

        first, data = asyncio.run(go())
        with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
            Path(tmp.name).write_bytes(data)
            ffmpeg_to_wav(tmp.name, dst)
        return first
    return run


_phonikud = {}
def make_phonikud(voice_file):
    def run(text, dst):
        from phonikud_onnx import Phonikud
        from phonikud import phonemize
        from piper_onnx import Piper
        if "nikud" not in _phonikud:
            _phonikud["nikud"] = Phonikud(str(MODELS / "phonikud-1.0.int8.onnx"))
        if voice_file not in _phonikud:
            _phonikud[voice_file] = Piper(str(MODELS / voice_file), str(MODELS / "model.config.json"))
        diac = _phonikud["nikud"].add_diacritics(text)
        ph = phonemize(diac)
        samples, sr = _phonikud[voice_file].create(ph, is_phonemes=True, length_scale=1.20, noise_scale=0.640, noise_w=1.0)
        samples = np.clip(samples * 2, -1, 1)
        sf.write(dst, samples, sr)
        Path(str(dst) + ".nikud.txt").write_text(diac + "\n\n" + ph)
    return run


_mms = {}
def mms(text, dst):
    import torch
    from transformers import VitsModel, AutoTokenizer
    if not _mms:
        _mms["m"] = VitsModel.from_pretrained("facebook/mms-tts-heb")
        _mms["t"] = AutoTokenizer.from_pretrained("facebook/mms-tts-heb")
    inputs = _mms["t"](text, return_tensors="pt")
    with torch.no_grad():
        wav = _mms["m"](**inputs).waveform[0].numpy()
    sf.write(dst, wav, _mms["m"].config.sampling_rate)


_cb = {}
def chatterbox(text, dst):
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    if not _cb:
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        _cb["m"] = ChatterboxMultilingualTTS.from_pretrained(device=dev)
    wav = _cb["m"].generate(text, language_id="he")
    sf.write(dst, wav.squeeze(0).cpu().numpy(), _cb["m"].sr)


_kok = {}
def kokoro_he(text, dst):
    from phonikud_onnx import Phonikud
    from phonikud import phonemize
    from kokoro_onnx import Kokoro
    if not _kok:
        _kok["nik"] = Phonikud(str(MODELS / "phonikud-1.0.int8.onnx"))
        _kok["k"] = Kokoro(str(MODELS / "kokoro_he/kokoro.onnx"), str(MODELS / "kokoro_he/voices-hebrew.bin"),
                           vocab_config=str(MODELS / "kokoro_he/config.json"))
    ph = phonemize(_kok["nik"].add_diacritics(text))
    samples, sr = _kok["k"].create(ph, voice="he_shaul", is_phonemes=True)
    sf.write(dst, samples, sr)


def f5_he(text, dst):
    import f5_engine
    wav, sr = f5_engine.synth(text)
    sf.write(dst, wav, sr)


ENGINES = {
    "kokoro_he": kokoro_he,
    "f5_he": f5_he,
    "mac_carmit": mac_say,
    "google_gtts": gtts,
    "edge_hila": make_edge("he-IL-HilaNeural"),
    "edge_avri": make_edge("he-IL-AvriNeural"),
    "phonikud_default": make_phonikud("model.onnx"),
    "phonikud_shaul": make_phonikud("shaul.onnx"),
    "phonikud_michael": make_phonikud("michael.onnx"),
    "mms_heb": mms,
    "chatterbox_mtl": chatterbox,
}


def with_normalizer(fn):
    from he_normalize import normalize
    return lambda text, dst: fn(normalize(text), dst)


for _k in ["phonikud_default", "phonikud_shaul", "phonikud_michael", "mms_heb", "kokoro_he", "f5_he"]:
    ENGINES[_k + "_norm"] = with_normalizer(ENGINES[_k])


def run_one(engine, tid, text, log):
    out_dir = Path(os.environ.get("SAMPLES_DIR", ROOT / "samples")) / engine
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"{tid}.wav"
    t0 = time.perf_counter()
    try:
        first = ENGINES[engine](text, dst)
        err = None
    except Exception as e:  # keep going; record failure
        first, err = None, f"{type(e).__name__}: {e}"
    total = time.perf_counter() - t0
    dur = sf.info(dst).duration if dst.exists() and err is None else 0.0
    rec = dict(engine=engine, id=tid, gen_s=round(total, 3), audio_s=round(dur, 3),
               rtf=round(total / dur, 3) if dur else None,
               first_audio_s=round(first, 3) if first else None, error=err)
    log.write(json.dumps(rec, ensure_ascii=False) + "\n"); log.flush()
    print(rec, flush=True)


def main():
    (ROOT / "results").mkdir(exist_ok=True)
    with open(ROOT / "results" / "timing.jsonl", "a") as log:
        for engine in sys.argv[1:]:
            # warm-up (model load) is excluded from the timings below
            run_one(engine, "00_warmup", "בדיקה", open(os.devnull, "w"))
            run_one(engine, "00_latency", LATENCY_TEXT, log)
            only = os.environ.get("TEXT_IDS", "").split(",")
            for t in TEXTS:
                if only == [""] or t["id"] in only:
                    run_one(engine, t["id"], t["text"], log)


if __name__ == "__main__":
    main()
