FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-cluster.lock pyproject.toml README.md LICENSE ./
COPY src ./src
COPY integrations/distributed/worker.py ./worker.py
RUN pip install --no-cache-dir --require-hashes -r requirements-cluster.lock && pip install --no-deps .
CMD ["python", "worker.py"]
