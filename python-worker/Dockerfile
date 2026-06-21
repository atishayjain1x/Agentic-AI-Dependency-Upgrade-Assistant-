# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12
ARG OSV_SCANNER_VERSION=v1.9.2

FROM python:${PYTHON_VERSION}-slim-bookworm AS python-builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


FROM debian:bookworm-slim AS osv-scanner

ARG OSV_SCANNER_VERSION
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && case "${TARGETARCH}" in \
         amd64) OSV_ARCH=amd64 ;; \
         arm64) OSV_ARCH=arm64 ;; \
         *) echo "unsupported architecture: ${TARGETARCH}" && exit 1 ;; \
       esac \
    && curl -fsSL "https://github.com/google/osv-scanner/releases/download/${OSV_SCANNER_VERSION}/osv-scanner_linux_${OSV_ARCH}" \
         -o /usr/local/bin/osv-scanner \
    && chmod +x /usr/local/bin/osv-scanner


FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PATH="/home/worker/.local/bin:${PATH}" \
    WORKER_HOST=0.0.0.0 \
    WORKER_PORT=8123

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        openjdk-17-jdk-headless \
        maven \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --system --uid 10001 worker

COPY --from=python-builder /install /home/worker/.local
COPY --from=osv-scanner /usr/local/bin/osv-scanner /usr/local/bin/osv-scanner

COPY app ./app
COPY rag-docs ./rag-docs

RUN mkdir -p /app/data \
    && chown -R worker:worker /app /home/worker/.local

USER worker

EXPOSE 8123

CMD ["sh", "-c", "uvicorn app.main:app --host ${WORKER_HOST} --port ${WORKER_PORT}"]
