# 🧠 SmartResearch —— 多模态智能学习与科研助手

[![CI](https://github.com/hubnsh/SmartResearch/actions/workflows/ci.yml/badge.svg)](https://github.com/hubnsh/SmartResearch/actions/workflows/ci.yml)
[![Build Desktop](https://github.com/hubnsh/SmartResearch/actions/workflows/build-desktop.yml/badge.svg)](https://github.com/hubnsh/SmartResearch/actions/workflows/build-desktop.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📖 项目简介

**SmartResearch** 是一个"第二大脑"（Second Brain）知识管理工具。它把散落在各处的知识——图片截图、网页文章、论文 PDF、视频教程——自动解析为结构化笔记，支持 AI 摘要和知识提取。

### 两种使用方式

| 方式 | 适合谁 | 特点 |
|------|--------|------|
| 🖥️ **桌面版**（推荐） | 普通用户 | 像 CCswitch 一样下载即用，拖入图片/粘贴链接即可 |
| 🌐 **Web 版** | 开发者 / 服务器部署 | 浏览器访问，支持文档上传 + RAG 问答 |

---

## ✨ 功能一览

| 功能 | 说明 | 桌面版 | Web 版 |
|------|------|--------|--------|
| 🖼️ **图片 OCR** | 拖入图片 → 自动识别文字 | ✅ | ✅ |
| 🔗 **链接解析** | 粘贴链接 → 自动抓取网页内容 | ✅ | ✅ |
| 🤖 **AI 摘要** | LLM 自动生成摘要 + 关键词 + 实体 | ✅ | ✅ |
| 📝 **笔记生成** | 多个素材合成结构化 Markdown 笔记 | ✅ | ✅ |
| 📄 **文档解析** | PDF / Word / PPT 内容提取 | ❌ | ✅ |
| 🎬 **视频字幕** | B站 / YouTube 字幕提取 | ❌ | ✅ |
| 🎵 **音频转写** | MP3 / WAV 语音转文字 | ❌ | ✅ |
| 🔍 **RAG 问答** | 基于知识库的语义检索 | ❌ | ✅ |
| 🕸️ **知识图谱** | Neo4j 实体关系可视化 | ❌ | ✅ |

---

## 🚀 快速开始

### 方式一：桌面版（下载即用）

从 [GitHub Releases](https://github.com/hubnsh/SmartResearch/releases) 下载 `SmartResearch-Desktop-*.zip`：

```
1. 解压 ZIP 文件
2. 编辑 .env 文件，填入你的 API Key（见下方配置）
3. 双击 SmartResearch.exe
4. 拖入图片或点击「导入链接」→ 点击「生成笔记」
```

> 也可以自己构建：`pip install pyinstaller && python build_exe.py desktop`

### 方式二：Web 版（浏览器访问）

```bash
# 1. 克隆
git clone https://github.com/hubnsh/SmartResearch.git
cd SmartResearch

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env → 填入你的 API Key

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动
python run_server.py

# 5. 浏览器打开 http://localhost:8002/js
```

---

## 🤖 LLM 提供商配置

SmartResearch 支持 **4 种 LLM 提供商**，在桌面端「编辑 → 设置」中可随时切换：

| 提供商 | API Key 格式 | 特点 | 注册地址 |
|--------|-------------|------|---------|
| **DeepSeek**（推荐） | `sk-...` | 中文强、¥1/百万 token | [platform.deepseek.com](https://platform.deepseek.com) |
| **OpenAI** | `sk-...` | GPT-4o、生态完善 | [platform.openai.com](https://platform.openai.com) |
| **Anthropic Claude** | `sk-ant-...` | 长上下文、推理强 | [console.anthropic.com](https://console.anthropic.com) |
| **自定义** | 不限 | 任意 OpenAI 兼容 API | Groq / Together / vLLM / Ollama |

桌面版配置方法：

```
编辑 → 设置 → LLM 提供商 [下拉选择]
  ├── DeepSeek → 填入 sk-... + 选择模型
  ├── OpenAI   → 填入 sk-... + 选择模型
  ├── Claude   → 填入 sk-ant-... + 选择模型
  └── 自定义   → 填入 Key + API 地址 + 模型名
```

---

## 🖥️ 桌面版使用指南

首次启动后，桌面的主要操作流程：

```
① 拖入图片  →  ② 导入链接  →  ③ 生成笔记  →  ④ 导出 .md
  自动 OCR       自动抓取       AI 整理       保存文件
```

**界面布局：**

```
┌──────────────────────────────────────────────────┐
│  [+ 导入图片] [+ 导入链接]  [保存] [打开]       │ ← 工具栏
├────────────────────┬─────────────────────────────┤
│  📦 素材列表       │  📝 笔记内容                │
│                    │                             │
│  🖼️  screenshot.png│  # 研究笔记 — 2026-07-08    │
│  🔗  arxiv.org/... │                             │
│  🔗  github.com/.. │  ## 1. 🔗 论文摘要          │
│                    │  **摘要**: 本文提出...       │
│                    │  **关键词**: NLP, Transformer│
│                    │                             │
│ 共 3 个素材        │  [生成笔记] [导出 .md]       │
└────────────────────┴─────────────────────────────┘
```

---

## 🌐 Web 版使用指南

启动后访问以下路径：

| 路径 | 说明 | 特点 |
|------|------|------|
| `/` | 首页（no-JS） | 纯 HTML 表单，兼容所有浏览器 |
| `/js` | JS 增强版 | 侧边栏导航 + Markdown 实时渲染 |
| `/graph` | 知识图谱 | 实体-关系表格式浏览 |
| `/health` | 健康检查 | JSON 状态 + 版本信息 |
| `/docs` | API 文档 | Swagger 自动生成 |

**API 端点：**

```bash
# 智能问答
curl -X POST http://localhost:8002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是Transformer？"}'

# 解析链接
curl -X POST http://localhost:8002/api/link \
  -H "Content-Type: application/json" \
  -d '{"url": "https://arxiv.org/abs/1706.03762"}'

# 上传文件
curl -X POST http://localhost:8002/api/upload \
  -F "file=@paper.pdf"
```

---

## 📦 Windows 桌面版打包

### 从源码构建 exe

```bash
pip install pyinstaller
python build_exe.py desktop
# 输出: dist/SmartResearch-Desktop-v1.0.0.zip
```

### GitHub Actions 自动构建

打 `v*` tag 自动触发：

```bash
git tag v1.0.0
git push origin v1.0.0
```

或在 GitHub → Actions → **Build Desktop** → **Run workflow** 手动触发。构建产物：
- `SmartResearch-Desktop-*.zip`（含 exe + .env + README）
- `SmartResearch.exe`（裸 exe）

---

## 📁 项目结构

```
SmartResearch/
├── desktop/                    # 🖥️ 桌面版（PySide6 GUI）
│   ├── window.py               # 主窗口
│   ├── widgets.py              # 素材列表 + 笔记面板
│   ├── workers.py              # 后台处理线程
│   ├── dialogs.py              # 设置 / 关于 / 详情对话框
│   ├── models.py               # 数据模型
│   ├── project_manager.py      # 项目文件管理
│   ├── logging_config.py       # 桌面版日志配置
│   └── icon.ico / icon.png     # 应用图标
├── src/                        # 🧠 核心逻辑
│   ├── agents/                 # 多模态 AI Agent
│   │   ├── base.py             # 抽象基类 + 注册中心
│   │   ├── document_agent.py   # PDF/Word/PPT/TXT/MD
│   │   ├── web_agent.py        # 网页/Arxiv/GitHub
│   │   ├── vision_agent.py     # 图片 OCR + Vision
│   │   ├── video_agent.py      # B站/YouTube 字幕
│   │   └── audio_agent.py      # 音频语音识别
│   ├── services/
│   │   ├── llm_service.py      # 多提供商 LLM 封装
│   │   ├── rag_service.py      # ChromaDB 向量检索
│   │   ├── kg_service.py       # Neo4j 知识图谱
│   │   ├── dispatcher.py       # Agent 路由调度
│   │   └── offline_embeddings.py # TF-IDF 离线向量化
│   ├── api/
│   │   └── routes.py           # FastAPI 路由
│   ├── core/
│   │   ├── config.py           # .env 配置管理
│   │   └── logging_config.py   # 日志配置
│   └── main.py                 # FastAPI 应用入口
├── static/                     # 🎨 前端静态文件
│   ├── marked.js               # Markdown 渲染
│   ├── test.html               # 测试页
│   └── nojs.html               # 兼容页面
├── tests/                      # 🧪 测试
├── .github/workflows/          # ⚡ CI/CD
│   ├── ci.yml                  # 自动化测试
│   └── build-desktop.yml       # Windows exe 构建
├── desktop_app.py              # 桌面版入口
├── run_server.py               # Web 版入口
├── build_exe.py                # 打包脚本
├── desktop_build.spec          # 桌面版 PyInstaller 配置
├── desktop_launcher.bat        # 桌面版启动器
├── launcher.bat                # Web 版启动器
├── diagnose.py                 # 环境诊断工具
├── requirements.txt            # 依赖清单
└── .env.example                # 配置模板
```

---

## 🔧 扩展：自定义 Agent

你可以添加自己的 Agent 来实现任意功能——文本翻译、代码分析、数据可视化等。

### 三步创建一个自定义 Agent

**① 创建文件**

在 `custom_agents/` 目录下新建 `.py` 文件：

```python
from src.agents.base import BaseAgent, agent_registry

class MyAgent(BaseAgent):
    AGENT_TYPE = "my_agent"                # 唯一标识
    SUPPORTED_EXTENSIONS = {".csv", ".json"}  # 匹配文件类型

    async def process(self, input_data: str) -> dict:
        self._ensure_services()            # 获取 LLM/KG/RAG
        # 你的处理逻辑...
        return {"summary": "结果", "keywords": [], "entities": []}

agent_registry.register(MyAgent)  # 注册！
```

**② 重启应用**

Agent 会自动加载，可以在日志中看到：
```
[CustomAgent] 已加载: my_agent.py
```

**③ 使用**

- **上传文件** → Agent 根据扩展名自动匹配
- **提交链接** → Agent 的 `handles_url()` 方法判断是否匹配

### 参考示例

查看 [custom_agents/example_agent.py](custom_agents/example_agent.py) 获取完整示例，包括：
- 文件匹配型 Agent（按扩展名自动触发）
- URL 匹配型 Agent（按链接模式自动触发）

---

## 🧪 测试

```bash
# 运行全部测试
cd SmartResearch && python -m pytest tests/ -v

# 快速结构测试
python -m pytest tests/test_phase1.py -v

# Agent 分发测试
python -m pytest tests/test_phase2.py -v
```

---

## 🎯 技术栈

| 技术 | 用途 |
|------|------|
| **Python 3.11+** | 运行时 |
| **PySide6** | 桌面 GUI（类似 CCswitch 的原生体验） |
| **FastAPI + Uvicorn** | Web 服务器 |
| **LangChain** | LLM 调用抽象 |
| **ChromaDB** | 向量数据库 |
| **scikit-learn** | 离线 TF-IDF 向量化 |
| **BeautifulSoup + httpx** | 网页抓取 |
| **PyMuPDF / python-docx** | 文档解析 |
| **PyInstaller** | Windows exe 打包 |
| **DeepSeek / OpenAI / Claude** | 多 LLM 提供商支持 |

---

## ⚠️ 常见问题

| 症状 | 原因 | 解决 |
|------|------|------|
| 桌面版启动后"未配置 API Key" | .env 未填写 | 编辑 → 设置 → 填入 API Key |
| "请求超时" | 网络问题或 API 服务不稳定 | 检查网络连接，重试 |
| "网站拒绝访问（403）" | 目标网站有反爬保护 | 已自动重试 + 切换 User-Agent |
| 图片 OCR 失败 | Tesseract 未安装 | 安装 Tesseract OCR 5.x |
| 本地 Embedding 下载慢 | 首次需下载模型 | 耐心等待，或关闭 USE_LOCAL_EMBEDDING |
| Web 版首次请求 30-60 秒 | 服务懒加载 | 正常，后续请求 < 5 秒 |

---

## 📄 License

MIT License — 自由使用、修改、分发。

---

**Made with ❤️ by SmartResearch Team**
