#!/usr/bin/env python3
"""
LouDuck 构建脚本 v2.0 (build 260603) — onedir 目录式发布
更新：改用 onedir 模式，显著缩短启动时间（无单文件解压开销）
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def ensure_pillow():
    """确保安装 Pillow（PyInstaller处理图标需要）"""
    try:
        from PIL import Image
        print("[OK] Pillow installed")
        return True
    except ImportError:
        print("[WARN] Missing Pillow, installing...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'Pillow'])
            print("[OK] Pillow install complete")
            return True
        except Exception as e:
            print(f"[ERR] Pillow install failed: {e}")
            return False


def find_icon():
    """查找项目中的图标文件"""
    project_dir = Path(__file__).parent.absolute()
    
    search_paths = [
        project_dir / 'icon.ico',
        project_dir / 'assets' / 'icon.ico',
        project_dir / 'resources' / 'icon.ico',
        project_dir / 'icons' / 'icon.ico',
    ]
    
    for ico_file in project_dir.rglob('*.ico'):
        if ico_file.stat().st_size > 0:
            print(f"[OK] Found icon: {ico_file}")
            return str(ico_file)
    
    for path in search_paths:
        if path.exists() and path.stat().st_size > 0:
            print(f"[OK] Found icon: {path}")
            return str(path)
    
    print("[WARN] No valid .ico found, using default")
    return None


def check_dependencies():
    """检查并安装必要的依赖"""
    required = {
        'pyinstaller': 'PyInstaller',
        'PySide6': 'PySide6',
        'soundfile': 'soundfile',
        'numpy': 'numpy',
        'scipy': 'scipy',
        'openpyxl': 'openpyxl',
        'ebu-adm-renderer': 'ear',
    }
    
    print("=" * 60)
    print("检查依赖...")
    print("=" * 60)
    
    for pip_pkg, module_name in required.items():
        try:
            __import__(module_name)
            print(f"  [OK] {pip_pkg}")
        except ImportError:
            print(f"  [ERR] {pip_pkg} - 正在安装...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pip_pkg])
            print(f"  [OK] {pip_pkg} 安装完成")
    
    ensure_pillow()
    print()


def create_spec_file(project_dir, src_dir, icon_path, output_dir):
    """创建 onedir 模式的 .spec 文件"""
    
    adm_parser = str(src_dir / 'adm_parser.py').replace('\\', '/')
    itu1770 = str(src_dir / 'itu1770_meter.py').replace('\\', '/')
    report_exporter = str(src_dir / 'report_exporter.py').replace('\\', '/')
    mono_matcher = str(src_dir / 'mono_channel_matcher.py').replace('\\', '/')
    renderers_dir = str(src_dir / 'renderers').replace('\\', '/')
    main_script = str(src_dir / 'main_gui.py').replace('\\', '/')
    hooks_dir = str(project_dir / 'pyinstaller_hooks').replace('\\', '/')
    assets_dir = str(project_dir / 'assets').replace('\\', '/')
    i18n_dir = str(project_dir / 'i18n').replace('\\', '/')
    
    icon_str = f"icon='{icon_path.replace(chr(92), '/')}'," if icon_path else ""
    
    # EAR 数据文件路径
    try:
        import ear
        ear_pkg_dir = Path(ear.__file__).parent
        ear_core_data = str(ear_pkg_dir / 'core' / 'data').replace('\\', '/')
        ear_adm_data = str(ear_pkg_dir / 'fileio' / 'adm' / 'data').replace('\\', '/')
        ear_datas = f"""('{ear_core_data}', 'ear/core/data'),
        ('{ear_adm_data}', 'ear/fileio/adm/data'),"""
    except Exception:
        ear_datas = ""
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
sys.setrecursionlimit(5000)

a = Analysis(
    ['{main_script}'],
    pathex=['{str(project_dir).replace(chr(92), '/')}', '{str(src_dir).replace(chr(92), '/')}'],
    binaries=[],
    datas=[
        ('{adm_parser}', '.'),
        ('{itu1770}', '.'),
        ('{report_exporter}', '.'),
        ('{mono_matcher}', '.'),
        ('{renderers_dir}', 'renderers'),
        ('{assets_dir}', 'assets'),
        ('{i18n_dir}', 'i18n'),
        {ear_datas}
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'scipy.signal',
        'scipy._lib.messagestream',
        'scipy.special._cdflib',
        'unittest',
        'unittest.mock',
        'numpy.core._dtype_ctypes',
        'numpy.core._multiarray_tests',
        'soundfile',
        '_soundfile_data',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'renderers',
        'renderers.ear_renderer',
        'ear.cmdline.render_file',
        'ear.core.bs2051',
        'ear.core.allocentric',
        'ear.core.hoa',
        'ear.core.direct_speakers',
        'ear.core.objectbased',
        'ear.core.metadata_input',
        'ear.fileio',
        'ear.fileio.bw64',
        'ear.fileio.adm',
        'ear.fileio.adm.xml',
        'dataclasses',
        'xml.etree.ElementTree',
        'pathlib',
        'typing',
        're',
        'struct',
    ],
    hookspath=['{hooks_dir}'],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
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
    [],
    exclude_binaries=True,
    name='LouDuck',
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
    {icon_str}
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LouDuck',
)
'''
    
    spec_path = output_dir / 'LouDuck.spec'
    spec_path.write_text(spec_content, encoding='utf-8')
    print(f"[OK] Created spec file: {spec_path}")
    return str(spec_path)


def build_executable():
    """构建 onedir 目录"""
    print("=" * 60)
    print("开始构建 onedir 目录...")
    print("=" * 60)
    print()
    
    project_dir = Path(__file__).parent.absolute()
    src_dir = project_dir / 'src'
    
    main_script = src_dir / 'main_gui.py'
    if not main_script.exists():
        print(f"[ERR] Main script not found: {main_script}")
        return False
    
    build_dir = project_dir / 'build'
    dist_dir = project_dir / 'dist'
    
    def _remove_readonly(func, path, exc):
        import stat
        os.chmod(path, stat.S_IWRITE)
        func(path)

    for d in [build_dir, dist_dir]:
        if d.exists():
            try:
                shutil.rmtree(d, onexc=_remove_readonly)
                print(f"[OK] Cleaned: {d}")
            except PermissionError as e:
                print(f"[ERR] Cannot remove {d}: {e}")
                print("      请检查是否有程序实例正在运行，或手动删除该目录后重试。")
                return False
    
    build_dir.mkdir(exist_ok=True)
    dist_dir.mkdir(exist_ok=True)
    
    icon_path = find_icon()
    spec_file = create_spec_file(project_dir, src_dir, icon_path, build_dir)
    
    print()
    print("执行 PyInstaller 构建...")
    print("-" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'PyInstaller', spec_file, '--distpath', str(dist_dir), '--workpath', str(build_dir), '--noconfirm'],
            check=True,
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print("警告/信息:", result.stderr)
        
        exe_path = dist_dir / 'LouDuck' / 'LouDuck.exe'
        if exe_path.exists():
            dir_size = sum(f.stat().st_size for f in (dist_dir / 'LouDuck').rglob('*') if f.is_file())
            size_mb = dir_size / (1024 * 1024)
            print()
            print("=" * 60)
            print("[OK] Build success!")
            print("=" * 60)
            print(f"  输出目录: {dist_dir / 'LouDuck'}")
            print(f"  总大小:   {size_mb:.1f} MB")
            print(f"  启动方式: 双击 LouDuck.exe")
            print()
            return True
        else:
            print("[ERR] Build failed: output not found")
            return False
            
    except subprocess.CalledProcessError as e:
        print("[ERR] Build failed!")
        print("错误输出:")
        print(e.stdout)
        print(e.stderr)
        return False


def create_installer():
    """创建安装脚本（适配 onedir 目录结构）"""
    install_script = '''@echo off
chcp 65001 >nul
echo ==========================================
echo LouDuck 安装程序
echo ==========================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 请以管理员身份运行此脚本！
    pause
    exit /b 1
)

set INSTALL_DIR=%ProgramFiles%\\LouDuck
echo 安装目录: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo 复制文件...
xcopy /E /I /Y "LouDuck" "%INSTALL_DIR%"
if errorlevel 1 (
    echo 复制失败！
    pause
    exit /b 1
)

echo 创建桌面快捷方式...
set SHORTCUT="%USERPROFILE%\\Desktop\\LouDuck.lnk"
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%INSTALL_DIR%\\LouDuck.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\\LouDuck.exe,0'; $Shortcut.Save()"

echo 创建开始菜单快捷方式...
set STARTMENU="%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs\\LouDuck.lnk"
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTMENU%'); $Shortcut.TargetPath = '%INSTALL_DIR%\\LouDuck.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\\LouDuck.exe,0'; $Shortcut.Save()"

echo.
echo ==========================================
echo 安装完成！
echo ==========================================
echo.
echo 您可以通过以下方式启动程序:
echo   - 桌面快捷方式
echo   - 开始菜单
echo   - 直接运行: %INSTALL_DIR%\\LouDuck.exe
echo.
pause
'''
    
    install_bat = Path('install.bat')
    install_bat.write_text(install_script, encoding='utf-8')
    print(f"[OK] Created install script: {install_bat}")


def main():
    print()
    print("=" * 60)
    print("LouDuck 构建程序 v2.0 (build 260603) — onedir")
    print("=" * 60)
    print()
    print("此脚本将:")
    print("  1. 检查并安装依赖（包括 Pillow）")
    print("  2. 查找项目中的 .ico 图标文件")
    print("  3. 生成 .spec 文件（onedir 模式）")
    print("  4. 使用 PyInstaller 打包成目录")
    print("  5. 创建可选的安装脚本")
    print()
    
    if sys.version_info < (3, 8):
        print("[ERR] Requires Python 3.8+")
        return 1
    
    check_dependencies()
    
    if build_executable():
        create_installer()
        
        print()
        print("=" * 60)
        print("构建完成！")
        print("=" * 60)
        print()
        print("输出目录:")
        print("  dist/LouDuck/        - 主程序目录（可直接运行）")
        print("  dist/LouDuck.exe     - 不存在（onedir 模式）")
        print("  install.bat           - 安装脚本（可选）")
        print()
        print("分发方式:")
        print("  1. 压缩 dist/LouDuck/ 为 zip 直接分发")
        print("  2. 使用 install.bat 安装到系统")
        print()
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
