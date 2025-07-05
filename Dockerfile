FROM nvidia/cuda:12.2.2-base-ubuntu20.04

# Set environment variables to avoid writing .pyc files and pip caching
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    MALLOC_TRIM_THRESHOLD_=100000 \
    MALLOC_MMAP_THRESHOLD_=100000 \
    PYTHONHASHSEED=random
    
# Configuración de usuario para NFS
ARG PUID=1000
ARG PGID=1000
ENV PUID=${PUID}
ENV PGID=${PGID}

# Install Python, compilers, and utilities needed for the application
RUN apt-get update -qq && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 python3-dev python3-pip python3-venv \
    ffmpeg curl wget git gcc g++ build-essential htop procps \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Ensure 'python' points to 'python3'
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Crear usuario para NFS con UID/GID específicos
RUN groupadd -g ${PGID} appgroup && \
    useradd -u ${PUID} -g appgroup -m -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Crear directorios con permisos correctos
RUN mkdir -p /app/uploads /app/output /app/models /app/video_source && \
    chown -R appuser:appgroup /app

# Create a virtual environment to isolate dependencies
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy dependency file
COPY requirements.txt /app/

# Upgrade pip and setuptools (setuptools>=70 required for Python 3.12 compatibility)
RUN pip install --upgrade pip setuptools>=70.0.0 wheel

# Install PyTorch and other packages optimized with CUDA 12.1 support
RUN pip install torch==2.2.0+cu121 torchaudio==2.2.0+cu121 torchvision==0.17.0+cu121 --index-url https://download.pytorch.org/whl/cu121

# Install the rest of the project dependencies
RUN pip install -r requirements.txt

# Copy the application source code
COPY --chown=appuser:appgroup . /app/

# Create necessary directories
RUN mkdir -p /app/uploads /app/output /app/models /app/video_source

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:5000/api/health || exit 1

EXPOSE 5000
CMD ["python3", "app.py"]