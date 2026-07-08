"""
SmartResearch 启动脚本
"""
import os, sys, threading

# 缓存定向到项目目录
os.environ.setdefault("HF_HOME", os.path.join(os.path.dirname(__file__), "data", "huggingface"))
os.environ.setdefault("PYTHONPYCACHEPREFIX", os.path.join(os.path.dirname(__file__), "data", "pycache"))

import uvicorn
from src.main import app
from loguru import logger

# 加载自定义 Agent
try:
    from custom_agents import load_custom_agents
    load_custom_agents()
except Exception:
    pass

# 后台预热（不阻塞启动）
def warmup():
    try:
        from src.services.dispatcher import TaskDispatcher
        d = TaskDispatcher()
        _ = d.llm
        _ = d.rag
        logger.info("Services warmed up")
    except Exception as e:
        logger.warning(f"Warmup failed (non-fatal): {e}")

threading.Thread(target=warmup, daemon=True).start()
logger.info("Starting server (services warming up in background)...")
uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
