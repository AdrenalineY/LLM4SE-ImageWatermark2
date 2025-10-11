@echo off
echo ===========================================
echo    Photo Watermark 2 应用程序打包脚本
echo ===========================================
echo.

echo 正在检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python环境！
    echo 请确保已安装Python并添加到系统PATH中。
    pause
    exit /b 1
)

echo.
echo 正在检查PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller未安装，正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo 错误: PyInstaller安装失败！
        pause
        exit /b 1
    )
)

echo.
echo 正在检查项目依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误: 依赖安装失败！
    pause
    exit /b 1
)

echo.
echo 开始打包应用程序...
echo 这可能需要几分钟时间，请耐心等待...
echo.

rem 清理之前的构建
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

rem 开始打包
pyinstaller PhotoWatermark2.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ❌ 打包失败！请检查错误信息。
    pause
    exit /b 1
) else (
    echo.
    echo ✅ 打包成功！
    echo.
    echo 应用程序已生成到: dist\PhotoWatermark2\
    echo 主程序文件: dist\PhotoWatermark2\PhotoWatermark2.exe
    echo.
    echo 您可以将整个 dist\PhotoWatermark2 文件夹复制到任何Windows计算机上运行。
    echo 双击 PhotoWatermark2.exe 即可启动应用程序。
    echo.
    
    rem 询问是否立即运行
    set /p choice="是否立即运行应用程序？(y/n): "
    if /i "%choice%"=="y" (
        echo 正在启动应用程序...
        start "" "dist\PhotoWatermark2\PhotoWatermark2.exe"
    )
)

echo.
echo 打包完成！
pause