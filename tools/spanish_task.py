#!/usr/bin/env python3
"""
Spanish mod, step 6: the text of the actors' tasks (Us/task/alltask, asset 0x8A).

What the townsfolk, gangsters, guards and job givers say on the streets comes from
their task (see src/game/task.cpp, task_mgr.cpp, task_actions.cpp and tools/task.py).
task/alltask is a container of 182 task files, each LZSS-packed, in the order of the
executable's name table (0x2D7D10):

    u32 count, u32 alignment (64), u32 data start, u32 0, u32 table[count]
    then each entry at the alignment: u32 packed (bytes of the entry, these 8 too),
    u32 unpacked size, the LZSS stream; zeros up to table[i] = packed rounded up to 16,
    and zeros up to the alignment.

A task file is u32, then 11 programs; a program is a count and its commands
{index, op, float seconds, who1, who2, text length, text (UTF-16, the length rounded
up to 4, a 0 only if it fits), 5 x {type, value}}.  Six commands carry text that is
shown (KINDS below).  The mod's file (mods/espanol/files/Us/task/alltask) is the
container as the volume gives it: the port reads it whole and unpacks one entry when
an actor needs that task (spawner.cpp, LoadTask).  `build` keeps the disc's bytes
of every task that has no Spanish, and packs the others again.

A string is known by "<task>:<program>.<command index>" (work_bugyo_a:0.260): what the
game itself uses to tell commands apart, fixed because the disc never changes, and
readable.  The same English (spaces about line breaks aside) in many places is
translated once, under the id where it comes first in the order of the batches; every
other place takes that translation unless the .tsv gives its own id too.

The translation: translations/es/task/<batch>.tsv (all the .tsv there are read):

    # comments and blank lines are ignored
    <id><TAB><Spanish, \\n for a line break>

  tools/spanish_task.py list [--tasks]        batches (or tasks), strings, done
  tools/spanish_task.py extract BATCH|all     work files: translations/es/original/task/
  tools/spanish_task.py build                 mods/espanol/files/Us/task/alltask
  tools/spanish_task.py check [BATCH…]        errors and warnings (exit 1 on errors)
  tools/spanish_task.py show TASK|ID…         id, kind, who, widths, English, Spanish
  tools/spanish_task.py verify [--pack-all]   round trips: container, tasks, LZSS, build

docs/spanish/06_tasks.md has the rules and the batches.
"""
import argparse
import re
import struct
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spanish_font import to_game  # noqa: E402
from spanish_text import ICONS  # noqa: E402
from spanish_script import Widths  # noqa: E402

from wotsroot import ROOT  # noqa: E402
TRANSLATIONS = ROOT / "translations" / "es" / "task"
WORK = ROOT / "translations" / "es" / "original" / "task"
OUT = ROOT / "mods" / "espanol" / "files" / "Us" / "task" / "alltask"
FONT = ROOT / "mods" / "espanol" / "files" / "Us" / "Font" / "Samu2.Fnt"
GAME_PATH = "task/alltask"
DATALIST = "task/DataList"          # asset 0x40: the kinds of actor and their tasks
LEVELS = 11

# op -> kind.  See docs/spanish/06_tasks.md for where each one is seen.
KINDS = {
    0x10: "bocadillo",      # DrawSerif: a balloon; not wrapped, the \n rule
    0x24: "eleccion",       # DrawTalkSelect: the player's choices, one a line
    0x2D: "aviso",          # DrawInfoPlate: a plate on the HUD
    0x3F: "objetivo",       # SetWorkMessage: the job's line on the status screen
    0x46: "encargo",        # SetWorkName: the job's name (HUD plate, status screen)
    0x58: "estado",         # SetOtherMessage: the status screen's line (pickpockets)
    0x05: "voz",            # PlayVoice: has text in 3 commands, never shown
}
OPS = {v: k for k, v in KINDS.items()}

# Widest line (pixels of the font at 1x) a kind may take: the larger of this and its
# English.  Balloons and choices grow with the text and are not wrapped (the English
# of the tasks: balloons up to 300, choices 318, plates 237, job names 141).  Seen in
# the game: a 324 px balloon is whole; the status screen's "Trabajo : " line has room
# for about 200 px of job name.
ROOM = {"bocadillo": 330, "eleccion": 450, "aviso": 300, "encargo": 200}
BALLOON_LINES = 3           # the English never has more
# SetWorkName keeps the name only if it is shorter than 0x18 characters.
NAME_CHARS = 0x18
# SetWorkMessage keeps the text only if its length field (bytes, rounded up to 4) < 0xF0.
MESSAGE_BYTES = 0xF0
# SetOtherMessage copies into 0x100 bytes (PlayerData +0x6D40).
OTHER_CHARS = 0x80
# The status screen's help line (status_menu.cpp, Frame_Draw): Font_DrawBox at 0.88,
# 0x1EA0 wide, 800 high, wrap + clip: characters (not words) go to the next line at
# the right edge, and a line that starts below the box is not drawn.  3 lines fit.
HELP_SCALE, HELP_W, HELP_H, LINE_H = 0.88, 0x1EA0, 800, 0x160

WHO = {0: "el jugador", 1: "el NPC", 2: "su objetivo", 6: "su acompañante", 7: "otro"}

# Order of the batches: jobs, main characters, then the rest; tasks nobody uses last.
GROUPS = [("work", "work_"), ("main", "main_"), ("news", "news_"),
          ("magistrate", ("magistrate_", "magistoka_")), ("evil", "evil_"), ("normal", "normal_")]
BATCH_TARGET, BATCH_MAX = 200, 250
FEMALE = ("lady", "girl", "madam", "woman", "yujo", "chiyo", "kasumi", "oboro", "otomi", "nami",
          "kyojiro")
JAPANESE = re.compile(r"[぀-ヿ一-鿿]")
NAME = re.compile(r"%[sS]")
ID = re.compile(r"^([a-z0-9_]+):(\d+)\.(\d+)$")


# ── LZSS (spawner.cpp, Unpack: 4 KB window from 0xFEE) ───────────────────

def unpack(entry: bytes) -> bytes:
    """As the game's Unpack (0x13BA60), its bounds included."""
    packed, size = struct.unpack_from("<2I", entry, 0)
    src = entry + b"\0\0"          # it may read one byte past `packed`
    window = bytearray(0x1000)
    out = bytearray()
    w, flags, read = 0xFEE, 0, 8

    def byte():
        nonlocal read
        if packed < read:
            raise StopIteration
        b = src[read]
        read += 1
        return b

    try:
        while True:
            flags >>= 1
            if not flags & 0x100:
                flags = byte() | 0xFF00
            if flags & 1:
                b = byte()
                out.append(b)
                window[w] = b
                w = (w + 1) & 0xFFF
                if size < len(out) - 1:
                    break
            else:
                lo, hi = byte(), byte()
                at = lo | (hi & 0xF0) << 4
                for k in range((hi & 0xF) + 3):
                    b = window[(at + k) & 0xFFF]
                    out.append(b)
                    window[w] = b
                    w = (w + 1) & 0xFFF
                    if size < len(out) - 1:
                        break
                else:
                    continue
                break
    except StopIteration:
        pass
    return bytes(out[:size])


def pack(data: bytes) -> bytes:
    """LZSS in the game's format: greedy, matches 3..18 bytes within the last 4078
    (never into the window's untouched start), 8-byte header {packed, size}."""
    n = len(data)
    out = bytearray(struct.pack("<2I", 0, n))
    heads: dict[bytes, list[int]] = {}
    i = 0
    while i < n:
        flag_at = len(out)
        out.append(0)
        flags = 0
        for bit in range(8):
            if i >= n:
                break
            best, best_at = 0, 0
            if i + 3 <= n:
                cands = heads.get(data[i:i + 3])
                if cands:
                    limit = min(18, n - i)
                    for j in reversed(cands[-48:]):
                        if i - j > 0x1000 - 18:
                            break
                        k = 3
                        while k < limit and data[j + k] == data[i + k]:
                            k += 1
                        if k > best:
                            best, best_at = k, j
                            if k == limit:
                                break
            step = best if best >= 3 else 1
            for p in range(i, min(i + step, n - 2)):
                heads.setdefault(data[p:p + 3], []).append(p)
            if best >= 3:
                pos = (0xFEE + best_at) & 0xFFF
                out += bytes((pos & 0xFF, (pos >> 4) & 0xF0 | (best - 3)))
            else:
                flags |= 1 << bit
                out.append(data[i])
            i += step
        out[flag_at] = flags
    struct.pack_into("<I", out, 0, len(out))
    return bytes(out)


# ── The container ────────────────────────────────────────────────────────

def read_container(blob: bytes) -> tuple[int, list[bytes]]:
    count, align, start, zero = struct.unpack_from("<4I", blob, 0)
    if zero != 0 or align & (align - 1) or start != _up(16 + 4 * count, align):
        raise ValueError("task/alltask: not the expected header")
    table = struct.unpack_from(f"<{count}I", blob, 16)
    entries, off = [], start
    for i, size in enumerate(table):
        packed, = struct.unpack_from("<I", blob, off)
        if _up(packed, 16) != size:
            raise ValueError(f"task/alltask: entry {i}: packed {packed}, table {size}")
        entries.append(blob[off:off + packed])
        off += _up(size, align)
    if off != len(blob):
        raise ValueError("task/alltask: does not end after its last entry")
    if write_container(align, entries) != blob:
        raise ValueError("task/alltask: does not write back as it was")
    return align, entries


def write_container(align: int, entries: list[bytes]) -> bytes:
    count = len(entries)
    start = _up(16 + 4 * count, align)
    head = struct.pack(f"<4I{count}I", count, align, start, 0, *(_up(len(e), 16) for e in entries))
    out = bytearray(head.ljust(start, b"\0"))
    for e in entries:
        out += e.ljust(_up(_up(len(e), 16), align), b"\0")
    return bytes(out)


def _up(n: int, a: int) -> int:
    return (n + a - 1) & ~(a - 1)


# ── A task file ──────────────────────────────────────────────────────────

@dataclass
class Command:
    level: int
    index: int
    op: int
    who1: int
    who2: int
    head: bytes             # the 24 bytes up to the text
    raw: bytes              # the text bytes, as on the disc
    tail: bytes             # the 5 arguments
    text: str = ""          # the text up to its 0

    def encoded(self, text: str | None) -> bytes:
        if text is None or text == self.text:
            return self.head + self.raw + self.tail
        units = text.encode("utf-16-le")
        length = (len(units) + 3) & ~3          # a 0 at the end only if it fits, as the disc
        body = units.ljust(length, b"\0")
        return self.head[:20] + struct.pack("<i", length) + body + self.tail


@dataclass
class TaskFile:
    first: bytes
    programs: list[tuple[int, list[Command]]]

    def commands(self):
        for _, cmds in self.programs:
            yield from cmds

    def serialize(self, texts: dict[tuple[int, int], str] | None = None) -> bytes:
        texts = texts or {}
        out = bytearray(self.first)
        for count, cmds in self.programs:
            out += struct.pack("<i", count)
            for c in cmds:
                out += c.encoded(texts.get((c.level, c.index)))
        return bytes(out)


def parse_task(data: bytes) -> TaskFile:
    """As Task_Load (task.cpp): the length is skipped rounded down to 4."""
    o, programs = 4, []
    for level in range(LEVELS):
        count, = struct.unpack_from("<i", data, o)
        o += 4
        cmds = []
        while count > 0:
            index, op, _, who1, who2, length = struct.unpack_from("<2if3i", data, o)
            head = data[o:o + 24]
            o += 24
            raw = b""
            if length > 0:
                if length & 3:
                    raise ValueError(f"program {level} command {index}: text length {length}")
                raw = data[o:o + length]
                o += length
            tail = data[o:o + 40]
            o += 40
            text = raw.decode("utf-16-le").split("\0")[0] if raw else ""
            cmds.append(Command(level, index, op, who1, who2, head, raw, tail, text))
            if index == count - 1:
                break
        programs.append((count, cmds))
    if o != len(data):
        raise ValueError(f"{len(data) - o} bytes after the last program")
    return TaskFile(data[:4], programs)


# ── The strings ──────────────────────────────────────────────────────────

@dataclass
class Text:
    id: str
    task: str               # short name: work_bugyo_a
    level: int
    index: int
    op: int
    who1: int
    who2: int
    en: str
    used: bool              # the task is in task/DataList
    cls: str = "texto"      # texto, signos, japones, sin_uso
    key: str = ""
    canon: str = ""         # the id whose translation it takes
    before: str = ""        # the text command before it in the program

    @property
    def kind(self) -> str:
        return KINDS[self.op]


def key_of(en: str) -> str:
    return "\n".join(" ".join(line.split()) for line in en.split("\n"))


def group_of(task: str) -> str:
    for name, prefix in GROUPS:
        if task.startswith(prefix):
            return name
    return "other"


def female(task: str) -> bool:
    return any(f in task for f in FEMALE)


class Disc:
    def __init__(self, path: Path | None = None):
        import task as task_tool
        import volume
        vol = volume.Volume()
        self.blob = path.read_bytes() if path else vol.read_path(GAME_PATH)
        self.align, self.entries = read_container(self.blob)
        self.names = [n.split("/")[-1][:-4] for n in task_tool.names()]
        if len(self.names) != len(self.entries):
            raise ValueError(f"{len(self.names)} task names, {len(self.entries)} entries")
        datalist = vol.read_path(DATALIST)
        self.used = {m.decode()[5:-4] for m in re.findall(rb"task/[A-Za-z0-9_]+\.bin", datalist)}
        self.data = [unpack(e) for e in self.entries]
        self.tasks = [parse_task(d) for d in self.data]
        self.texts: list[Text] = []
        for name, tf in zip(self.names, self.tasks):
            prev: dict[int, str] = {}
            for c in tf.commands():
                if not c.raw:
                    continue
                t = Text(f"{name}:{c.level}.{c.index}", name, c.level, c.index, c.op, c.who1, c.who2,
                         c.text, name in self.used)
                if c.op not in KINDS:
                    raise ValueError(f"{t.id}: text in op {c.op:#x}")
                t.before = prev.get(c.level, "")
                prev[c.level] = c.text
                if JAPANESE.search(c.text):
                    t.cls = "japones"
                elif c.op == OPS["voz"]:
                    t.cls = "sin_uso"
                elif not any(ch.isalpha() for ch in c.text):
                    t.cls = "signos"
                t.key = key_of(c.text)
                self.texts.append(t)
        self.by_id = {t.id: t for t in self.texts}
        self._batches()

    def order(self) -> list[str]:
        """The tasks in the order of the batches: by group, the unused ones last."""
        rank = {name: k for k, (name, _) in enumerate(GROUPS)}

        def sort_key(i_name):
            i, name = i_name
            return (name not in self.used, rank.get(group_of(name), len(GROUPS)), i)
        return [n for _, n in sorted(enumerate(self.names), key=sort_key)]

    def _batches(self):
        by_task = defaultdict(list)
        for t in self.texts:
            by_task[t.task].append(t)
        first: dict[str, Text] = {}
        self.canon: list[Text] = []          # one per distinct English, in batch order
        for name in self.order():
            for t in by_task[name]:
                if t.cls != "texto":
                    continue
                if t.key in first:
                    t.canon = first[t.key].id
                else:
                    first[t.key] = t
                    t.canon = t.id
                    self.canon.append(t)
        self.repeats = defaultdict(list)    # canonical id -> the other ids
        for t in self.texts:
            if t.cls == "texto" and t.canon != t.id:
                self.repeats[t.canon].append(t.id)
        # Batches: whole tasks while they fit; a task too big for one is cut; never
        # two groups (or used and unused tasks) in one batch.
        self.batches: list[tuple[str, list[Text]]] = []
        cur: list[Text] = []
        cur_group = None

        def close():
            nonlocal cur
            if cur:
                g = cur_group[1] if cur_group[0] else "sin_uso"
                self.batches.append((f"{len(self.batches) + 1:02d}_{g}", cur))
            cur = []
        canon_by_task = defaultdict(list)
        for t in self.canon:
            canon_by_task[t.task].append(t)
        for name in self.order():
            mine = canon_by_task[name]
            if not mine:
                continue
            g = (name in self.used, group_of(name))
            if g != cur_group:
                close()
                cur_group = g
            if len(mine) > BATCH_MAX:
                # A big task (the job givers): fill this batch, then batches of its own,
                # cut where a program starts if there is one near.
                while len(cur) + len(mine) > BATCH_MAX:
                    cut = _cut(mine, BATCH_TARGET - len(cur))
                    cur += mine[:cut]
                    mine = mine[cut:]
                    close()
            elif cur and len(cur) + len(mine) > BATCH_MAX:
                close()
            cur += mine
            if len(cur) >= BATCH_TARGET:
                close()
        close()
        self.batch_of = {t.id: b for b, ts in self.batches for t in ts}


def _cut(texts: list, want: int) -> int:
    """Where to cut a task's strings near `want`: at the start of a program if one is
    within 50, else at `want` (at least 1)."""
    want = max(1, want)
    near = [k for k in range(max(1, want - 50), min(len(texts), want + 50))
            if texts[k].level != texts[k - 1].level]
    return min(near, key=lambda k: abs(k - want)) if near else want


# ── Translations ─────────────────────────────────────────────────────────

def read_translations(folder: Path = TRANSLATIONS) -> tuple[dict[str, str], dict[str, Path], list[str]]:
    out, where, problems = {}, {}, []
    for path in sorted(folder.glob("*.tsv")) if folder.exists() else []:
        for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip() or raw.startswith("#"):
                continue
            if "\t" not in raw:
                problems.append(f"{path.name}:{n}: no tab between id and text")
                continue
            key, text = raw.split("\t", 1)
            if key in out:
                problems.append(f"{path.name}:{n}: {key} given again (first in {where[key].name})")
                continue
            out[key] = text
            where[key] = path
    return out, where, problems


def unescape(es: str) -> str:
    return es.replace("\\n", "\n")


def resolved(disc: Disc, spanish: dict[str, str]) -> dict[str, str]:
    """id -> the Spanish it gets (its own, else its canonical's), unescaped, game codes."""
    out = {}
    for t in disc.texts:
        es = spanish.get(t.id)
        if es is None and t.canon and t.canon != t.id:
            es = spanish.get(t.canon)
        if es is not None:
            out[t.id] = to_game(unescape(es))
    return out


def build(disc: Disc, spanish: dict[str, str]) -> tuple[bytes, int]:
    res = resolved(disc, spanish)
    per_task = defaultdict(dict)
    for tid, es in res.items():
        t = disc.by_id[tid]
        per_task[t.task][(t.level, t.index)] = es
    entries, changed = [], 0
    for name, tf, data, entry in zip(disc.names, disc.tasks, disc.data, disc.entries):
        texts = per_task.get(name)
        new = tf.serialize(texts) if texts else data
        if new == data:
            entries.append(entry)
        else:
            entries.append(pack(new))
            changed += 1
    return write_container(disc.align, entries), changed


# ── Checking ─────────────────────────────────────────────────────────────

def help_lines(widths: Widths, text: str) -> tuple[int, bool]:
    """How Font_DrawBox lays out the status screen's help line: (lines it needs,
    whether a word gets cut at the right edge)."""
    max_x = HELP_W
    pen, lines, cut = 0, 1, False
    prev_alpha = False
    for ch in text:
        if ch == "\n":
            pen, lines, prev_alpha = 0, lines + 1, False
            continue
        w = widths.w.get(ord(ch))
        if w is None:
            continue
        adv = int(HELP_SCALE * (w << 4))
        if max_x < pen or max_x < pen + adv:
            lines += 1
            if prev_alpha and ch.isalnum():
                cut = True
            pen = 0
        pen += adv
        prev_alpha = ch.isalnum()
    return lines, cut


def help_room() -> int:
    y, n = 0, 0
    while y <= HELP_H:
        n += 1
        y += int(LINE_H * HELP_SCALE)
    return n


def check_text(t: Text, es_raw: str, widths: Widths, report) -> None:
    en = t.en
    if not es_raw.strip():
        report("error", t.id, "vacío")
        return
    if "\\" in es_raw.replace("\\n", ""):
        report("error", t.id, "barra invertida que no es \\n")
    if "\t" in es_raw or "\r" in es_raw:
        report("error", t.id, "tabulador o retorno de carro")
    es = to_game(unescape(es_raw))
    kind = t.kind
    if len(NAME.findall(en)) != len(NAME.findall(es)):
        report("error", t.id, f"%s: {len(NAME.findall(en))} en inglés, {len(NAME.findall(es))} en español")
    if kind != "bocadillo" and "%" in es and "%" not in en:
        report("error", t.id, "un % donde el juego no pone el nombre")
    icons_en = sorted(c for c in en if c in ICONS)
    icons_es = sorted(c for c in es if c in ICONS)
    if icons_en != icons_es:
        report("error", t.id, f"iconos {''.join(icons_en)!r} -> {''.join(icons_es)!r}")
    if missing := widths.missing(es):
        report("error", t.id, f"no están en la fuente: {''.join(sorted(missing))!r}")
    lines_en, lines_es = en.split("\n"), es.split("\n")
    w_en = max(widths.line(x) for x in lines_en)
    w_es = max(widths.line(x) for x in lines_es)
    if kind == "eleccion" and len(lines_en) != len(lines_es):
        report("error", t.id, f"{len(lines_en)} opciones -> {len(lines_es)} (una por línea)")
    if kind in ROOM and w_es > max(w_en, ROOM[kind]):
        report("warning", t.id, f"{w_es} px > {max(w_en, ROOM[kind])} px: {es_raw}")
    if kind == "bocadillo" and len(lines_es) > max(len(lines_en), BALLOON_LINES):
        report("warning", t.id, f"{len(lines_es)} líneas (el inglés {len(lines_en)}, máx. {BALLOON_LINES})")
    if kind == "encargo":
        if "\n" in es:
            report("error", t.id, "salto de línea en el nombre de un trabajo")
        if len(es) >= NAME_CHARS:
            report("error", t.id, f"{len(es)} caracteres: el juego no lo guarda si pasa de {NAME_CHARS - 1}")
    if kind == "objetivo" and (len(es.encode("utf-16-le")) + 3) & ~3 >= MESSAGE_BYTES:
        report("error", t.id, f"{len(es)} caracteres: el juego lo descarta a partir de "
                              f"{(MESSAGE_BYTES - 4) // 2 + 1} (cuenta cada \\n como uno)")
    if kind == "estado":
        if len(es) >= OTHER_CHARS:
            report("error", t.id, f"{len(es)} caracteres: no caben en {OTHER_CHARS - 1}")
        elif len(es) > len(en):
            report("warning", t.id, f"más largo que el inglés ({len(es)} > {len(en)})")
    if kind in ("objetivo", "estado"):
        n, cut = help_lines(widths, es)
        n_en, _ = help_lines(widths, en)
        if n > help_room():
            report("error", t.id, f"{n} líneas en la línea de ayuda del estado: solo se ven {help_room()}")
        elif cut:
            report("error", t.id, "una palabra queda cortada en la línea de ayuda (añade un \\n antes)")
        elif n > n_en:
            report("warning", t.id, f"{n} líneas (el inglés {n_en})")


def run_check(disc: Disc, spanish: dict[str, str], where: dict[str, Path], problems: list[str],
              widths: Widths, only: set[str] | None) -> tuple[int, int]:
    errors = warnings = 0

    def report(kind, tid, msg):
        nonlocal errors, warnings
        if kind == "error":
            errors += 1
        else:
            warnings += 1
        print(f"{kind:7} {tid}  {msg}")

    for p in problems:
        report("error", "-", p)
    for tid, es in spanish.items():
        t = disc.by_id.get(tid)
        if only is not None and where[tid].stem not in only \
                and (t is None or disc.batch_of.get(t.canon) not in only):
            continue
        if t is None:
            m = ID.match(tid)
            report("error", tid, "no es un id de texto" + ("" if m else " (formato tarea:programa.índice)"))
            continue
        if t.cls != "texto":
            report("error", tid, f"no se traduce ({t.cls}): {t.en!r}")
            continue
        check_text(t, es, widths, report)
        if t.canon != t.id:
            if t.canon not in spanish:
                report("warning", tid, f"traduce una repetición de {t.canon}, que no está traducido")
            # the same English with its own translation elsewhere: fine (gender, context)
        else:
            # the others that take this translation, in their own kind
            for other in disc.repeats.get(tid, []):
                o = disc.by_id[other]
                if other not in spanish and o.kind != t.kind:
                    check_text(o, es, widths, report)
    total = [t for t in disc.canon if t.used and (only is None or disc.batch_of[t.id] in only)]
    done = sum(1 for t in total if t.id in spanish)
    print(f"{done} de {len(total)} cadenas distintas (tareas en uso) traducidas; "
          f"{errors} errores, {warnings} avisos")
    return errors, warnings


# ── Work files ───────────────────────────────────────────────────────────

def describe(t: Text) -> str:
    k = t.kind
    if k == "bocadillo":
        speaker = WHO.get(t.who1, f"el personaje {t.who1}")
        if t.who2 == t.who1:
            to = "para sí (comentario)"
        else:
            to = ("a " + WHO.get(t.who2, f"el personaje {t.who2}")).replace("a el ", "al ")
        s = f"habla {speaker} {to}"
    elif k == "eleccion":
        s = "opciones del protagonista"
    else:
        s = {"aviso": "aviso del HUD", "objetivo": "objetivo del trabajo (pantalla de estado)",
             "encargo": "nombre del trabajo (<24 caracteres)", "estado": "línea de la pantalla de estado"}[k]
    if NAME.search(t.en):
        s += "; %s = nombre del jugador"
    return s


def task_header(name: str, used: bool) -> str:
    who = "probablemente mujer" if female(name) else ""
    bits = [b for b in (who, "" if used else "SIN USO (no está en task/DataList)") if b]
    return f"===== tarea {name}" + (f" ({'; '.join(bits)})" if bits else "") + " ====="


def esc(s: str) -> str:
    return s.replace("\n", "\\n")


def work_file(disc: Disc, batch: str, texts: list[Text], widths: Widths, spanish: dict[str, str]) -> str:
    todo = sum(1 for t in texts if t.id not in spanish)
    out = [f"# Tanda {batch}: {len(texts)} cadenas distintas, {todo} por traducir. Salida: id<TAB>español",
           f"# en translations/es/task/{batch}.tsv (ver docs/spanish/06_tasks.md).",
           "# Cada cadena: una línea de comentario (tipo, quién habla, ancho del inglés en px,",
           "# repeticiones que heredan la traducción) y la línea id<TAB>inglés.  Las ya traducidas",
           "# van solo como comentario «# hecha: id<TAB>español», para dar contexto.", ""]
    last_task, prev_text = None, None
    for t in texts:
        if t.task != last_task:
            out += ["", "# " + task_header(t.task, t.used)]
            last_task = t.task
        notes = [t.kind, describe(t)]
        w = max(widths.line(x) for x in t.en.split("\n"))
        notes.append(f"{w} px")
        reps = disc.repeats.get(t.id, [])
        if reps:
            others = sorted({disc.by_id[r].task for r in reps} - {t.task})
            notes.append(f"repetida {len(reps)}x" + (f" (también en {', '.join(others[:4])}"
                                                       f"{'…' if len(others) > 4 else ''})" if others else ""))
            if t.kind == "bocadillo" and len({female(n) for n in others + [t.task]}) > 1:
                notes.append("OJO: la dicen hombres y mujeres (forma neutra, o una línea propia para el otro id)")
        if t.before and t.before != prev_text:
            notes.append(f"antes: «{esc(t.before)[:70]}»")
        if t.id in spanish:
            out.append(f"# hecha: {t.id}\t{spanish[t.id]}   ({esc(t.en)})")
        else:
            out.append("# " + " · ".join(notes))
            out.append(f"{t.id}\t{esc(t.en)}")
        prev_text = t.en
    return "\n".join(out) + "\n"


# ── Commands ─────────────────────────────────────────────────────────────

def cmd_list(disc: Disc, args, spanish):
    if args.tasks:
        for name in disc.order():
            ts = [t for t in disc.texts if t.task == name]
            c = Counter(t.cls for t in ts)
            mine = [t for t in disc.canon if t.task == name]
            done = sum(1 for t in mine if t.id in spanish)
            print(f"{name:34} {'uso' if name in disc.used else 'SIN USO':7} textos {len(ts):4}  "
                  f"nuevas {len(mine):4}  traducidas {done:4}  "
                  + " ".join(f"{k} {v}" for k, v in sorted(c.items()) if k != "texto"))
        return
    for b, ts in disc.batches:
        tasks = []
        for t in ts:
            if not tasks or tasks[-1][0] != t.task:
                tasks.append([t.task, 0])
            tasks[-1][1] += 1
        done = sum(1 for t in ts if t.id in spanish)
        print(f"{b:16} {len(ts):4} cadenas, {done:4} traducidas  "
              + ", ".join(f"{n} ({k})" for n, k in tasks))
    c = Counter((t.cls, t.used) for t in disc.texts)
    kinds = Counter(t.kind for t in disc.canon if t.used)
    used_canon = sum(1 for t in disc.canon if t.used)
    print(f"\n{len(disc.texts)} comandos con texto, {len(disc.canon)} cadenas distintas a traducir "
          f"({used_canon} en tareas en uso); por tipo (en uso): "
          + ", ".join(f"{k} {v}" for k, v in kinds.most_common()))
    print("no se traducen: " + ", ".join(f"{cls}{'' if used else ' (sin uso)'} {n}"
                                          for (cls, used), n in sorted(c.items()) if cls != "texto"))
    print(f"tareas sin uso: {', '.join(n for n in disc.names if n not in disc.used)}")


def cmd_extract(disc: Disc, args, widths, spanish):
    names = [b for b, _ in disc.batches]
    want = names if args.what == ["all"] else args.what
    WORK.mkdir(parents=True, exist_ok=True)
    for b in want:
        if b not in names:
            sys.exit(f"no hay tanda {b!r} (ver: list)")
        ts = dict(disc.batches)[b]
        path = WORK / f"{b}.tsv"
        path.write_text(work_file(disc, b, ts, widths, spanish), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({len(ts)} cadenas)")
    if args.what == ["all"]:
        jp = [t for t in disc.texts if t.cls == "japones"]
        path = WORK / "_japones.tsv"
        path.write_text("# Texto japonés de las tareas: no se traduce (ver docs/spanish/06_tasks.md)\n"
                        + "".join(f"{t.id}\t{'uso' if t.used else 'sin uso'}\t{t.kind}\t{esc(t.en)}\n"
                                  for t in jp), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({len(jp)} cadenas)")


def cmd_build(disc: Disc, args, spanish):
    blob, changed = build(disc, spanish)
    out = args.out or OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    same = " (idéntico al del disco)" if blob == disc.blob else ""
    n = len(resolved(disc, spanish))
    print(f"wrote {out}: {len(blob)} bytes, {changed} tareas reempaquetadas, {n} comandos en español{same}")


def compare(disc: Disc, blob: bytes, spanish: dict[str, str]) -> list[str]:
    """Reads a built container back: the same tasks, commands and arguments, the text
    changed only where the translation says."""
    problems = []
    align, entries = read_container(blob)
    if align != disc.align or len(entries) != len(disc.entries):
        return ["otro número de tareas o alineación"]
    res = resolved(disc, spanish)
    for name, tf, entry in zip(disc.names, disc.tasks, entries):
        data = unpack(entry)
        if len(data) != struct.unpack_from("<I", entry, 4)[0]:
            problems.append(f"{name}: no se desempaqueta entero")
            continue
        new = parse_task(data)
        a, b = list(tf.commands()), list(new.commands())
        if [p[0] for p in tf.programs] != [p[0] for p in new.programs] or len(a) != len(b):
            problems.append(f"{name}: otros programas")
            continue
        for x, y in zip(a, b):
            tid = f"{name}:{x.level}.{x.index}"
            if (x.head[:20], x.tail) != (y.head[:20], y.tail):
                problems.append(f"{tid}: cambia algo que no es el texto")
            want = res.get(tid, x.text)
            if y.text != want:
                problems.append(f"{tid}: texto {y.text!r}, se esperaba {want!r}")
    return problems


def cmd_verify(disc: Disc, args, spanish):
    print(f"contenedor: {len(disc.entries)} tareas, se reescribe igual byte a byte")
    for name, tf, data in zip(disc.names, disc.tasks, disc.data):
        if tf.serialize() != data:
            sys.exit(f"{name}: no se reescribe igual")
    print("cada tarea se lee y se reescribe igual byte a byte")
    blob, changed = build(disc, {})
    print("build sin traducción: " + ("idéntico al del disco" if blob == disc.blob else "DISTINTO"))
    if args.pack_all:
        total = packed = 0
        for name, data in zip(disc.names, disc.data):
            p = pack(data)
            if unpack(p) != data:
                sys.exit(f"{name}: LZSS no da lo mismo")
            total += len(data)
            packed += len(p)
        print(f"LZSS: las {len(disc.data)} tareas empaquetadas y desempaquetadas (como el juego) "
              f"iguales; {total} -> {packed} bytes (el disco: {sum(len(e) for e in disc.entries)})")
    blob, changed = build(disc, spanish)
    problems = compare(disc, blob, spanish)
    for p in problems[:30]:
        print("error  ", p)
    print(f"build con la traducción ({changed} tareas reempaquetadas): "
          + ("se relee y solo cambia el texto traducido" if not problems else f"{len(problems)} problemas"))
    return 1 if problems or blob is None else 0


def cmd_show(disc: Disc, args, spanish, widths):
    res = resolved(disc, spanish)
    for what in args.what:
        ts = [disc.by_id[what]] if what in disc.by_id else [t for t in disc.texts if t.task == what]
        if not ts:
            print(f"{what}: no es una tarea ni un id")
        for t in ts:
            es = res.get(t.id)
            src = "" if t.id in spanish else (f" (de {t.canon})" if es is not None else "")
            w_en = max(widths.line(x) for x in t.en.split("\n"))
            w_es = max(widths.line(x) for x in es.split("\n")) if es else "-"
            cls = "" if t.cls == "texto" else f" [{t.cls}]"
            print(f"{t.id}  {t.kind}{cls}  {describe(t)}  {w_en}/{w_es} px{src}")
            print(f"    {esc(t.en)}")
            print(f"    {esc(es) if es is not None else '(sin traducir)'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["list", "extract", "build", "check", "show", "verify"])
    ap.add_argument("what", nargs="*", help="extract/check: tandas (o all); show: tareas o ids")
    ap.add_argument("--tasks", action="store_true", help="list: por tarea")
    ap.add_argument("--orig", type=Path, help="un task/alltask extraído en lugar de extracted/VOLUME.DAT")
    ap.add_argument("--tsv", type=Path, default=TRANSLATIONS, help="la carpeta de las traducciones")
    ap.add_argument("--out", type=Path, help="build: dónde escribir")
    ap.add_argument("--font", type=Path, default=FONT)
    ap.add_argument("--pack-all", action="store_true", help="verify: también empaqueta las 182 tareas (lento)")
    args = ap.parse_args()

    disc = Disc(args.orig)
    spanish, where, problems = read_translations(args.tsv)
    if args.command == "list":
        cmd_list(disc, args, spanish)
    elif args.command == "extract":
        if not args.what:
            sys.exit("extract: tanda(s) o all")
        cmd_extract(disc, args, Widths(args.font), spanish)
    elif args.command == "build":
        if problems:
            sys.exit("\n".join(problems))
        cmd_build(disc, args, spanish)
    elif args.command == "check":
        only = set(args.what) if args.what else None
        errors, _ = run_check(disc, spanish, where, problems, Widths(args.font), only)
        sys.exit(1 if errors else 0)
    elif args.command == "show":
        cmd_show(disc, args, spanish, Widths(args.font))
    else:
        sys.exit(cmd_verify(disc, args, spanish))


if __name__ == "__main__":
    main()
