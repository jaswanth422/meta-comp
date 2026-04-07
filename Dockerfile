FROM public.ecr.aws/docker/library/python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DEFAULT_TIMEOUT=120
WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
	&& python -m pip install -r requirements.txt

COPY pyproject.toml README.md ./
COPY support_ops_env ./support_ops_env
COPY server ./server
COPY inference.py ./inference.py
COPY openenv.yaml ./openenv.yaml

RUN python -m pip install --no-deps .

EXPOSE 7860
CMD ["uvicorn", "support_ops_env.server.app:app", "--host", "0.0.0.0", "--port", "7860"]
