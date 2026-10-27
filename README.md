# Hebrew TTS Benchmark · מבחן דיבור עברי

Offline Hebrew text-to-speech: a benchmark of 12 engines on hard Hebrew text, a Hebrew text normalizer, and a local web studio for listening, trying text and fixing nikud. Built for air-gapped environments (no internet at runtime).

השוואה של מנועי דיבור עברי (TTS) שרצים מקומית, בלי אינטרנט. הפרויקט כולל:
- **מנרמל טקסט עברי:** מספרים, תאריכים, שעות, טלפונים, ראשי תיבות ואנגלית הופכים למילים.
- **בדיקה של 34 מילים בעייתיות:** מילים שנכתבות זהה ונקראות שונה.
- **אתר מקומי:** האזנה, ניסוי טקסט חופשי, תיקון ניקוד ושמירת הקלטות.

## התוצאות

כל מנוע הקריא 8 טקסטים קשים ([texts.json](texts.json)):
- מספרים וכסף
- מילים זהות בכתיב
- ראשי תיבות ואנגלית
- שפה משפטית ורפואית
- טלפונים ושעות
- טקסט ספרותי

כל הקלטה תומללה בחזרה עם Whisper העברי של ivrit.ai והושוותה לטקסט המקורי. **דיוק** = 100 פחות שיעור שגיאות המילים (WER). **RTF** = זמן ההפקה חלקי אורך האודיו (נמוך = מהיר). נמדד על MacBook M1 Pro.

| מנוע | רץ מקומית | דיוק | משפט קצר | RTF | רישיון |
|---|---|---|---|---|---|
| **Kokoro עברית** + מנרמל | ✅ | **95** | 0.67 שנ׳ | 0.25 (CPU) | לא מסחרי |
| **F5-TTS עברית v2** + מנרמל | ✅ | **95** | ~20 שנ׳ | ~4.5 (Apple GPU) | Apache-2.0* |
| Phonikud + Piper · מיכאל + מנרמל | ✅ | 92 | 0.15 שנ׳ | 0.045 | לא מסחרי |
| Phonikud + Piper · ברירת מחדל + מנרמל | ✅ | 91 | 0.14 שנ׳ | 0.043 | לא מסחרי |
| Phonikud + Piper · שאול + מנרמל | ✅ | 89 | 0.11 שנ׳ | 0.054 | לא מסחרי |
| macOS Carmit | ✅ | 85 | 1.8 שנ׳ | 0.078 | macOS בלבד |
| Meta MMS-TTS + מנרמל | ✅ | 79 | 0.44 שנ׳ | 0.12 | CC-BY-NC 4.0 |
| Phonikud + Piper · מיכאל, **בלי** מנרמל | ✅ | 77 | 0.14 שנ׳ | 0.037 | לא מסחרי |
| Chatterbox Multilingual (3 טקסטים) | ✅ | 23 | 19 שנ׳ | ~8 | MIT |
| Google Translate TTS (ענן, להשוואה) | ❌ | 94 | 0.56 שנ׳ | 0.13 | לא רשמי |
| Microsoft Hila (ענן, להשוואה) | ❌ | 91 | 1.9 שנ׳ | 0.35 | Azure, בתשלום |
| Microsoft Avri (ענן, להשוואה) | ❌ | 90 | 2.3 שנ׳ | 0.28 | Azure, בתשלום |

\* F5-TTS Hebrew מסומן Apache-2.0, אבל אומן בין השאר על SASPEECH, שהוא לא מסחרי. לבדוק לפני שימוש מסחרי.

**מסקנות:**
- **Kokoro עברית** נותן את האיזון הכי טוב בין איכות למהירות, על מעבד רגיל.
- **F5-TTS** מדויק באותה מידה ומשכפל כל קול מהקלטה של 10 שניות, אבל צריך GPU של NVIDIA כדי להיות מהיר.
- **המנרמל העברי** מעלה את הדיוק של Phonikud מ־77 ל־92.
- **מילים בעייתיות:** בבדיקה של 34 משפטים ([homographs.json](homographs.json)), רכיב הניקוד (Phonikud) קרא נכון 28. כל המנועים המקומיים חולקים את הרכיב הזה, ולכן גם את הטעויות. הטעויות היו:
  - עָרֵב (ערבות)
  - הַלֹּוֶה
  - לִוָּה
  - הַסַּפָּר
  - חָלָק
  - הַיִּתְרָה

  באתר אפשר לתקן את הניקוד ידנית.

## המודלים שנבדקו

### רצים מקומית
| מודל | קישור |
|---|---|
| Kokoro Hebrew (ONNX) | https://huggingface.co/thewh1teagle/kokoro-hebrew-nc (מקור: https://huggingface.co/avris/kokoro-hebrew-saspeech) |
| F5-TTS Hebrew v2 | https://huggingface.co/Yzamari/f5tts-hebrew-v2 (בסיס: https://github.com/SWivid/F5-TTS), ‏vocoder: https://huggingface.co/charactr/vocos-mel-24khz |
| Phonikud: ניקוד אוטומטי ו־G2P | https://github.com/thewh1teagle/phonikud · https://huggingface.co/Phonikud/phonikud-onnx |
| Phonikud TTS: קולות Piper (שאול, מיכאל, ברירת מחדל) | https://huggingface.co/Phonikud/phonikud-tts-checkpoints |
| Meta MMS-TTS Hebrew | https://huggingface.co/facebook/mms-tts-heb |
| Chatterbox Multilingual | https://github.com/resemble-ai/chatterbox · https://huggingface.co/ResembleAI/chatterbox |
| macOS Carmit | הקול העברי המובנה של macOS (`say -v Carmit`) |

### ענן, להשוואה בלבד
| מודל | קישור |
|---|---|
| Microsoft Azure Neural TTS: he-IL-HilaNeural, he-IL-AvriNeural (נבדק דרך edge-tts) | https://github.com/rany2/edge-tts · https://learn.microsoft.com/azure/ai-services/speech-service/language-support |
| Google Translate TTS (דרך gTTS) | https://github.com/pndurette/gTTS |

### בדיקה (תמלול חוזר)
| מודל | קישור |
|---|---|
| ivrit.ai Whisper large-v3-turbo | https://huggingface.co/ivrit-ai/whisper-large-v3-turbo-ct2 |

### נמצאו אבל לא נבדקו
- ElevenLabs v3 (ענן בלבד)
- Cartesia Sonic: https://cartesia.ai/languages/hebrew. יש התקנה מקומית בחוזה ארגוני: https://docs.cartesia.ai/self-hosted/introduction
- Azure Speech בקונטיינר מנותק: https://learn.microsoft.com/azure/ai-services/containers/disconnected-containers
- Zonos-Hebrew: https://huggingface.co/notmax123/Zonos-Hebrew
- HebTTS: https://github.com/slp-rl/HebTTS

## הפעלה

```bash
uv venv --python 3.12 .venv
VIRTUAL_ENV=.venv uv pip install -r requirements-studio.txt   # להוספת F5: requirements-f5.txt
bash scripts/download_models.sh                               # Kokoro, Phonikud, קולות Piper (להוספת F5: --f5)
.venv/bin/python scripts/app.py                               # http://localhost:8800
```

הלשוניות "נסו בעצמכם" ו"ההקלטות שלי" עובדות מיד. ההקלטות של הבדיקה לא נמצאות בריפו. כדי לייצר אותן, מריצים:

```bash
.venv/bin/python scripts/synth.py kokoro_he_norm phonikud_shaul_norm   # ההקלטות
.venv/bin/python scripts/score.py kokoro_he_norm phonikud_shaul_norm   # הציונים
.venv/bin/python scripts/homographs.py                                 # המילים הבעייתיות
```

**F5-TTS:** משכפל קול מהקלטת ייחוס. שמים ב־`models/f5he/ref/`:
- קובץ `ref_57.wav`: 8–12 שניות של דיבור נקי
- קובץ `ref.json`: התמלול

**שרת NVIDIA (למשל H100) בלי אינטרנט:** ראו [SETUP_HE.md](SETUP_HE.md) ואת `scripts/prepare_h100_bundle.sh`. הסקריפט בונה תיקייה אחת עם הקוד, המודלים וכל חבילות Python ל־Linux, להעברה לרשת סגורה.

## מבנה

| קובץ | תפקיד |
|---|---|
| `scripts/he_normalize.py` | מנרמל טקסט עברי לפני TTS |
| `scripts/engines_local.py` | ממשק אחיד: מנרמל, ואז ניקוד, ואז דיבור (Kokoro, F5, Piper) |
| `scripts/app.py`, `web/index.html` | האתר המקומי |
| `scripts/synth.py`, `scripts/score.py` | הבדיקה: הפקה ומדידה |
| `scripts/homographs.py` | בדיקת המילים הבעייתיות |
| `results/` | תוצאות הבדיקה (תמלולים, זמנים, הערות) |

## רישיון
הקוד בריפו הזה ברישיון MIT. המודלים לא כלולים בריפו, ולכל אחד יש רישיון משלו (ראו את הטבלה). חלק מהם לא מסחריים.
