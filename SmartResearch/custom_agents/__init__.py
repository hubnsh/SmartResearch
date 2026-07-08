"""
自定义 Agent 加载器
====================
自动发现并注册 custom_agents/ 目录下的所有自定义 Agent。

使用方式：
  1. 在 custom_agents/ 目录下创建 Python 文件
  2. 文件中定义继承 BaseAgent 的类
  3. 在类定义末尾调用 agent_registry.register(YourAgent)
  4. 重启应用，Agent 自动生效

参考 example_agent.py 了解完整写法。
"""
import importlib
import logging
import os
import pkgutil
from pathlib import Path

logger = logging.getLogger(__name__)

# 标记 custom_agents 是否已加载
_loaded = False


def load_custom_agents():
    """扫描并加载 custom_agents/ 目录下所有自定义 Agent"""
    global _loaded
    if _loaded:
        return
    _loaded = True

    from src.agents.base import agent_registry

    agents_dir = Path(__file__).parent
    count = 0

    # 遍历所有 .py 文件（除了 __init__.py）
    for f in sorted(agents_dir.glob("*.py")):
        if f.name == "__init__.py":
            continue

        module_name = f"custom_agents.{f.stem}"
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, str(f))
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 模块内的 agent 注册在其自身的 agent_registry.register() 调用中完成
            count += 1
            logger.info(f"[CustomAgent] 已加载: {f.name}")
        except Exception as e:
            logger.warning(f"[CustomAgent] 加载失败 {f.name}: {e}")

    registered = [a["type"] for a in agent_registry.list_agents()]
    logger.info(
        f"[CustomAgent] 加载完成: {count} 个文件, "
        f"当前共 {len(registered)} 个 Agent: {registered}"
    )
    return count
