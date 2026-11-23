# PyInstaller: el parcheador del mod en español como un solo programa.
#   pyinstaller --noconfirm --distpath dist --workpath build-patcher packaging/parchear-espanol.spec
# Da dist/parchear-espanol (Linux) o dist/parchear-espanol.exe (Windows).
from pathlib import Path

root = Path(SPECPATH).resolve().parent
tools = root / "tools"

a = Analysis(
    [str(tools / "spanish_patcher.py")],
    pathex=[str(tools)],
    # el parcheador las importa por nombre al ejecutar cada paso
    hiddenimports=["spanish_font", "spanish_text", "spanish_script", "spanish_data",
                   "spanish_task", "volume", "task", "sx", "bpm", "font_info"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name="parchear-espanol", console=True, upx=False)
