"""
SmartResearch Windows 打包脚本
用法: python build_exe.py

依赖: pip install pyinstaller
"""

import subprocess, sys, shutil
from pathlib import Path


def check_pyinstaller():
    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__} 已安装")
        return True
    except ImportError:
        print("PyInstaller 未安装")
        return False


def install_pyinstaller():
    print("正在安装 PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def clean():
    for d in ["build", "dist"]:
        p = Path(d)
        if p.exists():
            shutil.rmtree(p)
            print(f"清理: {d}")


def build():
    print("\n" + "=" * 50)
    print("  SmartResearch - 开始打包")
    print("=" * 50 + "\n")

    clean()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "SmartResearch.spec",
        "--noconfirm",
        "--clean",
    ]
    print(f"运行: {' '.join(cmd)}\n")
    subprocess.check_call(cmd)

    exe = Path("dist/SmartResearch.exe")
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"\n打包成功: {exe} ({size_mb:.1f} MB)")
        print(f"\n使用方法:")
        print(f"  1. 将 dist/ 文件夹复制到目标电脑")
        print(f"  2. 确保 .env 文件与 SmartResearch.exe 在同一目录")
        print(f"  3. 双击 SmartResearch.exe")
    else:
        print("\n打包失败，请检查错误信息")


def main():
    if not check_pyinstaller():
        resp = input("是否现在安装 PyInstaller? (y/n): ")
        if resp.lower() == 'y':
            install_pyinstaller()
        else:
            print("已取消。手动安装: pip install pyinstaller")
            return

    # 确认 .env 存在
    if not Path(".env").exists():
        print("\n⚠ 警告: .env 文件不存在！")
        if Path(".env.example").exists():
            shutil.copy(".env.example", ".env")
            print("已从 .env.example 创建 .env，请编辑填入 API Key")

    build()


if __name__ == "__main__":
    main()