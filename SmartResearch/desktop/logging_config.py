"""
桌面版日志配置 — 输出到控制台 + 文件（带自动轮转）
"""
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logging(log_dir: str = "data/logs", level: int = logging.INFO,
                  max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
    """配置桌面应用的日志系统（带轮转）

    Args:
        log_dir: 日志文件目录
        level: 日志级别
        max_bytes: 单个日志文件最大字节数（默认 10MB）
        backup_count: 保留的备份文件数
    """
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

    # 文件 handler（带轮转：10MB，保留 5 个备份）
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8",
    )
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

    logging.info(f"日志已初始化: {log_file} (轮转: {max_bytes//1024//1024}MB x {backup_count})")
    return log_file
