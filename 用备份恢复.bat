@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo  ImmersiveLoudness 备份恢复工具
echo ==========================================
echo.

if not exist backups (
    echo [错误] 没有找到 backups 文件夹
echo     请先运行 "备份.bat" 生成备份
echo.
    pause
    exit /b 1
)

echo [可用备份列表]
dir /b backups\src-*.zip 2>nul
echo.

echo 使用方法：
echo   1. 先把当前的 src 文件夹重命名（如改成 src_改崩了）
echo   2. 把上面列表中你想恢复的备份文件名（不含 .zip）填入下面
echo.
set /p backup_name=输入要恢复的备份文件名（如 src-20260423-013644-xxx）: 

if not exist "backups\%backup_name%.zip" (
    echo [错误] 找不到 backups\%backup_name%.zip
echo.
    pause
    exit /b 1
)

echo.
echo [正在恢复...]
tar -xf "backups\%backup_name%.zip" -C .
if %errorlevel% == 0 (
    echo [OK] 恢复完成，当前 src 已替换为备份版本
echo.
) else (
    echo [错误] 恢复失败，请检查 tar 命令是否可用
echo.
)

pause
