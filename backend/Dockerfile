FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
# .pyc 캐시를 안 쓰게 해서, docker exec로 돌리는 1회성 테스트 스크립트가 __pycache__를
# 건드려 fastapi dev의 auto-reload를 계속 재트리거하는 걸 막는다 (테스트 동작 자체엔 영향 없음)
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && crawl4ai-setup \
    && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('jhgan/ko-sroberta-multitask')"

COPY . .

EXPOSE 8000

CMD ["fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
