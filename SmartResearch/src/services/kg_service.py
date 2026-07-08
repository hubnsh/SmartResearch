from neo4j import GraphDatabase
from src.core.config import settings
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class KGService:
    """知识图谱服务：封装 Neo4j 连接与 CRUD 操作"""

    def __init__(self):
        self.driver: Optional[GraphDatabase.driver] = None
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
            self.driver.verify_connectivity()
            logger.info("✅ Neo4j 驱动初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ Neo4j 不可用，图谱功能已禁用: {e}")
            if self.driver:
                try:
                    self.driver.close()
                except Exception:
                    pass
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    # ------ 写入实体与关系 ------
    def upsert_knowledge(self, extraction_result: Dict[str, Any], source_info: Dict[str, str] = None):
        """将提取结果写入图谱"""
        if not self.driver:
            return
        try:
            with self.driver.session() as session:
                for entity in extraction_result.get("entities", []):
                    session.execute_write(self._upsert_entity, entity, source_info)
                for relation in extraction_result.get("relations", []):
                    session.execute_write(self._upsert_relation, relation)
        except Exception as e:
            logger.warning(f"Neo4j 写入失败 (非致命): {e}")

    @staticmethod
    def _upsert_entity(tx, entity: Dict[str, Any], source_info: Dict[str, str] = None):
        label = entity["type"].replace(" ", "_")
        query = (
            f"MERGE (e:{label} {{name: $name}}) "
            "SET e.description = $description, "
            "    e.updated_at = timestamp() "
        )
        params = {"name": entity["name"], "description": entity.get("description", "")}
        if source_info:
            query += ", e.source_type = $source_type, e.source_path = $source_path"
            params["source_type"] = source_info.get("type", "")
            params["source_path"] = source_info.get("path", "")
        query += " RETURN e"
        tx.run(query, **params)

    @staticmethod
    def _upsert_relation(tx, relation: Dict[str, Any]):
        rel_type = relation["type"].replace(" ", "_").upper()
        # 使用 label 约束避免全表扫描；如节点不存在则先创建
        query = (
            "MERGE (a:Entity {name: $source}) "
            "MERGE (b:Entity {name: $target}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            "SET r.updated_at = timestamp() "
            "RETURN r"
        )
        tx.run(query, source=relation["source"], target=relation["target"])

    # ------ 查询 ------
    def query(self, cypher: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if not self.driver:
            return []
        try:
            with self.driver.session() as session:
                result = session.run(cypher, params or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.warning(f"Neo4j query failed: {e}")
            return []

    def search_related(self, entity_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self.query(
            "MATCH (e {name: $name})-[r]-(other) "
            "RETURN e.name AS source, type(r) AS relation, other.name AS target, "
            "       other.description AS description "
            "LIMIT $limit",
            {"name": entity_name, "limit": limit},
        )

    def get_full_graph(self, limit: int = 100) -> Dict[str, Any]:
        """返回用于前端可视化的图谱数据"""
        items = self.query(
            "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT $limit",
            {"limit": limit},
        )
        nodes = {}
        links = []
        for item in items:
            n, m, r = item["n"], item["m"], item["r"]
            nodes[n.element_id] = {
                "id": n.element_id,
                "label": n.get("name", "unknown"),
                "type": list(n.labels)[0] if n.labels else "Unknown",
            }
            nodes[m.element_id] = {
                "id": m.element_id,
                "label": m.get("name", "unknown"),
                "type": list(m.labels)[0] if m.labels else "Unknown",
            }
            links.append({
                "source": n.element_id,
                "target": m.element_id,
                "type": r.type,
            })
        return {"nodes": list(nodes.values()), "links": links}
