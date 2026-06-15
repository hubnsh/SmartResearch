# SmartResearch 后端架构设计方案

## 1. 总体架构图 (逻辑)
系统采用插件式 Agent 架构，确保不同模态的处理逻辑解耦。

```text
[用户输入层] 
    → 文件上传 (PDF, Image)
    → 链接提交 (Web, Video, Arxiv)
    → 外部同步 (Notion, Obsidian)

[任务分发层 (Task Dispatcher)]
    → 识别模态类型
    → 路由至对应 Agent 插件

[Agent 插件层 (Multimodal Processors)]
    → Document Agent: PDF/Docx 解析 (Unstructured/PyMuPDF)
    → OCR & Vision Agent: 图片文字提取与语义分析 (GPT-4o Vision/PaddleOCR)
    → Web Agent: 网页正文提取与摘要 (Playwright/BeautifulSoup)
    → Video Agent: 语音转文字与知识点总结 (Whisper/GPT)

[核心引擎层 (Intelligence Engine)]
    → Semantic Integration: 语义聚合与实体提取
    → Knowledge Graph Builder: Neo4j 关系建立
    → Vector Embedding: ChromaDB 向量索引

[交互层 (Interface)]
    → FastAPI RESTful Endpoints
    → RAG Q&A Engine
    → Proactive Recommendation Service
```

## 2. 关键技术组件
*   **API 框架**: FastAPI (异步支持，适合高并发任务处理)
*   **任务队列**: Celery + Redis (处理耗时的 OCR 和视频解析任务)
*   **LLM 编排**: LangGraph (管理 Agent 的复杂状态转换与主动推送逻辑)
*   **存储引擎**:
    *   **PostgreSQL**: 存储元数据与用户信息
    *   **Neo4j**: 存储知识图谱实体与边
    *   **ChromaDB**: 存储文档片段向量

## 3. 核心流程设计：多模态数据流
1.  **Ingestion**: 用户通过 API 提交一个 B站视频链接。
2.  **Dispatch**: 调度器检测到是视频类型，调用 `VideoAgent`。
3.  **Extraction**: `VideoAgent` 获取视频字幕，发送给 LLM 进行摘要和知识点提取。
4.  **Enrichment**: `IntelligenceEngine` 获取知识点，在 Neo4j 中查找是否已有相关概念（如“深度学习”）。
5.  **Linking**: 发现关联后，自动在 Neo4j 中创建 `EXPLAINS` 或 `RELATED_TO` 关系。
6.  **Recommendation**: 触发主动推送，告知用户：“新视频内容已与您收藏的《Deep Learning》笔记关联”。

## 4. 后续开发规划
1.  **Phase 1**: 基础环境搭建，集成文档解析与 Web Agent。
2.  **Phase 2**: 集成 OCR 与 Vision Agent，实现图片语义理解。
3.  **Phase 3**: 实现视频处理逻辑与全自动图谱构建。
4.  **Phase 4**: 优化主动推送算法与全链路集成测试。
