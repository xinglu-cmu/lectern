FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY lectern_worker ./lectern_worker
RUN pip install --no-cache-dir .
CMD ["lectern-worker"]
