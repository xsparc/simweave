FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SIMWEAVE_DB=/data/runs.sqlite3
WORKDIR /app
COPY pyproject.toml README.md LICENSE requirements.lock ./
COPY src ./src
RUN pip install --no-cache-dir --require-hashes -r requirements.lock && \
    pip install --no-cache-dir --no-deps . && \
    useradd --uid 10001 --create-home simweave && \
    mkdir /data && chown simweave:simweave /data
USER simweave
EXPOSE 8000
CMD ["simweave", "serve", "--host", "0.0.0.0"]
