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

import os

import ttkbootstrap

block_cipher = None

# PyInstaller's Analysis only follows actual Python imports - a non-.py
# file sitting next to code (e.g. system_prompt.md) is invisible to it
# unless listed here explicitly. Rather than hardcode each one (and
# inevitably forget the next one added later), collect every non-.py
# file under eps_runcoach/ automatically, keeping it next to its source
# in the bundle so Path(__file__).parent-relative lookups still work.
package_datas = []
for root, _dirs, files in os.walk("eps_runcoach"):
    for filename in files:
        if not filename.endswith((".py", ".pyc")):
            package_datas.append((os.path.join(root, filename), root))

a = Analysis(
    ["eps_runcoach/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("assets", "assets"),
        (ttkbootstrap.__path__[0], "ttkbootstrap"),
        *package_datas,
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
