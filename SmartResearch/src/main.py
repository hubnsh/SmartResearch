"""
SmartResearch —— 多模态智能学习与科研助手平台
FastAPI 主入口
"""
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from src.core.config import settings
from src.core.logging_config import setup_logging
from src.api.routes import router
from loguru import logger

# ---------- 初始化日志 ----------
setup_logging()


# ---------- 生命周期管理（优雅关机） ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时创建必要目录，关机时释放 Neo4j 连接"""
    logger.info(f"SmartResearch v0.1.0 starting (env={settings.APP_ENV})")
    for d in [settings.UPLOAD_DIR, settings.CHROMA_DB_PATH, "data/logs"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    yield
    logger.info("Shutdown received, releasing resources...")
    try:
        from src.services.kg_service import KGService
        kg = KGService()
        if kg.driver:
            kg.close()
            logger.info("Neo4j driver closed")
    except Exception as e:
        logger.warning(f"Neo4j shutdown error: {e}")
    logger.info("SmartResearch shut down gracefully")


# ---------- FastAPI 应用 ----------
app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    description="多模态 Second Brain Agent —— 支持文档、图片、网页、论文链接的智能知识管理",
    version="0.1.0",
)

app.include_router(router, prefix="/api")

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 简易速率限制（内存，每 IP 每分钟 30 次） ----------
# 定期清理过期条目，避免内存无限增长
_rate_limits: dict = {}
_RATE_LIMIT_WINDOW = 60  # 窗口期（秒）
_RATE_LIMIT_MAX = 30     # 窗口期内最大请求数

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    from time import time
    client = request.client.host if request.client else "unknown"
    now = time()
    window = now - _RATE_LIMIT_WINDOW
    _rate_limits.setdefault(client, [])
    _rate_limits[client] = [t for t in _rate_limits[client] if t > window]
    if len(_rate_limits[client]) >= _RATE_LIMIT_MAX:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Too many requests"}, status_code=429)
    _rate_limits[client].append(now)
    # 每 100 次请求清理一次过期条目，防止内存泄漏
    if len(_rate_limits) > 1000:
        cutoff = now - 300  # 清理 5 分钟前的 IP
        _rate_limits.clear()
    return await call_next(request)

# 挂载静态文件（目录不存在则自动创建）
_static_dir = Path("static")
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------- 健康检查 ----------
@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


# ---------- 首页 ----------
@app.api_route("/", methods=["GET", "POST"], response_class=HTMLResponse)
async def index(request: Request):
    from fastapi import Form
    result_html = ""
    if request.method == "POST":
        from src.api.routes import dispatcher
        form = await request.form()
        if "query" in form and form["query"]:
            answer = await dispatcher.chat(form["query"])
            result_html = '<div class="card"><h2>Q: ' + form["query"] + '</h2><div class="result">' + answer + '</div></div>' + chr(10) + '<form method="post" action="/export-md-form" style="margin-top:10px"><input type="hidden" name="content" value="' + answer.replace(chr(34), '&quot;') + '"><input type="hidden" name="filename" value="chat_' + form["query"][:30].replace(" ", "_") + '.md"><button type="submit" style="background:var(--green);width:auto;padding:8px 16px">&#x1F4E5; 下载为 .md</button></form>'
        elif "url" in form and form["url"]:
            r = await dispatcher.handle_link(form["url"])
            s = r.get("summary", "N/A") if r else "Failed"
            result_html = '<div class="card"><h2>Link: ' + form["url"] + '</h2><div class="result">' + s + '</div></div>'

        elif "file" in form:
            f = form["file"]
            if hasattr(f, "filename") and f.filename:
                import os, uuid
                content = await f.read()
                ext = os.path.splitext(f.filename)[1] or ".tmp"
                os.makedirs("data/uploads", exist_ok=True)
                save_path = os.path.join("data", "uploads", uuid.uuid4().hex + ext)
                with open(save_path, "wb") as fp:
                    fp.write(content)
                r = await dispatcher.handle_file(save_path)
                s = r.get("summary", "N/A") if r else "Unsupported type"
                result_html = '<div class="card"><h2>File: ' + f.filename + '</h2><div class="result">' + s + '</div></div>' + chr(10) + '<form method="post" action="/export-md-form" style="margin-top:10px"><input type="hidden" name="content" value="' + s.replace(chr(34), '&quot;') + '"><input type="hidden" name="filename" value="link_' + form["url"][:30].replace("/", "_").replace(":", "") + '.md"><button type="submit" style="background:var(--green);width:auto;padding:8px 16px">&#x1F4E5; 下载为 .md</button></form>'
            else:
                result_html = '<div class="card"><h2>Error</h2><div class="result">No file selected</div></div>'
    return NOJS_PAGE.replace("RESPONSE_PLACEHOLDER", result_html)



# ---------- 导出 Markdown（no-JS） ----------
@app.post("/export-md-form", response_class=HTMLResponse)
async def export_md_form(request: Request):
    from fastapi import Form
    from urllib.parse import quote
    form = await request.form()
    content = form.get("content", "")
    filename = form.get("filename", "research.md")
    encoded = quote(content)
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8"><title>Download</title>
<style>body{{font-family:sans-serif;background:#0a0e17;color:#e2e8f0;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;flex-direction:column;gap:20px}}
a{{color:#3b82f6;font-size:18px}}a:hover{{color:#60a5fa}}p{{color:#94a3b8}}</style></head><body>
<p>&#x1F4E5; 下载已开始，若未自动下载请点击下方链接</p>
<a href="data:text/markdown;charset=utf-8,{encoded}" download="{filename}">&#x1F4C4; 下载 {filename}</a>
<p style="margin-top:12px"><a href="/">&#x2190; 返回首页</a></p>
</body></html>""")


@app.get("/graph", response_class=HTMLResponse)
async def graph_page():
    from src.api.routes import dispatcher
    data = dispatcher.get_graph()
    ns = data.get("nodes", [])
    ls = data.get("links", [])
    nr = "".join("<tr><td>[" + n["type"] + "]</td><td>" + n["label"] + "</td></tr>" for n in ns)
    lr = "".join("<tr><td>" + l["source"] + "</td><td>" + l["type"] + "</td><td>" + l["target"] + "</td></tr>" for l in ls)
    return """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Graph</title>
<style>body{font-family:sans-serif;background:#0a0e17;color:#e2e8f0;max-width:800px;margin:20px auto;padding:20px}
h2{color:#3b82f6}table{width:100%;border-collapse:collapse}th,td{border:1px solid #1e2d3d;padding:8px}th{background:#111827}
a{color:#3b82f6}</style></head><body>
<h2>Graph (""" + str(len(ns)) + " nodes, " + str(len(ls)) + """ links)</h2>
<h3>Nodes</h3><table><tr><th>Type</th><th>Label</th></tr>""" + nr + """</table>
<h3>Links</h3><table><tr><th>Source</th><th>Relation</th><th>Target</th></tr>""" + lr + """</table>
<p><a href="/">Back</a></p></body></html>"""


@app.get("/js", response_class=HTMLResponse)
async def index_js():
    return _HTML_PAGE







# ---- 从文件加载前端页面（替代内联 HTML）----
_JS_PAGE_PATH = Path("static/js_page.html")
_NOJS_PAGE_PATH = Path("static/nojs_page.html")

if _JS_PAGE_PATH.exists():
    _HTML_PAGE = _JS_PAGE_PATH.read_text(encoding="utf-8")
else:
    _HTML_PAGE = "<h1>JS page not found</h1>"

if _NOJS_PAGE_PATH.exists():
    NOJS_PAGE = _NOJS_PAGE_PATH.read_text(encoding="utf-8")
else:
    NOJS_PAGE = "<h1>Page not found</h1>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)


