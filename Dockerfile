FROM python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./backend/

# 复制前端构建产物
COPY frontend/dist/ ./frontend/dist/

# 数据目录
RUN mkdir -p /data /media

WORKDIR /app/backend

EXPOSE 8686

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8686"]
