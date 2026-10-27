"""Local Hebrew TTS engines with a shared front-end: normalize -> vocalize (nikud) -> speak.

Splitting vocalization out lets the user see and correct the nikud before synthesis,
which is how homograph mistakes (ספר / סַפָּר) get fixed.
"""
import threading
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
_lock = threading.Lock()
_c = {}


def _nik():
    if "nik" not in _c:
        from phonikud_onnx import Phonikud
        _c["nik"] = Phonikud(str(MODELS / "phonikud-1.0.int8.onnx"))
    return _c["nik"]


def normalize(text):
    from he_normalize import normalize as n
    return n(text)


def vocalize(text):
    return _nik().add_diacritics(text).replace("|", "")


def _piper(voice_file):
    def run(vtext, speed):
        from phonikud import phonemize
        from piper_onnx import Piper
        key = "piper:" + voice_file
        if key not in _c:
            _c[key] = Piper(str(MODELS / voice_file), str(MODELS / "model.config.json"))
        samples, sr = _c[key].create(phonemize(vtext), is_phonemes=True, length_scale=1.20 / speed,
                                     noise_scale=0.640, noise_w=1.0)
        return np.clip(samples * 2, -1, 1), sr
    return run


def _kokoro(vtext, speed):
    from phonikud import phonemize
    from kokoro_onnx import Kokoro
    if "kokoro" not in _c:
        _c["kokoro"] = Kokoro(str(MODELS / "kokoro_he/kokoro.onnx"), str(MODELS / "kokoro_he/voices-hebrew.bin"),
                              vocab_config=str(MODELS / "kokoro_he/config.json"))
    return _c["kokoro"].create(phonemize(vtext), voice="he_shaul", speed=speed, is_phonemes=True)


def _f5(vtext, speed):
    import f5_engine
    return f5_engine.synth(vtext, speed=speed, vocalized=True)


ENGINES = {
    "kokoro_he": dict(name="Kokoro עברית", note="מהיר, קול שאול", run=_kokoro),
    "f5_he": dict(name="F5-TTS עברית", note="איכותי, איטי, משכפל קול", run=_f5),
    "phonikud_shaul": dict(name="Phonikud · שאול", note="הכי מהיר", run=_piper("shaul.onnx")),
    "phonikud_michael": dict(name="Phonikud · מיכאל", note="הכי מהיר", run=_piper("michael.onnx")),
    "phonikud_default": dict(name="Phonikud · ברירת מחדל", note="הכי מהיר", run=_piper("model.onnx")),
}


def speak(vtext, engine, speed=1.0):
    with _lock:  # models are not thread-safe; one synthesis at a time
        return ENGINES[engine]["run"](vtext, speed)
