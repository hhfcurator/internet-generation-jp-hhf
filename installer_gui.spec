# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: Internet Generation 日本語化パッチ GUI インストーラ
ビルド: pyinstaller installer_gui.spec
出力: dist/InternetGeneration-JP-Installer.exe (単一 .exe)
"""
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# UnityPy はサブモジュール/データが多いので collect_all で根こそぎ取り込む
unitypy_datas, unitypy_binaries, unitypy_hidden = collect_all('UnityPy')
pil_hidden = collect_submodules('PIL')

ROOT = Path('.').resolve()
TOOLS = ROOT / 'tools'
DATA = ROOT / 'data'
DLLPATCH = TOOLS / 'dll_patcher'

# 同梱データ: (src on disk, dest in bundle)
datas = [
    (str(DATA / 'story_jp.json'), 'data'),
    (str(DATA / 'dll_mappings.json'), 'data'),
    (str(DATA / 'asset_mappings.json'), 'data'),
    (str(DATA / 'jp_adverbs.txt'), 'data'),
    (str(DATA / 'katakana_parts.txt'), 'data'),
    # patcher.py / sf_rewriter.py を tools/ に
    (str(TOOLS / 'patcher.py'), 'tools'),
    (str(TOOLS / 'sf_rewriter.py'), 'tools'),
    # DLL patcher (.NET Patcher.exe + Mono.Cecil)
    (str(DLLPATCH / 'Patcher.exe'), 'tools/dll_patcher'),
    (str(DLLPATCH / 'Patcher.dll'), 'tools/dll_patcher'),
    (str(DLLPATCH / 'Patcher.deps.json'), 'tools/dll_patcher'),
    (str(DLLPATCH / 'Patcher.runtimeconfig.json'), 'tools/dll_patcher'),
    (str(DLLPATCH / 'Mono.Cecil.dll'), 'tools/dll_patcher'),
    (str(DLLPATCH / 'Mono.Cecil.Mdb.dll'), 'tools/dll_patcher'),
    (str(DLLPATCH / 'Mono.Cecil.Pdb.dll'), 'tools/dll_patcher'),
    (str(DLLPATCH / 'Mono.Cecil.Rocks.dll'), 'tools/dll_patcher'),
    # アイコン (ランタイムでも参照)
    (str(ROOT / 'icon.ico'), '.'),
]

hiddenimports = unitypy_hidden + pil_hidden + [
    'UnityPy',
    'UnityPy.classes',
    'UnityPy.files',
    'UnityPy.files.ObjectReader',
    'PIL',
    'PIL.Image',
]

# UnityPy が同梱する型ツリーデータ等
datas += unitypy_datas
# UnityPy が含む C 拡張バイナリ
_extra_binaries = unitypy_binaries

a = Analysis(
    [str(TOOLS / 'installer_gui.py')],
    pathex=[str(TOOLS)],
    binaries=_extra_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'openpyxl',
        'matplotlib',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
        # numpy は UnityPy が条件付きで使うため除外しない
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='InternetGeneration-JP-Installer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,            # UPX 圧縮は AV 誤検知率上昇のため無効
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # --windowed (本番)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'icon.ico'),
)
