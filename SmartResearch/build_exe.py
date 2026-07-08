"""
SmartResearch Windows 打包脚本
====================
将 Python 项目打包为独立的 Windows exe 文件，无需安装 Python 即可运行。

用法:
    python build_exe.py              # 交互式选择
    python build_exe.py web          # 打包 Web 服务器版
    python build_exe.py desktop      # 打包桌面版（推荐，像 CCswitch 一样下载即用）

依赖: pip install pyinstaller
"""

import subprocess, sys, shutil, os, zipfile
from pathlib import Path


VERSION = "1.0.0"
BUILD_TYPES = {
    "web": {
        "spec": "SmartResearch.spec",
        "name": "SmartResearch-Web",
        "desc": "Web 服务器版（需浏览器访问 http://localhost:8002）",
    },
    "desktop": {
        "spec": "desktop_build.spec",
        "name": "SmartResearch-Desktop",
        "desc": "桌面版（原生 GUI 应用，像 CCswitch 一样双击即用）",
    },
}


# ══════════════════════════════════════════════════════════
#  依赖检查和安装
# ══════════════════════════════════════════════════════════


def check_pyinstaller():
    try:
        import PyInstaller
        version = getattr(PyInstaller, "__version__", "unknown")
        print(f"  [OK] PyInstaller {version}")
        return True
    except ImportError:
        print("  [..] PyInstaller 未安装")
        return False


def install_pyinstaller():
    print("  正在安装 PyInstaller...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "pyinstaller"],
        stdout=subprocess.DEVNULL,
    )
    print("  [OK] PyInstaller 安装完成")


def check_env():
    """检查 .env 文件，缺失则从 .env.example 创建"""
    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        # 检查是否有 API Key
        with open(env_file, "r", encoding="utf-8") as f:
            content = f.read()
        if "DEEPSEEK_API_KEY=sk-" in content:
            print("  [OK] .env 文件已配置 API Key")
        else:
            print("  [!!] .env 文件中未检测到有效的 DEEPSEEK_API_KEY")
            print("       用户需自行配置 API Key 才能使用 AI 功能")
        return

    if env_example.exists():
        shutil.copy(str(env_example), str(env_file))
        print("  [OK] 已从 .env.example 创建 .env 文件")
        print("  [!!] 请编辑 .env 填入 DEEPSEEK_API_KEY 后再分发")
    else:
        print("  [!!] .env 和 .env.example 均不存在，请手动创建 .env 文件")


def check_requirements():
    """检查核心依赖是否已安装"""
    required = ["PySide6", "httpx", "beautifulsoup4", "markdown", "loguru"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"  [!!] 缺少依赖: {', '.join(missing)}")
        print(f"  运行: pip install {' '.join(missing)}")
        return False
    return True


# ══════════════════════════════════════════════════════════
#  构建
# ══════════════════════════════════════════════════════════


def clean():
    for d in ["build", "dist"]:
        p = Path(d)
        if p.exists():
            shutil.rmtree(p)
            print(f"  [OK] 清理: {d}")


def build(build_type: str):
    """执行 PyInstaller 打包"""
    info = BUILD_TYPES[build_type]
    spec = info["spec"]
    name = info["name"]

    print()
    print("  ╔════════════════════════════════════════╗")
    print(f"  ║  构建: {name:<31} ║")
    print(f"  ║  配置: {spec:<31} ║")
    print("  ╚════════════════════════════════════════╝")
    print()

    # 检查 spec 文件
    if not Path(spec).exists():
        print(f"  [错误] 找不到 {spec}")
        return False

    # 清理旧构建
    clean()

    # 执行 PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        spec,
        "--noconfirm",
        "--clean",
    ]
    print(f"  运行: pyinstaller {spec}")
    print()

    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(f"  [错误] PyInstaller 打包失败 (code={e.returncode})")
        print(f"  请尝试手动运行: pyinstaller {spec}")
        return False

    # 检查结果
    exe_path = Path("dist/SmartResearch.exe")
    if not exe_path.exists():
        print("  [错误] 打包失败，未生成 SmartResearch.exe")
        return False

    size_mb = exe_path.stat().st_size / (1024 * 1024)

    # 创建分发目录
    dist_name = f"{name}-v{VERSION}"
    dist_dir = Path("dist") / dist_name
    if dist_dir.exists():
        shutil.rmtree(str(dist_dir))
    dist_dir.mkdir(parents=True, exist_ok=True)

    # 复制 exe
    shutil.copy(str(exe_path), str(dist_dir / "SmartResearch.exe"))

    # 复制 .env（优先已有配置）
    if Path(".env").exists():
        shutil.copy(".env", str(dist_dir / ".env"))
    elif Path(".env.example").exists():
        shutil.copy(".env.example", str(dist_dir / ".env.example"))

    # 复制 README
    if Path("README.md").exists():
        shutil.copy("README.md", str(dist_dir / "README.md"))

    # 创建 ZIP 压缩包
    zip_path = Path("dist") / f"{dist_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in dist_dir.rglob("*"):
            zf.write(f, f.relative_to(dist_dir.parent))

    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)

    print()
    print("  ╔════════════════════════════════════════╗")
    print(f"  ║  ✅ 打包成功!                          ║")
    print(f"  ║                                      ║")
    print(f"  ║  可执行文件: SmartResearch.exe         ║")
    print(f"  ║  大小:       {size_mb:.1f} MB               ║")
    print(f"  ║  压缩包:     {zip_path.name}             ║")
    print(f"  ║  压缩后:     {zip_size_mb:.1f} MB               ║")
    print(f"  ║                                      ║")
    print(f"  ║  使用方法:                            ║")
    print(f"  ║  1. 解压 ZIP 文件                     ║")
    print(f"  ║  2. 编辑 .env 填入 API Key            ║")
    print(f"  ║  3. 双击 SmartResearch.exe            ║")
    print("  ╚════════════════════════════════════════╝")
    print()

    # 清理临时目录
    shutil.rmtree(str(dist_dir))

    return True


def list_build_types():
    """列出可用的构建类型"""
    print()
    print("  可用的构建类型:")
    for i, (key, info) in enumerate(BUILD_TYPES.items(), 1):
        print(f"    [{i}] {key:<12} {info['desc']}")
    print()


# ══════════════════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════════════════


def main():
    ci_mode = len(sys.argv) > 1 and sys.argv[1].lower() in ("desktop", "web")

    if not ci_mode:
        print()
        print("  ╔════════════════════════════════════════╗")
        print("  ║      SmartResearch 构建工具 v1.0      ║")
        print("  ║      将 Python 项目打包为 Windows exe ║")
        print("  ╚════════════════════════════════════════╝")
        print()

    # 检查环境
    cwd = Path.cwd()
    if not ci_mode:
        print(f"  工作目录: {cwd}")
        print()
        print("  [检查环境]")
        check_env()
        print()

    if not check_pyinstaller():
        if ci_mode:
            install_pyinstaller()
        else:
            print()
            print("  PyInstaller 是必需的打包工具。")
            resp = input("  是否现在安装 PyInstaller? (Y/n): ").strip().lower()
            if resp in ("", "y", "yes"):
                install_pyinstaller()
            else:
                print("  已取消。手动安装: pip install pyinstaller")
                return

    if not check_requirements():
        if ci_mode:
            print("  [CI] 自动安装依赖...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            )
            print("  [OK] 依赖安装完成")
        else:
            print()
            resp = input("  是否现在安装所有依赖? (y/N): ").strip().lower()
            if resp in ("y", "yes"):
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                )
                print("  [OK] 依赖安装完成")
            else:
                print("  [!!] 缺少依赖可能导致打包失败")

    # 确定构建类型
    build_type = None

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in BUILD_TYPES:
            build_type = arg
        elif arg in ("-h", "--help"):
            print("  用法: python build_exe.py [web|desktop]")
            list_build_types()
            return
        else:
            print(f"  [错误] 未知的构建类型: {arg}")
            list_build_types()
            return
    else:
        # 交互式选择
        print()
        print("  ╔════════════════════════════════════════╗")
        print("  ║  请选择构建类型:                       ║")
        print("  ║                                      ║")
        print("  ║  [1] 桌面版（推荐）                    ║")
        print("  ║      原生 GUI 应用，像 CCswitch 一样    ║")
        print("  ║      双击即用，无需浏览器               ║")
        print("  ║                                      ║")
        print("  ║  [2] Web 服务器版                      ║")
        print("  ║      需浏览器访问                      ║")
        print("  ║      http://localhost:8002             ║")
        print("  ╚════════════════════════════════════════╝")
        print()
        choice = input("  请输入 1 或 2 (默认 1): ").strip()
        build_type = "desktop" if choice in ("", "1") else "web"

    success = build(build_type)

    if success:
        print()
        print("  ╔════════════════════════════════════════╗")
        print("  ║  🎉 构建成功!                         ║")
        print("  ║                                      ║")
        print("  ║  输出目录: dist/                      ║")
        print("  ║  压缩包:   dist/*.zip                 ║")
        print("  ╚════════════════════════════════════════╝")
        print()
    else:
        print()
        print("  [错误] 构建失败，请检查上面的错误信息")
        print("  常见问题: https://github.com/hubnsh/SmartResearch/issues")
        print()


if __name__ == "__main__":
    main()
