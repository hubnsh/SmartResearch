from neo4j import GraphDatabase
from src.core.config import settings
from typing import List, Dict, Any

class KGService:
    def __init__(self):
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
        except Exception as e:
            print(f"⚠️ Warning: Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def upsert_knowledge(self, extraction_result: Dict[str, Any]):
        """将提取的实体和关系存入 Neo4j"""
        with self.driver.session() as session:
            # 1. 插入/更新实体
            for entity in extraction_result.get("entities", []):
                session.execute_write(self._upsert_entity, entity)
            
            # 2. 插入/更新关系
            for relation in extraction_result.get("relations", []):
                session.execute_write(self._upsert_relation, relation)

    @staticmethod
    def _upsert_entity(tx, entity: Dict[str, Any]):
        # 使用 MERGE 确保实体唯一，并更新属性
        query = (
            f"MERGE (e:{entity['type']} {{name: $name}}) "
            "SET e.description = $description, e.updated_at = timestamp() "
            "RETURN e"
        )
        tx.run(query, name=entity['name'], description=entity['description'])

    @staticmethod
    def _upsert_relation(tx, relation: Dict[str, Any]):
        # 建立两个实体之间的关系
        # 注意：这里假设实体已经存在，或者在同一个事务中处理
        query = (
            "MATCH (a {name: $source}), (b {name: $target}) "
            f"MERGE (a)-[r:{relation['type']}]->(b) "
            "SET r.updated_at = timestamp() "
            "RETURN r"
        )
        tx.run(query, source=relation['source'], target=relation['target'])

    def query_graph(self, cypher_query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """执行自定义 Cypher 查询"""
        with self.driver.session() as session:
            result = session.run(cypher_query, parameters or {})
            return [record.data() for record in result]
