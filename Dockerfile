# =========================
# Stage 0: Builder
# =========================
FROM nvidia/cuda:12.2.2-base-ubuntu20.04 AS builder

# Set environment variables to avoid writing .pyc files and pip caching
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install Python, compilers, and utilities needed to build dependencies
RUN apt-get update -qq && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 python3-dev python3-pip python3-venv \
    ffmpeg curl wget git gcc g++ build-essential htop procps \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Ensure 'python' points to 'python3'
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Set working directory
WORKDIR /app

# Create a virtual environment to isolate dependencies
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy dependency file
COPY requirements.txt /app/
# Upgrade pip and setuptools (setuptools>=70 required for Python 3.12 compatibility)
RUN pip install --upgrade pip setuptools>=70.0.0 wheel
# Install PyTorch and other packages optimized with CUDA 12.1 support (modify as needed)
RUN pip install torch==2.2.0+cu121 torchaudio==2.2.0+cu121 torchvision==0.17.0+cu121 --index-url https://download.pytorch.org/whl/cu121
# Install the rest of the project dependencies
RUN pip install -r requirements.txt

# =========================
# Stage 1: Runtime
# =========================
FROM nvidia/cuda:12.2.2-base-ubuntu20.04

ARG PUID=1000
ARG PGID=1000

ENV PUID=${PUID} \
    PGID=${PGID} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MALLOC_TRIM_THRESHOLD_=100000 \
    MALLOC_MMAP_THRESHOLD_=100000 \
    PYTHONHASHSEED=random

# Forzar modo no interactivo para evitar prompts durante instalación (por ejemplo, zona horaria)
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Instala solo las dependencias necesarias para ejecutar la aplicación (runtime mínimo)
RUN apt-get update -qq && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 python3-venv ffmpeg curl wget git htop procps \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Asegura que 'python' apunte a 'python3'
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Crear grupo y usuario
RUN if getent group ${PGID}; then \
        groupmod -n appgroup $(getent group ${PGID} | cut -d: -f1); \
    else \
        groupadd -g ${PGID} appgroup; \
    fi && \
    if getent passwd ${PUID}; then \
        usermod -l appuser -g appgroup -s /bin/bash $(getent passwd ${PUID} | cut -d: -f1); \
    else \
        useradd -u ${PUID} -g appgroup -m -s /bin/bash appuser; \
    fi

# Define el directorio de trabajo
WORKDIR /app

# Copia las dependencias instaladas en el entorno virtual desde la etapa builder
COPY --from=builder /app/venv/lib/python3.12/site-packages /usr/local/lib/python3.12/dist-packages
COPY --from=builder /app/venv/bin /usr/local/bin

# Copia el código fuente de la aplicación al contenedor
COPY . /app/

# Crea los directorios necesarios y ajusta permisos para el usuario no-root
RUN mkdir -p /app/uploads /app/output /app/models /app/video_source \
    && chown -R ${PUID}:${PGID} /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:5000/api/health || exit 1

EXPOSE 5000
CMD ["python3", "app.py"]
