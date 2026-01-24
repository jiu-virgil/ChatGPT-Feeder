# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# Icon path - PyInstaller resolves relative to current working directory
icon_path = 'resources/spoon.ico'
icon = icon_path if os.path.exists(icon_path) else None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources/spoon.ico', 'resources'),
        ('resources/styles.qss', 'resources'),
        # Only include svg directory if it exists
        *([('resources/svg', 'resources/svg')] if os.path.exists('resources/svg') else []),
        ('resources/icons', 'resources/icons'),
        ('src', 'src'),
    ],
    hiddenimports=[
        'pyperclip',
        'src',
        'src.app',
        'src.config',
        'src.state',
        'src.components',
        'src.components.main_window',
        'src.components.file_tree',
        'src.components.toolbar',
        'src.components.context_usage',
        'src.utils',
        'src.utils.icons',
        'src.utils.icon_manifest',
        'src.utils.files',
        'src.utils.clipboard',
        'src.utils.tokens',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # --- SAFE TO EXCLUDE (Large 3rd party libs) ---
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'tkinter',
        'ipython',
        'notebook',
        
        # --- SAFE TO EXCLUDE (Unused PySide6 Modules) ---
        'PySide6.QtWebEngine',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtQuick',
        'PySide6.QtQuickWidgets',
        'PySide6.QtQml',
        'PySide6.QtBluetooth',
        'PySide6.QtNfc',
        'PySide6.QtPositioning',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtSql',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        'PySide6.QtWebSockets',
        'PySide6.QtXml',
        'PySide6.QtXmlPatterns',
        'PySide6.QtHelp',
        'PySide6.QtDesigner',
        'PySide6.QtUiTools',
        'PySide6.Qt3D',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtGamepad',
        'PySide6.QtLocation',
        'PySide6.QtNetwork',
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
        'PySide6.QtRemoteObjects',
        'PySide6.QtScxml',
        'PySide6.QtScript',
        'PySide6.QtScriptTools',
        'PySide6.QtStateMachine',
        'PySide6.QtTextToSpeech',
        'PySide6.QtVirtualKeyboard',
        
        # --- REMOVED DANGEROUS EXCLUDES ---
        # Do NOT exclude standard library modules like 'asyncio', 
        # 'concurrent.futures', 'email', 'http', etc. 
        # This causes the "No module named threading" error.
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
    name='Spoon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Changed to False for safety, True can sometimes break Windows builds
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)