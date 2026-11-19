#!/usr/bin/env python3
"""
Spanish mod, step 2: the game's font with the glyphs Spanish needs and it lacks.

The font (Us/Font/Samu2.Fnt + Us/Font/Samu2.Pim, see tools/font_info.py) has every
Spanish letter, ¡ and « already, but the codes of ¿, » and º draw button icons
(U+00BF is the Cross button, U+00BB and U+00BA arrows), and the game's own texts
use them as such.  So the new glyphs get codes of their own, from the Private Use
Area, and the mod's texts write those codes in place of the real characters:

    ¿  U+E000   the font's ? turned through 180°, standing where ¡ stands
    »  U+E001   the font's « mirrored
    º  U+E002   the font's o, reduced to the size and place of its ª

They are drawn into the free part of texture 1 (rows 220 and on), in its palette
(the grey ramp of indices 206..255 that the Latin letters use), one 22-pixel cell
each like the rest of that texture, and inserted in order into the sorted glyph
table.  Everything is derived from the disc's files, so the output is the same on
every run.

  tools/spanish_font.py                       read extracted/VOLUME.DAT, write
                                              mods/espanol/files/Us/Font/Samu2.{Fnt,Pim}
  tools/spanish_font.py --fnt F --pim P       start from extracted originals
  tools/spanish_font.py --out DIR             write somewhere else
  tools/spanish_font.py --png DIR             also a preview: the new glyphs, enlarged,
                                              and some text set with the new font
  tools/spanish_font.py --text "¿Qué?"        the text of the preview

`to_game(text)` (importable) turns ordinary Spanish text into what the game must
be given: ¿ » º replaced by their codes.
"""
import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpm  # noqa: E402
import font_info  # noqa: E402

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "mods" / "espanol" / "files" / "Us" / "Font"

# The new characters and their codes.  Keep in step with docs/spanish/02_new_glyphs.md.
NEW_GLYPHS = {"¿": 0xE000, "»": 0xE001, "º": 0xE002}
TO_GAME = str.maketrans({ch: chr(code) for ch, code in NEW_GLYPHS.items()})


def to_game(text: str) -> str:
    """Spanish text as the game's font must be given it."""
    return text.translate(TO_GAME)


TEX = 1             # the texture of the Latin letters
CELL = 22           # its glyphs lie in 22x22 cells, at (22 * col, 1 + 22 * row)
FIRST_ROW = 10      # cells from y = 221 on are free (step 1: rows 220..511 are blank)
BLANK = 206         # palette index of the empty texel (alpha 0)
RAMP = np.arange(206, 256)      # the grey ramp: alpha rises with the index
FIXED_FIELD = 0     # high nibble of the texture byte: 0 = drawn in the text's colour


def load(args):
    if args.fnt and args.pim:
        return args.fnt.read_bytes(), args.pim.read_bytes()
    import volume
    vol = volume.Volume()
    return vol.read_path("Font/Samu2.Fnt"), vol.read_path("Font/Samu2.Pim")


class Font:
    def __init__(self, fnt: bytes, pim: bytes):
        self.glyphs, trailing = font_info.parse_fnt(fnt)
        if trailing:
            raise ValueError(f".Fnt has {trailing} trailing bytes")
        self.pim = bytearray(pim)
        self.texs = bpm.Bpm(bytes(pim)).textures
        for t in self.texs:
            if t.psm == 0x1B:   # PSMT8H, plain row order (bpm.py does not know it)
                t._indices = np.frombuffer(t.pixels, np.uint8)[:t.width * t.height] \
                    .reshape(t.height, t.width)
        t = self.texs[TEX]
        if t.psm != 0x1B or (t.width, t.height) != (512, 512) or t.clut_count != 1:
            raise ValueError("texture 1 is not the 512x512 8-bit texture expected")
        self.pix_off = t.pix_off            # (offsets count from the start of a .Pim)
        self.alpha = font_info.palette(t, 0)[:, 3]
        # Only the grey ramp: everything there is the same grey, alpha alone differs.
        pal = font_info.palette(t, 0)
        if not (np.all(pal[RAMP, :3] == 128) and np.all(np.diff(self.alpha[RAMP].astype(int)) > 0)):
            raise ValueError("texture 1's palette is not the one expected")
        # The levels the letters actually use (the art is ~16 levels).
        letters = [g for g in self.glyphs if g["tex"] == TEX and 0x21 <= g["code"] < 0x7F]
        used = np.unique(np.concatenate([self.cell(g).ravel() for g in letters]))
        self.levels = np.array([i for i in used if i in RAMP])

    def index_map(self) -> np.ndarray:
        """Texture 1 as a writable 512x512 array of palette indices (a view on self.pim)."""
        return np.frombuffer(self.pim, np.uint8, 512 * 512, self.pix_off).reshape(512, 512)

    def find(self, code: int):
        for g in self.glyphs:
            if g["code"] == code:
                return g
        raise KeyError(f"U+{code:04X}")

    def cell(self, g) -> np.ndarray:
        """The glyph's rectangle, palette indices."""
        return self.index_map()[g["v"]:g["v"] + g["h"], g["u"]:g["u"] + g["w"]].copy()

    def quantize(self, alpha: np.ndarray) -> np.ndarray:
        """Coverage 0..255 to the nearest of the letters' palette indices."""
        lv = self.alpha[self.levels].astype(float)
        return self.levels[np.abs(alpha[..., None] - lv).argmin(axis=-1)].astype(np.uint8)

    def to_bytes(self) -> tuple[bytes, bytes]:
        glyphs = sorted(self.glyphs, key=lambda g: g["code"])     # stable: duplicates keep their order
        out = bytearray(struct.pack("<H", len(glyphs)))
        for g in glyphs:
            out += struct.pack("<HHHBBBB", g["code"], g["u"], g["v"], g["tex"] | g["fixed"] << 4,
                               g["clut"], g["w"], g["h"])
        return bytes(out), bytes(self.pim)


def ink_box(cell: np.ndarray):
    """Rows and columns holding ink."""
    ys, xs = np.nonzero(cell != BLANK)
    return ys.min(), ys.max() + 1, xs.min(), xs.max() + 1


def area_resize(a: np.ndarray, h: int, w: int) -> np.ndarray:
    """Box-filtered resize (exact area average)."""
    a = a.astype(float)
    big = np.repeat(np.repeat(a, h, axis=0), w, axis=1)            # (H*h, W*w)
    H, W = a.shape
    return big.reshape(h, H, w, W).mean(axis=(1, 3))


def make_glyphs(font: Font):
    """The new glyphs as (code, cell of palette indices); a cell's top row is the glyph's v."""
    out = []

    # ¿: ? turned through 180°.  Upside down its ink would sit where ? is; ¿ hangs
    # below the line as the font's ¡ does, so the ink goes in ¡'s rows.
    q = font.find(ord("?"))
    inv = font.find(ord("¡"))
    qc = font.cell(q)
    y0, y1, x0, x1 = ink_box(qc)
    turned = qc[y0:y1, x0:x1][::-1, ::-1]
    iy0, iy1, _, _ = ink_box(font.cell(inv))
    if turned.shape[0] != iy1 - iy0:
        raise ValueError("? and ¡ no longer have the same height of ink")
    w = turned.shape[1] + 2                     # a texel either side, as the ¡
    cell = np.full((iy1 + 1, w), BLANK, np.uint8)
    cell[iy0:iy1, 1:1 + turned.shape[1]] = turned
    out.append((NEW_GLYPHS["¿"], cell))

    # »: « mirrored, its whole rectangle (so its spacing mirrors too: the space
    # « leaves after it, » leaves before).
    out.append((NEW_GLYPHS["»"], font.cell(font.find(ord("«")))[:, ::-1].copy()))

    # º: the font's o, reduced to the size of the font's ª and put where ª is.
    o = font.cell(font.find(ord("o")))
    fa = font.find(ord("ª"))
    fac = font.cell(fa)
    ay0, ay1, ax0, ax1 = ink_box(fac)
    oy0, oy1, ox0, ox1 = ink_box(o)
    small = area_resize(font.alpha[o[oy0:oy1, ox0:ox1]], ay1 - ay0, ax1 - ax0)
    # The reduction greys it; bring its strongest texel back to ª's.
    small *= font.alpha[fac].max() / small.max()
    cell = np.full(fac.shape, BLANK, np.uint8)
    cell[ay0:ay1, ax0:ax1] = font.quantize(small)
    out.append((NEW_GLYPHS["º"], cell))
    return out


def add_glyphs(font: Font, new):
    tex = font.index_map()
    taken = {(g["u"], g["v"]) for g in font.glyphs if g["tex"] == TEX}
    for n, (code, cell) in enumerate(new):
        if any(g["code"] == code for g in font.glyphs):
            raise ValueError(f"U+{code:04X} is in the font already")
        u, v = CELL * n, 1 + CELL * (FIRST_ROW + n // (512 // CELL))
        h, w = cell.shape
        if (u, v) in taken or h > CELL or w > CELL or not np.all(tex[v - 1:v - 1 + CELL, u:u + CELL] == BLANK):
            raise ValueError(f"the cell at ({u},{v}) is not free")
        tex[v:v + h, u:u + w] = cell
        font.glyphs.append(dict(code=code, u=u, v=v, tex=TEX, fixed=FIXED_FIELD, clut=0, w=w, h=h))


# ── Preview ───────────────────────────────────────────────────────────────

def render(font: Font, text: str, scale: int = 3) -> np.ndarray:
    """`text` set as the game sets it (top-left of each glyph on the line, width =
    advance, 22-pixel lines), white on a dark blue, enlarged."""
    alpha = font.alpha[font.index_map()]
    lines = text.split("\n")
    by_code = {}
    for g in font.glyphs:
        by_code.setdefault(g["code"], g)
    width = max(sum(by_code[ord(c)]["w"] for c in line if ord(c) in by_code) for line in lines) + 8
    cov = np.zeros((22 * len(lines) + 8, width))
    for row, line in enumerate(lines):
        x, y = 4, 4 + 22 * row
        for c in line:
            g = by_code.get(ord(c))
            if g is None:
                continue
            if g["tex"] == TEX:
                cov[y:y + g["h"], x:x + g["w"]] = np.maximum(
                    cov[y:y + g["h"], x:x + g["w"]], alpha[g["v"]:g["v"] + g["h"], g["u"]:g["u"] + g["w"]])
            else:
                cov[y:y + g["h"], x:x + g["w"]] = np.maximum(
                    cov[y:y + g["h"], x:x + g["w"]], font_info.glyph_alpha(font.texs, g))
            x += g["w"]
    bg, fg = np.array([24, 28, 48.0]), np.array([255, 255, 255.0])
    a = (cov / 255.0)[..., None]
    img = (bg * (1 - a) + fg * a).astype(np.uint8)
    img = np.repeat(np.repeat(img, scale, axis=0), scale, axis=1)
    return np.dstack([img, np.full(img.shape[:2], 255, np.uint8)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--fnt", type=Path)
    ap.add_argument("--pim", type=Path)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--png", type=Path, help="write preview images here")
    ap.add_argument("--text", default="¿Qué hacéis aquí? «Nada», dijo.\n"
                                      "¡Corre! Calle nº 3, 1º piso.\n"
                                      "¿Y el señor Ñoño? ¿ ? ¡ ! « » º ª o")
    args = ap.parse_args()

    font = Font(*load(args))
    if font.texs[0].tw != 9 or font.texs[0].th != 10:
        raise ValueError("unexpected font file")
    new = make_glyphs(font)
    add_glyphs(font, new)
    fnt, pim = font.to_bytes()

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "Samu2.Fnt").write_bytes(fnt)
    (args.out / "Samu2.Pim").write_bytes(pim)
    print(f"wrote {args.out}/Samu2.Fnt ({len(font.glyphs)} glyphs) and Samu2.Pim")
    for ch, code in NEW_GLYPHS.items():
        g = font.find(code)
        print(f"  {ch} U+{code:04X}  {g['w']}x{g['h']} at ({g['u']},{g['v']}) in texture {g['tex']}")

    if args.png:
        args.png.mkdir(parents=True, exist_ok=True)
        bpm.save_png(args.png / "text.png", render(font, to_game(args.text)))
        # The same text with the real codes: what an untranslated ¿ » º would show.
        bpm.save_png(args.png / "text_without_mapping.png", render(font, args.text))
        # The new glyphs and their models, side by side, large.
        bpm.save_png(args.png / "glyphs.png",
                     render(font, "?" + chr(0xE000) + "¡!  «" + chr(0xE001) + "  ª" + chr(0xE002) + "o°", 8))
        print(f"  previews in {args.png}")


if __name__ == "__main__":
    main()
