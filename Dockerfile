# SyncDub MVP - Dockerfile with full AI support
FROM python:3.11-slim

# Permitir personalizar UID/GID
ARG PUID=1000
ARG PGID=1000

# Instalar dependencias del sistema incluyendo FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Crear grupo y usuario con UID/GID configurables
RUN groupadd -g ${PGID} appgroup && \
    useradd -u ${PUID} -g ${PGID} -m appuser

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-descargar modelos de IA (opcional, se pueden descargar en runtime)
RUN python -c "import whisper; whisper.load_model('base')" || echo "Whisper model will be downloaded on first use"
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')" || echo "Sentence transformer model will be downloaded on first use"

# Copiar el código de la aplicación
COPY . .

# Crear directorios necesarios y ajustar permisos
RUN mkdir -p uploads output models media && \
    chown -R appuser:appgroup /app

# Exponer puerto
EXPOSE 5000

# Variables de entorno
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Cambiar a usuario no root
USER appuser

# Comando de inicio
CMD ["python", "app.py"]
