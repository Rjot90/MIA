# Phase 1 : Foundation Image - On utilise "devel" pour avoir nvcc et compiler llama.cpp
FROM nvidia/cuda:12.2.2-devel-ubuntu22.04

LABEL maintainer="Local AI Assistant"
LABEL description="Assistant IA local sur Qwen-2.5-7B avec llama.cpp"

# ============================================================================
# CONFIGURATION SYSTÈME
# ============================================================================

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    CUDA_VISIBLE_DEVICES=0 \
    CMAKE_ARGS="-DGGML_CUDA=on" \
    FORCE_CMAKE=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH

WORKDIR /app

# ============================================================================
# INSTALLATION DÉPENDANCES SYSTÈME
# ============================================================================

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
    nano \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ============================================================================
# SETUP PYTHON ENVIRONNEMENT VIRTUEL
# ============================================================================
# Utiliser un venv évite l'erreur "Cannot uninstall pip 24.0... installed by debian"
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ============================================================================
# INSTALLATION DÉPENDANCES PYTHON
# ============================================================================

# Fix for missing libcuda.so.1 during build time
RUN ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64/stubs:${LD_LIBRARY_PATH}"

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel ninja scikit-build-core
RUN pip install -r requirements.txt
ENV CMAKE_ARGS="-DLLAMA_CUBLAS=on"
RUN pip install llama-cpp-python==0.3.25 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu122 --no-cache-dir

# ============================================================================
# COPIE CODE APPLICATION
# ============================================================================

COPY main.py .
COPY inference.py .
COPY memory.py .
COPY config.py .
COPY discord_bot.py .
COPY discord_bridge.py .
COPY discord_context.py .
COPY discord_handlers.py .
COPY rag_manager.py .
COPY ingest.py .

# ============================================================================
# CRÉATION RÉPERTOIRES POUR DONNÉES PERSISTANTES
# ============================================================================

RUN mkdir -p /app/data /app/models /app/documents /app/logs

# ============================================================================
# HEALTHCHECK
# ============================================================================

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ============================================================================
# EXPOSITION PORTS
# ============================================================================

EXPOSE 8000

# ============================================================================
# DÉMARRAGE APPLICATION
# ============================================================================

CMD ["python3", "-u", "main.py"]