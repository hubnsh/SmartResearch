# 🧠 SmartResearch —— 多模态智能学习与科研助手

[![CI](https://github.com/hubnsh/SmartResearch/actions/workflows/ci.yml/badge.svg)](https://github.com/hubnsh/SmartResearch/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-4B8BF5.svg)](https://www.deepseek.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 超越传统文档管理的"第二大脑"平台。自动解析 PDF、图片、网页、视频等多模态知识来源，通过 AI Agent 构建统一知识图谱，实现**知识点级**而非文件级的管理。

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 📄 **文档解析** | PDF / Word / PPT / TXT / Markdown 自动提取与摘要 |
| 🖼️ **图片理解** | OCR 文字识别 + LLM Vision 语义分析 |
| 🌐 **网页抓取** | 通用网页正文提取、Arxiv 论文元数据解析、GitHub 仓库分析 |
| 🎬 **视频处理** | B站 / YouTube 字幕提取 + 知识树生成 |
| 🎵 **音频分析** | MP3 / WAV / M4A 语音识别与摘要 |
| 🕸️ **知识图谱** | Neo4j 自动构建实体关系网络，支持可视化浏览 |
| 💬 **RAG 问答** | 基于 ChromaDB 向量检索 + DeepSeek LLM 的智能对话 |
| 📥 **Markdown 导出** | 对话结果一键下载为 .md 文件 |

---

## 🚀 快速开始

### 环境要求

- **Python 3.11+**
- Docker（可选，用于 Neo4j 知识图谱）
- Tesseract OCR（可选，用于图片文字识别）

### 1. 克隆仓库

```bash
git clone https://github.com/hubnsh/SmartResearch.git
cd SmartResearch
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，至少填入 DEEPSEEK_API_KEY
```

`.env` 关键配置：

```ini
# 必填：DeepSeek API Key（https://platform.deepseek.com/api_keys）
DEEPSEEK_API_KEY=sk-your-key-here

# Embedding（零网络依赖，开箱即用）
USE_LOCAL_EMBEDDING=True

# Neo4j（可选，需 Docker）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 启动服务

**方式一：双击启动（Windows 推荐）**
```
双击 launcher.bat → 自动打开浏览器
```

**方式二：命令行**
```bash
python run_server.py
# 访问 http://localhost:8002
```

**方式三：Docker（可选基础设施）**
```bash
docker-compose up -d    # 启动 Neo4j + ChromaDB
python run_server.py     # 启动应用
```

---

## 📖 使用指南

### Web 界面

| 页面 | 地址 | 说明 |
|------|------|------|
| 首页 (no-JS) | `http://localhost:8002/` | 纯 HTML 表单，兼容所有浏览器 |
| JS 增强版 | `http://localhost:8002/js` | 侧边栏导航 + Markdown 渲染 + 一键下载 |
| 知识图谱 | `http://localhost:8002/graph` | 实体关系表格式浏览 |
| 健康检查 | `http://localhost:8002/health` | 服务状态查询 |

### 对话与下载

1. 在输入框输入问题（如"什么是机器学习"）
2. 点击**发送**，等待 30-60 秒（首次预热）
3. 查看 AI 回复（Markdown 格式渲染）
4. 点击 **📥 下载为 .md** 保存结果

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/chat` | RAG 智能问答 |
| `POST` | `/api/upload` | 上传文件解析 |
| `POST` | `/api/link` | 提交链接抓取 |
| `GET` | `/api/graph` | 知识图谱数据 |
| `POST` | `/api/export-md` | 导出 Markdown |
| `POST` | `/export-md-form` | no-JS Markdown 下载 |

### CLI 模式

```bash
# 命令行对话
python -m src.services.dispatcher chat "解释量子计算的基本原理"

# 列出已注册的 Agent
python -m src.services.dispatcher agents
```

---

## 📦 打包为 Windows .exe

```bash
pip install pyinstaller
python build_exe.py
# 输出: dist/SmartResearch.exe
```

将 `dist/SmartResearch.exe` 与 `.env` 文件放在同一目录，双击即可运行。

---

## 📁 项目结构

```
SmartResearch/
├── src/
│   ├── agents/              # 多模态 Agent
│   │   ├── base.py          # Agent 基类 + 注册中心
│   │   ├── document_agent.py # PDF/Word/PPT/TXT/MD
│   │   ├── vision_agent.py  # 图片 OCR + Vision
│   │   ├── web_agent.py     # 网页/Arxiv/GitHub
│   │   ├── video_agent.py   # B站/YouTube 字幕
│   │   └── audio_agent.py   # 音频转写
│   ├── api/
│   │   └── routes.py        # FastAPI 路由
│   ├── core/
│   │   ├── config.py        # 配置管理（Pydantic Settings）
│   │   └── logging_config.py # Loguru 结构化日志
│   └── services/
│       ├── dispatcher.py    # 任务调度中心
│       ├── llm_service.py   # DeepSeek LLM 封装
│       ├── rag_service.py   # ChromaDB 向量检索
│       ├── kg_service.py    # Neo4j 知识图谱
│       └── offline_embeddings.py # TF-IDF 离线向量化
├── static/                  # 前端静态资源
├── tests/                   # 测试用例
├── docs/                    # 设计文档
├── launcher.bat             # Windows 双击启动
├── build_exe.py             # PyInstaller 打包脚本
├── SmartResearch.spec       # PyInstaller 配置
├── run_server.py            # 主启动入口
├── requirements.txt         # Python 依赖
├── docker-compose.yml       # Docker 基础设施
└── .github/workflows/       # CI/CD 流水线
```

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **API 框架** | FastAPI + Uvicorn |
| **LLM** | DeepSeek (deepseek-chat) + LangChain |
| **知识图谱** | Neo4j |
| **向量数据库** | ChromaDB |
| **向量化** | TF-IDF 离线模式 / HuggingFace all-MiniLM-L6-v2 |
| **文档解析** | PyMuPDF / python-docx / python-pptx |
| **OCR** | PaddleOCR / Tesseract |
| **日志** | Loguru（JSON 结构化 + 自动轮转） |
| **CI/CD** | GitHub Actions（lint → 测试 → Docker 构建） |

---

## 🔧 添加新 Agent

1. 在 `src/agents/` 创建新文件，继承 `BaseAgent`：

```python
from src.agents.base import BaseAgent, agent_registry

class MyAgent(BaseAgent):
    agent_type = "my_type"
    supported_extensions = [".xyz"]

    async def process(self, input_path: str):
        # 实现处理逻辑
        return {"summary": "...", "keywords": [...]}

agent_registry.register(MyAgent)
```

2. 在 `src/services/dispatcher.py` 的 `_load_agents()` 中导入：

```python
from src.agents.my_agent import MyAgent
agent_registry.register(MyAgent)
```

---

## ⚠️ 常见问题

| 问题 | 解决方案 |
|------|----------|
| 首次请求很慢（30-60秒） | 正常现象：模型预热 + DeepSeek API 首次调用延迟，之后会很快 |
| 知识图谱为空 | 未启动 Neo4j：`docker-compose up -d` |
| ChromaDB 连接失败 | 本地文件模式自动降级，检查 `CHROMA_DB_PATH` 目录权限 |
| 点击发送按钮无反应 | 服务器版本过旧，执行 `Get-Process python \| Stop-Process -Force` 后重启 |
| API Key 无效 | 检查 `.env` 中 `DEEPSEEK_API_KEY` 是否正确 |

---

## 📄 License

MIT License

---

**Made with ❤️ by SmartResearch Team**