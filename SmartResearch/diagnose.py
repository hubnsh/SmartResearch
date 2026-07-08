"""
SmartResearch 诊断工具
运行: python diagnose.py
快速检查环境问题并给出修复建议
"""
import sys, os, importlib

# 确保路径正确
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GREEN = "\033[92m" if sys.platform != "win32" else ""
RED = "\033[91m" if sys.platform != "win32" else ""
YELLOW = "\033[93m" if sys.platform != "win32" else ""
RESET = "\033[0m" if sys.platform != "win32" else ""


def check(module_name: str, pip_name: str = "", critical: bool = True):
    """检查模块是否可导入"""
    try:
        importlib.import_module(module_name)
        print(f"  {GREEN}[OK]{RESET} {module_name}")
        return True
    except ImportError:
        pkg = pip_name or module_name
        print(f"  {RED}[!!]{RESET} {module_name} 未安装")
        print(f"       运行: pip install {pkg}")
        if critical:
            return False
        return True
    except Exception as e:
        print(f"  {YELLOW}[??]{RESET} {module_name}: {e}")
        return True


def main():
    print()
    print("  SmartResearch 环境诊断")
    print("  " + "=" * 40)
    print()

    # ===== 1. Python 版本 =====
    pyver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"  Python: {pyver}")
    if sys.version_info < (3, 10):
        print(f"  {RED}[!!]{RESET} 需要 Python 3.10+")
    else:
        print(f"  {GREEN}[OK]{RESET} 版本满足要求")
    print()

    # ===== 2. 核心依赖 =====
    print("  [核心依赖]")
    all_ok = True
    all_ok &= check("PySide6", "PySide6>=6.5.0")
    all_ok &= check("httpx", "httpx")
    all_ok &= check("bs4", "beautifulsoup4")
    all_ok &= check("sklearn.feature_extraction.text", "scikit-learn")
    all_ok &= check("markdown", "markdown")
    all_ok &= check("loguru", "loguru")
    all_ok &= check("PIL", "Pillow")
    print()

    # ===== 3. 可选依赖 =====
    print("  [可选依赖]")
    check("pytesseract", "pytesseract", critical=False)  # OCR
    check("faster_whisper", "faster-whisper", critical=False)  # 语音
    check("yt_dlp", "yt-dlp", critical=False)  # 视频
    check("youtube_transcript_api", "youtube-transcript-api", critical=False)
    check("langchain_anthropic", "langchain-anthropic", critical=False)  # Claude
    print()

    # ===== 4. 配置检查 =====
    print("  [配置文件]")
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        print(f"  {RED}[!!]{RESET} .env 文件不存在！")
        print("       请复制 .env.example 为 .env 并填入 API Key")
    else:
        try:
            from src.core.config import settings

            print(f"  {GREEN}[OK]{RESET} .env 文件存在")
            print(f"  LLM_PROVIDER = {settings.LLM_PROVIDER}")
            print(f"  API Key 已配置 = {bool(settings.llm_api_key)}")
            print(f"  模型 = {settings.llm_model}")
            print(f"  USE_LOCAL_EMBEDDING = {settings.USE_LOCAL_EMBEDDING}")

            if not settings.llm_api_key:
                print(f"  {YELLOW}[!!]{RESET} API Key 未配置，AI 功能不可用")
                print("       请通过「编辑 → 设置」配置或编辑 .env 文件")
        except Exception as e:
            print(f"  {RED}[!!]{RESET} 配置加载失败: {e}")
    print()

    # ===== 5. LLM 连通性测试 =====
    print("  [LLM 连通性测试]")
    try:
        from src.core.config import settings
        if settings.llm_api_key:
            import asyncio
            from src.services.llm_service import LLMService

            svc = LLMService()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                resp = loop.run_until_complete(
                    svc.chat("Reply in 3 words: hello", "test")
                )
                print(f"  {GREEN}[OK]{RESET} API 通信正常")
                print(f"  回复: {resp.strip()[:60]}")
            except Exception as e:
                err = str(e)
                if "401" in err or "unauthorized" in err:
                    print(f"  {RED}[!!]{RESET} API Key 无效或已过期")
                    print("       请检查 .env 中的 API Key 是否正确")
                elif "402" in err or "insufficient" in err or "quota" in err:
                    print(f"  {RED}[!!]{RESET} API 额度不足")
                    print("       请检查账户余额")
                elif "timeout" in err or "connect" in err:
                    print(f"  {RED}[!!]{RESET} 无法连接 API 服务")
                    print("       请检查网络连接和代理设置")
                else:
                    print(f"  {RED}[!!]{RESET} {err[:100]}")
            finally:
                loop.close()
        else:
            print(f"  {YELLOW}[??]{RESET} 跳过（未配置 API Key）")
    except Exception as e:
        print(f"  {RED}[!!]{RESET} 测试失败: {e}")
    print()

    # ===== 结果 =====
    print("  " + "=" * 40)
    if all_ok:
        print(f"  {GREEN}环境正常，应用可以启动{RESET}")
    else:
        print(f"  {RED}存在缺失依赖，请按上方提示安装{RESET}")
    print()

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
