"""Hebrew text normalizer for TTS front-ends (offline, rule + glossary based).

Turns digits, symbols, acronyms and Latin words into speakable Hebrew words so a
phoneme-based TTS (Phonikud/Piper, MMS) never sees characters it cannot read.
Extend ACRONYMS / LATIN with your organization's own terms.
"""
import re
from num2words import num2words

MONTHS = "ינואר|פברואר|מרץ|מרס|אפריל|מאי|יוני|יולי|אוגוסט|ספטמבר|אוקטובר|נובמבר|דצמבר"
# nouns that take a masculine number ("חמישה ימים")
MASC_NOUNS = ("ימים", "חודשים", "חדרים", "שקלים", "אחוזים", "מיליגרם", "גרם", "קילוגרם", "מטרים",
              "קילומטר", "דקות_x", "ש\"ח", "₪", "מ\"ג", "ק\"ג", "ק\"מ", "ס\"מ", "אחוז", "%")

ACRONYMS = {
    'ד"ר': "דוקטור", 'עו"ד': "עורך דין", 'יו"ר': "יושב ראש", 'מנכ"ל': "מנכל", 'מנכ"לית': "מנכלית",
    'סמנכ"ל': "סמנכל", 'צה"ל': "צהל", 'ארה"ב': "ארצות הברית", 'בע"מ': "בערבון מוגבל", 'ת"א': "תל אביב",
    'מ"ג': "מיליגרם", 'ק"ג': "קילוגרם", 'ק"מ': "קילומטר", 'ס"מ': "סנטימטר", 'מ"ל': "מיליליטר",
    'ש"ח': "שקלים", 'מע"מ': "מעמ", 'וכו\'': "וכולי", 'בי"ח': "בית חולים", 'ביה"ס': "בית הספר",
    'רח\'': "רחוב", 'מס\'': "מספר", 'ע"י': "על ידי", 'כ"א': "כל אחד", 'ח"כ': "חבר כנסת",
}
DAYS = {"א": "ראשון", "ב": "שני", "ג": "שלישי", "ד": "רביעי", "ה": "חמישי", "ו": "שישי", "ש": "שבת"}

# glossary for Latin words; unknown ALL-CAPS words are spelled out, other unknown words transliterated
LATIN = {
    "microsoft": "מייקרוסופט", "google": "גוגל", "apple": "אפל", "amazon": "אמזון", "facebook": "פייסבוק",
    "dashboard": "דשבורד", "email": "אימייל", "mail": "מייל", "cloud": "קלאוד", "server": "סרבר",
    "info": "אינפו", "example": "אקזמפל", "www": "דאבליו דאבליו דאבליו", "com": "קום", "co": "קו", "il": "איל",
    "gmail": "ג'ימייל", "zoom": "זום", "excel": "אקסל", "word": "וורד", "office": "אופיס",
}
LETTERS = {c: n for c, n in zip("abcdefghijklmnopqrstuvwxyz",
           ["איי", "בי", "סי", "די", "אי", "אף", "ג'י", "אייץ'", "איי", "ג'יי", "קיי", "אל", "אם", "אן", "או",
            "פי", "קיו", "אר", "אס", "טי", "יו", "וי", "דאבליו", "אקס", "וויי", "זי"])}
TRANSLIT = [("sh", "ש"), ("ch", "צ'"), ("th", "ת'"), ("ph", "פ"), ("oo", "ו"), ("ee", "י"), ("a", "א"), ("b", "ב"),
            ("c", "ק"), ("d", "ד"), ("e", "ה"), ("f", "פ"), ("g", "ג"), ("h", "ה"), ("i", "י"), ("j", "ג'"), ("k", "ק"),
            ("l", "ל"), ("m", "מ"), ("n", "נ"), ("o", "ו"), ("p", "פ"), ("q", "ק"), ("r", "ר"), ("s", "ס"), ("t", "ט"),
            ("u", "ו"), ("v", "ו"), ("w", "ו"), ("x", "קס"), ("y", "י"), ("z", "ז")]
DIGITS_F = ["אפס", "אחת", "שתיים", "שלוש", "ארבע", "חמש", "שש", "שבע", "שמונה", "תשע"]


def num(n, gender="f"):
    return num2words(int(n), lang="he", gender=gender)


def latin_word(w):
    lw = w.lower()
    if lw in LATIN:
        return LATIN[lw]
    if w.isupper() and len(w) <= 5:
        return " ".join(LETTERS[c] for c in lw)
    out, i = "", 0
    while i < len(lw):
        for a, b in TRANSLIT:
            if lw.startswith(a, i):
                out += b; i += len(a); break
        else:
            i += 1
    return out


def number_token(m, text):
    """Speak a numeric token, choosing gender from the following word."""
    raw = m.group(0).replace(",", "")
    after = text[m.end():m.end() + 14].lstrip(" ")
    masc = after.startswith(MASC_NOUNS) or re.match(rf"ב?({MONTHS})", after) is not None
    g = "m" if masc else "f"
    if "." in raw:
        a, b = raw.split(".", 1)
        return f"{num(a)} נקודה {' '.join(DIGITS_F[int(d)] for d in b)}"
    return num(raw, g)


def normalize(text: str) -> str:
    t = text
    # emails
    def email(m):
        user, domain = m.group(1), m.group(2)
        say = lambda part: " נקודה ".join(latin_word(p) for p in part.split(".") if p)
        return f"{say(user)} שטרודל {say(domain)}"
    t = re.sub(r"([A-Za-z0-9._]+)@([A-Za-z0-9.]+[A-Za-z])", email, t)
    # acronyms (longest first)
    for k in sorted(ACRONYMS, key=len, reverse=True):
        t = t.replace(k, ACRONYMS[k])
    # day ranges like א'-ה'
    t = re.sub(r"\b([אבגדהוש])'\s*-\s*([אבגדהוש])'", lambda m: f"{DAYS[m.group(1)]} עד {DAYS[m.group(2)]}", t)
    # phone numbers: read digit by digit, grouped
    def phone(m):
        d = re.sub(r"\D", "", m.group())
        groups = [d[:-7], d[-7:-4], d[-4:]]
        return ", ".join(" ".join(DIGITS_F[int(x)] for x in g) for g in groups)
    t = re.sub(r"(?<!\d)0\d(?:-?\d){7,8}(?!\d)", phone, t)
    # prefix letters glued with hyphen: ב-1.8 / ה-API / ל-17
    t = re.sub(r"(?<![א-ת])([בהלמוכש]{1,2})-(?=[\dA-Za-z])", r"\1", t)
    # times H:MM
    def time_(m):
        h, mm = int(m.group(1)), int(m.group(2))
        s = num(h)
        return s if mm == 0 else s + (" וחצי" if mm == 30 else " ורבע" if mm == 15 else f" ו{num(mm)} דקות")
    t = re.sub(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", time_, t)
    # percent / currency become words after the number
    t = re.sub(r"(\d)\s*%", r"\1 אחוז", t)
    t = re.sub(r"(\d)\s*₪", r"\1 שקלים", t)
    # section refs like 12(ב)
    t = re.sub(r"(\d+)\(([א-ת])\)", lambda m: f"{num(m.group(1))} {m.group(2)}'", t)
    # numbers
    t = re.sub(r"\d+(?:,\d{3})*(?:\.\d+)?", lambda m: number_token(m, t), t)
    # Latin words
    t = re.sub(r"[A-Za-z]+", lambda m: latin_word(m.group()), t)
    t = t.replace("–", ",").replace("(", ",").replace(")", ",")
    return re.sub(r"\s+", " ", t).strip()


if __name__ == "__main__":
    import json, sys
    for x in json.load(open(sys.argv[1])):
        print(x["id"], "→", normalize(x["text"]), "\n")
