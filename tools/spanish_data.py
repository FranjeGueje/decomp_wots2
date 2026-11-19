#!/usr/bin/env python3
"""
Spanish mod, step 5: the text kept in the game's data files (not the menus'
menutext.txt, not the scripts, not the task files) in Spanish.

  item/ItemInfo.Dat              items: name, help line, description, what using it says
  object/ObjectName.Lst          things lying on the ground (what you pick up)
  Accessory/AccessoryPos.Lst     where an accessory is worn (Records)
  menu/Title/TitleNameList       the player's titles (fixed records of 25 characters)
  chara/paramlist                characters' names: only the generic roles are translated
  ui/GameUI/ShopList.dat         what shopkeepers say, the shop's yes / no menus
  mcard/message.dat              the save screens' messages
  ui/NameInput/CharGlance.txt    the keyboard of the name entry
  end_roll/*.er2                 the rolls of text: the opening, the endings

Each file is read from extracted/VOLUME.DAT, its strings replaced, and written whole
and uncompressed to mods/espanol/files/Us/<path> (the game reads a mod's file as it
is).  With no translation `build` gives back the disc's file byte for byte
(`roundtrip` checks that for every file).

The translation of a file lives in translations/es/data/<path without extension>.tsv
(translations/es/data/item/ItemInfo.tsv, translations/es/data/end_roll/opening.tsv):

    # comments and blank lines are ignored
    <id><TAB><Spanish>

ordinary Spanish (¿ » º as they are: to_game() turns them into the font's codes);
`\\n` a line break, `\\\\` a backslash, `\\t` a tab.  No English: the original comes
from the disc each time.  Missing ids stay in English, but a string whose English
is the same as another of the same kind in the same file takes its translation.
The spaces at the ends of each line are put back as in the English.

  tools/spanish_data.py list                    the files, strings, translated
  tools/spanish_data.py extract [FILE…]         work files: translations/es/original/data/
  tools/spanish_data.py build [FILE…|--all]     mods/espanol/files/Us/<path>
  tools/spanish_data.py check [FILE…]           errors and warnings (exit 1 on errors)
  tools/spanish_data.py show FILE [ID…]         id, kind, width / room, English, Spanish
  tools/spanish_data.py roundtrip               every file rebuilt untranslated == the disc's

FILE is the path without extension (item/ItemInfo, end_roll/opening) or a
directory (end_roll); none means every file that has a translation (build, check)
or every file (list, extract).  docs/spanish/05_data.md has the formats and rules.
"""
import argparse
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spanish_font import to_game  # noqa: E402
from spanish_script import Widths  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TRANSLATIONS = ROOT / "translations" / "es" / "data"
WORK = ROOT / "translations" / "es" / "original" / "data"
OUT = ROOT / "mods" / "espanol" / "files" / "Us"
FONT = OUT / "Font" / "Samu2.Fnt"

JAPANESE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")     # kana, kanji
ICONS = set("①②③④⑤⑥←↑→↓○●") | {chr(c) for c in (0xA7, *range(0xB8, 0xC0))}
# %s %d (and in the save screen's messages %n %p), with the asterisks after them
# that kept room for the value in the original.
PLACEHOLDER = re.compile(r"%[sdnp]\**")
MARKS = "＆＃"                  # the save screen's: KB needed, the card slot
ROLL_END = "\uf8f3"             # ends the last line of a roll (drawn as nothing)


@dataclass
class Entry:
    id: str
    kind: str
    en: str                     # as the game has it (real line breaks)
    text: bool = True           # to be translated
    note: str = ""              # for the translator: whose / where
    same_as: str = ""           # the first entry of this kind with the same English
    borrowed: bool = False      # takes its Spanish from another file (see ObjectName)


# ── Kinds: where a string is seen, and its limits ─────────────────────────
# room: the widest line in pixels of the font (unscaled) that fits, if known;
#       otherwise the widest English line of that kind in the file is the guide.
# lines: most lines; breaks: "same" (the count of \n must not change: an error),
#       "none" (no \n at all: an error), None (free, within `lines`).
# chars: most characters (a fixed field).
@dataclass
class Kind:
    what: str
    room: float = 0
    lines: int = 0
    breaks: str | None = None
    chars: int = 0


SHOP_NAME_ROOM = (238 - 86) / 0.82      # shop rows: the name from x 86 to its panel's end (238), at 0.82x
SHOP_DESC_ROOM = 277 / 0.82             # shop: the description box, 277 px wide at 0.82x
KINDS = {
    "item.name": Kind("nombre del objeto: listas de objetos (0,9×), tienda (0,82×), «Has conseguido …»", room=SHOP_NAME_ROOM, lines=1, breaks="none"),
    "item.help": Kind("línea de ayuda abajo en el menú de objetos (2 líneas)", lines=2),
    "item.desc": Kind("descripción en un recuadro (tienda, creación de personaje), 3 líneas a 0,82×", room=SHOP_DESC_ROOM, lines=3),
    "item.use": Kind("mensaje al usar el objeto (casi nunca se ve: 05_data.md)", lines=2),
    "object": Kind("nombre de lo que se recoge del suelo (aviso del HUD)", lines=1, breaks="none"),
    "worn": Kind("dónde se lleva el accesorio (Récords, página de accesorios)", lines=1, breaks="none"),
    "title": Kind("título del jugador (Récords, resultados); registro fijo", lines=1, breaks="none", chars=24),
    # (the same plate as Battle.SetName's names: spanish_script.py's "nombre", 200)
    "role": Kind("nombre genérico de un personaje (barra del rival, quien habla)", room=200, lines=1, breaks="none"),
    "shop.choice": Kind("menú sí / no de la tienda: una opción por línea", breaks="same"),
    "shop.label": Kind("rótulo del monedero de la tienda (centrado, 0,82×)", room=60, lines=1, breaks="none"),
    "shop.got": Kind("aviso al comprar; %s = el objeto", room=300, lines=1, breaks="none"),
    # drawn at x 474 at 0.82x: to the picture's edge, less a margin
    "shop.hint": Kind("pista de botón al pie de la tienda (0,82×)", room=(630 - 474) / 0.82, lines=1, breaks="none"),
    "shop.line": Kind("bocadillo del tendero (el \\n manda; no se parte)", lines=2),
    "mcard": Kind("mensaje de las pantallas de guardar / cargar"),
    "mcard.short": Kind("palabra suelta de la pantalla de guardar (botón, rótulo)", lines=1, breaks="none"),
    "keys": Kind("fila del teclado de nombre: 15 caracteres (tres grupos de 5)", chars=15),
    "roll": Kind("línea de un rollo de texto (1,2×); una línea por línea, sin \\n", lines=1, breaks="none"),
}

# The rolls are drawn at 1.2x from x to the right edge of the 640 px picture; a
# line may reach x 600 (the widest English line, in ed07_01, reaches 606).
ROLL_RIGHT = 600


# ── The files ─────────────────────────────────────────────────────────────

def u16z(d: bytes, p: int) -> tuple[str, int]:
    """A 16-bit string ended by 0 at p -> (string, the offset after its 0)."""
    q = p
    while q + 1 < len(d) and (d[q] | d[q + 1]) != 0:
        q += 2
    return d[p:q].decode("utf-16-le"), q + 2


def enc(s: str) -> bytes:
    return s.encode("utf-16-le") + b"\0\0"


def has_words(s: str) -> bool:
    """Text to translate: letters, not Japanese, not a file name (item 0's description
    is "item/pim/item.BPM")."""
    return (any(c.isalpha() for c in s) and not JAPANESE.search(s)
            and not re.fullmatch(r"[\w/]+\.\w+", s))


class DataFile:
    """One file: parse() lists its strings, build() writes it with some replaced."""
    path = ""                    # under Us/

    @property
    def key(self) -> str:
        return self.path.rsplit(".", 1)[0] if "." in self.path.rsplit("/", 1)[-1] else self.path

    def parse(self, data: bytes) -> list[Entry]:
        raise NotImplementedError

    def build(self, es: dict[str, str]) -> bytes:
        raise NotImplementedError

    def room(self, e: Entry) -> float:
        return KINDS[e.kind].room


class ItemInfo(DataFile):
    """"ItIf", s16 count, s16 1, u32 offsets[count]; each record: what using it does
    (u8 usable, u8 effects, s16 amounts[2], s16 object), u32 its sprites (filled at
    run time), then offsets from the record to name, help, description, use
    (16-bit, ended by 0) and the icon's sprite sheet (ASCII), in that order; the
    icon's name is followed by its 0 and then 1 to 4 more zeros, to a multiple of 4."""
    path = "item/ItemInfo.Dat"
    FIELDS = ("name", "help", "desc", "use")

    def parse(self, data):
        self.head = data[:8]
        count, = struct.unpack_from("<h", data, 4)
        offs = struct.unpack_from(f"<{count}I", data, 8)
        self.records, out = [], []
        for n, o in enumerate(offs):
            r = struct.unpack_from("<8I", data, o)
            strings = [u16z(data, o + r[k])[0] for k in (3, 4, 5, 6)]
            icon = data[o + r[7]:data.index(b"\0", o + r[7])]
            self.records.append((data[o:o + 12], strings, icon))
            for f, s in zip(self.FIELDS, strings):
                out.append(Entry(f"{n}.{f}", f"item.{f}", s, has_words(s),
                                 note=f"objeto {n}: {strings[0]}" if f != "name" else ""))
        return out

    def build(self, es):
        body, offs = b"", []
        base = 8 + 4 * len(self.records)
        for n, (head, strings, icon) in enumerate(self.records):
            strings = [es.get(f"{n}.{f}", s) for f, s in zip(self.FIELDS, strings)]
            at, parts, rel = 0x20, [], []
            for s in strings:
                rel.append(at)
                parts.append(enc(s))
                at += len(parts[-1])
            rel.append(at)
            rec = head + struct.pack("<5I", *rel) + b"".join(parts) + icon + b"\0"
            rec += b"\0" * (4 - len(rec) % 4)         # then 1-4 zeros, to a multiple of 4
            offs.append(base + len(body))
            body += rec
        return self.head + struct.pack(f"<{len(offs)}I", *offs) + body


class ObjectName(DataFile):
    """"003", then per kind of object: its model (ASCII, 0), its name (16-bit, 0),
    float size[3], u8 param, type, a, b.  Only the first 34 (money and items) have
    English names; the rest are the developers' Japanese labels, never shown.
    An item's name here takes the Spanish of the same name in item/ItemInfo (by
    the English) unless this file's translation gives another; "5 mon" stays."""
    path = "object/ObjectName.Lst"
    borrowed: dict = {}         # English item name -> Spanish, from item/ItemInfo

    def parse(self, data):
        self.head, p, self.items, out = data[:3], 3, [], []
        while p < len(data):
            e = data.index(b"\0", p)
            model = data[p:e + 1]
            name, p = u16z(data, e + 1)
            self.items.append((model, name, data[p:p + 16]))
            out.append(Entry(str(len(self.items) - 1), "object", name,
                             has_words(name) and not re.fullmatch(r"\d+ mon", name)))
            p += 16
        return out

    def build(self, es):
        return self.head + b"".join(m + enc(es.get(str(n), s)) + rest
                                    for n, (m, s, rest) in enumerate(self.items))


class Strings(DataFile):
    """16-bit strings one after another (each ended by 0), after a byte-order mark
    (`bom`); the list ends with an empty string."""
    bom = False
    kind = ""

    def parse(self, data):
        start = 2 if self.bom else 0
        if self.bom and data[:2] != b"\xff\xfe":
            raise ValueError(f"{self.path}: no byte-order mark")
        self.lead = data[:start]
        parts = data[start:].decode("utf-16-le").split("\0")
        self.strings = parts
        return [Entry(str(n), self.kind_of(s), s, has_words(s)) for n, s in enumerate(parts[:-1])]

    def kind_of(self, s: str) -> str:
        return self.kind

    def build(self, es):
        parts = [es.get(str(n), s) for n, s in enumerate(self.strings[:-1])] + [self.strings[-1]]
        return self.lead + "\0".join(parts).encode("utf-16-le")


class AccessoryPos(Strings):
    path = "Accessory/AccessoryPos.Lst"
    bom = True
    kind = "worn"


class McardMessages(Strings):
    """The save screens' messages, by their number (see src/game/mcard.cpp)."""
    path = "mcard/message.dat"
    kind = "mcard"

    def kind_of(self, s):
        return "mcard" if "\n" in s or len(s) > 24 else "mcard.short"


class TitleNames(DataFile):
    """s32 count, then count records of 0x32 bytes: a 16-bit name and zeros."""
    path = "menu/Title/TitleNameList"
    SIZE = 0x32

    def parse(self, data):
        count, = struct.unpack_from("<i", data)
        self.names = [data[4 + i * self.SIZE:4 + (i + 1) * self.SIZE].decode("utf-16-le").split("\0")[0]
                      for i in range(count)]
        return [Entry(str(n), "title", s) for n, s in enumerate(self.names)]

    def build(self, es):
        out = struct.pack("<i", len(self.names))
        for n, s in enumerate(self.names):
            raw = es.get(str(n), s).encode("utf-16-le")
            if len(raw) > self.SIZE - 2:
                raise ValueError(f"{self.path}: title {n} longer than {(self.SIZE - 2) // 2} characters")
            out += raw + b"\0" * (self.SIZE - len(raw))
        return out


# The generic names in chara/paramlist (the rest are people's names, kept).
ROLES = {
    "Thug", "Magistrate", "Warrior", "Merchant", "Citizen", "Foreigner", "Wife", "Guard", "Monk",
    "Child", "Girl", "Traveler", "Samurai", "Man", "Contact", "Old lady", "Ronin", "No-name",
    "Peddler", "Student", "Killer", "Character", "Lady", "Townsperson", "Courtesan", "Job Broker",
    "Collector", "Shady Man", "Kidnapper", "Son", "Daughter", "Spy", "Teacher", "Sculptor", "Worker",
    "The Count", "Carpenter", "Steward", "Informant",
}


class ParamList(DataFile):
    """u16 count, u16 version (9), then per character 14 s32 (id, health, sword,
    faction, model, ?, unique, role, ?, ?, child, ?, flag, ?) and its name: s32
    bytes, 16-bit characters padded with 0 to a multiple of 4 bytes."""
    path = "chara/paramlist"
    FIELDS = 14

    def parse(self, data):
        count, version = struct.unpack_from("<HH", data)
        if version != 9:
            raise ValueError(f"{self.path}: version {version}, not 9")
        p, self.head, self.chars, out = 4, data[:4], [], []
        for n in range(count):
            nums = data[p:p + 4 * self.FIELDS]
            p += 4 * self.FIELDS
            size, = struct.unpack_from("<i", data, p)
            name = data[p + 4:p + 4 + size].decode("utf-16-le").rstrip("\0")
            p += 4 + size
            self.chars.append((nums, name))
            out.append(Entry(str(n), "role", name, name in ROLES,
                             note=f"personaje {struct.unpack_from('<i', nums)[0]}"))
        return out

    def build(self, es):
        out = self.head
        for n, (nums, name) in enumerate(self.chars):
            raw = es.get(str(n), name).encode("utf-16-le")
            raw += b"\0" * (-len(raw) % 4)
            out += nums + struct.pack("<i", len(raw)) + raw
        return out


SHOP_LINES = ["al entrar", "¿qué desea?", "¿se lo lleva?", "gracias (al coger)", "cobro",
              "no le llega el dinero", "se niega a pagar", "pide ayuda (robo)",
              "gracias, vuelva", "no puede llevar más", "gracias (al salir)"]
SHOP_COMMON = ["shop.choice", "shop.choice", "shop.label", "shop.got", "shop.hint"]


class ShopList(DataFile):
    """s32 3, s32 count; five common strings (the two yes / no menus, "Money", "You
    got the %s", the quit hint); per shop: s16 goods[4][8][2], then eleven
    {s16 voice, 16-bit line} and its sign's sprite sheet (ASCII, padded to even).
    Shop 12 is a Japanese test shop."""
    path = "ui/GameUI/ShopList.dat"

    def parse(self, data):
        version, count = struct.unpack_from("<ii", data)
        if version != 3:
            raise ValueError(f"{self.path}: version {version}, not 3")
        p, out = 8, []
        self.common = []
        for i in range(5):
            s, p = u16z(data, p)
            self.common.append(s)
            out.append(Entry(f"c{i}", SHOP_COMMON[i], s))
        self.shops = []
        for k in range(count):
            goods = data[p:p + 0x80]
            p += 0x80
            lines = []
            for i in range(11):
                voice = data[p:p + 2]
                s, p = u16z(data, p + 2)
                lines.append((voice, s))
            e = data.index(b"\0", p)
            n = e + 1 - p
            sheet = data[p:p + n + (n & 1)]
            p += n + (n & 1)
            self.shops.append((goods, lines, sheet))
            name = sheet.rstrip(b"\0").decode("latin1").rsplit("/", 1)[-1]
            for i, (voice, s) in enumerate(lines):
                v, = struct.unpack("<h", voice)
                out.append(Entry(f"{k}.{i}", "shop.line", s, has_words(s),
                                 note=f"{name}, {SHOP_LINES[i]}" + (f", voz {v}" if v else "")))
        return out

    def build(self, es):
        out = struct.pack("<ii", 3, len(self.shops))
        out += b"".join(enc(es.get(f"c{i}", s)) for i, s in enumerate(self.common))
        for k, (goods, lines, sheet) in enumerate(self.shops):
            out += goods + b"".join(v + enc(es.get(f"{k}.{i}", s)) for i, (v, s) in enumerate(lines)) + sheet
        return out


class CharGlance(DataFile):
    """The name entry's keyboard: 16-bit text with a byte-order mark, CR LF.  The
    first page (up to a blank line) is the keyboard, 15 characters a row, rows one
    after another (the game joins them: only the last may be short); six rows are
    shown and the grid scrolls for more (src/game/name_input.cpp).  After it come
    the developers' unused Japanese pages, kept."""
    path = "ui/NameInput/CharGlance.txt"

    def parse(self, data):
        if data[:2] != b"\xff\xfe":
            raise ValueError(f"{self.path}: no byte-order mark")
        text = data[2:].decode("utf-16-le")
        page, sep, self.rest = text.partition("\r\n\r\n")
        self.rows = page.split("\r\n")
        return [Entry(str(n), "keys", r) for n, r in enumerate(self.rows)]

    def build(self, es):
        rows = list(self.rows)
        extra = sorted(int(k) for k in es if k.isdigit() and int(k) >= len(rows))
        if extra and extra != list(range(len(rows), len(rows) + len(extra))):
            raise ValueError(f"{self.path}: new rows must follow row {len(rows) - 1} without gaps")
        rows += [""] * len(extra)
        rows = [es.get(str(n), r) for n, r in enumerate(rows)]
        return b"\xff\xfe" + ("\r\n".join(rows) + "\r\n\r\n" + self.rest).encode("utf-16-le")


class Roll(DataFile):
    """An .er2 roll (src/game/text_roll.cpp): s16 x, y, mode, frames, stay, pad;
    float speed; s16 voice count, {s16 frame, voice}; then the lines: {s16 pixels
    below the line before, 16-bit text, 0}.  The timing is in the header and the
    gaps, which are kept: the Spanish has as many lines as the English."""

    def __init__(self, name):
        self.path = f"end_roll/{name}.er2"

    def parse(self, data):
        x, y, mode, frames, stay = struct.unpack_from("<5h", data)
        self.x = x
        voices, = struct.unpack_from("<h", data, 0x10)
        p = 0x12 + 4 * voices
        self.head, self.lines, out = data[:p], [], []
        while p + 2 <= len(data):
            gap = data[p:p + 2]
            s, p = u16z(data, p + 2)
            self.lines.append((gap, s))
        if p != len(data):
            raise ValueError(f"{self.path}: the last line is not ended")
        for n, (_, s) in enumerate(self.lines):
            out.append(Entry(str(n), "roll", s.replace(ROLL_END, "").rstrip(" "), has_words(s),
                             note=f"x {x}, {'sube' if mode == 0 else 'fija'}, {frames} fotogramas"))
        return out

    def build(self, es):
        out = self.head
        for n, (gap, s) in enumerate(self.lines):
            if str(n) in es:
                tail = s[len(s.replace(ROLL_END, "").rstrip(" ")):]    # " \uf8f3" of the last line
                s = es[str(n)] + tail
            out += gap + enc(s)
        return out

    def room(self, e):
        return (ROLL_RIGHT - self.x) / 1.2


ROLLS = ["opening", "ed01_01", "ed02_01", "ed02_02", "ed03_01", "ed03_02", "ed04_01", "ed04_02",
         "ed04_03", "ed05_01", "ed06_01", "ed07_01", "ed08_01", "ed09_01", "ed10_01", "ed11_01",
         "ed12_01", "ed13_01", "ed14_01", "jiseinoku", "later_01", "yokujitu", "doujitu"]
# Rolls written in capitals on purpose (Sayo's letter, misspelt: see 05_data.md).
CAPITALS_OK = {"end_roll/ed05_01"}


def all_files() -> list[DataFile]:
    return [ItemInfo(), ObjectName(), AccessoryPos(), TitleNames(), ParamList(), ShopList(),
            McardMessages(), CharGlance()] + [Roll(n) for n in ROLLS]


# ── Translations ──────────────────────────────────────────────────────────

def tsv_path(f: DataFile) -> Path:
    return TRANSLATIONS / f"{f.key}.tsv"


def unescape(s: str, where: str) -> str:
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            nxt = s[i + 1:i + 2]
            if nxt not in ("n", "\\", "t"):
                raise ValueError(f"{where}: unknown escape \\{nxt} (only \\n, \\\\, \\t)")
            out.append({"n": "\n", "\\": "\\", "t": "\t"}[nxt])
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")


def read_translation(path: Path) -> dict[str, str]:
    out = {}
    if not path.exists():
        return out
    for k, raw in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        raw = raw.rstrip("\r")
        if not raw.strip() or raw.startswith("#"):
            continue
        if "\t" not in raw:
            raise ValueError(f"{path}:{k}: no tab between id and text")
        key, text = raw.split("\t", 1)
        key = key.strip()
        if key in out:
            raise ValueError(f"{path}:{k}: id {key} given twice")
        out[key] = unescape(text, f"{path}:{k}")
    return out


def edges(en: str, es: str) -> str:
    """The Spanish with the spaces at the ends of each line as in the English (of
    the whole string when the number of lines differs)."""
    def one(a, b):
        return a[:len(a) - len(a.lstrip(" "))] + b.strip(" ") + a[len(a.rstrip(" ")):]
    a, b = en.split("\n"), es.split("\n")
    if len(a) == len(b):
        return "\n".join(one(x, y) for x, y in zip(a, b))
    return one(en, es)


def link_repeats(entries: list[Entry]) -> None:
    first = {}
    for e in entries:
        if e.text:
            e.same_as = first.setdefault((e.kind, e.en), e.id)
            if e.same_as == e.id:
                e.same_as = ""


def resolved(f: DataFile, entries: list[Entry], spanish: dict[str, str], game: bool = True) -> dict[str, str]:
    """id -> the Spanish as the game gets it: its own or its first duplicate's, the
    spaces at the ends as in the English, through to_game (unless `game` is false)."""
    conv = to_game if game else (lambda x: x)
    by_id = {e.id: e for e in entries}
    out = {}
    for e in entries:
        es = spanish.get(e.id)
        if es is None and e.same_as:
            es = spanish.get(e.same_as)
        if es is None and e.borrowed:
            es = f.borrowed.get(e.en)
        if es is None and e.text:
            # any other duplicate translated (the first one may be left)
            for o in entries:
                if o.text and o.kind == e.kind and o.en == e.en and o.id in spanish:
                    es = spanish[o.id]
                    break
        if es is None:
            continue
        if e.kind != "keys":
            es = edges(e.en, es)
        out[e.id] = conv(es)
    # rows beyond the keyboard's last are new
    if isinstance(f, CharGlance):
        for k, es in spanish.items():
            if k not in by_id:
                out[k] = conv(es)
    return out


# ── Checking ──────────────────────────────────────────────────────────────

class Disc:
    def __init__(self):
        import volume
        self.vol = volume.Volume()

    def read(self, f: DataFile) -> bytes:
        return self.vol.read_path(f.path)


def loaded(f: DataFile, disc: Disc) -> list[Entry]:
    entries = f.parse(disc.read(f))
    link_repeats(entries)
    if isinstance(f, ObjectName):
        items = ItemInfo()
        names = [e for e in loaded(items, disc) if e.kind == "item.name"]
        es = resolved(items, names, read_translation(tsv_path(items)), game=False)
        f.borrowed = {e.en: es[e.id] for e in names if e.id in es}
        known = {e.en for e in names}
        for e in entries:
            if e.text and e.en in known:
                e.borrowed = True
                e.note = "= nombre en item/ItemInfo"
    return entries


def width(widths: Widths, s: str) -> int:
    """The widest line, without the spaces at its end (some strings carry many)."""
    return max(widths.line(line.rstrip(" ")) for line in s.split("\n"))


def english_room(entries: list[Entry], widths: Widths) -> dict[str, int]:
    room = {}
    for e in entries:
        if e.text:
            room[e.kind] = max(room.get(e.kind, 0), width(widths, e.en))
    return room


def room_of(f: DataFile, e: Entry, eroom: dict[str, int]) -> float:
    """The larger of the room known for the place and the widest English of the kind."""
    return max(f.room(e), eroom.get(e.kind, 0))


def capitals(s: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    return len(letters) >= 6 and all(c.isupper() for c in letters)


def check_file(f: DataFile, disc: Disc, widths: Widths, verbose: bool = True) -> tuple[int, int]:
    entries = loaded(f, disc)
    spanish = read_translation(tsv_path(f))
    by_id = {e.id: e for e in entries}
    eroom = english_room(entries, widths)
    errors = warnings = 0

    def report(kind, i, msg):
        nonlocal errors, warnings
        if kind == "error":
            errors += 1
        else:
            warnings += 1
        if verbose or kind == "error":
            print(f"{f.key}: {kind:7} {i:>6}  {msg}")

    keyboard = isinstance(f, CharGlance)
    for i, es in spanish.items():
        e = by_id.get(i)
        if e is None and keyboard and i.isdigit():
            e = Entry(i, "keys", "", True)
        if e is None:
            report("error", i, "no such id in the file")
            continue
        if not e.text:
            report("error", i, f"not a string to translate ({e.en!r})")
            continue
        k = KINDS[e.kind]
        game = to_game(es)
        if not es.strip() and e.en.strip():
            report("error", i, "empty")
        if PLACEHOLDER.findall(e.en) != PLACEHOLDER.findall(es):
            report("error", i, f"placeholders {PLACEHOLDER.findall(e.en)} -> {PLACEHOLDER.findall(es)}")
        for m in MARKS:
            if e.en.count(m) != es.count(m):
                report("error", i, f"{m} {e.en.count(m)} -> {es.count(m)}")
        icons_en = sorted(c for c in e.en if c in ICONS)
        icons_es = sorted(c for c in game if c in ICONS)
        if icons_en != icons_es:
            report("error", i, f"icons {''.join(icons_en)!r} -> {''.join(icons_es)!r}")
        if missing := widths.missing(game.replace(ROLL_END, "")):
            report("error", i, f"not in the font: {''.join(sorted(missing))!r}")
        if "\r" in es or "\t" in es:
            report("error", i, "a CR or a tab")
        n_en, n_es = e.en.count("\n"), es.count("\n")
        if k.breaks == "none" and n_es:
            report("error", i, "a line break (\\n) where the game draws one line")
        elif k.breaks == "same" and n_en != n_es:
            report("error", i, f"{n_en + 1} lines -> {n_es + 1} (one per option)")
        elif k.lines and n_es + 1 > max(k.lines, n_en + 1):
            report("warning", i, f"{n_es + 1} lines (at most {k.lines})")
        if k.chars and len(game) > k.chars:
            report("error", i, f"{len(game)} characters (at most {k.chars})")
        if keyboard:
            last = max(int(x) for x in [*by_id, *spanish] if x.isdigit())
            if int(i) != last and len(game) != 15:
                report("error", i, f"{len(game)} keys: every row but the last has 15")
        room = room_of(f, e, eroom)
        w = width(widths, game)
        if room and w > room:
            report("warning", i, f"{w} px > {room:.0f}: {es!r}")
        if e.borrowed and f.borrowed.get(e.en, es) != es:
            report("warning", i, f"item/ItemInfo calls it {f.borrowed[e.en]!r}")
        if capitals(es) and f.key not in CAPITALS_OK:
            report("warning", i, f"in capitals (write normal case): {es!r}")
    if keyboard:
        rows = [spanish.get(str(n), r) for n, r in enumerate(f.rows)]
        rows += [spanish[str(n)] for n in range(len(f.rows), len(f.rows) + 100) if str(n) in spanish]
        keys = to_game("".join(rows))
        dup = sorted({c for c in keys if keys.count(c) > 1 and c != " "})
        if dup:
            report("warning", "-", f"keys twice: {''.join(dup)!r}")
    # duplicates translated differently
    seen = {}
    for e in entries:
        if e.text and e.id in spanish:
            other = seen.setdefault((e.kind, e.en), (e.id, spanish[e.id]))
            if other[1] != spanish[e.id]:
                report("warning", e.id, f"same English as {other[0]}, translated differently")
    # all the strings put together must still build
    try:
        f.build(resolved(f, entries, spanish))
    except ValueError as ex:
        report("error", "-", str(ex))
    done, total = counts(f, entries, spanish)
    extra = sum(1 for k in spanish if k not in by_id)
    if verbose:
        more = f" (+{extra} new rows)" if keyboard and extra else ""
        print(f"{f.key}: {done} of {total} distinct strings translated{more}; {errors} errors, {warnings} warnings")
    return errors, warnings


def counts(f: DataFile, entries: list[Entry], spanish: dict[str, str]) -> tuple[int, int]:
    distinct = [e for e in entries if e.text and not e.same_as and not e.borrowed]
    translated = set()
    for e in entries:
        if e.text and (e.id in spanish or (e.borrowed and e.en in getattr(f, "borrowed", {}))):
            translated.add((e.kind, e.en))
    return sum(1 for e in distinct if (e.kind, e.en) in translated), len(distinct)


# ── Commands ──────────────────────────────────────────────────────────────

def has_translation(f: DataFile) -> bool:
    """A translation of its own, or (ObjectName) of the names it borrows."""
    return tsv_path(f).exists() or (isinstance(f, ObjectName) and tsv_path(ItemInfo()).exists())


def select(names: list[str], only_translated: bool) -> list[DataFile]:
    files = all_files()
    if not names:
        return [f for f in files if not only_translated or has_translation(f)]
    out = []
    for n in names:
        n = n.strip("/")
        hit = [f for f in files if f.key == n or f.path == n or f.key.startswith(n + "/")]
        if not hit:
            sys.exit(f"unknown file {n!r}: tools/spanish_data.py list")
        out += [f for f in hit if f not in out]
    return out


def out_path(f: DataFile) -> Path:
    return OUT / f.path


def work_file(f: DataFile, entries: list[Entry], widths: Widths) -> str:
    eroom = english_room(entries, widths)
    repeats = {}
    for e in entries:
        if e.same_as:
            repeats.setdefault(e.same_as, []).append(e.id)
    lines = [f"# {f.path}: id<TAB>English. Translation: translations/es/data/{f.key}.tsv",
             "# (repeated strings and names taken from another file are left out)",
             "# kinds: " + ", ".join(sorted({e.kind for e in entries if e.text})),
             ""]
    for e in entries:
        if not e.text or e.same_as or e.borrowed:
            continue
        room = room_of(f, e, eroom)
        info = [e.kind, f"{width(widths, e.en)}/{room:.0f}px"]
        if e.note:
            info.append(e.note)
        if e.id in repeats:
            info.append("repetida en: " + " ".join(repeats[e.id]))
        lines.append("# " + " | ".join(info))
        lines.append(f"{e.id}\t{escape(e.en)}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["list", "extract", "build", "check", "show", "roundtrip"])
    ap.add_argument("names", nargs="*", help="files (show: FILE then ids)")
    ap.add_argument("--all", action="store_true", help="build: every file, translated or not")
    ap.add_argument("--out", type=Path, default=OUT, help="build: the Us/ directory to write into")
    ap.add_argument("--font", type=Path, default=FONT, help="the mod's .Fnt (for widths)")
    ap.add_argument("-q", "--quiet", action="store_true", help="check: errors and totals only")
    args = ap.parse_args()
    disc = Disc()

    if args.command == "roundtrip":
        bad = 0
        for f in all_files():
            data = disc.read(f)
            entries = loaded(f, disc)
            same = f.build({}) == data
            # and with every string "translated" as itself, through the whole path
            again = f.build(resolved(f, entries, {e.id: e.en for e in entries if e.text})) == data
            print(f"{f.path:32} {len(data):6} bytes  {'same' if same else 'DIFFERENT'}"
                  f"{'' if again else '  (DIFFERENT through resolved())'}")
            bad += (not same) + (not again)
        sys.exit(1 if bad else 0)

    if args.command == "show":
        if not args.names:
            sys.exit("show FILE [ID…]")
        f = select(args.names[:1], False)[0]
        ids = set(args.names[1:])
        widths = Widths(args.font)
        entries = loaded(f, disc)
        spanish = read_translation(tsv_path(f))
        final = resolved(f, entries, spanish, game=False)
        eroom = english_room(entries, widths)
        if isinstance(f, CharGlance):
            entries += [Entry(k, "keys", "", True) for k in final if k not in {e.id for e in entries}]
        for e in entries:
            if (ids and e.id not in ids) or (not ids and not e.text):
                continue
            es = final.get(e.id)
            w_es = width(widths, to_game(es)) if es is not None else "-"
            room = room_of(f, e, eroom)
            print(f"{e.id:>6} {e.kind:12} {width(widths, e.en):4} {w_es:>4} /{room:4.0f}  {escape(e.en)}")
            if e.same_as:
                print(f"{'':31}(= {e.same_as})")
            print(f"{'':31}{escape(es) if es is not None else '(sin traducir)'}")
        return

    files = select(args.names, only_translated=args.command in ("build", "check") and not args.all)

    if args.command == "list":
        total = [0, 0, 0]
        print(f"{'file':32} {'strings':>7} {'distinct':>8} {'done':>5}")
        for f in files:
            entries = loaded(f, disc)
            done, distinct = counts(f, entries, read_translation(tsv_path(f)))
            n = sum(1 for e in entries if e.text)
            print(f"{f.key:32} {n:7} {distinct:8} {done:5}")
            total = [total[0] + n, total[1] + distinct, total[2] + done]
        print(f"{'total':32} {total[0]:7} {total[1]:8} {total[2]:5}")
    elif args.command == "extract":
        widths = Widths(args.font)
        for f in files:
            entries = loaded(f, disc)
            out = WORK / f"{f.key}.tsv"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(work_file(f, entries, widths), encoding="utf-8")
            print(f"wrote {out.relative_to(ROOT)}")
    elif args.command == "build":
        for f in files:
            entries = loaded(f, disc)
            spanish = read_translation(tsv_path(f))
            out = args.out / f.path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(f.build(resolved(f, entries, spanish)))
            done, distinct = counts(f, entries, spanish)
            borrowed = sum(1 for e in entries if e.borrowed and e.en in f.borrowed)
            more = f", {borrowed} names from item/ItemInfo" if borrowed else ""
            print(f"wrote {out}: {done} of {distinct} strings in Spanish{more}")
    elif args.command == "check":
        widths = Widths(args.font)
        errors = warnings = 0
        for f in files:
            e, w = check_file(f, disc, widths, verbose=not args.quiet)
            errors += e
            warnings += w
        print(f"{len(files)} files: {errors} errors, {warnings} warnings")
        sys.exit(1 if errors else 0)


if __name__ == "__main__":
    try:
        main()
    except ValueError as ex:           # a translation that cannot be read, a field too long
        sys.exit(f"error: {ex}")
