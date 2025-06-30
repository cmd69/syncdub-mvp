# Dockerfile optimizado para SyncDub MVP
# Versión mejorada para manejo de memoria y recursos

FROM python:3.11-slim

# Variables de entorno para optimización
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Configuración de memoria y recursos
ENV MALLOC_TRIM_THRESHOLD_=100000
ENV MALLOC_MMAP_THRESHOLD_=100000
ENV PYTHONHASHSEED=random

# Configuración de usuario para NFS
ARG PUID=1000
ARG PGID=1000
ENV PUID=${PUID}
ENV PGID=${PGID}

# Instalar dependencias del sistema de forma optimizada
RUN apt-get update && apt-get install -y --no-install-recommends \
    # FFmpeg para procesamiento de audio/video
    ffmpeg \
    # Herramientas de sistema
    curl \
    wget \
    git \
    # Dependencias para compilación (mínimas)
    gcc \
    g++ \
    python3-dev \
    # Herramientas de monitoreo
    htop \
    procps \
    # Limpiar cache
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Crear usuario para NFS con UID/GID específicos
RUN groupadd -g ${PGID} appgroup && \
    useradd -u ${PUID} -g appgroup -m -s /bin/bash appuser

# Crear directorios de la aplicación
WORKDIR /app

# Crear directorios con permisos correctos
RUN mkdir -p /app/uploads /app/output /app/models /app/video_source && \
    chown -R appuser:appgroup /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Instalar dependencias Python de forma optimizada
RUN pip install --no-cache-dir -r requirements.txt

# Pre-descargar modelos de IA para evitar descargas durante ejecución
RUN python -c "
import whisper
import warnings
warnings.filterwarnings('ignore')
try:
    print('Downloading Whisper tiny model...')
    whisper.load_model('tiny')
    print('Whisper tiny model downloaded successfully')
except Exception as e:
    print(f'Warning: Could not download Whisper model: {e}')
"

RUN python -c "
from sentence_transformers import SentenceTransformer
import warnings
warnings.filterwarnings('ignore')
try:
    print('Downloading Sentence Transformer model...')
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print('Sentence Transformer model downloaded successfully')
except Exception as e:
    print(f'Warning: Could not download Sentence Transformer model: {e}')
"

# Copiar código de la aplicación
COPY --chown=appuser:appgroup . /app/

# Configurar permisos
RUN chmod +x /app/start.sh 2>/dev/null || true

# Cambiar a usuario no-root
USER appuser

# Configuración de salud del contenedor
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Puerto de la aplicación
EXPOSE 5000

# Comando por defecto
CMD ["python", "app.py"]

