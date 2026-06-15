# ========== 基础镜像 ==========
FROM python:3.11-slim

# ========== 环境变量 ==========
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ========== 系统依赖（Tesseract OCR 中文支持） ==========
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

# ========== 工作目录 ==========
WORKDIR /app

# ========== 安装 Python 依赖（利用 Docker 层缓存） ==========
COPY requirements.txt .
RUN pip install -r requirements.txt

# ========== 复制源码 ==========
COPY . .

# ========== 数据目录（运行时挂载 volume） ==========
RUN mkdir -p /app/data/uploads /app/data/chroma

# ========== 启动 ==========
EXPOSE 8002
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
