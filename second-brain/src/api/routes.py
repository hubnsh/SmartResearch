from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.services.agent_service import SecondBrainAgent
from src.services.kg_service import KGService
from typing import List, Dict, Any

router = APIRouter()
agent = SecondBrainAgent()
kg_service = KGService()

class QueryRequest(BaseModel):
    text: str

class QueryResponse(BaseModel):
    answer: str

@router.post("/chat", response_model=QueryResponse)
async def chat(request: QueryRequest):
    """与 Second Brain Agent 对话"""
    try:
        answer = await agent.run(request.text)
        return QueryResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph/data")
async def get_graph_data():
    """获取知识图谱可视化数据"""
    if not kg_service.driver:
        raise HTTPException(status_code=503, detail="Neo4j service is unavailable.")
    
    query = "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100"
    try:
        data = kg_service.query_graph(query)
        # 转换格式以适应 D3.js 或 Cytoscape
        nodes = {}
        links = []
        for record in data:
            n = record['n']
            m = record['m']
            r = record['r']
            
            nodes[n.element_id] = {"id": n.element_id, "label": n['name'], "type": list(n.labels)[0]}
            nodes[m.element_id] = {"id": m.element_id, "label": m['name'], "type": list(m.labels)[0]}
            links.append({
                "source": n.element_id,
                "target": m.element_id,
                "type": r.type
            })
            
        return {"nodes": list(nodes.values()), "links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
