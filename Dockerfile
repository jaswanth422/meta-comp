FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY support_ops_env ./support_ops_env
COPY server ./server
COPY inference.py ./inference.py
COPY openenv.yaml ./openenv.yaml

RUN pip install --no-cache-dir .

EXPOSE 7860
CMD ["uvicorn", "support_ops_env.server.app:app", "--host", "0.0.0.0", "--port", "7860"]
