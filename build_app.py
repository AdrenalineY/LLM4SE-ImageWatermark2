#!/usr/bin/env python3
"""
一键打包脚本 - Python版本
支持Windows、macOS和Linux
"""

import os
import sys
import subprocess
import shutil
import platform

def check_python():
    """检查Python环境"""
    print("正在检查Python环境...")
    try:
        version = sys.version
        print(f"✅ Python版本: {version}")
        return True
    except Exception as e:
        print(f"❌ Python检查失败: {e}")
        return False

def install_pyinstaller():
    """安装PyInstaller"""
    print("正在检查PyInstaller...")
    try:
        import PyInstaller
        print("✅ PyInstaller已安装")
        return True
    except ImportError:
        print("PyInstaller未安装，正在安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✅ PyInstaller安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ PyInstaller安装失败: {e}")
            return False

def install_dependencies():
    """安装项目依赖"""
    print("正在安装项目依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

def clean_build():
    """清理之前的构建"""
    print("正在清理之前的构建...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"✅ 已清理 {folder} 文件夹")

def build_app():
    """打包应用程序"""
    print("开始打包应用程序...")
    print("这可能需要几分钟时间，请耐心等待...\n")
    
    try:
        # 使用spec文件打包
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller", 
            "PhotoWatermark2.spec", 
            "--clean", 
            "--noconfirm"
        ])
        print("\n✅ 打包成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包失败: {e}")
        return False

def create_simple_spec():
    """如果spec文件不存在，创建一个简单的spec文件"""
    if not os.path.exists("PhotoWatermark2.spec"):
        print("创建打包配置文件...")
        
        # 确定可执行文件扩展名
        exe_name = "PhotoWatermark2.exe" if platform.system() == "Windows" else "PhotoWatermark2"
        
        spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'jupyter',
        'notebook',
        'IPython',
        'test',
        'unittest',
        'distutils',
        'setuptools'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{exe_name}',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PhotoWatermark2',
)
"""
        with open("PhotoWatermark2.spec", "w", encoding="utf-8") as f:
            f.write(spec_content)
        print("✅ 配置文件创建成功")

def main():
    """主函数"""
    print("="*50)
    print("    Photo Watermark 2 应用程序打包脚本")
    print("="*50)
    print()
    
    # 检查当前目录
    if not os.path.exists("app/main.py"):
        print("❌ 错误: 未找到 app/main.py 文件！")
        print("请确保在项目根目录运行此脚本。")
        return False
    
    # 步骤1: 检查Python环境
    if not check_python():
        return False
    
    # 步骤2: 安装PyInstaller
    if not install_pyinstaller():
        return False
    
    # 步骤3: 安装依赖
    if not install_dependencies():
        return False
    
    # 步骤4: 创建spec文件（如果不存在）
    create_simple_spec()
    
    # 步骤5: 清理之前的构建
    clean_build()
    
    # 步骤6: 打包应用程序
    if not build_app():
        return False
    
    # 成功信息
    print()
    print("="*50)
    print("🎉 打包完成！")
    print("="*50)
    
    exe_name = "PhotoWatermark2.exe" if platform.system() == "Windows" else "PhotoWatermark2"
    dist_path = os.path.join("dist", "PhotoWatermark2")
    exe_path = os.path.join(dist_path, exe_name)
    
    print(f"应用程序已生成到: {dist_path}")
    print(f"主程序文件: {exe_path}")
    print()
    print("您可以将整个 dist/PhotoWatermark2 文件夹复制到任何计算机上运行。")
    print(f"双击 {exe_name} 即可启动应用程序。")
    print()
    
    # 询问是否立即运行
    if os.path.exists(exe_path):
        try:
            choice = input("是否立即运行应用程序？(y/n): ").lower().strip()
            if choice in ['y', 'yes', '是']:
                print("正在启动应用程序...")
                if platform.system() == "Windows":
                    os.startfile(exe_path)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.Popen(["open", exe_path])
                else:  # Linux
                    subprocess.Popen([exe_path])
        except KeyboardInterrupt:
            print("\\n用户取消")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\\n❌ 打包失败！")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\\n\\n用户中断打包过程")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ 发生意外错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)