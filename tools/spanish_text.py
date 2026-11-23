#!/usr/bin/env python3
"""
Spanish mod, step 3: the menus' text (Us/menu/menutext.txt) in Spanish.

menutext.txt (read by TextTable_Parse, src/engine/text_table.cpp) is UTF-16LE with
a byte-order mark, one string per line, every line ended by CR.  The game knows a
string by its line number (0, 1, 2…), so the file must keep every line in its
place: the Spanish file has the same number of lines, in the same order.  The two
characters `\\n` inside a line are a line break.  Lines holding a single "." are
padding: ids nothing uses.

The translation lives in the repository as translations/es/menutext.tsv:

    # comments and blank lines are ignored
    <id><TAB><Spanish text>

ordinary Spanish (¿ » º as they are: to_game() turns them into the font's codes),
`\\n` for a line break as in the original.  It holds no English: the original comes
from the disc each time.  Ids missing from it stay in English.

  tools/spanish_text.py extract       the original as id<TAB>text, to work from:
                                      translations/es/original/menutext.tsv (not in git)
  tools/spanish_text.py build         mods/espanol/files/Us/menu/menutext.txt
  tools/spanish_text.py check         what may be wrong with the translation
  tools/spanish_text.py show [ID…]    id, width, English and Spanish side by side

`--orig FILE` reads an extracted menutext.txt instead of extracted/VOLUME.DAT.
`check` measures with the mod's font (mods/espanol/files/Us/Font/Samu2.Fnt, made by
tools/spanish_font.py); it exits with 1 if it found errors (not mere warnings).
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spanish_font import NEW_GLYPHS, to_game  # noqa: E402
import font_info  # noqa: E402

from wotsroot import ROOT  # noqa: E402
GAME_PATH = "menu/menutext.txt"
TRANSLATION = ROOT / "translations" / "es" / "menutext.tsv"
WORK = ROOT / "translations" / "es" / "original" / "menutext.tsv"
OUT = ROOT / "mods" / "espanol" / "files" / "Us" / "menu" / "menutext.txt"
FONT = ROOT / "mods" / "espanol" / "files" / "Us" / "Font" / "Samu2.Fnt"

FILLER = "."
PLACEHOLDER = re.compile(r"%[sd]")
# Characters that are not words: button marks, arrows, and the Latin-1 codes the
# font draws as icons (see docs/spanish/01_font_glyphs.md).
ICONS = set("①②③④⑤⑥←↑→↓○●") | {chr(c) for c in (0xA7, *range(0xB8, 0xC0))}

# Strings that were seen in the game to have more room than the English used
# (id: the widest Spanish, in pixels, that fits there).  See docs/spanish/03_menu_text.md.
def _room(px, *ids):
    return {i: px for group in ids for i in (group if isinstance(group, range) else (group,))}


ROOM = {
    # Settings: the buttons on the left ("Barras de color", 123, overflowed;
    # "Prueba sonidos", 114, fits), the values, the buttons on the right, the hint.
    **_room(116, 106, 107, 108, 111, 114, 117, 118, 119, 122, 123, 124, 125),
    **_room(120, 109, 110, 112, 113, 115, 116, 120, 121, 126, 127, 128),
    **_room(80, 17),
    # The pause menu's sliding buttons ("Volver al juego", 125, with room to spare).
    **_room(150, range(62, 80)),
    # Status: the four lines (date + period, place, sword, job) and the gauges' labels.
    **_room(100, range(159, 163)), **_room(120, range(35, 45)), **_room(90, range(30, 35)),
    **_room(190, range(82, 93)), **_room(24, range(136, 142)), **_room(50, 27),
    **_room(160, range(133, 136)),
    # Character setup: the menu's labels and the hint under the sword.
    **_room(90, range(166, 173)), **_room(280, range(173, 177)),
    # Records (from the title): tabs, labels, the back button.
    **_room(170, range(272, 282)), **_room(35, 14), **_room(50, 18), **_room(80, 282),
}


# ── The file ─────────────────────────────────────────────────────────────

def read_original(path: Path | None) -> list[str]:
    if path is not None:
        data = path.read_bytes()
    else:
        import volume
        data = volume.Volume().read_path(GAME_PATH)
    lines = parse(data)
    if serialize(lines) != data:
        raise ValueError("menutext.txt does not read back as it was")
    return lines


def parse(data: bytes) -> list[str]:
    if data[:2] != b"\xff\xfe":
        raise ValueError("menutext.txt: no UTF-16LE byte-order mark")
    text = data[2:].decode("utf-16-le")
    if "\n" in text:
        raise ValueError("menutext.txt: LF line ends (the disc's file has CR alone)")
    if not text.endswith("\r"):
        raise ValueError("menutext.txt: the last line is not ended")
    return text[:-1].split("\r")


def serialize(lines: list[str]) -> bytes:
    for i, line in enumerate(lines):
        if "\r" in line or "\n" in line:
            raise ValueError(f"line {i}: a real line break (write \\n)")
    return b"\xff\xfe" + "".join(line + "\r" for line in lines).encode("utf-16-le")


def read_translation(path: Path) -> dict[int, str]:
    out = {}
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.startswith("#"):
            continue
        if "\t" not in raw:
            raise ValueError(f"{path}:{n}: no tab between id and text")
        key, text = raw.split("\t", 1)
        if not key.isdigit():
            raise ValueError(f"{path}:{n}: '{key}' is not an id")
        if int(key) in out:
            raise ValueError(f"{path}:{n}: id {key} given twice")
        out[int(key)] = text
    return out


def merged(original: list[str], spanish: dict[int, str]) -> list[str]:
    bad = [i for i in spanish if i >= len(original)]
    if bad:
        raise ValueError(f"ids past the end of the file ({len(original)} lines): {bad}")
    return [to_game(spanish[i]) if i in spanish else line for i, line in enumerate(original)]


# ── Measuring ────────────────────────────────────────────────────────────

class Widths:
    def __init__(self, fnt: Path):
        if not fnt.exists():
            sys.exit(f"{fnt} is missing: run tools/spanish_font.py first")
        glyphs, _ = font_info.parse_fnt(fnt.read_bytes())
        self.w = {}
        for g in glyphs:
            self.w.setdefault(g["code"], g["w"])

    def missing(self, text: str) -> set[str]:
        return {c for c in text.replace("\\n", "") if ord(c) not in self.w}

    def lines(self, text: str) -> list[int]:
        """The width in pixels of each line of a string (as the game gives it)."""
        return [sum(self.w.get(ord(c), 0) for c in part) for part in text.split("\\n")]

    def __call__(self, text: str) -> int:
        return max(self.lines(text))


def words(text: str) -> bool:
    """Whether a line has anything to translate."""
    return any(c.isalpha() and ord(c) < 0x3000 for c in text.replace("\\n", "")) and text != FILLER


def check(original: list[str], spanish: dict[int, str], widths: Widths) -> int:
    errors = warnings = 0

    def report(kind, i, msg):
        nonlocal errors, warnings
        if kind == "error":
            errors += 1
        else:
            warnings += 1
        print(f"{kind:7} {i:3}  {msg}")

    for i, es in sorted(spanish.items()):
        if i >= len(original):
            report("error", i, "past the end of the file")
            continue
        en, game = original[i], to_game(es)
        if en == FILLER:
            if es != FILLER:
                report("error", i, "a padding line (\".\") translated")
            continue
        if not es.strip() and en.strip():
            report("error", i, "empty")
        if PLACEHOLDER.findall(en) != PLACEHOLDER.findall(es):
            report("error", i, f"placeholders {PLACEHOLDER.findall(en)} -> {PLACEHOLDER.findall(es)}")
        icons_en = sorted(c for c in en if c in ICONS)
        icons_es = sorted(c for c in game if c in ICONS)
        if icons_en != icons_es:
            report("error", i, f"icons {''.join(icons_en)!r} -> {''.join(icons_es)!r}")
        if en.count("\\n") != es.count("\\n"):
            report("warning", i, f"{en.count(chr(92) + 'n')} line breaks -> {es.count(chr(92) + 'n')}")
        if "\\" in es.replace("\\n", ""):
            report("error", i, "a backslash that is not \\n")
        lead = lambda s: len(s) - len(s.lstrip(" "))          # noqa: E731
        trail = lambda s: len(s) - len(s.rstrip(" "))         # noqa: E731
        if (lead(en) > 0) != (lead(es) > 0) or (trail(en) > 0) != (trail(es) > 0):
            report("error", i, f"the spaces at the ends differ ({en!r} -> {es!r}); the game joins this string to others")
        if missing := widths.missing(game):
            report("error", i, f"not in the font: {''.join(sorted(missing))!r}")
        w_en, w_es = widths(en), widths(game)
        room = max(w_en, ROOM.get(i, 0))
        if w_es > room:
            more = f" (room seen in the game: {ROOM[i]})" if i in ROOM else ""
            report("warning", i, f"{w_es} px > {w_en} px{more}: {en!r} -> {es!r}")

    # The padding lines must stay where they are, and everything else be translated.
    for i, en in enumerate(original):
        if en == FILLER and i in spanish and spanish[i] != FILLER:
            pass                                    # reported above
        elif words(en) and i not in spanish:
            report("warning", i, f"not translated: {en!r}")
    done = sum(1 for i in spanish if i < len(original) and words(original[i]))
    total = sum(1 for en in original if words(en))
    print(f"{done} of {total} lines with words translated; {errors} errors, {warnings} warnings")
    return errors


# ── Commands ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["extract", "build", "check", "show"])
    ap.add_argument("ids", nargs="*", type=int, help="show: these ids only")
    ap.add_argument("--orig", type=Path, help="an extracted Us/menu/menutext.txt")
    ap.add_argument("--tsv", type=Path, default=TRANSLATION, help="the translation")
    ap.add_argument("--out", type=Path, help="extract / build: where to write")
    ap.add_argument("--font", type=Path, default=FONT, help="the mod's .Fnt (for widths)")
    args = ap.parse_args()

    original = read_original(args.orig)

    if args.command == "extract":
        out = args.out or WORK
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(f"{i}\t{line}\n" for i, line in enumerate(original)), encoding="utf-8")
        print(f"wrote {out} ({len(original)} lines)")
        return

    spanish = read_translation(args.tsv)

    if args.command == "build":
        lines = merged(original, spanish)
        assert len(lines) == len(original)
        out = args.out or OUT
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(serialize(lines))
        n = sum(1 for i in spanish if original[i] != FILLER)
        print(f"wrote {out}: {len(lines)} lines, {n} in Spanish")
    elif args.command == "check":
        sys.exit(1 if check(original, spanish, Widths(args.font)) else 0)
    else:
        widths = Widths(args.font)
        for i, en in enumerate(original):
            if (args.ids and i not in args.ids) or (not args.ids and not words(en)):
                continue
            es = spanish.get(i)
            w_es = widths(to_game(es)) if es is not None else "-"
            print(f"{i:3} {widths(en):4} {w_es:>4}  {en}\n{'':14}{es if es is not None else '(sin traducir)'}")


if __name__ == "__main__":
    main()
