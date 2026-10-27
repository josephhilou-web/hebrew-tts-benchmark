"""Check which reading Phonikud picks for each homograph, and render audio for listening.

Writes results/homographs.json and samples/<engine>/hg_XX.wav for the local engines.
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synth
from phonikud import phonemize

ROOT = Path(__file__).resolve().parent.parent
ITEMS = json.loads((ROOT / "homographs.json").read_text())
LISTEN_ENGINES = ["f5_he_norm", "kokoro_he_norm", "phonikud_shaul_norm", "phonikud_michael_norm"]


def simplify(ph):
    return re.sub(r"[ˈʔ.,:;!?]", "", ph)


def main():
    from phonikud_onnx import Phonikud
    nik = Phonikud(str(ROOT / "models" / "phonikud-1.0.int8.onnx"))
    out = []
    for i, it in enumerate(ITEMS, 1):
        diac = nik.add_diacritics(it["text"])
        words, dwords = it["text"].split(), diac.split()
        idx = next(k for k, w in enumerate(words) if w.strip(".,") == it["target"])
        got_diac = dwords[idx].replace("|", "")
        got = simplify(phonemize(dwords[idx]))
        ok = got == simplify(it["expect"])
        out.append(dict(n=i, **it, got=got, got_diac=got_diac, ok=ok, diac=diac.replace("|", "")))
        print(f"{i:2d} {'✓' if ok else '✗'} {it['target']:6s} expect {it['expect']:10s} got {got:10s} {got_diac}")
        for e in LISTEN_ENGINES:
            d = ROOT / "samples" / e
            d.mkdir(parents=True, exist_ok=True)
            synth.ENGINES[e](it["text"], d / f"hg_{i:02d}.wav")
    (ROOT / "results" / "homographs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\nPhonikud correct: {sum(o['ok'] for o in out)}/{len(out)}")


if __name__ == "__main__":
    main()
