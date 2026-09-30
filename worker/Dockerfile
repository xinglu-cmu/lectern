FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY lectern ./lectern
COPY lectern_worker ./lectern_worker
# The worker runs the same engine package as the CLI, plus the queue client.
RUN pip install --no-cache-dir ".[worker]"
CMD ["lectern-worker"]
