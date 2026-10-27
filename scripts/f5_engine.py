"""F5-TTS Hebrew v2 (Yzamari/f5tts-hebrew-v2) runner: Phonikud-vocalized text in, 24 kHz audio out.

The model was trained on Phonikud-diacritized text (with stress marks), so both the
reference transcript and the target text go through Phonikud first.
"""
import json, os
from pathlib import Path

import numpy as np
import torch
from safetensors.torch import load_file

ROOT = Path(__file__).resolve().parent.parent
MD = ROOT / "models" / "f5he"
_s = {}


def _load():
    if _s:
        return _s
    from f5_tts.model import CFM, DiT
    from f5_tts.model.utils import get_tokenizer
    from f5_tts.infer.utils_infer import load_vocoder
    from phonikud_onnx import Phonikud

    dev = os.environ.get("F5_DEVICE") or ("cuda" if torch.cuda.is_available()
                                          else "mps" if torch.backends.mps.is_available() else "cpu")
    vocab_map, vocab_size = get_tokenizer(str(MD / "vocab.txt"), "custom")
    model = CFM(
        transformer=DiT(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4,
                        text_num_embeds=vocab_size, mel_dim=100),
        mel_spec_kwargs=dict(n_fft=1024, hop_length=256, win_length=1024, n_mel_channels=100,
                             target_sample_rate=24000, mel_spec_type="vocos"),
        odeint_kwargs=dict(method="euler"),
        vocab_char_map=vocab_map,
    )
    model.load_state_dict(load_file(str(MD / "model.safetensors")))
    _s.update(model=model.to(dev).eval(), vocoder=load_vocoder("vocos", is_local=(MD.parent / "vocos").exists(),
                                                                  local_path=str(MD.parent / "vocos"), device=dev), dev=dev,
              nik=Phonikud(str(ROOT / "models" / "phonikud-1.0.int8.onnx")))
    return _s


def vocalize(text):
    return _load()["nik"].add_diacritics(text).replace("|", "")


def synth(text, ref_wav=None, ref_text=None, nfe_step=32, speed=1.0, vocalized=False):
    """Return (samples float32, 24000). vocalized=True means `text` already carries nikud."""
    from f5_tts.infer.utils_infer import infer_process
    s = _load()
    if ref_wav is None:
        meta = json.loads((MD / "ref" / "ref.json").read_text())
        ref_wav = str(MD / "ref" / "ref_57.wav")
        ref_text = meta[1]["text"] + " " + meta[2]["text"]
    import re
    vtext = text if vocalized else vocalize(text)
    # one sentence per call: long batches trip a Metal (MPS) driver assertion on Apple GPUs
    parts = []
    for sent in re.split(r"(?<=[.!?:])\s+", vtext):
        # long sentences are split again at commas, keeping chunks near 100 characters
        chunk = ""
        for c in re.split(r"(?<=,)\s+", sent):
            if chunk and len(chunk) + len(c) > 100:
                parts.append(chunk); chunk = c
            else:
                chunk = (chunk + " " + c).strip()
        if chunk.strip():
            parts.append(chunk.strip())
    vref = vocalize(ref_text) + " "
    pieces, sr = [], 24000
    for p in parts:
        wav, sr, _ = infer_process(str(ref_wav), vref, p, s["model"], s["vocoder"],
                                   mel_spec_type="vocos", nfe_step=nfe_step, speed=speed, device=s["dev"],
                                   show_info=lambda *a: None, progress=None)
        pieces += [np.asarray(wav, dtype=np.float32), np.zeros(int(0.18 * sr), dtype=np.float32)]
    return np.concatenate(pieces[:-1]) if pieces else np.zeros(0, dtype=np.float32), sr
