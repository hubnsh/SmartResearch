"""
API 路由：文件上传、链接提交、对话、图谱查询。
"""
import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from src.core.config import settings
from src.services.dispatcher import TaskDispatcher

router = APIRouter()
dispatcher = TaskDispatcher()

# ---- 请求模型 ----
class LinkRequest(BaseModel):
    url: str

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str           # Markdown 格式的回答


# ==============================
#  文件上传
# ==============================
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文档 / 图片，自动解析并入库"""
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")

    # 保存文件
    ext = os.path.splitext(file.filename)[1] or ".tmp"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, saved_name)

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # 调度
    result = await dispatcher.handle_file(save_path)
    if result is None:
        return {"status": "ok", "message": f"文件已保存，但当前版本暂不支持 {ext} 的内容提取", "file": saved_name}

    return {
        "status": "ok",
        "file": saved_name,
        "summary": result.get("summary", ""),
        "keywords": result.get("keywords", []),
        "entities": result.get("entities", []),
        "relations": result.get("relations", []),
    }


# ==============================
#  链接提交
# ==============================
@router.post("/link")
async def submit_link(req: LinkRequest):
    """提交网页 / Arxiv / GitHub 链接，自动抓取解析"""
    if not req.url:
        raise HTTPException(400, "URL 不能为空")

    result = await dispatcher.handle_link(req.url)
    if result is None:
        raise HTTPException(500, "链接解析失败，请检查 URL 是否可访问")

    return {
        "status": "ok",
        "url": req.url,
        "summary": result.get("summary", ""),
        "keywords": result.get("keywords", []),
        "entities": result.get("entities", []),
        "relations": result.get("relations", []),
        "knowledge_tree": result.get("knowledge_tree", ""),
    }


# ==============================
#  对话
# ==============================
@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """与 Second Brain Agent 对话"""
    if not req.query:
        raise HTTPException(400, "问题不能为空")

    answer = await dispatcher.chat(req.query)
    return ChatResponse(answer=answer)


# ==============================
#  图谱可视化数据
# ==============================
@router.get("/graph")
async def get_graph_data():
    """获取知识图谱数据（用于前端可视化）"""
    return dispatcher.get_graph()
