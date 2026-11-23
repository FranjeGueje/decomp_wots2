#!/usr/bin/env python3
"""
Spanish mod, step 4: the text of the event scripts (Us/script/**/*.sol) in Spanish.

Every script on the disc comes with its source (UTF-16, a byte-order mark, CR LF).
A mod's .sol under files/Us/script/ comes before the disc's compiled .sx, so the
Spanish scripts are the English sources with their text literals replaced.

The scripts are found by the names VOLUME.DAT stores after each file (not through
the path hash: Us/script/CTX/TimeC/C01AFx and C01B3x share a hash, and so do
C01BFx and C01C3x).

A literal is known by its number in the script: the 0-based position among all the
string literals of the source, as the game's lexer finds them (comments // and
/* */ skipped, "…" and '…' with backslash escapes).  The disc's source never
changes, so the number is fixed; `check` refuses a number that is not a text
literal, which catches a translation made against another lexer.

The translation lives in translations/es/script/<script>.tsv:

    # comments and blank lines are ignored
    <number><TAB><Spanish, as written in the source: \\n a line break, \\" a quote>

ordinary Spanish (¿ » º as they are: to_game() turns them into the font's codes).
No English: the original comes from the disc each time.  Missing numbers stay in
English; a literal whose English is the same as one translated earlier in the same
script takes that translation (so repeated lines need translating once).

  tools/spanish_script.py list [--all]          the scripts, what they are, how much text
  tools/spanish_script.py extract SCRIPT|all    work files: translations/es/original/script/
  tools/spanish_script.py build [SCRIPT…]       mods/espanol/files/Us/script/<script>.sol
  tools/spanish_script.py check [SCRIPT…]       errors and warnings; compiles each one
  tools/spanish_script.py show SCRIPT [N…]      number, kind, width, English, Spanish
  tools/spanish_script.py doubtful              literals the filter could not place

Which literals are text is decided in classify() below; docs/spanish/04_scripts.md
lists the rules.
"""
import argparse
import os
import re
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spanish_font import to_game  # noqa: E402
import font_info  # noqa: E402

from wotsroot import ROOT  # noqa: E402
TRANSLATIONS = ROOT / "translations" / "es" / "script"
WORK = ROOT / "translations" / "es" / "original" / "script"
OUT = ROOT / "mods" / "espanol" / "files" / "Us" / "script"
FONT = ROOT / "mods" / "espanol" / "files" / "Us" / "Font" / "Samu2.Fnt"
SOLC_CANDIDATES = [ROOT / "build" / "lib" / "sol" / "solc", ROOT / "build-sol" / "solc"]

# ── The scripts on the disc ──────────────────────────────────────────────

# Where the game starts scripts by name: the executable (StartUp2, config, EndRoll,
# shop/prison) and the map files in VOLUME.DAT (the shops).  The rest are reached
# through StartScript / Require from these.
ROOTS_EXE = ["StartUp2", "config", "EndRoll", "Shop/prison"]
ROOTS_MAPS = [
    "Shop/amakaze/douguya", "Shop/amakaze/gofukuya", "Shop/amakaze/izakaya", "Shop/amakaze/kanzasiya",
    "Shop/amakaze/komamonoya", "Shop/amakaze/yukaku", "Shop/kakinuma/izakaya", "Shop/kakinuma/syokuji",
    "Shop/kakinuma/tyaya", "Shop/kakinuma/yadoya", "Shop/numata/kajiya", "Shop/numata/sento_m",
    "Shop/numata/sento_w", "Shop/numata/syokuji", "Shop/numata/yaoya", "Shop/ootemon/syokuji",
    "Shop/ootemon/tyaya", "Shop/ootemon/yadoya", "Shop/ootuka/douguya", "Shop/ootuka/izakaya",
    "Shop/ootuka/komamonoya", "Shop/ootuka/kusuriya", "Shop/ootuka/myhome", "Shop/ootuka/yaoya",
    "Shop/shikano/syokuji", "Shop/zinzya/douguya", "Shop/zinzya/komamonoya", "Shop/zinzya/syokuji",
    "Shop/zinzya/tyaya",
]
# The name the game asks for, where it differs from the disc's spelling (the mod's
# files are looked up as asked, or all in lower case, and Linux minds the case).
REQUESTED = {"Shop/prison": "shop/prison"}


class Disc:
    """Us/script/**/*.sol and *.h from VOLUME.DAT, by their stored names."""

    def __init__(self):
        import volume
        self.vol = volume.Volume()
        self.files = {}         # "CTX/TimeA/A01A1x.sol" -> entry
        self.collide = set()
        for e in self.vol.entries:
            self.vol.f.seek(self.vol.data_start + e[4])
            name = self.vol.f.read(e[5]).split(b"\0")[0].decode("latin1")
            if name.startswith("Us\\script\\") and name.endswith((".sol", ".h")):
                rel = name[len("Us\\script\\"):].replace("\\", "/")
                self.files[rel] = e
                if e[3] & 1:
                    self.collide.add(rel[:-4])

    def scripts(self) -> list[str]:
        return sorted(n[:-4] for n in self.files if n.endswith(".sol") and not n.startswith("---"))

    def find(self, name: str) -> str | None:
        """A script name as a script or the game writes it (any case) -> the disc's spelling."""
        low = name.lower()
        for n in self.files:
            if n.endswith(".sol") and n[:-4].lower() == low:
                return n[:-4]
        return None

    def source(self, name: str) -> str:
        data = self.vol.read(self.files[name + ".sol"])
        if data[:2] != b"\xff\xfe":
            raise ValueError(f"{name}.sol: not UTF-16LE with a byte-order mark")
        return data[2:].decode("utf-16-le")

    def header(self, name: str) -> bytes:
        return self.vol.read(self.files[name])

    def headers(self) -> list[str]:
        return [n for n in self.files if n.endswith(".h")]


# ── The lexer (as lib/sol/src/compiler.cpp: skip_string, skip_comment) ───

SEPARATORS = set(" \t\n\r:;()[]{}<>,.+-*/%=@!#$&~\\|")
BLANKS = set(" \t\r\n")


@dataclass
class Tok:
    kind: str           # "s" string, "p" separator, "w" word
    start: int
    end: int
    line: int


def lex(s: str) -> list[Tok]:
    out, p, n, line = [], 0, len(s), 1
    while p < n:
        c = s[p]
        if c in BLANKS or c == "﻿":
            line += c == "\n"
            p += 1
        elif c in "\"'":
            q, prev = p + 1, ""
            while q < n and not (s[q] == c and prev != "\\"):
                prev = s[q]
                q += 1
            out.append(Tok("s", p, min(q + 1, n), line))
            line += s.count("\n", p, q)
            p = q + 1
        elif s.startswith("//", p):
            q = s.find("\n", p)
            p = n if q < 0 else q
        elif s.startswith("/*", p):
            q = s.find("*/", p + 2)
            q = n if q < 0 else q + 2
            line += s.count("\n", p, q)
            p = q
        elif c in SEPARATORS:
            out.append(Tok("p", p, p + 1, line))
            p += 1
        else:
            q = p
            while q < n and s[q] not in SEPARATORS and s[q] not in "\"'":
                q += 1
            out.append(Tok("w", p, q, line))
            p = q
    return out


def unescape(raw: str) -> str:
    """As the compiler's unescape (0x1BB760): \\n, \\t, else the character itself."""
    out, i = [], 0
    while i < len(raw):
        if raw[i] == "\\" and i + 1 < len(raw):
            out.append({"n": "\n", "t": "\t"}.get(raw[i + 1], raw[i + 1]))
            i += 2
        else:
            out.append(raw[i])
            i += 1
    return "".join(out)


# ── Literals and which are text ──────────────────────────────────────────

# call -> (kind, which arguments are the text).  "even": 0, 2, 4…
TEXT_CALLS = {
    "Effect.Telop": ("subtitulo", "even"),      # subtitle, wrapped to 612 px at 1.2x
    "Telop": ("subtitulo", "even"),             # CTX/macro: Effect.Telop on a thread
    "UI.SetSerif": ("bocadillo", {0}),          # speech balloon, no wrapping
    "UI.SetSerif2": ("bocadillo", {0}),
    "SetSerifEx": ("bocadillo", {0}),           # a shop's helper around UI.SetSerif
    "UI.SetTalkSelect": ("eleccion", {1}),      # the choices, one per line
    "EventFlag.SetMessage": ("mensaje", {0}),   # the goal shown on the status screen
    "UI.AddMessage": ("aviso", {0}),            # a line of the HUD
    "Battle.SetName": ("nombre", {1}),          # a fighter's name over the gauge
    "Effect.DrawText": ("texto", {0}),
}
# The voiced line: TelopVoice([voice, seconds, text, lips], speaker).  The text is
# "" throughout this release; the lip data ("o2c2o4…") is not text.
VOICE_CALLS = {"TelopVoice", "Effect.TelopVoice", "TV"}
# Strings put together in a variable before they are shown: (script, variable) -> kind.
# `doubtful` lists any other assignment of a string with words in it.
TEXT_VARS = {
    ("Shop/numata/kajiya", "st"): "aviso",      # GetUpParam: "Attack +3", for UI.AddMessage
}
# Arguments that are names of things, never text.
CODE_CALLS = {"Require", "StartScript", "print", "Effect.EndRoll", "Sound.PlayStream", "LoadScript"}

JAPANESE = re.compile(r"[　-ヿ一-鿿＀-￯]")
LATIN_WORD = re.compile(r"[A-Za-z]{2,}")
ICONS = set("①②③④⑤⑥←↑→↓○●") | {chr(c) for c in (0xA7, *range(0xB8, 0xC0))}
PLACEHOLDER = re.compile(r"%[sd]")


@dataclass
class Literal:
    n: int
    start: int          # the opening quote
    end: int            # past the closing quote
    line: int
    quote: str
    raw: str            # between the quotes, as written
    call: str = ""      # the innermost call the literal is an argument of
    arg: int = -1
    item: int = -1      # its place in a list, if inside one
    kind: str = ""      # a text kind (TEXT_CALLS), or "codigo", "japones", "signos", "vacio", "dudoso"
    why: str = ""
    who: str = ""       # who says it, when the script says
    var: str = ""       # the variable it is assigned to (x = "…", x += "…")
    same_as: int = -1   # the first literal of the script with the same English

    @property
    def text(self) -> bool:
        return self.kind in TEXT_KINDS

    @property
    def value(self) -> str:
        return unescape(self.raw)


TEXT_KINDS = {k for k, _ in TEXT_CALLS.values()}


def literals(src: str, script: str = "") -> list[Literal]:
    toks = lex(src)
    out: list[Literal] = []
    # Open brackets: [char, callee, argument number, the token index]
    stack: list[list] = []
    last_voice = (None, -10)    # (speaker, line) of the last TelopVoice
    for i, t in enumerate(toks):
        txt = src[t.start:t.end]
        if t.kind == "p" and txt in "([":
            j, parts = i - 1, []
            while j >= 0 and (toks[j].kind == "w" or src[toks[j].start:toks[j].end] == "."):
                parts.insert(0, src[toks[j].start:toks[j].end])
                j -= 1
            stack.append([txt, "".join(parts), 0, i])
        elif t.kind == "p" and txt in ")]":
            if stack:
                top = stack.pop()
                if top[0] == "(" and top[1] in VOICE_CALLS:
                    who = src[toks[top[3]].end:t.start]
                    m = re.search(r"\]\s*,\s*CharaID\.(\w+)", who)
                    last_voice = (m.group(1) if m else None, t.line)
        elif t.kind == "p" and txt == "," and stack:
            stack[-1][2] += 1
        elif t.kind == "s":
            lit = Literal(len(out), t.start, t.end, t.line, src[t.start], src[t.start + 1:t.end - 1])
            prev = src[toks[i - 1].start:toks[i - 1].end] if i else ""
            calls = [s for s in stack if s[0] == "("]
            if stack and stack[-1][0] == "[":
                lit.item = stack[-1][2]
                lit.call = stack[-2][1] if len(stack) > 1 and stack[-2][0] == "(" else "["
                lit.arg = stack[-2][2] if len(stack) > 1 else -1
            elif calls:
                lit.call, lit.arg = stack[-1][1], stack[-1][2]
            if prev == "include":
                lit.call = "#include"
            if prev == "=" and i >= 2:
                k = i - 2
                if src[toks[k].start:toks[k].end] == "+":
                    k -= 1
                if k >= 0 and toks[k].kind == "w":
                    lit.var = src[toks[k].start:toks[k].end]
            if last_voice[0] and lit.line - last_voice[1] <= 3:
                lit.who = last_voice[0]
            out.append(lit)
            classify(lit, script, calls)
            if lit.kind == "bocadillo" and lit.arg == 0:
                m = re.match(r"\s*,\s*(?:CharaID\.)?([\w.]+)", src[lit.end:])
                if m:
                    lit.who = m.group(1)
    first = {}
    for lit in out:
        if lit.text:
            if lit.raw in first:
                lit.same_as = first[lit.raw]
            else:
                first[lit.raw] = lit.n
    return out


def classify(lit: Literal, script: str, calls: list):
    v = lit.value

    def set_(kind, why):
        lit.kind, lit.why = kind, why

    if lit.call == "#include":
        return set_("codigo", "#include")
    if v.strip() == "":
        return set_("vacio", "empty")
    if lit.call in CODE_CALLS or any(c[1] in CODE_CALLS for c in calls):
        return set_("codigo", f"argument of {lit.call or calls[-1][1]}")
    if lit.call in VOICE_CALLS and lit.item >= 0:
        if lit.item == 2:
            pass                                    # a voiced line's text: fall through
        else:
            return set_("codigo", "TelopVoice data (lip movements)")
    kind = None
    if (script, lit.var) in TEXT_VARS and LATIN_WORD.search(v):
        return set_(TEXT_VARS[script, lit.var], f"assigned to {lit.var}, shown later")
    if lit.var and LATIN_WORD.search(v) and not calls:
        return set_("dudoso", f"assigned to {lit.var}")
    if lit.call in TEXT_CALLS:
        kind, args = TEXT_CALLS[lit.call]
        if args == "even" and lit.arg % 2 != 0 or args != "even" and lit.arg not in args:
            return set_("codigo", f"argument {lit.arg} of {lit.call}")
        if lit.item >= 0:
            return set_("dudoso", f"in a list inside {lit.call}")
    elif lit.call in VOICE_CALLS and lit.item == 2:
        kind = "subtitulo"
    if kind is None:
        # Not an argument of anything known: judge by the look of it.
        prose = LATIN_WORD.search(v) and (" " in v.strip() or re.search(r"[.!?…]$", v))
        if JAPANESE.search(v) and not LATIN_WORD.search(v):
            return set_("japones", f"Japanese, {lit.call or 'no call'}")
        if prose:
            return set_("dudoso", f"prose-like, {lit.call or 'outside any call'}")
        return set_("codigo", f"a name or a value, {lit.call or 'outside any call'}")
    if JAPANESE.search(v) and not LATIN_WORD.search(v):
        return set_("japones", f"Japanese text in {lit.call} (developers' scripts)")
    if not re.search(r"[A-Za-z]", v):
        return set_("signos", "no letters (…!, ?)")
    set_(kind, lit.call)


# ── Translations ─────────────────────────────────────────────────────────

def tsv_path(name: str) -> Path:
    return TRANSLATIONS / f"{name}.tsv"


def read_translation(path: Path) -> dict[int, str]:
    out = {}
    if not path.exists():
        return out
    for k, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.startswith("#"):
            continue
        if "\t" not in raw:
            raise ValueError(f"{path}:{k}: no tab between number and text")
        key, text = raw.split("\t", 1)
        if not key.strip().isdigit():
            raise ValueError(f"{path}:{k}: '{key}' is not a number")
        if int(key) in out:
            raise ValueError(f"{path}:{k}: number {key} given twice")
        out[int(key)] = text
    return out


def edges(en: str, es: str) -> str:
    """The Spanish with the English's spaces at its ends (editors drop trailing
    spaces, and the game joins some strings to others: "…my leg " + "and…")."""
    lead = en[:len(en) - len(en.lstrip(" "))]
    trail = en[len(en.rstrip(" ")):]
    return lead + es.strip(" ") + trail


def resolved(lits: list[Literal], spanish: dict[int, str]) -> dict[int, str]:
    """The Spanish of every literal (its own, else that of its first duplicate),
    with the spaces at its ends as in the English."""
    out = {}
    for lit in lits:
        es = spanish.get(lit.n, spanish.get(lit.same_as) if lit.same_as >= 0 else None)
        if es is not None:
            out[lit.n] = edges(lit.raw, es)
    return out


def merged(src: str, lits: list[Literal], es: dict[int, str]) -> str:
    parts, at = [], 0
    for lit in lits:
        if lit.n in es:
            parts.append(src[at:lit.start + 1])
            parts.append(to_game(es[lit.n]))
            at = lit.end - 1
    parts.append(src[at:])
    return "".join(parts)


# ── Measuring ────────────────────────────────────────────────────────────

TELOP_ROOM = 9800 / 16 / 1.2       # Effect.Telop wraps at 0x2648/16 px, drawn at 1.2x
MESSAGE_ROOM = 8000 / 16 / 0.92    # EventFlag.SetMessage wraps at 8000/16 px at 0.92x
MESSAGE_CHARS = 0x80               # ...and is dropped if the wrapped text is longer
# Balloons and choices are not wrapped: the box grows with the text.  The widest
# lines of the English release (in use) are the guide: balloons 282 px, choices
# 443, HUD notices 269.  A Spanish line may reach the larger of its English and:
ROOM = {"bocadillo": 300, "eleccion": 450, "aviso": 300, "nombre": 200, "texto": 500}
# Subtitles wrap by themselves; the English ones take 1-2 lines (a few 3-4).
TELOP_LINES = 2


class Widths:
    def __init__(self, fnt: Path):
        if not fnt.exists():
            sys.exit(f"{fnt} is missing: run tools/spanish_font.py first")
        glyphs, _ = font_info.parse_fnt(fnt.read_bytes())
        self.w = {}
        for g in glyphs:
            self.w.setdefault(g["code"], g["w"])

    def missing(self, text: str) -> set[str]:
        return {c for c in text if c not in "\n\r\t" and ord(c) not in self.w}

    def line(self, text: str) -> int:
        return sum(self.w.get(ord(c), 0) for c in text)

    def lines(self, text: str) -> list[int]:
        return [self.line(p) for p in text.split("\n")]

    def wrap(self, text: str, room: float) -> list[str]:
        """WrapText (0x1E7540): words onto a line while it fits."""
        out, line, at = [], None, 0
        while at <= len(text):
            ends = [k for k in (text.find(" ", at), text.find("\n", at)) if k >= 0]
            end = min(ends) if ends else len(text)
            word = text[at:end]
            tried = word if not line else line + " " + word
            if line and self.line(tried) > room:
                out.append(line)
                line = word
            else:
                line = tried
            if end < len(text) and text[end] == "\n":
                out.append(line)
                line = ""
            at = end + 1
        out.append(line or "")
        return out


# ── Checking ─────────────────────────────────────────────────────────────

def solc_path() -> Path:
    for p in SOLC_CANDIDATES:
        if p.exists():
            return p
    print("building solc (cmake -S lib/sol -B build-sol)", file=sys.stderr)
    subprocess.run(["cmake", "-S", str(ROOT / "lib/sol"), "-B", str(ROOT / "build-sol")], check=True,
                   stdout=subprocess.DEVNULL)
    subprocess.run(["cmake", "--build", str(ROOT / "build-sol")], check=True, stdout=subprocess.DEVNULL)
    return ROOT / "build-sol" / "solc"


def compile_ops(solc: Path, source: bytes, name: str, incdir: Path) -> tuple[str | None, list]:
    """Compile with solc; -> (error, ops with string values blanked)."""
    import sx
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / (Path(name).name + ".sol")
        out = Path(tmp) / "out.sx"
        src.write_bytes(source)
        r = subprocess.run([str(solc), str(src), "-o", str(out), "-I", str(incdir)], capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            return (r.stdout + r.stderr).strip() or "solc failed", []
        data = out.read_bytes()
    size, = struct.unpack_from("<I", data, 8)
    lines: list[str] = []
    sx.disassemble(data[0x14:0x14 + size], 0, size, 0, lines)
    ops = []
    for ln in lines:
        body = ln[6:].strip() if len(ln) > 6 else ln.strip()
        if body.startswith("wstring"):
            body = "wstring"
        elif body.startswith("def {"):
            body = "def {"
        ops.append(body)
    return None, ops


def check_script(name: str, src: str, lits: list[Literal], spanish: dict[int, str], widths: Widths,
                 report) -> None:
    by_n = {lit.n: lit for lit in lits}
    for n, es in sorted(spanish.items()):
        lit = by_n.get(n)
        if lit is None:
            report("error", n, f"no literal {n} (the script has {len(lits)})")
            continue
        if not lit.text:
            report("error", n, f"not a text literal ({lit.kind}: {lit.why}): {lit.raw!r}")
            continue
        check_literal(lit, edges(lit.raw, es), widths, report)
    for lit in lits:
        if lit.text and lit.same_as >= 0 and lit.n in spanish and lit.same_as in spanish \
                and spanish[lit.n] != spanish[lit.same_as]:
            report("warning", lit.n, f"the same English as {lit.same_as}, another Spanish")


def check_literal(lit: Literal, es: str, widths: Widths, report) -> None:
    n, en_raw = lit.n, lit.raw
    if not es.strip():
        report("error", n, "empty")
        return
    # The raw text goes between the quotes as it is: the quote and stray backslashes.
    k = 0
    while k < len(es):
        if es[k] == "\\":
            if k + 1 >= len(es) or es[k + 1] not in "n\\\"'t":
                report("error", n, f"a backslash that is not \\n, \\\\, \\\" ({es!r})")
            k += 2
            continue
        if es[k] == lit.quote:
            report("error", n, f"an unescaped {lit.quote} ends the literal early; write \\{lit.quote}")
        if es[k] in "\r\n":
            report("error", n, "a real line break; write \\n")
        k += 1
    en, game = lit.value, unescape(to_game(es))
    if PLACEHOLDER.findall(en) != PLACEHOLDER.findall(game):
        report("error", n, f"placeholders {PLACEHOLDER.findall(en)} -> {PLACEHOLDER.findall(game)}")
    icons_en, icons_es = sorted(c for c in en if c in ICONS), sorted(c for c in game if c in ICONS)
    if icons_en != icons_es:
        report("error", n, f"icons {''.join(icons_en)!r} -> {''.join(icons_es)!r}")
    if missing := widths.missing(game):
        report("error", n, f"not in the font: {''.join(sorted(missing))!r}")
    breaks_en, breaks_es = en.count("\n"), game.count("\n")
    if lit.kind == "eleccion" and breaks_en != breaks_es:
        report("error", n, f"{breaks_en} line breaks -> {breaks_es}: each line is one choice, "
                           "and the script counts them")
    elif breaks_en != breaks_es and lit.kind != "subtitulo":
        report("warning", n, f"{breaks_en} line breaks -> {breaks_es}")
    if lit.kind == "subtitulo":
        l_en, l_es = widths.wrap(en, TELOP_ROOM), widths.wrap(game, TELOP_ROOM)
        if "" in l_es[:-1] or l_es[-1:] == [""]:
            report("warning", n, "an empty line once wrapped (a \\n after a full line, or a space "
                                 "before it): leave line breaks in subtitles to the game")
        if len(l_es) > max(TELOP_LINES, len(l_en)):
            report("warning", n, f"the subtitle wraps to {len(l_es)} lines (English {len(l_en)}): "
                                 f"{' | '.join(l_es)}")
    elif lit.kind == "mensaje":
        wrapped = "\n".join(widths.wrap(game, MESSAGE_ROOM))
        if len(wrapped) >= MESSAGE_CHARS:
            report("error", n, f"{len(wrapped)} characters: the game drops a message of "
                               f"{MESSAGE_CHARS} or more")
        l_en = widths.wrap(en, MESSAGE_ROOM)
        if wrapped.count("\n") + 1 > max(2, len(l_en)):
            report("warning", n, f"the message wraps to {wrapped.count(chr(10)) + 1} lines")
    else:
        w_en, w_es = max(widths.lines(en)), max(widths.lines(game))
        room = max(w_en, ROOM.get(lit.kind, 0))
        if w_es > room:
            report("warning", n, f"a line of {w_es} px > {room} px ({lit.kind}, English {w_en}): "
                                 f"{game!r}")


# ── Script facts ─────────────────────────────────────────────────────────

class Scripts:
    def __init__(self):
        self.disc = Disc()
        self._lits = {}
        self._src = {}

    def src(self, name):
        if name not in self._src:
            self._src[name] = self.disc.source(name)
        return self._src[name]

    def lits(self, name):
        if name not in self._lits:
            self._lits[name] = literals(self.src(name), name)
        return self._lits[name]

    def resolve(self, arg: str) -> str:
        n = self.disc.find(arg.removesuffix(".sol"))
        if n is None:
            sys.exit(f"no script {arg!r} on the disc (see `list --all`)")
        return n

    def reached(self) -> dict[str, str]:
        """Script -> how the game gets to it."""
        how = {}
        todo = [(n, "executable") for n in ROOTS_EXE] + [(n, "map files") for n in ROOTS_MAPS]
        while todo:
            name, why = todo.pop(0)
            found = self.disc.find(name)
            if found is None or found in how:
                continue
            how[found] = why
            for lit in self.lits(found):
                if lit.call in ("StartScript", "Require") and lit.kind == "codigo":
                    todo.append((lit.value, f"{lit.call} in {found}"))
        return how

    def translated(self):
        return sorted(str(p.relative_to(TRANSLATIONS))[:-4] for p in TRANSLATIONS.rglob("*.tsv")) \
            if TRANSLATIONS.exists() else []


def category(name: str, reached: dict) -> str:
    if name not in reached:
        return "sin uso"
    if name.startswith("CTX/Time") or name in ("CTX/Opening", "CTX/MaturiStart"):
        return "historia"
    if name.lower().startswith("shop/"):
        return "tienda"
    return "sistema"


def counts(lits: list[Literal], spanish: dict[int, str]) -> tuple[int, int, int, int]:
    text = [lit for lit in lits if lit.text]
    unique = [lit for lit in text if lit.same_as < 0]
    es = resolved(lits, spanish)
    return len(text), len(unique), sum(1 for lit in text if lit.n in es), \
        sum(1 for lit in unique if lit.n in spanish)


# ── Commands ─────────────────────────────────────────────────────────────

def cmd_list(S: Scripts, args):
    reached = S.reached()
    rows, tot = [], [0, 0, 0, 0]
    for name in S.disc.scripts():
        cat = category(name, reached)
        if cat == "sin uso" and not args.all:
            continue
        lits = S.lits(name)
        t, u, d, du = counts(lits, read_translation(tsv_path(name)))
        if t == 0 and not args.all:
            continue
        flags = " colisión-hash" if name in S.disc.collide else ""
        rows.append(f"{name:30} {cat:9} {len(lits):5} {t:5} {u:5} {d:5}  {reached.get(name, '-')}{flags}")
        if cat != "sin uso":
            for k, v in enumerate((t, u, d, du)):
                tot[k] += v
    print(f"{'script':30} {'tipo':9} {'lits':>5} {'texto':>5} {'único':>5} {'trad':>5}  cómo se llega")
    print("\n".join(rows))
    print(f"\nen uso: {tot[0]} cadenas de texto ({tot[1]} distintas por script); "
          f"traducidas {tot[2]} ({tot[3]} distintas)")


KIND_NOTE = {
    "subtitulo": "subtítulo (se parte solo a ~510 px; 2 líneas como mucho)",
    "bocadillo": "bocadillo (no se parte: \\n donde el inglés; líneas ≤ ~400 px)",
    "eleccion": "opción de respuesta (una por línea; mismos \\n que el inglés)",
    "mensaje": "pensamiento/objetivo de la pantalla de estado (< 128 caracteres)",
    "aviso": "aviso del HUD",
    "nombre": "nombre de luchador",
    "texto": "texto en pantalla",
}


def work_file(name: str, lits: list[Literal]) -> str:
    text = [lit for lit in lits if lit.text]
    dups: dict[int, list[int]] = {}
    for lit in text:
        if lit.same_as >= 0:
            dups.setdefault(lit.same_as, []).append(lit.n)
    out = [f"# {name}: {len(text)} cadenas de texto, {len(text) - sum(map(len, dups.values()))} distintas.",
           "# Cada cadena: una línea «# L<línea> <tipo> [quién] [repetida en: …]» y otra «número<TAB>inglés».",
           "# Traducción: translations/es/script/" + name + ".tsv con «número<TAB>español» (sin el inglés).",
           "# Las repetidas se traducen una vez (la primera); build copia la traducción a las demás.", ""]
    for lit in text:
        if lit.same_as >= 0:
            continue
        note = [f"L{lit.line}", lit.kind]
        if lit.who:
            note.append(f"habla: {lit.who}")
        if lit.kind == "eleccion":
            note.append("habla: el protagonista")
        if lit.n in dups:
            note.append("repetida en: " + ", ".join(map(str, dups[lit.n])))
        out.append("# " + " ".join(note))
        out.append(f"{lit.n}\t{lit.raw}")
    return "\n".join(out) + "\n"


def cmd_extract(S: Scripts, args):
    reached = S.reached()
    names = [n for n in S.disc.scripts() if category(n, reached) != "sin uso"] \
        if args.scripts == ["all"] else [S.resolve(a) for a in args.scripts]
    doubtful = []
    written = 0
    for name in names:
        lits = S.lits(name)
        doubtful += [(name, lit) for lit in lits if lit.kind == "dudoso"]
        if not any(lit.text for lit in lits):
            continue
        path = WORK / f"{name}.tsv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(work_file(name, lits), encoding="utf-8")
        written += 1
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "_dudosos.tsv").write_text(
        "# Literales que el filtro no sabe colocar (no se traducen; revisar y, si son texto,\n"
        "# añadir su llamada a TEXT_CALLS en tools/spanish_script.py)\n"
        + "".join(f"{n}\t{lit.n}\tL{lit.line}\t{lit.why}\t{lit.raw}\n" for n, lit in doubtful),
        encoding="utf-8")
    print(f"wrote {written} work files under {WORK} ({len(doubtful)} doubtful in _dudosos.tsv)")


def out_path(name: str) -> Path:
    return OUT / f"{REQUESTED.get(name, name)}.sol"


def cmd_build(S: Scripts, args):
    names = [S.resolve(a) for a in args.scripts] or [S.resolve(n) for n in S.translated()]
    for name in names:
        src, lits = S.src(name), S.lits(name)
        es = resolved(lits, read_translation(tsv_path(name)))
        text = merged(src, lits, es)
        path = out_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        print(f"wrote {path.relative_to(ROOT)}: {len(es)} of {sum(1 for x in lits if x.text)} in Spanish")


def cmd_check(S: Scripts, args):
    names = [S.resolve(a) for a in args.scripts] or [S.resolve(n) for n in S.translated()]
    widths = Widths(args.font)
    solc = solc_path()
    errors = warnings = 0
    with tempfile.TemporaryDirectory() as inc:
        for h in S.disc.headers():
            p = Path(inc) / h
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(S.disc.header(h))
        for name in names:
            src, lits = S.src(name), S.lits(name)
            spanish = read_translation(tsv_path(name))

            before = errors

            def report(kind, n, msg):
                nonlocal errors, warnings
                if kind == "error":
                    errors += 1
                else:
                    warnings += 1
                print(f"{kind:7} {name}:{n}  {msg}")

            check_script(name, src, lits, spanish, widths, report)
            # The built file: it must compile, and to the same code but for its strings.
            built = out_path(name)
            if not built.exists():
                report("warning", "-", f"{built.relative_to(ROOT)} not built yet (run build)")
                continue
            expect = merged(src, lits, resolved(lits, spanish)).encode("utf-8")
            if built.read_bytes() != expect:
                report("warning", "-", f"{built.relative_to(ROOT)} is out of date (run build)")
            err, ops = compile_ops(solc, built.read_bytes(), name, Path(inc))
            if err:
                report("error", "-", f"does not compile: {err}")
                continue
            err0, ops0 = compile_ops(solc, b"\xff\xfe" + src.encode("utf-16-le"), name, Path(inc))
            if err0 is None and ops != ops0:
                report("error", "-", "compiles to other code than the original (beyond its strings)")
            t, u, d, du = counts(lits, spanish)
            state = "ok     " if errors == before else "FAILED "
            print(f"{state} {name}: compiles; {d} of {t} text literals in Spanish ({du} of {u} distinct)")
    print(f"{errors} errors, {warnings} warnings")
    sys.exit(1 if errors else 0)


def cmd_show(S: Scripts, args):
    if not args.scripts:
        sys.exit("show SCRIPT [N…]")
    name = S.resolve(args.scripts[0])
    only = {int(x) for x in args.scripts[1:]}
    widths = Widths(args.font)
    lits = S.lits(name)
    es = resolved(lits, read_translation(tsv_path(name)))
    for lit in lits:
        if (only and lit.n not in only) or (not only and not lit.text):
            continue
        w_en = max(widths.lines(lit.value))
        s = es.get(lit.n)
        w_es = max(widths.lines(unescape(to_game(s)))) if s is not None else "-"
        who = f" {lit.who}" if lit.who else ""
        print(f"{lit.n:4} L{lit.line:<5} {lit.kind:9}{who} {w_en:4} {w_es:>4}  {lit.raw}")
        if lit.text or only:
            print(f"{'':30}{s if s is not None else '(sin traducir)'}")


def cmd_doubtful(S: Scripts, args):
    reached = S.reached()
    for name in S.disc.scripts():
        for lit in S.lits(name):
            if lit.kind == "dudoso":
                print(f"{name}:{lit.n} L{lit.line} [{category(name, reached)}] {lit.why}: {lit.raw}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["list", "extract", "build", "check", "show", "doubtful"])
    ap.add_argument("scripts", nargs="*", help="script names (CTX/TimeA/A01A1x), or `all` for extract")
    ap.add_argument("--all", action="store_true", help="list: also the scripts the game never runs")
    ap.add_argument("--font", type=Path, default=FONT, help="the mod's .Fnt (for widths)")
    args = ap.parse_args()
    S = Scripts()
    if args.command == "extract" and not args.scripts:
        sys.exit("extract SCRIPT… | all")
    {"list": cmd_list, "extract": cmd_extract, "build": cmd_build, "check": cmd_check,
     "show": cmd_show, "doubtful": cmd_doubtful}[args.command](S, args)


if __name__ == "__main__":
    main()
