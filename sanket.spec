# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification for SANKET — AI-Assisted FSOC Virtual Camera Tracking System.
SIH 2026 Problem Statement PS-26169 (Department of Space / ISRO).

Bundles the complete Python backend, scenario JSONs, AI model, PySide6 GUI, and OpenCV.
Builds the unified SANKET.exe executable with console=True for complete CLI and GUI support,
bypassing Windows Application Control (WDAC) restrictions on windowless bootloaders.
"""

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

added_files = [
    ('scenarios/*.json', 'scenarios'),
    ('lr_model.json', '.'),
    ('src/plugins/algorithms', 'src/plugins/algorithms'),
    ('models', 'models'),
    ('frontend/dist', 'frontend/dist'),
    ('App_Logo_Assets_Final', 'App_Logo_Assets_Final'),
    ('Videos', 'Videos'),
]

# Explicitly bundle Microsoft Visual C++ runtime DLLs into _internal root to guarantee clean-machine immunity
windir = os.environ.get('WINDIR', 'C:\\Windows')
sys32 = os.path.join(windir, 'System32')
extra_binaries = []
for dll_name in ['msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'vcruntime140.dll', 'vcruntime140_1.dll']:
    p = os.path.join(sys32, dll_name)
    if os.path.exists(p):
        extra_binaries.append((p, '.'))

hidden_imports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebChannel',
    'cv2',
    'numpy',
] + collect_submodules('src')

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=extra_binaries,
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SANKET',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='App_Logo_Assets_Final\\favicon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SANKET',
)
