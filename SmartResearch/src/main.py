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






# ---- 内联前端页面 ----
_HTML_PAGE = """
﻿<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SmartResearch - 智能科研助手</title>
<script src="/static/marked.js"></script>
<style>
:root {
  --bg: #0a0e17;
  --surface: #111827;
  --surface2: #1a2332;
  --border: #1e2d3d;
  --text: #e2e8f0;
  --text2: #94a3b8;
  --accent: #3b82f6;
  --accent2: #2563eb;
  --green: #10b981;
  --purple: #8b5cf6;
  --orange: #f59e0b;
  --radius: 12px;
  --shadow: 0 4px 24px rgba(0,0,0,0.4);
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex}
/* Sidebar */
.sidebar{width:280px;background:var(--surface);border-right:1px solid var(--border);padding:24px 20px;display:flex;flex-direction:column;gap:8px;flex-shrink:0}
.sidebar .logo{display:flex;align-items:center;gap:12px;margin-bottom:24px}
.sidebar .logo .icon{width:40px;height:40px;background:linear-gradient(135deg,var(--accent),var(--purple));border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px}
.sidebar .logo h2{font-size:16px;font-weight:700;color:var(--text);letter-spacing:-0.3px}
.sidebar .logo span{font-size:11px;color:var(--text2);display:block}
.sidebar .nav-btn{display:flex;align-items:center;gap:10px;padding:12px 16px;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;color:var(--text2);background:transparent;transition:all 0.2s;width:100%;text-align:left}
.sidebar .nav-btn:hover{background:var(--surface2);color:var(--text)}
.sidebar .nav-btn.active{background:var(--accent);color:#fff}
.sidebar .nav-btn .emoji{font-size:16px;width:24px;text-align:center}
.sidebar .divider{height:1px;background:var(--border);margin:8px 0}
.sidebar .status{font-size:11px;color:var(--text2);padding:8px 16px;display:flex;align-items:center;gap:6px}
.sidebar .status .dot{width:6px;height:6px;background:var(--green);border-radius:50%}
/* Main */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.header{padding:20px 32px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px}
.header h3{font-size:18px;font-weight:600;flex:1}
.header .badge{font-size:11px;padding:3px 10px;border-radius:12px;background:var(--surface2);color:var(--accent);font-weight:500}
/* Chat */
.chat-area{flex:1;overflow-y:auto;padding:24px 32px;display:flex;flex-direction:column;gap:16px}
.chat-area::-webkit-scrollbar{width:6px}
.chat-area::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.welcome{text-align:center;padding:60px 20px}
.welcome .w-icon{font-size:48px;margin-bottom:16px}
.welcome h2{font-size:24px;margin-bottom:8px}
.welcome p{color:var(--text2);max-width:400px;margin:0 auto;line-height:1.6}
.msg{max-width:75%;padding:14px 18px;border-radius:var(--radius);line-height:1.65;font-size:14px;animation:fadeIn 0.3s ease}
.msg.user{align-self:flex-end;background:var(--accent);color:#fff;border-bottom-right-radius:4px}
.msg.agent{align-self:flex-start;background:var(--surface);border:1px solid var(--border);border-bottom-left-radius:4px}
.msg.system{align-self:center;background:var(--surface2);font-size:13px;color:var(--text2);max-width:90%;text-align:center}
.msg.agent h1,.msg.agent h2,.msg.agent h3{color:var(--accent);margin:8px 0 4px;font-size:16px}
.msg.agent h1{font-size:18px}
.msg.agent ul,.msg.agent ol{margin:4px 0;padding-left:20px}
.msg.agent code{background:var(--surface2);padding:2px 6px;border-radius:4px;font-size:13px;color:var(--orange)}
.msg.agent pre{background:var(--bg);padding:14px;border-radius:8px;overflow-x:auto;margin:8px 0;border:1px solid var(--border)}
.msg.agent pre code{background:none;padding:0;color:var(--green)}
.msg.agent table{border-collapse:collapse;margin:8px 0;width:100%;font-size:13px}
.msg.agent th,.msg.agent td{border:1px solid var(--border);padding:8px 12px;text-align:left}
.msg.agent th{background:var(--surface2);font-weight:600}
.msg.agent strong{color:var(--orange)}
.msg.agent a{color:var(--accent)}
.msg.agent blockquote{border-left:3px solid var(--accent);padding-left:12px;color:var(--text2);margin:8px 0}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
/* Input */
.input-area{padding:20px 32px;border-top:1px solid var(--border);display:flex;gap:12px;background:var(--surface)}
.input-area input{flex:1;padding:14px 18px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;outline:none;transition:border 0.2s}
.input-area input:focus{border-color:var(--accent)}
.input-area button{padding:14px 28px;border-radius:10px;border:none;background:var(--accent);color:#fff;font-size:14px;font-weight:600;cursor:pointer;transition:all 0.2s;white-space:nowrap}
.input-area button:hover{background:var(--accent2);transform:translateY(-1px);box-shadow:0 4px 12px rgba(59,130,246,0.3)}
/* Upload & Link */
.upload-section,.link-section{flex:1;overflow-y:auto;padding:32px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px}
.upload-card,.link-card{background:var(--surface);border:2px dashed var(--border);border-radius:var(--radius);padding:40px;text-align:center;max-width:480px;width:100%;transition:border 0.2s}
.upload-card:hover,.link-card:hover{border-color:var(--accent)}
.upload-card .icon,.link-card .icon{font-size:40px;margin-bottom:12px}
.upload-card h3,.link-card h3{margin-bottom:8px;font-size:16px}
.upload-card p,.link-card p{color:var(--text2);font-size:13px;margin-bottom:20px}
.upload-card input[type=file],.link-card input[type=text]{width:100%;padding:10px 14px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;margin:8px 0}
.upload-card button,.link-card button{padding:12px 32px;border-radius:8px;border:none;background:var(--accent);color:#fff;font-size:14px;font-weight:600;cursor:pointer;transition:all 0.2s;margin-top:8px}
.upload-card button:hover,.link-card button:hover{background:var(--accent2)}
/* Graph */
.graph-section{flex:1;overflow-y:auto;padding:32px;display:none}
.graph-section.active{display:block}
.graph-card{background:var(--surface);border-radius:var(--radius);padding:24px;border:1px solid var(--border)}
.graph-card table{width:100%;border-collapse:collapse;font-size:13px}
.graph-card th,.graph-card td{border:1px solid var(--border);padding:8px 12px;text-align:left}
.graph-card th{background:var(--surface2);font-weight:600;color:var(--accent)}
.graph-card .stat{display:flex;gap:24px;margin-bottom:20px}
.graph-card .stat-item{text-align:center}
.graph-card .stat-item .num{font-size:28px;font-weight:700;color:var(--accent)}
.graph-card .stat-item .label{font-size:12px;color:var(--text2)}
.hidden{display:none!important}
/* Loading */
.spinner{width:20px;height:20px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin 0.6s linear infinite;display:inline-block;vertical-align:middle;margin-right:8px}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<!-- Sidebar -->
<div class="sidebar">
  <div class="logo">
    <div class="icon">&#x1F9E0;</div>
    <div><h2>SmartResearch</h2><span>Second Brain Agent</span></div>
  </div>
  <button class="nav-btn active" onclick="showChat()">
    <span class="emoji">&#x1F4AC;</span> 对话
  </button>
  <button class="nav-btn" onclick="showUpload()">
    <span class="emoji">&#x1F4C4;</span> 上传文件
  </button>
  <button class="nav-btn" onclick="showLink()">
    <span class="emoji">&#x1F517;</span> 提交链接
  </button>
  <button class="nav-btn" onclick="loadGraph()">
    <span class="emoji">&#x1F578;</span> 知识图谱
  </button>
  <div class="divider"></div>
  <div class="status"><span class="dot"></span> DeepSeek + TF-IDF</div>
</div>

<!-- Main -->
<div class="main">
  <div class="header">
    <h3 id="header-title">&#x1F4AC; 对话</h3>
    <span class="badge">v0.1</span>
  </div>

  <!-- Chat -->
  <div id="chat-section" class="chat-area">
    <div class="welcome">
      <div class="w-icon">&#x1F9E0;</div>
      <h2>SmartResearch</h2>
      <p>上传文档、图片或提交链接，AI 自动构建你的第二大脑。现在开始提问吧。</p>
    </div>
  </div>
  <div id="chat-input-area" class="input-area">
    <input id="chat-input" type="text" placeholder="输入你的问题，按 Enter 发送..." onkeydown="if(event.key==='Enter')sendChat()">
    <button onclick="sendChat()">&#x27A4; 发送</button>
  </div>

  <!-- Upload -->
  <div id="upload-section" class="upload-section hidden">
    <div class="upload-card">
      <div class="icon">&#x1F4C4;</div>
      <h3>上传文档或图片</h3>
      <p>支持 PDF / Word / PPT / TXT / Markdown / JPG / PNG</p>
      <input type="file" id="file-input">
      <button onclick="uploadFile()">&#x2601; 上传并解析</button>
    </div>
  </div>
  <div id="upload-input-area" class="input-area hidden"></div>

  <!-- Link -->
  <div id="link-section" class="upload-section hidden">
    <div class="link-card">
      <div class="icon">&#x1F517;</div>
      <h3>提交网页或视频链接</h3>
      <p>支持通用网页 / Arxiv / GitHub / B站 / YouTube</p>
      <input type="text" id="link-input" placeholder="https://...">
      <button onclick="submitLink()">&#x1F50D; 解析链接</button>
    </div>
  </div>
  <div id="link-input-area" class="input-area hidden"></div>

  <!-- Graph -->
  <div id="graph-section" class="graph-section">
    <div class="graph-card" id="graph-container">
      <span class="spinner"></span> 加载中...
    </div>
  </div>
</div>

<script>
let currentSection = 'chat';

// 带超时的 fetch（默认 30s 超时，避免请求卡死）
async function fetchWithTimeout(url, options = {}, timeout = 30000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(id);
        return response;
    } catch (e) {
        clearTimeout(id);
        if (e.name === 'AbortError') {
            throw new Error('请求超时，请检查网络连接或稍后重试');
        }
        throw e;
    }
}

function showSection(id) {
    document.querySelectorAll('.chat-area,.upload-section,.graph-section,.input-area').forEach(e => e.classList.add('hidden'));
    document.getElementById(id+'-section').classList.remove('hidden');
    if (id==='chat') document.getElementById('chat-input-area').classList.remove('hidden');
    currentSection = id;
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.nav-btn[onclick*="'+id+'"]')?.classList.add('active');
}

function showChat() { showSection('chat'); document.getElementById('header-title').innerHTML = '&#x1F4AC; 对话'; }
function showUpload() { showSection('upload'); document.getElementById('header-title').innerHTML = '&#x1F4C4; 上传文件'; }
function showLink() { showSection('link'); document.getElementById('header-title').innerHTML = '&#x1F517; 提交链接'; }

function addMsg(role, text) {
    const area = document.getElementById('chat-section');
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    if (role === 'agent') {
        div.innerHTML = marked.parse(text);
        var btn = document.createElement('button');
        btn.textContent = ' Download MD';
        btn.style.cssText = 'margin-top:8px;padding:4px 12px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text2);cursor:pointer';
        btn.onclick = function(){ downloadMd(text, 'research_' + Date.now() + '.md'); };
        div.appendChild(btn);
    } else div.textContent = text;
    area.appendChild(div);
    area.scrollTop = area.scrollHeight;
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const q = input.value.trim();
    if (!q) return;
    showChat();
    addMsg('user', q);
    input.value = '';
    addMsg('system', ' 思考中...');
    try {
        const res = await fetchWithTimeout('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query: q})
        }, 60000);
        const data = await res.json();
        document.querySelector('#chat-section .msg.system:last-child')?.remove();
        addMsg('agent', data.answer || '暂无回复');
    } catch(e) {
        document.querySelector('#chat-section .msg.system:last-child')?.remove();
        addMsg('system', ' 请求失败: ' + e.message);
    }
}

async function uploadFile() {
    const file = document.getElementById('file-input').files[0];
    if (!file) return alert('请选择文件');
    showChat();
    addMsg('system', ' 正在解析: ' + file.name);
    const form = new FormData(); form.append('file', file);
    try {
        const res = await fetchWithTimeout('/api/upload', {method:'POST',body:form}, 60000);
        const data = await res.json();
        document.querySelector('#chat-section .msg.system:last-child')?.remove();
        if (data.summary) addMsg('agent', '**'+file.name+'**\n\n'+data.summary);
        else addMsg('system', data.message || '解析完成');
    } catch(e) {
        addMsg('system', '上传失败: ' + e.message);
    }
}

async function submitLink() {
    const url = document.getElementById('link-input').value.trim();
    if (!url) return alert('请输入链接');
    showChat();
    addMsg('user', '提交链接: ' + url);
    document.getElementById('link-input').value = '';
    addMsg('system', ' 正在解析...');
    try {
        const res = await fetchWithTimeout('/api/link', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({url})
        }, 60000);
        const data = await res.json();
        document.querySelector('#chat-section .msg.system:last-child')?.remove();
        let r = '**'+url+'**\n\n'+data.summary;
        if (data.knowledge_tree) r += '\n\n### 知识树\n'+data.knowledge_tree;
        addMsg('agent', r);
    } catch(e) {
        addMsg('system', '解析失败: ' + e.message);
    }
}

async function downloadMd(text, filename) {
    const res = await fetchWithTimeout('/api/export-md', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content: text, filename: filename || 'export.md'})
    }, 15000);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename || 'export.md';
    a.click(); URL.revokeObjectURL(url);
}

async function loadGraph() {
    showSection('graph');
    document.getElementById('header-title').innerHTML = '&#x1F578; 知识图谱';
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.nav-btn[onclick*="loadGraph"]')?.classList.add('active');
    const c = document.getElementById('graph-container');
    c.innerHTML = '<span class="spinner"></span> 加载中...';
    try {
        const res = await fetchWithTimeout('/api/graph', {}, 15000);
        const data = await res.json();
        const ns = data.nodes || [], ls = data.links || [];
        let h = '<div class="stat"><div class="stat-item"><div class="num">'+ns.length+'</div><div class="label">Nodes</div></div><div class="stat-item"><div class="num">'+ls.length+'</div><div class="label">Links</div></div></div>';
        h += '<h3 style="margin:16px 0 8px;color:var(--accent)">Nodes</h3><table><tr><th>Type</th><th>Label</th></tr>';
        ns.forEach(n => h += '<tr><td>'+n.type+'</td><td>'+n.label+'</td></tr>');
        h += '</table>';
        h += '<h3 style="margin:16px 0 8px;color:var(--accent)">Links</h3><table><tr><th>Source</th><th>Relation</th><th>Target</th></tr>';
        ls.forEach(l => h += '<tr><td>'+l.source+'</td><td>'+l.type+'</td><td>'+l.target+'</td></tr>');
        h += '</table>';
        c.innerHTML = h;
    } catch(e) {
        c.innerHTML = ' 加载失败: ' + e.message;
    }
}
</script>
</body>
</html>

"""

NOJS_PAGE = """
﻿<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SmartResearch</title>
<style>
:root{--bg:#0a0e17;--surface:#111827;--border:#1e2d3d;--text:#e2e8f0;--text2:#94a3b8;--accent:#3b82f6;--green:#10b981;--warn:#f59e0b}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);max-width:860px;margin:0 auto;padding:24px;min-height:100vh}
.header{display:flex;align-items:center;gap:12px;margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid var(--border)}
.header .icon{font-size:28px}
.header h1{font-size:20px;color:var(--accent);letter-spacing:-0.5px}
.header span{font-size:12px;color:var(--text2)}
.note{background:#1e293b;border:1px solid var(--warn);border-radius:8px;padding:12px 16px;margin:16px 0;font-size:13px;color:var(--warn);display:flex;align-items:center;gap:8px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;margin:16px 0}
.card h2{font-size:15px;color:var(--accent);margin-bottom:16px;display:flex;align-items:center;gap:8px}
input,textarea{width:100%;padding:12px 16px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:14px;outline:none;transition:border .2s}
input:focus{border-color:var(--accent)}
button{width:100%;padding:12px;border-radius:8px;border:none;background:var(--accent);color:#fff;font-size:14px;font-weight:600;cursor:pointer;margin-top:8px;transition:all .2s;position:relative}
button:hover{background:#2563eb}
button:active{background:#1d4ed8;transform:scale(0.98)}
button:active::after{content:" ...";animation:dots 1.5s steps(4,end) infinite}
@keyframes dots{0%{content:" ."}33%{content:" .."}66%{content:" ..."}}
.result{background:var(--bg);border-radius:8px;padding:20px;margin:16px 0;line-height:1.7;white-space:pre-wrap;border:1px solid var(--border);font-size:14px}
.result h2,.result h3{color:var(--accent);margin:10px 0}
.result code{background:var(--surface);padding:2px 6px;border-radius:4px;color:#f59e0b;font-size:13px}
.result pre{background:var(--surface);padding:14px;border-radius:8px;overflow-x:auto;margin:8px 0}
.result table{width:100%;border-collapse:collapse;margin:8px 0}
.result th,.result td{border:1px solid var(--border);padding:6px 10px;text-align:left}
.result th{background:var(--surface)}
.result strong{color:#f59e0b}
.result a{color:var(--accent)}
.result blockquote{border-left:3px solid var(--accent);padding-left:12px;color:var(--text2)}
.footer{text-align:center;color:var(--text2);font-size:12px;margin-top:40px;padding-top:20px;border-top:1px solid var(--border)}
.back{display:inline-block;margin-top:12px;color:var(--accent);text-decoration:none;font-size:13px}
.back:hover{text-decoration:underline}
</style>
</head>
<body>
<div class="header">
  <div class="icon">&#x1F9E0;</div>
  <div><h1>SmartResearch</h1><span>Second Brain Agent - DeepSeek + TF-IDF</span></div>
</div>

RESPONSE_PLACEHOLDER

<div class="note">&#x23F3; 首次请求需 30-60 秒，提交后请耐心等待，勿重复点击</div>

<div class="card">
  <form method="post" action="/">
    <h2>&#x1F4AC; 对话</h2>
    <input name="query" placeholder="输入你的问题..." required autofocus>
    <button type="submit">&#x1F680; 发送</button>
  </form>
</div>

<div class="card">
  <form method="post" action="/" enctype="multipart/form-data">
    <h2>&#x1F4C4; 上传文件</h2>
    <input type="file" name="file" required>
    <button type="submit">上传并解析</button>
  </form>
</div>

<div class="card">
  <form method="post" action="/">
    <h2>&#x1F517; 提交链接</h2>
    <input name="url" placeholder="https://..." required>
    <button type="submit">解析链接</button>
  </form>
</div>

<div class="card">
  <form method="get" action="/graph">
    <h2>&#x1F578; 知识图谱</h2>
    <button type="submit">查看图谱</button>
  </form>
</div>

<div class="footer">SmartResearch v0.1.0 | DeepSeek + TF-IDF</div>
</body>
</html>

"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)


