#!/usr/bin/env python3
"""
Parcheador del mod en español de Way of the Samurai 2 (port nativo).

Lee tu disco ya extraído (carpeta «extracted», que el port crea la primera vez que
le das tu ISO) y la traducción de «translations/es», y escribe el mod en
«mods/espanol/files».  No contiene nada del juego: solo la traducción y el código
para aplicarla.

Va en la carpeta del port, junto a «wots2».  Es lo mismo que ejecutar, en orden,
spanish_font.py, spanish_text.py build, spanish_script.py build,
spanish_data.py build y spanish_task.py build.

  parchear-espanol              genera el mod
  parchear-espanol --comprobar  además, comprueba las traducciones (más lento)
  parchear-espanol --detalle    muestra todo lo que escribe cada paso
"""
import argparse
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wotsroot import ROOT  # noqa: E402

# Un VOLUME.DAT de verdad pesa unos 366 MB; por debajo de esto no es el del disco.
MIN_VOLUME = 300 * 1024 * 1024


def fail(msg: str, code: int = 2):
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def check_extracted():
    ext = ROOT / "extracted"
    if not ext.is_dir():
        fail(f"no existe la carpeta «extracted» en {ROOT}.\n"
             "Arranca primero el juego con tu ISO (./wots2 \"Way of the Samurai 2.iso\"):\n"
             "la primera vez extrae los archivos del disco ahí. Después vuelve a ejecutar esto.")
    vol, elf = ext / "VOLUME.DAT", ext / "SLUS_208.93"
    for p in (vol, elf):
        if not p.is_file() or p.stat().st_size == 0:
            fail(f"falta «{p.relative_to(ROOT)}» o está vacío: la extracción del disco no se completó.\n"
                 "Borra la carpeta «extracted» y vuelve a arrancar el juego con tu ISO.")
    if vol.stat().st_size < MIN_VOLUME:
        fail(f"«{vol.relative_to(ROOT)}» pesa solo {vol.stat().st_size:,} bytes: está incompleto.\n"
             "Borra la carpeta «extracted» y vuelve a arrancar el juego con tu ISO.")
    with open(vol, "rb") as f:
        head = f.read(20)
    if head[:4] != b"\xfa\xde\xba\xbe":
        fail("«extracted/VOLUME.DAT» no es el archivo del disco (cabecera distinta).")
    # El mod es para el disco norteamericano: sus rutas llevan el prefijo «Us/».
    import volume
    if volume.Volume(vol).find("menu/menutext.txt") is None:
        fail("este disco no es el norteamericano (SLUS-208.93): no tiene los textos «Us/».")
    if not (ROOT / "translations" / "es" / "menutext.tsv").is_file():
        fail(f"falta la carpeta «translations/es» junto al programa ({ROOT}).")
    if not (ROOT / "mods").is_dir():
        fail(f"falta la carpeta «mods» junto al programa ({ROOT}): ejecútalo en la carpeta del port.")


def run(title: str, module: str, argv: list[str], verbose: bool = False):
    """Run one tool's main().  Its output is long (a line per file): show only the last
    line, or all of it when something fails or with --detalle."""
    import contextlib
    import importlib
    import io
    print(f"== {title}", flush=True)
    mod = importlib.import_module(module)
    sys.argv = [module + ".py"] + argv
    buf = io.StringIO()
    code = None
    try:
        with contextlib.redirect_stdout(buf):
            mod.main()
    except SystemExit as e:
        code = e.code
    out = buf.getvalue().rstrip("\n").split("\n")
    if verbose or code not in (None, 0):
        print("\n".join(out))
    elif out and out[-1]:
        print("   " + out[-1])
    if code not in (None, 0):
        fail(f"«{title}» ha fallado (código {code}).", 1)


def ensure_mod_ini():
    ini = ROOT / "mods" / "espanol" / "mod.ini"
    if not ini.exists():
        ini.parent.mkdir(parents=True, exist_ok=True)
        ini.write_text("[mod]\nname = Español\ndescription = The game in Spanish\nenabled = 1\n",
                       encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comprobar", action="store_true", help="comprobar también las traducciones")
    ap.add_argument("--detalle", action="store_true", help="mostrar toda la salida de cada paso")
    args = ap.parse_args()

    # Windows redirige a la página de códigos local (cp1252): sin esto, los acentos salen rotos.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    print("Mod en español de Way of the Samurai 2")
    check_extracted()
    ensure_mod_ini()

    steps = [("Fuente con ¿ » º", "spanish_font", []),
             ("Menús", "spanish_text", ["build"]),
             ("Historia y tiendas", "spanish_script", ["build"]),
             ("Datos (objetos, tiendas, finales…)", "spanish_data", ["build"]),
             ("Conversaciones de los NPC", "spanish_task", ["build"])]
    for title, module, argv in steps:
        run(title, module, argv, args.detalle)
    if args.comprobar:
        for title, module in (("menús", "spanish_text"), ("datos", "spanish_data"), ("tareas", "spanish_task")):
            run(f"Comprobar {title}", module, ["check"], args.detalle)

    files = [p for p in (ROOT / "mods" / "espanol" / "files").rglob("*") if p.is_file()]
    print(f"\nListo: {len(files)} archivos en mods/espanol/files "
          f"({sum(p.stat().st_size for p in files) / 1e6:.1f} MB).")
    print("Arranca el juego de siempre: el mod «Español» está activado.")


if __name__ == "__main__":
    try:
        main()
    finally:
        # Con doble clic en Windows la ventana se cerraría al acabar y no se leería nada.
        if getattr(sys, "frozen", False) and os.name == "nt" and sys.stdin and sys.stdin.isatty():
            try:
                input("\nPulsa Intro para cerrar.")
            except EOFError:    # entrada redirigida (NUL también «es» una consola)
                pass
