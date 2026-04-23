@echo off
chcp 65001 >nul
echo ==========================================
echo ImmersiveLoudness 安装程序
echo ==========================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 请以管理员身份运行此脚本！
    pause
    exit /b 1
)

set INSTALL_DIR=%ProgramFiles%\ImmersiveLoudness
echo 安装目录: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo 复制文件...
copy /Y "ImmersiveLoudness.exe" "%INSTALL_DIR%\"
if errorlevel 1 (
    echo 复制失败！
    pause
    exit /b 1
)

echo 创建桌面快捷方式...
set SHORTCUT="%USERPROFILE%\Desktop\ImmersiveLoudness.lnk"
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%INSTALL_DIR%\ImmersiveLoudness.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\ImmersiveLoudness.exe,0'; $Shortcut.Save()"

echo 创建开始菜单快捷方式...
set STARTMENU="%ProgramData%\Microsoft\Windows\Start Menu\Programs\ImmersiveLoudness.lnk"
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTMENU%'); $Shortcut.TargetPath = '%INSTALL_DIR%\ImmersiveLoudness.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\ImmersiveLoudness.exe,0'; $Shortcut.Save()"

echo.
echo ==========================================
echo 安装完成！
echo ==========================================
echo.
echo 您可以通过以下方式启动程序:
echo   - 桌面快捷方式
echo   - 开始菜单
echo   - 直接运行: %INSTALL_DIR%\ImmersiveLoudness.exe
echo.
pause
