# SyncDub MVP - Dockerfile
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Descargar modelos de IA (opcional, se pueden descargar en runtime)
RUN python -c "import whisper; whisper.load_model('base')" || echo "Whisper model will be downloaded on first use"
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')" || echo "Sentence transformer model will be downloaded on first use"

# Copiar código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p uploads output models

# Configurar permisos
RUN chmod +x app.py

# Exponer puerto
EXPOSE 5000

# Variables de entorno
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Comando de inicio
CMD ["python", "app.py"]

