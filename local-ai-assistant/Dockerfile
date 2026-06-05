# Phase 1: Builder - Compilation de llama-cpp-python avec CUDA
FROM nvidia/cuda:12.2.2-devel-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    build-essential \
    cmake \
    git \
    wget \
    ca-certificates \
    curl \
    clang \
    libclang-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Fix pour libcuda lors du build
RUN ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64/stubs:${LD_LIBRARY_PATH}"

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel ninja scikit-build-core
RUN pip install -r requirements.txt

ENV CMAKE_ARGS="-DLLAMA_CUBLAS=on -DGGML_CUDA=on"
ENV FORCE_CMAKE=1
RUN pip install llama-cpp-python==0.3.25 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu122 --no-cache-dir


# Phase 2: Runtime - Image finale allégée
FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04

LABEL maintainer="Local AI Assistant"
LABEL description="Assistant IA local sur LFM2.5 avec llama.cpp (Clean Architecture)"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CUDA_VISIBLE_DEVICES=0 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Installation des dépendances minimales d'exécution (python3, curl pour le healthcheck, et libgomp1 pour llama.cpp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    curl \
    nano \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copie de l'environnement virtuel compilé depuis le builder
COPY --from=builder /opt/venv /opt/venv

# Copie du code source refactoré
COPY api/ /app/api/
COPY core/ /app/core/
COPY services/ /app/services/
COPY tools/ /app/tools/
COPY bot/ /app/bot/

# Création des dossiers nécessaires
RUN mkdir -p /app/data /app/models /app/documents /app/logs

# Variables d'environnement pour que Python trouve les modules
ENV PYTHONPATH=/app

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

# Le point d'entrée FastAPI change de main.py à api/server.py
CMD ["python3", "-u", "api/server.py"]
