# -*- mode: python ; coding: utf-8 -*-

import sys
sys.setrecursionlimit(5000)

a = Analysis(
    ['D:/My Documents/家庭/我的开发/ImmersiveLoudness/src/main_gui.py'],
    pathex=['D:/My Documents/家庭/我的开发/ImmersiveLoudness'],
    binaries=[],
    datas=[
        ('D:/My Documents/家庭/我的开发/ImmersiveLoudness/src/adm_parser.py', '.'),
        ('D:/My Documents/家庭/我的开发/ImmersiveLoudness/src/itu1770_meter.py', '.'),
        ('D:/My Documents/家庭/我的开发/ImmersiveLoudness/src/report_exporter.py', '.'),
    ],
    hiddenimports=[
        # PySide6
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        # SciPy / NumPy（必须包含 unittest）
        'scipy.signal',
        'scipy._lib.messagestream',
        'scipy.special._cdflib',
        'unittest',
        'unittest.mock',
        # NumPy
        'numpy.core._dtype_ctypes',
        'numpy.core._multiarray_tests',
        # soundfile
        'soundfile',
        '_soundfile_data',
        # openpyxl
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        # 其他
        'dataclasses',
        'xml.etree.ElementTree',
        'pathlib',
        'typing',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不必要的模块（但不要排除 unittest！）
        'matplotlib',
        'pandas',
        'tkinter',
        'pytest',
        'ipython',
        'jupyter',
        'notebook',
        'sphinx',
        'docutils',
        'PyQt5',
        'PyQt6',
        'PySide2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ImmersiveLoudness',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='D:/My Documents/家庭/我的开发/ImmersiveLoudness/assets/icon.ico',
)
