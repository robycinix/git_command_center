# PyInstaller specification for the current operating system.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files(
    "git_command_center",
    includes=["data/*.yaml", "data/locales/*.yaml", "themes/*.tcss"],
)
hiddenimports = collect_submodules("textual.widgets")

a = Analysis(
    ["src/git_command_center/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name="git-command-center",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
