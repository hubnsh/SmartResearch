# 🧠 SmartResearch —— 多模态智能学习与科研助手

[![CI](https://github.com/hubnsh/SmartResearch/actions/workflows/ci.yml/badge.svg)](https://github.com/hubnsh/SmartResearch/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-4B8BF5.svg)](https://www.deepseek.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📖 项目简介

**SmartResearch** 是一个面向科研工作者和技术人员的"第二大脑"（Second Brain）平台。它超越了传统的文件管理器思维，将各类知识来源——论文 PDF、技术文档、网页文章、视频教程、会议录音——自动解析、提炼为结构化的知识图谱，并提供基于大语言模型的智能问答。

### 解决什么问题？

| 痛点 | SmartResearch 方案 |
|------|-------------------|
| 资料散落各处（PDF/网页/视频/笔记） | 统一入口，自动解析 5 类格式 + 3 类链接 |
| 只记得内容不记得在哪个文件里 | 知识点级向量检索，用自然语言查找 |
| 读完就忘，知识没有形成网络 | Neo4j 自动构建实体关系图谱 |
| 论文/文档太长不想读 | LLM 自动生成摘要 + 提取核心概念 |
| 多个工具来回切换 | Web 一站式界面 + CLI + API 三种交互 |

### 核心理念

`
知识输入          知识加工              知识输出
─────────       ─────────────        ──────────
PDF/Word/PPT    Document Agent       智能摘要
图片/截图       Vision Agent         关键词提取
网页/论文链接    Web Agent           知识图谱
B站/YouTube     Video Agent          RAG 问答
音频/录音       Audio Agent          .md 导出
     ↓               ↓                   ↓
 多模态输入    →  AI Agent 处理    →  结构化知识
`

---

## 🏗️ 系统架构

`mermaid
graph TB
    subgraph "用户交互层"
        WEB["🌐 Web UI<br/>no-JS + JS 增强版"]
        CLI["💻 CLI<br/>命令行对话"]
        API["🔌 REST API<br/>第三方集成"]
    end

    subgraph "API 网关层"
        FASTAPI["FastAPI + Uvicorn<br/>路由 / CORS / 限流 / 静态文件"]
    end

    subgraph "Agent 调度层"
        DISPATCHER["TaskDispatcher<br/>文件类型识别 → Agent 路由"]
        REGISTRY["AgentRegistry<br/>5 个 Agent 动态注册"]
    end

    subgraph "Agent 执行层"
        DOC["📄 DocumentAgent<br/>PDF/Word/PPT/TXT/MD"]
        VISION["🖼️ OCRVisionAgent<br/>图片 OCR + Vision"]
        WEB_AGENT["🌐 WebAgent<br/>网页/Arxiv/GitHub"]
        VIDEO["🎬 VideoAgent<br/>B站/YouTube 字幕"]
        AUDIO["🎵 AudioAgent<br/>MP3/WAV/M4A 语音"]
    end

    subgraph "核心服务层"
        LLM["LLMService<br/>DeepSeek 对话 / 摘要 / 提取"]
        KG["KGService<br/>Neo4j 知识图谱"]
        RAG["RAGService<br/>ChromaDB 向量检索"]
        EMBED["OfflineEmbeddings<br/>TF-IDF 零网络依赖"]
    end

    subgraph "数据存储层"
        CHROMA[("🗄️ ChromaDB<br/>向量数据库")]
        NEO4J[("🕸️ Neo4j<br/>图数据库")]
        UPLOAD[("📁 Uploads<br/>原始文件")]
        LOGS[("📝 Logs<br/>结构化日志")]
    end

    WEB --> FASTAPI
    CLI --> DISPATCHER
    API --> FASTAPI
    FASTAPI --> DISPATCHER
    DISPATCHER --> REGISTRY
    REGISTRY --> DOC
    REGISTRY --> VISION
    REGISTRY --> WEB_AGENT
    REGISTRY --> VIDEO
    REGISTRY --> AUDIO
    DOC --> LLM
    DOC --> KG
    DOC --> RAG
    VISION --> LLM
    VISION --> KG
    VISION --> RAG
    WEB_AGENT --> LLM
    WEB_AGENT --> KG
    WEB_AGENT --> RAG
    RAG --> EMBED
    RAG --> CHROMA
    KG --> NEO4J
    DOC --> UPLOAD
`

---

## 🔄 数据处理流程

### RAG 对话流程

`mermaid
sequenceDiagram
    participant U as 👤 用户
    participant W as 🌐 Web UI
    participant D as Dispatcher
    participant R as RAGService
    participant E as Embedding
    participant C as ChromaDB
    participant L as LLM (DeepSeek)
    participant K as KGService (Neo4j)

    U->>W: 输入问题 "什么是Transformer"
    W->>D: POST /api/chat
    D->>R: hybrid_search(query, k=4)
    R->>E: embed_query(text)
    E-->>R: TF-IDF 向量 [0.12, 0.45, ...]
    R->>C: similarity_search(vector)
    C-->>R: 4 个相关文档片段
    D->>L: extract_knowledge(query)
    L-->>D: 实体: [Transformer, Attention, ...]
    D->>K: search_related("Transformer")
    K-->>D: 图谱关系: Transformer → USES → Self-Attention
    D->>L: chat(context + query)
    L-->>D: Markdown 格式回答
    D-->>W: ChatResponse(answer="...")
    W->>U: 渲染 Markdown + 显示下载按钮
`

### 文件处理流程

`mermaid
sequenceDiagram
    participant U as 👤 用户
    participant W as 🌐 Web
    participant D as Dispatcher
    participant A as Agent
    participant L as LLM
    participant K as KG (Neo4j)
    participant R as RAG (ChromaDB)

    U->>W: 上传 paper.pdf
    W->>D: handle_file(path)
    D->>D: 识别扩展名 .pdf
    D->>A: DocumentAgent.process(path)
    A->>A: PyMuPDF 提取文本
    A->>L: extract_knowledge(text[:10000])
    L-->>A: {entities, relations, summary, keywords}
    A->>K: upsert_knowledge(extraction)
    K-->>A: 图谱节点 + 关系已创建
    A->>R: add_documents([text], [metadata])
    R-->>A: 向量索引已更新
    A-->>D: {summary, keywords, entities, relations}
    D-->>W: 处理结果 JSON
    W->>U: 显示摘要 + 关键词 + 实体
`

---

## ✨ 核心功能详解

### 📄 文档解析 (DocumentAgent)

支持格式：**PDF、Word (.docx)、PPT (.pptx)、TXT、Markdown**

| 格式 | 解析引擎 | 能力 |
|------|----------|------|
| PDF | PyMuPDF (fitz) | 文本提取、字体识别 |
| Word | python-docx | 段落 + 表格 + 样式 |
| PPT | python-pptx | 幻灯片文本 + 备注 |
| TXT/MD | 原生读取 | UTF-8 自动检测 |

处理链路：文件读取 → 文本清洗 → LLM 摘要 → 关键词提取 → 实体识别 → KG 写入 → RAG 入库

### 🖼️ 图片理解 (OCRVisionAgent)

支持格式：**JPG、PNG、JPEG、BMP、TIFF**

`
图片 → PaddleOCR 文字提取 → 识别结果 → LLM 语义分析 → 知识入库
                ↓ (降级路径)
         Tesseract OCR
`

### 🌐 网页抓取 (WebAgent)

| URL 类型 | 识别模式 | 特殊处理 |
|----------|----------|----------|
| 通用网页 | https?:// | 正文提取（html2text） |
| Arxiv 论文 | rxiv.org/abs/ | 元数据 API + PDF 摘要 |
| GitHub 仓库 | github.com/*/* | README + 文件结构 |

### 🎬 视频处理 (VideoAgent)

`
B站/YouTube URL → yt-dlp 字幕提取 → 时间轴分段 → LLM 生成知识树
`

输出结构化的章节摘要和关键概念时间戳映射。

### 🎵 音频分析 (AudioAgent)

支持格式：**MP3、WAV、M4A、OGG**

`
音频文件 → whisper 语音识别 → 文本分段 → LLM 提取要点 → 知识入库
`

---

## 💾 数据存储方案

`
SmartResearch/
└── data/
    ├── uploads/           ← 上传的原始文件
    ├── chroma/            ← 向量数据库（SQLite）
    ├── huggingface/       ← Embedding 模型缓存
    ├── logs/              ← 运行日志（JSON，按天轮转）
    └── tfidf_cache.pkl    ← TF-IDF 向量化缓存
`

| 数据 | 存储 | 位置 | 说明 |
|------|------|------|------|
| 向量索引 | ChromaDB (SQLite) | data/chroma/ | 本地文件，无需服务端 |
| 知识图谱 | Neo4j | Docker olt://localhost:7687 | 未启动时优雅降级为空 |
| 原始文件 | 文件系统 | data/uploads/ | UUID 重命名 |
| 运行日志 | JSON 文件 | data/logs/ | Loguru 自动轮转 |
| 向量化 | TF-IDF (sklearn) | 内存 + data/tfidf_cache.pkl | 零网络依赖 |

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本 | 必需？ |
|------|------|--------|
| Python | 3.11+ | ✅ |
| DeepSeek API Key | — | ✅ |
| Docker | 最新版 | ❌ (仅 Neo4j 需要) |
| Tesseract OCR | 5.x | ❌ (图片 OCR 需要) |

### 一分钟启动

`ash
# 1. 克隆
git clone https://github.com/hubnsh/SmartResearch.git
cd SmartResearch

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env → 填入 DEEPSEEK_API_KEY

# 3. 安装
pip install -r requirements.txt

# 4. 启动
python run_server.py
# 打开 http://localhost:8002
`

**Windows 用户**：直接双击 launcher.bat，自动完成以上步骤。

---

## 📖 使用指南

### Web 界面

| 路径 | 说明 | 特点 |
|------|------|------|
| / | 首页（no-JS） | 纯 HTML 表单，兼容所有浏览器 |
| /js | JS 增强版 | 侧边栏导航 + Markdown 实时渲染 + 动画 |
| /graph | 知识图谱 | 实体-关系表格式浏览 |
| /health | 健康检查 | JSON 状态 + 版本信息 |
| /docs | Swagger 文档 | FastAPI 自动生成 |

### API 端点

`ash
# RAG 智能问答
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是Transformer架构？"}'

# 提交链接解析
curl -X POST http://localhost:8002/api/link \
  -H "Content-Type: application/json" \
  -d '{"url": "https://arxiv.org/abs/1706.03762"}'

# 上传文件
curl -X POST http://localhost:8002/api/upload \
  -F "file=@paper.pdf"

# 导出 Markdown
curl -X POST http://localhost:8002/api/export-md \
  -H "Content-Type: application/json" \
  -d '{"content": "# 标题\n内容...", "filename": "export.md"}'
`

### CLI 模式

`ash
# 命令行对话
python -m src.services.dispatcher chat "解释量子纠缠"

# 列出已注册的 Agent
python -m src.services.dispatcher agents
`

---

## 🧪 测试

`ash
# 运行全部测试
python -m pytest tests/ -v

# 快速结构测试（跳过 LLM 调用）
python -m pytest tests/test_phase1.py -v

# Agent 分发测试
python -m pytest tests/test_phase2.py -v
`

| 测试范围 | 文件 | 用例数 |
|----------|------|--------|
| API / 结构 / Config | 	est_phase1.py | 9 |
| Agent / Dispatcher / Chat | 	est_phase2.py | 7 |

---

## 📁 项目结构

`
SmartResearch/
├── src/
│   ├── agents/                # 🧠 多模态 AI Agent
│   │   ├── base.py            #    Agent 抽象基类 + 单例注册中心
│   │   ├── document_agent.py  #    PDF/Word/PPT/TXT/MD 解析
│   │   ├── vision_agent.py    #    图片 OCR + LLM Vision
│   │   ├── web_agent.py       #    网页/Arxiv/GitHub 爬取
│   │   ├── video_agent.py     #    B站/YouTube 字幕提取
│   │   └── audio_agent.py     #    音频语音识别
│   ├── api/
│   │   └── routes.py          # 🔌 FastAPI 路由（Chat/Upload/Link/Graph/Export）
│   ├── core/
│   │   ├── config.py          # ⚙️ Pydantic Settings（.env 配置管理）
│   │   └── logging_config.py  # 📝 Loguru 结构化日志配置
│   ├── models/                # 📦 数据模型（预留）
│   └── services/
│       ├── dispatcher.py      # 🎯 任务调度中心（Agent 发现 → 路由分发）
│       ├── llm_service.py     # 🤖 DeepSeek LLM 封装（对话/摘要/提取）
│       ├── rag_service.py     # 🔍 ChromaDB RAG 向量检索服务
│       ├── kg_service.py      # 🕸️ Neo4j 知识图谱 CRUD 服务
│       └── offline_embeddings.py # 📐 TF-IDF 离线向量化（零网络依赖）
├── static/                    # 🎨 前端静态资源
│   ├── index.html             #    独立版 JS 增强页面
│   ├── nojs.html              #    纯 HTML 兼容页面
│   ├── test.html              #    全功能测试页面
│   └── marked.js              #    Markdown 渲染库
├── tests/                     # 🧪 pytest 测试套件
├── docs/                      # 📚 架构设计与需求文档
├── data/                      # 💾 运行时数据（gitignore）
├── launcher.bat               # 🚀 Windows 双击启动脚本
├── build_exe.py               # 📦 PyInstaller 打包脚本
├── SmartResearch.spec         # 📦 PyInstaller 配置文件
├── run_server.py              # 🏁 主启动入口
├── requirements.txt           # 📋 Python 依赖清单
├── docker-compose.yml         # 🐳 Neo4j/ChromaDB 容器编排
├── Dockerfile                 # 🐳 应用容器镜像
└── .github/workflows/         # ⚡ CI/CD 流水线
`

---

## 🛠️ 技术选型与设计决策

### 为什么选这些技术？

| 技术 | 理由 |
|------|------|
| **FastAPI** | 异步原生支持、自动 OpenAPI 文档、类型安全、高性能 |
| **DeepSeek** | 中文能力强、API 兼容 OpenAI、成本低（¥1/百万 token） |
| **LangChain** | LLM 调用抽象层，支持 Prompt 模板 + 输出解析器 |
| **Neo4j** | 原生图数据库，Cypher 查询比 SQL JOIN 高效 100 倍 |
| **ChromaDB** | 嵌入式向量库，零配置、SQLite 持久化、LangChain 原生集成 |
| **TF-IDF** | 零网络依赖、启动即用、轻量级，作为离线 Embedding 降级方案 |
| **AgentRegistry** | 单例注册模式，新 Agent 只需 2 行代码注册 |

### 设计原则

1. **懒加载** — 所有服务（LLM/KG/RAG）首次调用才初始化，启动 < 2 秒
2. **优雅降级** — Neo4j 不可用时图谱返回空数组，不阻塞其他功能
3. **零网络依赖 Embedding** — TF-IDF 模式下无需下载任何模型
4. **纯 HTML 兼容** — 即使浏览器禁用 JS，/ 路由仍可正常对话
5. **单例注册中心** — Agent 发现通过类级注册，避免硬编码

---

## 🔧 扩展开发

### 添加新 Agent（3 步）

**1. 创建 src/agents/my_agent.py：**

`python
from src.agents.base import BaseAgent, agent_registry

class MyAgent(BaseAgent):
    AGENT_TYPE = "my_type"
    SUPPORTED_EXTENSIONS = {".xyz"}

    async def process(self, file_path: str):
        self._ensure_services()
        text = self._parse(file_path)
        extraction = await self.llm.extract_knowledge(text[:10000])
        self.kg.upsert_knowledge(extraction, {"source": file_path})
        self.rag.add_documents([text], [{"source": file_path}])
        return extraction

    def _parse(self, path): ...

agent_registry.register(MyAgent)
`

**2. 在 dispatcher.py 的 _load_agents() 中导入：**

`python
from src.agents.my_agent import MyAgent
agent_registry.register(MyAgent)
`

**3. 重启服务** — Agent 自动被发现和路由。

### 添加新 API 端点

`python
# src/api/routes.py
class MyRequest(BaseModel):
    text: str

@router.post("/my-endpoint")
async def my_handler(req: MyRequest):
    result = await some_service.process(req.text)
    return {"result": result}
`

---

## 📦 Windows 打包

`ash
pip install pyinstaller
python build_exe.py
# → dist/SmartResearch.exe
`

将 .exe 与 .env 放在同一目录即可运行，无需安装 Python。

---

## 🐳 Docker 部署

`ash
# 基础设施（Neo4j + ChromaDB）
docker-compose up -d

# 应用镜像
docker build -t smartresearch .
docker run -p 8002:8002 --env-file .env smartresearch
`

---

## ⚠️ 常见问题

| 症状 | 原因 | 解决 |
|------|------|------|
| 首次请求 30-60 秒 | 服务懒加载 + LLM API 冷启动 | 正常，后续请求 < 5 秒 |
| 知识图谱为空 | Neo4j 未启动 | docker-compose up -d |
| 向量检索无结果 | ChromaDB 未初始化或 Embedding 失败 | 检查 data/chroma/ 权限 |
| 发送按钮无反应 | 服务器运行旧版代码 | 重启：Get-Process python \| Stop-Process -Force |
| API Key 报错 | 未配置或余额不足 | 检查 .env 中 DEEPSEEK_API_KEY |

---

## 📄 License

MIT License — 自由使用、修改、分发。

---

**Made with ❤️ by SmartResearch Team**