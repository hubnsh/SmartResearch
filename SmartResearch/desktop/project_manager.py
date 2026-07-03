"""
Project Manager — 保存/加载 .smartresearch 项目文件
支持序列化全部素材项及其处理结果
"""
import json
import os
import logging
from datetime import datetime
from typing import List, Optional

from desktop.models import SourceItem, SourceType, ItemStatus

logger = logging.getLogger(__name__)

PROJECT_EXT = ".smartresearch"
PROJECT_VERSION = 2


class ProjectManager:
    """管理项目文件的保存与加载"""

    @staticmethod
    def items_to_dict(items: List[SourceItem]) -> list:
        return [it.to_dict() for it in items]

    @staticmethod
    def dicts_to_items(data: list) -> List[SourceItem]:
        items = []
        for d in data:
            st = SourceType(d.get("type", "image"))
            item = SourceItem(st, d.get("data", ""))
            item.id = d.get("id", item.id)
            item.label = d.get("label", item.label)
            # 状态还原
            status_str = d.get("status", "待处理")
            try:
                item.status = ItemStatus(status_str)
            except ValueError:
                item.status = ItemStatus.PENDING
            item.error_message = d.get("error_message", "")
            item.summary = d.get("summary", "")
            item.keywords = d.get("keywords", [])
            item.entities = d.get("entities", [])
            item.relations = d.get("relations", [])
            item.knowledge_tree = d.get("knowledge_tree", "")
            item.raw_content = d.get("raw_content", "")
            items.append(item)
        return items

    @staticmethod
    def save(path: str, items: List[SourceItem], note: str = "") -> bool:
        """保存项目到 .smartresearch 文件"""
        try:
            project = {
                "version": PROJECT_VERSION,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "item_count": len(items),
                "items": ProjectManager.items_to_dict(items),
                "note": note,
            }
            # 保证扩展名
            if not path.endswith(PROJECT_EXT):
                path += PROJECT_EXT
            with open(path, "w", encoding="utf-8") as f:
                json.dump(project, f, ensure_ascii=False, indent=2)
            logger.info(f"项目已保存: {path} ({len(items)} 个素材)")
            return True
        except Exception as e:
            logger.error(f"保存项目失败: {e}")
            return False

    @staticmethod
    def load(path: str) -> Optional[dict]:
        """从 .smartresearch 文件加载项目"""
        try:
            if not os.path.exists(path):
                logger.error(f"项目文件不存在: {path}")
                return None
            with open(path, "r", encoding="utf-8") as f:
                project = json.load(f)
            # 版本兼容检查
            version = project.get("version", 1)
            if version > PROJECT_VERSION:
                logger.warning(f"项目版本 {version} 高于当前支持 {PROJECT_VERSION}，可能不兼容")
            logger.info(f"项目已加载: {path} ({project.get('item_count', 0)} 个素材)")
            return project
        except Exception as e:
            logger.error(f"加载项目失败: {e}")
            return None

    @staticmethod
    def get_recent_projects(max_count: int = 5) -> List[dict]:
        """从项目目录扫描最近打开的 .smartresearch 文件"""
        recent = []
        # 检查当前目录和 data/projects 目录
        dirs_to_check = [".", "./data/projects"]
        for d in dirs_to_check:
            if not os.path.isdir(d):
                continue
            try:
                for fname in os.listdir(d):
                    if fname.endswith(PROJECT_EXT):
                        fpath = os.path.join(d, fname)
                        mtime = os.path.getmtime(fpath)
                        recent.append({
                            "path": os.path.abspath(fpath),
                            "name": fname[:-len(PROJECT_EXT)],
                            "mtime": datetime.fromtimestamp(mtime).isoformat(),
                        })
            except Exception:
                continue
        recent.sort(key=lambda x: x["mtime"], reverse=True)
        return recent[:max_count]
