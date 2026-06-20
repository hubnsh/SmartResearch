"""
结构化日志配置（基于 loguru）
- 控制台：彩色、可读格式
- 文件：JSON 结构化，按 50MB 自动轮转，保留 7 天
"""
import sys
from loguru import logger
from src.core.config import settings


def setup_logging():
    """初始化日志系统，移除默认 handler 并添加定制化配置"""
    logger.remove()  # 清除 loguru 默认 handler

    # ---- 控制台输出（开发友好） ----
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
    )

    # ---- 文件输出（JSON 结构化，生产可检索） ----
    logger.add(
        "data/logs/app_{time:YYYY-MM-DD}.json",
        format=(
            '{{"time": "{time:YYYY-MM-DDTHH:mm:ss.SSSZ}", '
            '"level": "{level}", '
            '"name": "{name}", '
            '"function": "{function}", '
            '"line": {line}, '
            '"message": "{message}", '
            '"extra": {extra}}}'
        ),
        rotation="50 MB",        # 单文件 50MB 自动轮转
        retention="7 days",      # 保留最近 7 天
        compression="gz",        # 轮转后压缩为 .gz
        level="INFO",
        serialize=False,         # False = 用上面手动构造的 JSON 格式
    )

    logger.info("日志系统初始化完成 (loguru)")

    # 拦截标准 logging 库输出，统一路由到 loguru
    import logging

    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            frame = logging.currentframe()
            depth = 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
