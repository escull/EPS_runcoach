# PyInstaller spec for EPS RunCoach.
#
# Rebuild with:
#   uv run pyinstaller eps_runcoach.spec --noconfirm
#
# Output goes to dist/EPS_RunCoach/EPS_RunCoach.exe. This is a "onedir"
# build (a folder, not a single .exe) - it starts faster and is more
# reliable with the numpy/matplotlib stack than --onefile, which
# re-extracts itself into a temp folder on every launch. A desktop
# shortcut to the .exe inside dist/EPS_RunCoach/ works exactly the same
# either way.

import ttkbootstrap

block_cipher = None

a = Analysis(
    ["eps_runcoach/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("assets", "assets"),
        (ttkbootstrap.__path__[0], "ttkbootstrap"),
    ],
    hiddenimports=[
        "google.genai",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EPS_RunCoach",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="EPS_RunCoach",
)
