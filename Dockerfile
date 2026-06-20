FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5)"

CMD ["uv", "run", "--frozen", "streamlit", "run", "src/streamlit/test_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
