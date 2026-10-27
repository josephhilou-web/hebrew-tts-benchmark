#!/usr/bin/env bash
# Build an offline bundle for a Linux x86_64 server with an NVIDIA H100.
# Run on any machine WITH internet (macOS or Linux) that has curl, python3 and uv.
# Output: a folder you copy into the closed network as-is (~8 GB).
#
#   bash scripts/prepare_h100_bundle.sh [output_dir]
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$SRC/h100_bundle}"
HF="https://huggingface.co"
TORCH_INDEX="https://download.pytorch.org/whl/cu128"
PLAT=(--platform manylinux_2_28_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 --platform linux_x86_64 --platform any)

echo "==> code"
mkdir -p "$OUT"
for p in scripts web texts.json homographs.json results requirements-h100.txt SETUP_HE.md; do
  cp -R "$SRC/$p" "$OUT/"
done

echo "==> python packages (Linux x86_64, Python 3.12, CUDA 12.8)"
uv pip compile "$SRC/requirements-h100.txt" --python-version 3.12 --python-platform x86_64-manylinux_2_28 \
  --extra-index-url "$TORCH_INDEX" --index-strategy unsafe-best-match -q -o "$OUT/requirements-h100.lock"
python3 -m pip download --no-deps -r "$OUT/requirements-h100.lock" -d "$OUT/wheels" \
  "${PLAT[@]}" --python-version 3.12 --implementation cp --extra-index-url "$TORCH_INDEX" -q
# build tools for the few source-only, pure-Python packages (encodec, docopt, ...)
python3 -m pip download --no-deps setuptools wheel -d "$OUT/wheels" "${PLAT[@]}" --python-version 3.12 -q

echo "==> models"
get() { mkdir -p "$(dirname "$OUT/models/$2")"; [ -s "$OUT/models/$2" ] || curl -fL --retry 3 -o "$OUT/models/$2" "$HF/$1"; }
get Phonikud/phonikud-onnx/resolve/main/phonikud-1.0.int8.onnx          phonikud-1.0.int8.onnx
get thewh1teagle/kokoro-hebrew-nc/resolve/main/kokoro.onnx               kokoro_he/kokoro.onnx
get thewh1teagle/kokoro-hebrew-nc/resolve/main/voices-hebrew.bin         kokoro_he/voices-hebrew.bin
get thewh1teagle/kokoro-hebrew-nc/resolve/main/config.json               kokoro_he/config.json
get Phonikud/phonikud-tts-checkpoints/resolve/main/shaul.onnx            shaul.onnx
get Phonikud/phonikud-tts-checkpoints/resolve/main/michael.onnx          michael.onnx
get Phonikud/phonikud-tts-checkpoints/resolve/main/model.onnx            model.onnx
get Phonikud/phonikud-tts-checkpoints/resolve/main/model.config.json     model.config.json
get Yzamari/f5tts-hebrew-v2/resolve/main/model.safetensors               f5he/model.safetensors
get Yzamari/f5tts-hebrew-v2/resolve/main/vocab.txt                       f5he/vocab.txt
get charactr/vocos-mel-24khz/resolve/main/config.yaml                    vocos/config.yaml
get charactr/vocos-mel-24khz/resolve/main/pytorch_model.bin              vocos/pytorch_model.bin
# F5 reference voice (replace with a recording your organization owns before production)
mkdir -p "$OUT/models/f5he/ref"
if [ -f "$SRC/models/f5he/ref/ref.json" ]; then cp "$SRC"/models/f5he/ref/{ref_57.wav,ref.json} "$OUT/models/f5he/ref/"
else echo "NOTE: no F5 reference voice found; put ref_57.wav + ref.json in models/f5he/ref/ before using F5"; fi

cat > "$OUT/install.sh" <<'EOS'
#!/usr/bin/env bash
# Run inside the closed network on the H100 server.
set -euo pipefail
cd "$(dirname "$0")"
python3.12 -m venv .venv
.venv/bin/pip install --no-index --find-links wheels -r requirements-h100.lock
.venv/bin/python -c "import onnxruntime as o, torch; print('ONNX providers:', o.get_available_providers()); print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
echo "Installed. Start with:  HOST=0.0.0.0 HF_HUB_OFFLINE=1 .venv/bin/python scripts/app.py"
EOS
chmod +x "$OUT/install.sh"

du -sh "$OUT" "$OUT/wheels" "$OUT/models"
echo "Done. Copy $OUT into the closed network and run ./install.sh there."
