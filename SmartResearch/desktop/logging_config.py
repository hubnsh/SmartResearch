"""
桌面版日志配置 — 输出到控制台 + 文件
"""
import logging
import os
import sys
from datetime import datetime


def setup_logging(log_dir: str = "data/logs", level: int = logging.INFO):
    """配置桌面应用的日志系统"""
    os.makedirs(log_dir, exist_ok=True)

    # 日志文件名按日期
    log_file = os.path.join(log_dir, f"desktop_{datetime.now().strftime('%Y%m%d')}.log")

    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有 handler（避免重复）
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    # 格式化
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # 文件 handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 控制台 handler（重要信息）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 特定模块的详细日志
    logging.getLogger("desktop").setLevel(logging.DEBUG)
    logging.getLogger("src").setLevel(logging.WARNING)

    logging.info(f"日志已初始化: {log_file}")
    return log_file
