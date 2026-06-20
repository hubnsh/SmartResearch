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

    # 校验文件大小
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    max_mb = settings.MAX_UPLOAD_SIZE_MB
    if size_mb > max_mb:
        raise HTTPException(413, f"文件过大 ({size_mb:.1f}MB)，最大允许 {max_mb}MB")

    # 保存文件
    ext = os.path.splitext(file.filename)[1] or ".tmp"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, saved_name)

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


# ==============================
#  HTML Form endpoints (no JS required)
# ==============================
from fastapi.responses import HTMLResponse
from fastapi import Form

@router.post("/chat-form", response_class=HTMLResponse)
async def chat_form(query: str = Form(...)):
    answer = await dispatcher.chat(query)
    return HTML_FORM % ("Q: " + query, answer)

@router.post("/link-form", response_class=HTMLResponse)
async def link_form(url: str = Form(...)):
    result = await dispatcher.handle_link(url)
    s = result.get("summary", "N/A") if result else "Failed"
    kw = ", ".join(result.get("keywords", [])) if result else ""
    return HTML_FORM % ("Link: " + url, "Summary: " + s + "\nKeywords: " + kw)

@router.get("/graph-html", response_class=HTMLResponse)
async def graph_html():
    data = dispatcher.get_graph()
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    nr = "".join("<tr><td>[%s]</td><td>%s</td></tr>" % (n["type"], n["label"]) for n in nodes)
    lr = "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (l["source"], l["type"], l["target"]) for l in links)
    return GRAPH_HTML % (len(nodes), len(links), nr, lr)


HTML_FORM = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8"><title>Result</title>
<style>body{font-family:sans-serif;background:#0f172a;color:#e2e8f0;max-width:800px;margin:20px auto;padding:20px}
h2{color:#38bdf8}pre{background:#1e293b;padding:16px;border-radius:8px;white-space:pre-wrap;line-height:1.6}
a{color:#38bdf8}</style></head><body>
<h2>%s</h2><pre>%s</pre>
<p><a href="/nojs">Back</a></p></body></html>"""

GRAPH_HTML = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8"><title>Graph</title>
<style>body{font-family:sans-serif;background:#0f172a;color:#e2e8f0;max-width:800px;margin:20px auto;padding:20px}
h2{color:#38bdf8}table{width:100%;border-collapse:collapse;margin:10px 0}
th,td{border:1px solid #475569;padding:8px}th{background:#1e293b}
a{color:#38bdf8}</style></head><body>
<h2>Knowledge Graph (%d nodes, %d links)</h2>
<h3>Nodes</h3><table><tr><th>Type</th><th>Label</th></tr>%s</table>
<h3>Links</h3><table><tr><th>Source</th><th>Relation</th><th>Target</th></tr>%s</table>
<p><a href="/nojs">Back</a></p></body></html>"""


# ==============================
#  Export Markdown
# ==============================
from fastapi.responses import Response

class MDRequest(BaseModel):
    content: str
    filename: str = "export.md"

@router.post("/export-md")
async def export_md(req: MDRequest):
    return Response(
        content=req.content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={req.filename}"}
    )
