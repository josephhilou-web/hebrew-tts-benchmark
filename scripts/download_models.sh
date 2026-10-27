#!/usr/bin/env bash
# Download the local models into models/.  Add --f5 for F5-TTS Hebrew (+1.4 GB).
set -euo pipefail
cd "$(dirname "$0")/.."
HF="https://huggingface.co"
get() { mkdir -p "$(dirname "models/$2")"; [ -s "models/$2" ] || curl -fL --retry 3 -o "models/$2" "$HF/$1"; }

get Phonikud/phonikud-onnx/resolve/main/phonikud-1.0.int8.onnx          phonikud-1.0.int8.onnx
get thewh1teagle/kokoro-hebrew-nc/resolve/main/kokoro.onnx               kokoro_he/kokoro.onnx
get thewh1teagle/kokoro-hebrew-nc/resolve/main/voices-hebrew.bin         kokoro_he/voices-hebrew.bin
get thewh1teagle/kokoro-hebrew-nc/resolve/main/config.json               kokoro_he/config.json
get Phonikud/phonikud-tts-checkpoints/resolve/main/shaul.onnx            shaul.onnx
get Phonikud/phonikud-tts-checkpoints/resolve/main/michael.onnx          michael.onnx
get Phonikud/phonikud-tts-checkpoints/resolve/main/model.onnx            model.onnx
get Phonikud/phonikud-tts-checkpoints/resolve/main/model.config.json     model.config.json

if [ "${1:-}" = "--f5" ]; then
  get Yzamari/f5tts-hebrew-v2/resolve/main/model.safetensors             f5he/model.safetensors
  get Yzamari/f5tts-hebrew-v2/resolve/main/vocab.txt                     f5he/vocab.txt
  get charactr/vocos-mel-24khz/resolve/main/config.yaml                  vocos/config.yaml
  get charactr/vocos-mel-24khz/resolve/main/pytorch_model.bin            vocos/pytorch_model.bin
  [ -f models/f5he/ref/ref.json ] || echo "F5: add a reference voice in models/f5he/ref/ (ref_57.wav + ref.json, see README)"
fi
echo "Models ready in models/"
