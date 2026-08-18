#!/usr/bin/env python3
"""
LouDuck 构建脚本 v3.2 (build 20260806)
原则：启动越快越好，安装越方便越好。

关键决策：
- 使用 onedir（目录式发布），避免 onefile 每次启动的解压开销。
- 开启 optimize=1，去除 assert 与 __debug__ 分支，提升启动速度。
-  strip=True 去除二进制调试符号，减小体积。
- 构建后自动打包为 zip（含 install.bat + 说明），方便分发与安装。
- 自动清理 __pycache__、build、dist，避免旧文件污染。
"""

import os
import sys
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


APP_NAME = "LouDuck"
DIST_DIR_NAME = APP_NAME  # dist/LouDuck/
SPEC_NAME = f"{APP_NAME}.spec"


def log_ok(msg: str) -> None:
    print(f"[OK] {msg}")


def log_warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def log_err(msg: str) -> None:
    print(f"[ERR] {msg}")


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def ensure_module(pip_pkg: str, module_name: str) -> bool:
    """确保指定 Python 模块已安装；若缺失则通过 pip 安装。"""
    try:
        __import__(module_name)
        log_ok(f"{pip_pkg} 已安装")
        return True
    except ImportError:
        log_warn(f"缺少 {pip_pkg}，正在安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_pkg])
            log_ok(f"{pip_pkg} 安装完成")
            return True
        except Exception as e:
            log_err(f"{pip_pkg} 安装失败: {e}")
            return False


def ensure_pillow() -> bool:
    """Pillow 用于 PyInstaller 处理图标。"""
    return ensure_module("Pillow", "PIL")


def check_dependencies() -> bool:
    """检查并安装构建与运行所需的依赖。"""
    log_info("检查依赖...")
    required = {
        "pyinstaller": "PyInstaller",
        "PySide6": "PySide6",
        "soundfile": "soundfile",
        "numpy": "numpy",
        "scipy": "scipy",
        "openpyxl": "openpyxl",
        "ebu-adm-renderer": "ear",
    }
    all_ok = True
    for pip_pkg, module_name in required.items():
        if not ensure_module(pip_pkg, module_name):
            all_ok = False
    if not ensure_pillow():
        all_ok = False
    print()
    return all_ok


def find_icon() -> str | None:
    """查找项目中的 .ico 图标文件。"""
    project_dir = Path(__file__).parent.absolute()
    search_paths = [
        project_dir / "icon.ico",
        project_dir / "assets" / "icon.ico",
        project_dir / "resources" / "icon.ico",
        project_dir / "icons" / "icon.ico",
    ]
    for ico_file in project_dir.rglob("*.ico"):
        if ico_file.stat().st_size > 0:
            log_ok(f"找到图标: {ico_file}")
            return str(ico_file)
    for path in search_paths:
        if path.exists() and path.stat().st_size > 0:
            log_ok(f"找到图标: {path}")
            return str(path)
    log_warn("未找到有效的 .ico 文件，将使用默认图标")
    return None


def discover_ear_data() -> list[str]:
    """自动发现 EAR 渲染器所需的数据目录。"""
    datas = []
    try:
        import ear
        ear_pkg_dir = Path(ear.__file__).parent
        candidates = [
            ear_pkg_dir / "core" / "data",
            ear_pkg_dir / "fileio" / "adm" / "data",
        ]
        for cand in candidates:
            if cand.exists() and cand.is_dir():
                rel = "ear/" + "/".join(cand.relative_to(ear_pkg_dir).parts)
                datas.append(f"('{str(cand).replace(chr(92), '/')}', '{rel}'),")
        if datas:
            log_ok(f"发现 EAR 数据目录: {len(datas)} 个")
    except Exception as e:
        log_warn(f"未能发现 EAR 数据目录: {e}")
    return datas


def create_spec_file(
    project_dir: Path,
    src_dir: Path,
    icon_path: str | None,
    output_dir: Path,
) -> Path:
    """生成适配 onedir 模式的 PyInstaller .spec 文件。"""
    icon_str = f"icon='{icon_path.replace(chr(92), '/')}'," if icon_path else ""

    # 核心源码文件：必须作为数据文件放入根目录，
    # 因为 main_gui 在 QThread 内部延迟 import，PyInstaller 静态分析可能漏掉。
    data_files = [
        (src_dir / "adm_parser.py", "."),
        (src_dir / "itu1770_meter.py", "."),
        (src_dir / "report_exporter.py", "."),
        (src_dir / "mono_channel_matcher.py", "."),
        (src_dir / "renderers", "renderers"),
        (project_dir / "assets", "assets"),
        (project_dir / "i18n", "i18n"),
    ]
    data_lines = [f"('{str(src).replace(chr(92), '/')}', '{dst}')," for src, dst in data_files]
    data_lines.extend(discover_ear_data())
    datas_block = "\n        ".join(data_lines)

    project_dir_posix = str(project_dir).replace(chr(92), "/")
    src_dir_posix = str(src_dir).replace(chr(92), "/")
    hooks_dir_posix = str(project_dir / "pyinstaller_hooks").replace(chr(92), "/")
    main_script_posix = str(src_dir / "main_gui.py").replace(chr(92), "/")

    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# 由 build20260806.py 自动生成，请勿手动修改。

import sys
sys.setrecursionlimit(5000)

a = Analysis(
    ['{main_script_posix}'],
    pathex=['{project_dir_posix}', '{src_dir_posix}'],
    binaries=[],
    datas=[
        {datas_block}
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
        # renderers / EAR
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
        # 其他
        'dataclasses',
        'xml.etree.ElementTree',
        'pathlib',
        'typing',
        're',
        'struct',
    ],
    hookspath=['{hooks_dir_posix}'],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        # 排除不必要的模块，减小体积并提升启动速度
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
        'PIL',  # 仅构建时用于图标处理，运行时由 Qt 负责图像
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[
        'Qt*.dll',
        'qwindows.dll',
        'qminimal.dll',
        'qoffscreen.dll',
        'python*.dll',
        'vcruntime*.dll',
        'msvcp*.dll',
        'libopenblas*.dll',
        'mkl*.dll',
    ],
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
    strip=True,
    upx=True,
    upx_exclude=[
        'Qt*.dll',
        'qwindows.dll',
        'qminimal.dll',
        'qoffscreen.dll',
        'python*.dll',
        'vcruntime*.dll',
        'msvcp*.dll',
        'libopenblas*.dll',
        'mkl*.dll',
    ],
    name='{APP_NAME}',
)
'''
    spec_path = output_dir / SPEC_NAME
    spec_path.write_text(spec_content, encoding="utf-8")
    log_ok(f"创建 spec 文件: {spec_path}")
    return spec_path


def clean_pycache(project_dir: Path) -> None:
    """删除项目中的 __pycache__ 和 .pyc 文件，避免打包进 bundle。"""
    removed = 0
    for p in project_dir.rglob("__pycache__"):
        if p.is_dir():
            try:
                shutil.rmtree(p)
                removed += 1
            except Exception as e:
                log_warn(f"无法删除 {p}: {e}")
    for p in project_dir.rglob("*.pyc"):
        try:
            p.unlink()
            removed += 1
        except Exception:
            pass
    if removed:
        log_ok(f"清理缓存: {removed} 处")


def remove_readonly_handler(func, path, exc_info) -> None:
    """shutil.rmtree 的只读文件处理回调。"""
    import stat
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        log_warn(f"清理失败 {path}: {e}")


def safe_rmtree(path: Path) -> bool:
    """安全删除目录。"""
    if not path.exists():
        return True
    try:
        shutil.rmtree(path, onexc=remove_readonly_handler)
        log_ok(f"清理目录: {path}")
        return True
    except Exception as e:
        log_err(f"无法删除 {path}: {e}")
        return False


def build_executable() -> bool:
    """执行 PyInstaller onedir 构建。"""
    log_info("开始构建 onedir 目录...")
    project_dir = Path(__file__).parent.absolute()
    src_dir = project_dir / "src"

    main_script = src_dir / "main_gui.py"
    if not main_script.exists():
        log_err(f"未找到主脚本: {main_script}")
        return False

    build_dir = project_dir / "build"
    dist_dir = project_dir / "dist"
    app_dist_dir = dist_dir / DIST_DIR_NAME

    clean_pycache(project_dir)

    for d in (build_dir, dist_dir):
        if not safe_rmtree(d):
            return False

    build_dir.mkdir(parents=True, exist_ok=True)
    dist_dir.mkdir(parents=True, exist_ok=True)

    icon_path = find_icon()
    spec_file = create_spec_file(project_dir, src_dir, icon_path, build_dir)

    print()
    log_info("执行 PyInstaller 构建...")
    print("-" * 60)

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                str(spec_file),
                "--distpath",
                str(dist_dir),
                "--workpath",
                str(build_dir),
                "--noconfirm",
                "--clean",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.stderr:
            log_warn(result.stderr)

        exe_path = app_dist_dir / f"{APP_NAME}.exe"
        if exe_path.exists():
            dir_size = sum(
                f.stat().st_size for f in app_dist_dir.rglob("*") if f.is_file()
            )
            size_mb = dir_size / (1024 * 1024)
            print()
            print("=" * 60)
            log_ok("构建成功！")
            print("=" * 60)
            log_info(f"输出目录: {app_dist_dir}")
            log_info(f"总大小:   {size_mb:.1f} MB")
            log_info(f"启动方式: 双击 {APP_NAME}.exe")
            print()
            return True
        else:
            log_err(f"构建失败: 未找到 {exe_path}")
            return False

    except subprocess.CalledProcessError as e:
        log_err("构建失败！")
        print("标准输出:")
        print(e.stdout)
        print("错误输出:")
        print(e.stderr)
        return False


def create_readme(app_dist_dir: Path) -> None:
    """在发布目录中生成运行说明。"""
    readme_path = app_dist_dir / "README_运行说明.txt"
    readme_text = f"""LouDuck v3.2 目录式发布（onedir）

使用方式（二选一）：
1. 便携版：直接双击本目录下的 {APP_NAME}.exe 运行。
2. 安装版：将本目录与 install.bat 一起复制到目标位置，右键以管理员身份运行 install.bat，
   即可安装到 %ProgramFiles%\\{APP_NAME} 并创建桌面/开始菜单快捷方式。

技术特点：
- 本版本为 onedir 目录式发布，启动时无需解压文件，因此启动速度比 onefile 单文件版更快。
- 若需分发，可将整个 {APP_NAME} 目录与 install.bat 一起压缩为 zip。
"""
    readme_path.write_text(readme_text, encoding="utf-8")
    log_ok(f"生成运行说明: {readme_path}")


def create_install_bat() -> None:
    """生成与 onedir 目录结构匹配的安装脚本。"""
    install_script = f'''@echo off
chcp 65001 >nul
echo ==========================================
echo {APP_NAME} 安装程序
echo ==========================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 请以管理员身份运行此脚本！
    echo 右键 install.bat -> 以管理员身份运行
    pause
    exit /b 1
)

set INSTALL_DIR=%ProgramFiles%\\{APP_NAME}
echo 安装目录: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo 复制文件...
xcopy /E /I /Y "{APP_NAME}" "%INSTALL_DIR%"
if errorlevel 1 (
    echo 复制失败！
    pause
    exit /b 1
)

echo 创建桌面快捷方式...
set SHORTCUT="%USERPROFILE%\\Desktop\\{APP_NAME}.lnk"
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%INSTALL_DIR%\\{APP_NAME}.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\\{APP_NAME}.exe,0'; $Shortcut.Save()"

echo 创建开始菜单快捷方式...
set STARTMENU="%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs\\{APP_NAME}.lnk"
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTMENU%'); $Shortcut.TargetPath = '%INSTALL_DIR%\\{APP_NAME}.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\\{APP_NAME}.exe,0'; $Shortcut.Save()"

echo.
echo ==========================================
echo 安装完成！
echo ==========================================
echo.
echo 您可以通过以下方式启动程序:
echo   - 桌面快捷方式
echo   - 开始菜单
echo   - 直接运行: %INSTALL_DIR%\\{APP_NAME}.exe
echo.
pause
'''
    install_bat = Path("install.bat")
    install_bat.write_text(install_script, encoding="utf-8")
    log_ok(f"创建安装脚本: {install_bat}")


def create_distribution_zip() -> Path | None:
    """将 dist/LouDuck/ + install.bat 打包为 zip，便于分发。"""
    project_dir = Path(__file__).parent.absolute()
    dist_dir = project_dir / "dist"
    app_dist_dir = dist_dir / DIST_DIR_NAME
    install_bat = project_dir / "install.bat"

    if not app_dist_dir.exists():
        log_err(f"发布目录不存在，跳过打包: {app_dist_dir}")
        return None

    zip_name = f"{APP_NAME}_Win_v3.2_{datetime.now().strftime('%Y%m%d')}.zip"
    zip_path = dist_dir / zip_name

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. 添加整个 onedir 目录
            for file_path in app_dist_dir.rglob("*"):
                if file_path.is_file():
                    arc_name = DIST_DIR_NAME / file_path.relative_to(app_dist_dir)
                    zf.write(file_path, arc_name)
            # 2. 添加安装脚本
            if install_bat.exists():
                zf.write(install_bat, "install.bat")
            # 3. 添加运行说明
            readme_path = app_dist_dir / "README_运行说明.txt"
            if readme_path.exists():
                zf.write(readme_path, "README_运行说明.txt")

        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        log_ok(f"打包完成: {zip_path} ({zip_size_mb:.1f} MB)")
        return zip_path
    except Exception as e:
        log_err(f"打包失败: {e}")
        return None


def main() -> int:
    print()
    print("=" * 60)
    print(f"{APP_NAME} 构建程序 v3.2 (build 20260806) — onedir")
    print("=" * 60)
    print()
    print("原则：启动越快越好，安装越方便越好")
    print()
    print("此脚本将:")
    print("  1. 检查并安装依赖（包括 Pillow）")
    print("  2. 自动清理 __pycache__ 与旧构建产物")
    print("  3. 生成 onedir 模式的 .spec 文件")
    print("  4. 使用 PyInstaller 构建目录式可执行文件")
    print("  5. 生成 install.bat 安装脚本")
    print("  6. 自动打包为 zip 分发包")
    print()

    if sys.version_info < (3, 8):
        log_err("需要 Python 3.8 或更高版本")
        return 1

    if not check_dependencies():
        log_err("依赖检查未通过，请手动修复后重试")
        return 1

    if not build_executable():
        return 1

    create_install_bat()

    project_dir = Path(__file__).parent.absolute()
    app_dist_dir = project_dir / "dist" / DIST_DIR_NAME
    create_readme(app_dist_dir)

    zip_path = create_distribution_zip()

    print()
    print("=" * 60)
    log_ok("全部完成！")
    print("=" * 60)
    print()
    log_info(f"输出目录: {app_dist_dir}")
    log_info(f"启动方式: 双击 {app_dist_dir / f'{APP_NAME}.exe'}")
    if zip_path:
        log_info(f"分发包:   {zip_path}")
    log_info(f"安装脚本: {Path('install.bat').absolute()}")
    print()
    print("使用建议:")
    print("  - 开发调试：直接运行 dist/LouDuck/LouDuck.exe")
    print("  - 系统安装：右键 install.bat -> 以管理员身份运行")
    print("  - 网络分发：直接发送 dist/ 下的 zip 文件")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
