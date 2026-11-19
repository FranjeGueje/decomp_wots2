#!/usr/bin/env python3
"""
Survey of the game's bitmap font: Font/Samu2.Fnt (glyph table) + Font/Samu2.Pim (textures).

.Fnt (little-endian), as read by Font_SetGlyphs (0x1535D0) and Font_FindGlyph (0x154E80):
  u16 count, then `count` x 10-byte FontGlyph sorted by code (binary search):
    u16 code (UTF-16)   u16 u, v (top-left texel)
    u8  texture         low nibble: .Pim descriptor; high nibble: drawn in the fixed colour
    u8  clut            added to the descriptor's CBP (an 8-bit palette is 4 units)
    u8  width, height   texels; the width is also the advance
.Pim: 0x30-byte descriptors (see tools/bpm.py).  This font's textures are PSMT8H (0x1B),
  stored in plain row order.  Texture 0 holds 2-bit anti-aliased glyphs packed as bit
  planes: palette N shows bits 2N..2N+1 of each texel, so one texel serves up to four
  different glyphs.  Texture 1 holds full-colour 8-bit icons (button marks and such).

  tools/font_info.py                       report (reads extracted/VOLUME.DAT)
  tools/font_info.py --fnt F --pim P       report from extracted files
  tools/font_info.py --png DIR             also write the textures / planes as PNG
  tools/font_info.py --list                also list every glyph
"""
import argparse
import collections
import struct
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpm  # noqa: E402

import numpy as np  # noqa: E402

SPANISH = "áéíóúÁÉÍÓÚñÑüÜ¿¡«»"


def parse_fnt(data: bytes):
    count, = struct.unpack_from("<H", data)
    glyphs = []
    for i in range(count):
        code, u, v, tex, clut, w, h = struct.unpack_from("<HHHBBBB", data, 2 + i * 10)
        glyphs.append(dict(code=code, u=u, v=v, tex=tex & 0x0F, fixed=tex >> 4,
                           clut=clut, w=w, h=h))
    return glyphs, len(data) - 2 - count * 10


def plane_bits(tex: "bpm.Texture", clut_index: int) -> int:
    """The bits of the texel index that palette `clut_index` makes visible."""
    alpha = palette(tex, clut_index)[:, 3]
    mask = 0
    for bit in range(8):
        idx = np.arange(256)
        if np.any(alpha[idx] != alpha[idx ^ (1 << bit)]):
            mask |= 1 << bit
    return mask


def palette(tex: "bpm.Texture", n: int) -> np.ndarray:
    """Palette n as RGBA (8-bit textures: CSM1 order undone, alpha scaled to 255)."""
    return bpm.read_clut8(tex.clut_raw[n * 1024:(n + 1) * 1024])


def alpha_map(tex: "bpm.Texture", n: int) -> np.ndarray:
    return palette(tex, n)[:, 3][tex.indices()]


def glyph_alpha(texs, g):
    """The glyph's coverage (0..255) as the game draws it."""
    t = texs[g["tex"]]
    return alpha_map(t, g["clut"] // 4)[g["v"]:g["v"] + g["h"], g["u"]:g["u"] + g["w"]]


def name(c):
    try:
        return unicodedata.name(chr(c))
    except ValueError:
        return "?"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--fnt", type=Path)
    ap.add_argument("--pim", type=Path)
    ap.add_argument("--png", type=Path, help="write texture / plane images here")
    ap.add_argument("--list", action="store_true", help="list every glyph")
    args = ap.parse_args()

    if args.fnt and args.pim:
        fnt, pim = args.fnt.read_bytes(), args.pim.read_bytes()
    else:
        import volume
        vol = volume.Volume()
        fnt, pim = vol.read_path("Font/Samu2.Fnt"), vol.read_path("Font/Samu2.Pim")

    glyphs, trailing = parse_fnt(fnt)
    for t in (texs := bpm.Bpm(pim).textures):
        if t.psm == 0x1B:   # PSMT8H, plain row order
            t._indices = np.frombuffer(t.pixels, np.uint8)[:t.width * t.height] \
                .reshape(t.height, t.width)
    codes = [g["code"] for g in glyphs]
    by_code = {}
    for g in glyphs:
        by_code.setdefault(g["code"], []).append(g)

    print(f".Fnt: {len(glyphs)} glyphs ({len(by_code)} distinct codes), "
          f"{trailing} trailing bytes, sorted={codes == sorted(codes)}")
    print(f"  codes U+{min(codes):04X} .. U+{max(codes):04X}")
    dups = {c: v for c, v in by_code.items() if len(v) > 1}
    if dups:
        print("  duplicate codes (binary search returns either):",
              ", ".join(f"U+{c:04X}" for c in sorted(dups)))

    blocks = collections.Counter()
    for c in by_code:
        blocks[("ASCII" if c < 0x80 else "Latin-1" if c < 0x100 else "Latin ext" if c < 0x250
                else "Greek" if 0x370 <= c < 0x400 else "punct/symbols" if 0x2000 <= c < 0x3000
                else "CJK punct/kana" if 0x3000 <= c < 0x3100 else "CJK ideographs" if 0x4E00 <= c < 0xA000
                else "fullwidth" if 0xFF00 <= c < 0xFFF0 else "other")] += 1
    print("  by block:", ", ".join(f"{k} {v}" for k, v in blocks.most_common()))

    missing_ascii = [chr(c) for c in range(0x20, 0x7F) if c not in by_code]
    print(f"  printable ASCII: {'all 95 present' if not missing_ascii else 'missing ' + repr(missing_ascii)}")
    missing_l1 = [f"U+{c:04X}" for c in range(0xA0, 0x100) if c not in by_code]
    print(f"  Latin-1 (U+00A0..U+00FF): {'all present' if not missing_l1 else 'missing ' + ' '.join(missing_l1)}")

    print("\nSpanish characters:")
    for ch in SPANISH:
        gs = by_code.get(ord(ch))
        if not gs:
            print(f"  {ch} U+{ord(ch):04X}  MISSING")
            continue
        g = gs[0]
        ink = int(np.count_nonzero(glyph_alpha(texs, g)))
        print(f"  {ch} U+{ord(ch):04X}  {g['w']:2d}x{g['h']:2d}  tex {g['tex']} clut {g['clut']:2d} "
              f"at ({g['u']},{g['v']})  {ink} inked texels")

    sizes = collections.Counter((g["w"], g["h"]) for g in glyphs)
    heights = collections.Counter(g["h"] for g in glyphs)
    widths = [g["w"] for g in glyphs]
    print(f"\nglyph sizes: width {min(widths)}..{max(widths)}, heights "
          + ", ".join(f"{h}:{n}" for h, n in sorted(heights.items())))
    print("  most common w x h:", ", ".join(f"{w}x{h}:{n}" for (w, h), n in sizes.most_common(8)))
    for key in ("a", "M", "0"):
        g = by_code[ord(key)][0]
        print(f"  '{key}': {g['w']}x{g['h']}")

    print("\ntextures:")
    for i, t in enumerate(texs):
        uses = collections.Counter((g["clut"], g["fixed"]) for g in glyphs if g["tex"] == i)
        print(f"  {i}: {t.width}x{t.height} psm={t.psm:#x} palettes={t.clut_count} "
              f"pixels={len(t.pixels):,} B; glyphs by (clut, fixed colour): "
              + ", ".join(f"{k}:{v}" for k, v in sorted(uses.items())))
        planes = range(t.clut_count) if t.clut_count > 1 else [None]
        for p in planes:
            if p is None:
                sel = [g for g in glyphs if g["tex"] == i]
                label = "    whole"
                ink = alpha_map(t, 0) != 0
            else:
                mask = plane_bits(t, p)
                sel = [g for g in glyphs if g["tex"] == i and g["clut"] // 4 == p]
                label = f"    plane {p} (palette {p}, clut {p * 4}, bits {mask:#04x})"
                ink = alpha_map(t, p) != 0
            claimed = np.zeros_like(ink)
            for g in sel:
                claimed[g["v"]:g["v"] + g["h"], g["u"]:g["u"] + g["w"]] = True
            free = ~(claimed | ink)
            free_rows = free.all(axis=1)
            # longest band of whole free rows
            best = run = start = best_start = 0
            for y, f in enumerate(free_rows):
                if f:
                    if run == 0:
                        start = y
                    run += 1
                    if run > best:
                        best, best_start = run, start
                else:
                    run = 0
            # how many 24x24 cells fit in what is free (greedy, cell grid)
            cells = sum(1 for y in range(0, t.height - 23, 24) for x in range(0, t.width - 23, 24)
                        if free[y:y + 24, x:x + 24].all())
            print(f"{label}: {len(sel)} glyphs, {claimed.mean():5.1%} of texels claimed, "
                  f"{ink.mean():5.1%} inked; free 24x24 cells: {cells}; "
                  f"largest free band rows {best_start}..{best_start + best - 1} ({best} rows)"
                  if best else
                  f"{label}: {len(sel)} glyphs, {claimed.mean():5.1%} claimed, {ink.mean():5.1%} inked; "
                  f"free 24x24 cells: {cells}")
            if args.png:
                args.png.mkdir(parents=True, exist_ok=True)
                img = palette(t, p or 0)[t.indices()]
                bpm.save_png(args.png / f"tex{i}{'' if p is None else f'_plane{p}'}.png", img)

    if args.list:
        print("\nall glyphs:")
        for g in glyphs:
            c = g["code"]
            ch = chr(c) if c >= 0x20 and unicodedata.category(chr(c))[0] != "C" else " "
            print(f"  U+{c:04X} {ch}  {g['w']:2d}x{g['h']:2d} tex {g['tex']}{'F' if g['fixed'] else ' '} "
                  f"clut {g['clut']:2d} ({g['u']:3d},{g['v']:4d})  {name(c)}")


if __name__ == "__main__":
    main()
