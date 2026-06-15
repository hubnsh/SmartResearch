"""
SmartResearch —— 多模态智能学习与科研助手平台
FastAPI 主入口
"""
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from src.core.config import settings
from src.api.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="多模态 Second Brain Agent —— 支持文档、图片、网页、论文链接的智能知识管理",
    version="0.1.0",
)

app.include_router(router, prefix="/api")

# 挂载静态文件目录（用于前端页面）
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """返回前端对话页面"""
    return _HTML_PAGE


# ---- 内联前端页面 ----
_HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartResearch - 智能科研助手</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; display: flex; }
        .sidebar { width: 260px; background: #1e293b; padding: 24px; display: flex; flex-direction: column; gap: 16px; border-right: 1px solid #334155; }
        .sidebar h2 { font-size: 18px; color: #38bdf8; }
        .sidebar .btn { padding: 10px 16px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; background: #334155; color: #e2e8f0; text-align: left; }
        .sidebar .btn:hover { background: #475569; }
        .sidebar .btn.primary { background: #0284c7; color: #fff; }
        .sidebar .btn.primary:hover { background: #0369a1; }
        .main { flex: 1; display: flex; flex-direction: column; }
        .header { padding: 20px 32px; border-bottom: 1px solid #334155; font-size: 20px; font-weight: 600; }
        .chat-area { flex: 1; overflow-y: auto; padding: 24px 32px; display: flex; flex-direction: column; gap: 16px; }
        .msg { max-width: 80%; padding: 14px 18px; border-radius: 12px; line-height: 1.6; }
        .msg.user { align-self: flex-end; background: #0284c7; white-space: pre-wrap; }
        .msg.agent { align-self: flex-start; background: #1e293b; border: 1px solid #334155; }
        .msg.agent h1,.msg.agent h2,.msg.agent h3 { color: #38bdf8; margin: 8px 0 4px; }
        .msg.agent ul,.msg.agent ol { margin: 4px 0; padding-left: 20px; }
        .msg.agent code { background: #334155; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
        .msg.agent pre { background: #0f172a; padding: 12px; border-radius: 8px; overflow-x: auto; margin: 8px 0; }
        .msg.agent pre code { background: none; padding: 0; }
        .msg.agent table { border-collapse: collapse; margin: 8px 0; width: 100%%; }
        .msg.agent th,.msg.agent td { border: 1px solid #475569; padding: 6px 10px; text-align: left; }
        .msg.agent th { background: #334155; }
        .msg.agent strong { color: #facc15; }
        .msg.system { align-self: center; background: #334155; font-size: 13px; max-width: 90%; text-align: center; }
        .input-area { padding: 20px 32px; border-top: 1px solid #334155; display: flex; gap: 12px; }
        .input-area input { flex: 1; padding: 12px 16px; border-radius: 10px; border: 1px solid #475569; background: #1e293b; color: #e2e8f0; font-size: 15px; outline: none; }
        .input-area input:focus { border-color: #38bdf8; }
        .input-area button { padding: 12px 24px; border-radius: 10px; border: none; background: #0284c7; color: #fff; font-size: 15px; cursor: pointer; }
        .input-area button:hover { background: #0369a1; }
        .upload-section { padding: 12px 32px; display: flex; gap: 12px; align-items: center; }
        .upload-section input[type=file] { color: #94a3b8; }
        .upload-section input[type=text] { flex: 1; padding: 8px 12px; border-radius: 8px; border: 1px solid #475569; background: #1e293b; color: #e2e8f0; font-size: 14px; outline: none; }
        .spinner { width: 20px; height: 20px; border: 2px solid #475569; border-top-color: #38bdf8; border-radius: 50%; animation: spin .6s linear infinite; display: inline-block; margin-right: 8px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .hidden { display: none !important; }
    </style>
</head>
<body>
<div class="sidebar">
    <h2>SmartResearch</h2>
    <p style="font-size:13px;color:#94a3b8;">多模态 Second Brain Agent</p>
    <button class="btn primary" onclick="showChat()">对话</button>
    <button class="btn" onclick="showUpload()">上传文件</button>
    <button class="btn" onclick="showLink()">提交链接</button>
    <button class="btn" onclick="loadGraph()">查看知识图谱</button>
    <div style="margin-top:auto;font-size:12px;color:#64748b;">v0.2.0 — Phase 2 ✓</div>
</div>

<div class="main">
    <div class="header" id="header-title">对话</div>

    <!-- 对话区 -->
    <div id="chat-section" class="chat-area"></div>
    <div id="chat-input-area" class="input-area">
        <input id="chat-input" type="text" placeholder="输入你的问题..." onkeydown="if(event.key==='Enter')sendChat()">
        <button onclick="sendChat()">发送</button>
    </div>

    <!-- 上传区 -->
    <div id="upload-section" class="chat-area hidden">
        <div class="msg system">支持 PDF / Word / PPT / TXT / Markdown / 图片 (JPG/PNG)<br>上传后系统将自动执行 OCR 识别 + 语义分析 + 知识图谱构建</div>
        <div class="input-area">
            <input type="file" id="file-input" accept=".pdf,.docx,.pptx,.txt,.md,.jpg,.jpeg,.png,.bmp,.tiff,.webp" style="color:#e2e8f0">
            <button onclick="uploadFile()">上传并解析</button>
        </div>
    </div>
    <div id="upload-input-area" class="input-area hidden"></div>

    <!-- 链接区 -->
    <div id="link-section" class="chat-area hidden">
        <div class="msg system">支持：网页 / Arxiv 论文 / GitHub 仓库 / B站视频 / YouTube 视频<br>视频链接将自动提取字幕并生成"课程知识树"</div>
        <div class="input-area">
            <input id="link-input" type="text" placeholder="输入网页 / 视频链接..." onkeydown="if(event.key==='Enter')submitLink()">
            <button onclick="submitLink()">解析</button>
        </div>
    </div>
    <div id="link-input-area" class="input-area hidden"></div>

    <!-- 图谱区 -->
    <div id="graph-section" class="chat-area hidden" style="align-items:center;justify-content:center;">
        <div id="graph-container" style="width:100%;height:100%;overflow:auto;font-size:13px;font-family:monospace;"></div>
    </div>
    <div id="graph-input-area" class="input-area hidden"></div>
</div>

<script>
    let currentSection = 'chat';

    function showSection(id) {
        document.querySelectorAll('.chat-area,.input-area').forEach(el => el.classList.add('hidden'));
        document.getElementById(id + '-section').classList.remove('hidden');
        document.getElementById(id + '-input-area').classList.remove('hidden');
        currentSection = id;
    }

    function showChat() { showSection('chat'); document.getElementById('header-title').textContent = '对话'; }
    function showUpload() { showSection('upload'); document.getElementById('header-title').textContent = '上传文件'; }
    function showLink() { showSection('link'); document.getElementById('header-title').textContent = '提交链接'; }

    function addMsg(role, text) {
        const area = document.getElementById('chat-section');
        const div = document.createElement('div');
        div.className = 'msg ' + role;
        if (role === 'agent') {
            div.innerHTML = marked.parse(text);
        } else {
            div.textContent = text;
        }
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
        addMsg('system', '<span class="spinner"></span>思考中...');
        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: q})
            });
            const data = await res.json();
            const last = document.querySelector('#chat-section .msg:last-child');
            if (last && last.className.includes('system')) last.remove();
            addMsg('agent', data.answer || '暂无回复');
        } catch (e) {
            addMsg('system', '请求失败: ' + e.message);
        }
    }

    async function uploadFile() {
        const fileInput = document.getElementById('file-input');
        const file = fileInput.files[0];
        if (!file) return alert('请选择文件');
        showChat();
        addMsg('system', '<span class="spinner"></span>正在解析文件: ' + file.name);
        const form = new FormData();
        form.append('file', file);
        try {
            const res = await fetch('/api/upload', { method: 'POST', body: form });
            const data = await res.json();
            const last = document.querySelector('#chat-section .msg:last-child');
            if (last && last.className.includes('system')) last.remove();
            if (data.summary) {
                addMsg('agent', '文件解析完成: ' + file.name + '\n摘要: ' + data.summary + '\n关键词: ' + (data.keywords||[]).join(', '));
            } else {
                addMsg('system', data.message || '解析完成');
            }
        } catch (e) {
            addMsg('system', '上传失败: ' + e.message);
        }
    }

    async function submitLink() {
        const input = document.getElementById('link-input');
        const url = input.value.trim();
        if (!url) return alert('请输入链接');
        showChat();
        addMsg('user', '提交链接: ' + url);
        input.value = '';
        addMsg('system', '<span class="spinner"></span>正在解析链接...');
        try {
            const res = await fetch('/api/link', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url})
            });
            const data = await res.json();
            const last = document.querySelector('#chat-section .msg:last-child');
            if (last && last.className.includes('system')) last.remove();
            let reply = '链接解析完成: ' + url + '\n摘要: ' + (data.summary||'') + '\n关键词: ' + (data.keywords||[]).join(', ');
            if (data.knowledge_tree) {
                reply += '\n\n【课程知识树】\n' + data.knowledge_tree;
            }
            addMsg('agent', reply);
        } catch (e) {
            addMsg('system', '解析失败: ' + e.message);
        }
    }

    async function loadGraph() {
        showSection('graph');
        document.getElementById('header-title').textContent = '知识图谱';
        const container = document.getElementById('graph-container');
        container.innerHTML = '<span class="spinner"></span>加载中...';
        try {
            const res = await fetch('/api/graph');
            const data = await res.json();
            const nodes = data.nodes || [];
            const links = data.links || [];
            let html = '<p>节点: ' + nodes.length + ' | 关系: ' + links.length + '</p><hr>';
            nodes.forEach(n => {
                html += '<p><b>[' + n.type + ']</b> ' + n.label + '</p>';
            });
            html += '<hr><p><b>关系列表:</b></p>';
            links.forEach(l => {
                html += '<p>' + l.source + ' → ' + l.type + ' → ' + l.target + '</p>';
            });
            container.innerHTML = html;
        } catch (e) {
            container.innerHTML = '加载失败: ' + e.message;
        }
    }
</script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
