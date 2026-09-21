# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification for LumiTrack — FSOC Virtual Camera Tracking System.
Bundles the complete application, scenario JSONs, AI model, and PySide6 frontend.
"""

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

added_files = [
    ('scenarios/*.json', 'scenarios'),
    ('lr_model.json', '.'),
    ('src/plugins/algorithms', 'src/plugins/algorithms'),
]

hidden_imports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'cv2',
    'numpy',
    'scipy',
] + collect_submodules('src')

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
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
    name='LumiTrack',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to True for evaluator CLI and debugging output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LumiTrack',
)
