#!/usr/bin/env python3
"""
Spanish mod -> xdelta patch for the North American PS2 disc (SLUS-208.93).

The mod's files (mods/espanol/files/Us/**) replace entries of VOLUME.DAT.  This
tool does the same on the disc image, then makes the patch with xdelta3:

  * .sol scripts are compiled to .sx with solc (the PS2 game only reads .sx).
  * Every replaced entry is written raw (flags 0; flags 1 for the entries that
    share a name hash, which carry their name after the data) at the end of
    VOLUME.DAT, aligned to 2048 bytes; the entry's row in the table is changed
    to point at it, the old data stay where they were.  The table stays sorted.
  * VOLUME.DAT grows, and the file after it on the disc, SAMURAI2 (100 MB of
    padding the game never opens), moves up by that much and loses the same
    amount from its end, so the image keeps its size and nothing else moves.
  * The two ISO 9660 directory records (VOLUME.DAT's size, SAMURAI2's place
    and size) are updated.

  tools/spanish_iso.py make  "USA.iso" -o es.xdelta     # build the patch
  tools/spanish_iso.py verify "USA.iso" es.xdelta       # apply it and check the result

The patched image is built in a work directory (about 2.5 GB), not kept unless
--keep is given.  Needs xdelta3.
"""
import argparse
import hashlib
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import volume  # noqa: E402

MOD = ROOT / "mods" / "espanol" / "files"
SECTOR = 2048
SOLC = ROOT / "build" / "lib" / "sol" / "solc"


def align(n: int) -> int:
    return (n + SECTOR - 1) // SECTOR * SECTOR


# ── ISO 9660 (just enough) ───────────────────────────────────────────────

class Iso:
    def __init__(self, path: Path):
        self.path = path
        self.f = open(path, "rb")
        self.f.seek(16 * SECTOR)
        pvd = self.f.read(SECTOR)
        if pvd[1:6] != b"CD001":
            raise SystemExit(f"{path}: not an ISO 9660 image")
        self.root_lba, = struct.unpack_from("<I", pvd, 158)
        self.root_len, = struct.unpack_from("<I", pvd, 166)

    def records(self):
        """Root directory records: name -> (record offset in the image, lba, size)."""
        self.f.seek(self.root_lba * SECTOR)
        d = self.f.read(self.root_len)
        out, o = {}, 0
        while o < len(d):
            n = d[o]
            if n == 0:                      # records never straddle a sector
                o = (o // SECTOR + 1) * SECTOR
                continue
            name = d[o + 33:o + 33 + d[o + 32]].decode("latin1").split(";")[0].rstrip(".")
            lba, size = struct.unpack_from("<II", d, o + 2)[0], struct.unpack_from("<I", d, o + 10)[0]
            out[name] = (self.root_lba * SECTOR + o, lba, size)
            o += n
        return out


def patch_record(f, rec_off: int, lba: int, size: int):
    """Write both-endian LBA (offset 2) and size (offset 10) of a directory record."""
    f.seek(rec_off + 2)
    f.write(struct.pack("<I", lba) + struct.pack(">I", lba))
    f.seek(rec_off + 10)
    f.write(struct.pack("<I", size) + struct.pack(">I", size))


# ── The mod's files as archive entries ───────────────────────────────────

def compile_scripts(tmp: Path) -> dict[str, bytes]:
    """.sol files of the mod -> {archive path with .sx: compiled bytes}."""
    import spanish_script
    if not SOLC.exists():
        raise SystemExit(f"{SOLC} not found (build the project first)")
    S = spanish_script.Scripts()
    inc = tmp / "inc"
    for h in S.disc.headers():
        p = inc / h
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(S.disc.header(h))
    out = {}
    for sol in sorted(MOD.rglob("*.sol")):
        rel = sol.relative_to(MOD).as_posix()
        src = tmp / "src" / sol.name
        src.parent.mkdir(exist_ok=True)
        src.write_bytes(sol.read_bytes())
        sx = tmp / "out.sx"
        sx.unlink(missing_ok=True)
        r = subprocess.run([str(SOLC), str(src), "-o", str(sx), "-I", str(inc)], capture_output=True, text=True)
        if r.returncode != 0 or not sx.exists():
            raise SystemExit(f"{rel}: solc failed\n{r.stdout}{r.stderr}")
        out[rel[:-4] + ".sx"] = sx.read_bytes()
    return out


def mod_files(tmp: Path) -> dict[str, bytes]:
    files = compile_scripts(tmp)
    for p in sorted(MOD.rglob("*")):
        if p.is_file() and p.suffix != ".sol":
            files[p.relative_to(MOD).as_posix()] = p.read_bytes()
    return files


class Table:
    """VOLUME.DAT's header and entry table, read from the image."""

    def __init__(self, iso: Iso, vol_lba: int):
        self.base = vol_lba * SECTOR
        iso.f.seek(self.base)
        magic, self.count, self.count2, self.data_start, self.total = struct.unpack(">4sIIII", iso.f.read(20))
        if magic != b"\xfa\xde\xba\xbe":
            raise SystemExit("VOLUME.DAT: bad magic")
        raw = iso.f.read(self.count * 24)
        self.rows = [list(struct.unpack_from(">6I", raw, i * 24)) for i in range(self.count)]
        self.iso = iso

    def stored_name(self, row) -> str:
        _, off, _, _, end, nlen = row
        self.iso.f.seek(self.base + self.data_start + end)
        return self.iso.f.read(nlen).split(b"\0")[0].decode("latin1")

    def find(self, path: str) -> int:
        h = volume.name_hash(path)
        hits = [i for i, r in enumerate(self.rows) if r[0] == h]
        if not hits:
            raise SystemExit(f"{path}: not in VOLUME.DAT")
        if len(hits) == 1:
            return hits[0]
        want = path.replace("/", "\\").upper()
        for i in hits:
            if self.stored_name(self.rows[i]).upper() == want:
                return i
        raise SystemExit(f"{path}: hash collision and no stored name matches")


# ── make ─────────────────────────────────────────────────────────────────

def build_image(src: Path, dst: Path, files: dict[str, bytes]) -> dict:
    iso = Iso(src)
    recs = iso.records()
    vol_rec, vol_lba, vol_size = recs["VOLUME.DAT"]
    pad_rec, pad_lba, pad_size = recs["SAMURAI2"]
    if vol_lba * SECTOR + align(vol_size) != pad_lba * SECTOR:
        raise SystemExit("SAMURAI2 does not follow VOLUME.DAT directly: layout not as expected")
    t = Table(iso, vol_lba)

    # New data, appended after the old (t.total is already a multiple of 2048).
    cursor = t.total
    blobs = []                               # (offset in the data area, bytes)
    for path, data in sorted(files.items()):
        i = t.find(path)
        row = t.rows[i]
        flags = row[3] & 1                   # keep the hash-collision flag, drop compression
        stored = data
        if flags:
            name = path.replace("/", "\\").encode("latin1") + b"\0"
            if len(name) > row[5]:
                raise SystemExit(f"{path}: stored name longer than its slot")
            stored = data + name.ljust(row[5], b"\0")
        row[1], row[2], row[3], row[4] = cursor, len(data), flags, cursor + len(data)
        blobs.append((cursor, stored))
        cursor = align(cursor + len(stored))
    new_total = cursor
    last_end = blobs[-1][0] + len(blobs[-1][1])
    new_vol_size = t.data_start + last_end
    added = align(new_vol_size) // SECTOR - align(vol_size) // SECTOR
    if added * SECTOR >= pad_size:
        raise SystemExit("not enough padding in SAMURAI2")

    print(f"{len(files)} files, {sum(len(b) for _, b in blobs):,} bytes; VOLUME.DAT grows by {added} sectors")
    shutil.copyfile(src, dst)
    with open(dst, "r+b") as f:
        # header and table
        f.seek(t.base)
        f.write(struct.pack(">4sIIII", b"\xfa\xde\xba\xbe", t.count, t.count2, t.data_start, new_total))
        f.write(b"".join(struct.pack(">6I", *r) for r in t.rows))
        for off, b in blobs:
            f.seek(t.base + t.data_start + off)
            f.write(b)
        # SAMURAI2 up by `added` sectors, shorter by the same at its end
        new_pad_lba, new_pad_size = pad_lba + added, pad_size - added * SECTOR
        with open(src, "rb") as g:
            g.seek(pad_lba * SECTOR)
            f.seek(new_pad_lba * SECTOR)
            left = new_pad_size
            while left:
                chunk = g.read(min(left, 1 << 22))
                f.write(chunk)
                left -= len(chunk)
        patch_record(f, vol_rec, vol_lba, new_vol_size)
        patch_record(f, pad_rec, new_pad_lba, new_pad_size)
    return {"table": t, "rows": t.rows, "total": new_total}


def xdelta(src: Path, dst: Path, out: Path):
    out.unlink(missing_ok=True)
    # -B: source window as big as the changes need; -9: best compression; -f: overwrite
    subprocess.run(["xdelta3", "-e", "-9", "-f", "-B", str(1 << 30), "-s", str(src), str(dst), str(out)], check=True)


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    return h.hexdigest()


def cmd_make(args):
    iso = Path(args.iso).expanduser()
    out = Path(args.out)
    with tempfile.TemporaryDirectory(dir=args.work) as w:
        w = Path(w)
        files = mod_files(w)
        dst = w / "patched.iso"
        build_image(iso, dst, files)
        xdelta(iso, dst, out)
        print(f"{out}: {out.stat().st_size:,} bytes")
        print(f"patched image md5: {md5(dst)}")
        if args.keep:
            shutil.move(dst, args.keep)
            print(f"kept {args.keep}")


# ── verify ───────────────────────────────────────────────────────────────

def read_entry(iso: Iso, t: Table, row) -> bytes:
    _, off, size, flags, end, _ = row
    iso.f.seek(t.base + t.data_start + off)
    data = iso.f.read(end - off)
    if flags & 2:
        return volume.lzo1x_decompress(data, size)
    if flags & 4:
        return volume.lzss_decompress(data, size)
    return data[:size]


def cmd_verify(args):
    iso_path = Path(args.iso).expanduser()
    with tempfile.TemporaryDirectory(dir=args.work) as w:
        w = Path(w)
        new = w / "applied.iso"
        subprocess.run(["xdelta3", "-d", "-f", "-s", str(iso_path), args.patch, str(new)], check=True)
        print(f"applied: {new.stat().st_size:,} bytes (original {iso_path.stat().st_size:,}), md5 {md5(new)}")
        a, b = Iso(iso_path), Iso(new)
        ra, rb = a.records(), b.records()
        for n in ra:
            print(f"  {n:<14} lba {ra[n][1]:>8} -> {rb[n][1]:>8}   size {ra[n][2]:>12,} -> {rb[n][2]:>12,}")
        ta, tb = Table(a, ra["VOLUME.DAT"][1]), Table(b, rb["VOLUME.DAT"][1])
        files = mod_files(w)
        replaced = {tb.find(p) for p in files}
        bad = 0
        for p, data in files.items():
            if read_entry(b, tb, tb.rows[tb.find(p)]) != data:
                print("  DIFFERENT:", p)
                bad += 1
        for i, (ra_, rb_) in enumerate(zip(ta.rows, tb.rows)):
            if i not in replaced and (ra_ != rb_ or read_entry(a, ta, ra_) != read_entry(b, tb, rb_)):
                print("  CHANGED ENTRY that should not have:", i)
                bad += 1
        # SAMURAI2 content intact (the part that is left)
        pa, pb = ra["SAMURAI2"], rb["SAMURAI2"]
        a.f.seek(pa[1] * SECTOR)
        b.f.seek(pb[1] * SECTOR)
        left = pb[2]
        while left:
            n = min(left, 1 << 22)
            if a.f.read(n) != b.f.read(n):
                print("  SAMURAI2 differs")
                bad += 1
                break
            left -= n
        print(f"{len(files)} replaced entries, {len(ta.rows) - len(files)} untouched: "
              + ("all as expected" if not bad else f"{bad} PROBLEMS"))
        sys.exit(1 if bad else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make", help="build the xdelta patch")
    m.add_argument("iso")
    m.add_argument("-o", "--out", required=True)
    m.add_argument("--keep", help="also keep the patched image here")
    m.add_argument("--work", help="directory for the temporary image (needs 2.5 GB)")
    v = sub.add_parser("verify", help="apply a patch and check the result")
    v.add_argument("iso")
    v.add_argument("patch")
    v.add_argument("--work")
    args = ap.parse_args()
    {"make": cmd_make, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    main()
