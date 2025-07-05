#!/bin/bash

# Script de inicio optimizado para SyncDub MVP
# Versión GPU con soporte completo para variables de entorno

set -e

echo "🚀 Iniciando SyncDub MVP (Versión GPU Optimizada)..."
echo "=================================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para logging con colores
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar si Docker está disponible
if ! command -v docker &> /dev/null; then
    log_error "Docker no está instalado o no está disponible"
    exit 1
fi

# Verificar Docker Compose (tanto docker-compose como docker compose)
DOCKER_COMPOSE_CMD=""
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    log_error "Docker Compose no está instalado o no está disponible"
    log_info "Instala docker-compose o usa Docker con plugin compose"
    exit 1
fi

log_success "Usando comando: $DOCKER_COMPOSE_CMD"

# Verificar archivo .env
if [ ! -f .env ]; then
    log_warning "Archivo .env no encontrado, creando uno por defecto..."
    cat > .env << EOF
# Configuración SyncDub MVP - GPU Optimizada
FLASK_ENV=production
SECRET_KEY=syncdub-secret-key-$(date +%s)
APP_PORT=5000

# Configuración de directorios
UPLOADS_DIR=./uploads
OUTPUT_DIR=./output
MODELS_DIR=./models

# Configuración NFS (opcional)
MEDIA_SOURCE_ENABLED=false
MEDIA_SOURCE_PATH=./video_source

# Configuración de usuario para NFS
PUID=1000
PGID=1000

# Configuración de recursos GPU
MAX_MEMORY=8G
MAX_CPUS=4.0
RESERVED_MEMORY=2G
RESERVED_CPUS=1.0

# Configuración GPU
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Configuración de modelos IA
WHISPER_MODEL=base
SENTENCE_TRANSFORMER_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# Configuración de archivos
MAX_CONTENT_LENGTH=21474836480
ALLOWED_EXTENSIONS=mp4,avi,mkv,mov,wmv,flv,webm

# Configuración Docker
CONTAINER_NAME=syncdub-mvp
NETWORK_NAME=syncdub-network
RESTART_POLICY=unless-stopped
EOF
    log_success "Archivo .env creado con configuración por defecto"
fi

# Cargar variables de entorno
source .env

# Verificar puerto disponible
PORT=${APP_PORT:-5000}
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "Puerto $PORT está ocupado, intentando liberar..."
    
    # Intentar detener contenedor existente
    $DOCKER_COMPOSE_CMD down 2>/dev/null || true
    
    # Esperar un momento
    sleep 2
    
    # Verificar nuevamente
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_error "No se pudo liberar el puerto $PORT"
        log_info "Puedes cambiar el puerto editando APP_PORT en .env"
        exit 1
    fi
fi

# Verificar soporte GPU
log_info "Verificando soporte GPU..."
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null || echo "Error")
    if [ "$GPU_INFO" != "Error" ]; then
        log_success "GPU detectada: $GPU_INFO"
    else
        log_warning "nvidia-smi disponible pero no se puede acceder a GPU"
    fi
else
    log_warning "nvidia-smi no encontrado - verificar instalación de drivers NVIDIA"
fi

# Verificar Docker con soporte GPU
if docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi &>/dev/null; then
    log_success "Docker con soporte GPU verificado"
else
    log_warning "Docker no tiene acceso a GPU - verificar nvidia-container-toolkit"
fi

# Verificar recursos del sistema
log_info "Verificando recursos del sistema..."

# Verificar memoria disponible
AVAILABLE_MEMORY=$(free -g | awk 'NR==2{printf "%.1f", $7}')
REQUIRED_MEMORY=4.0

if (( $(echo "$AVAILABLE_MEMORY < $REQUIRED_MEMORY" | bc -l) )); then
    log_warning "Memoria disponible: ${AVAILABLE_MEMORY}GB (recomendado: ${REQUIRED_MEMORY}GB+)"
    log_warning "El procesamiento puede ser más lento o fallar con archivos grandes"
else
    log_success "Memoria disponible: ${AVAILABLE_MEMORY}GB"
fi

# Verificar espacio en disco
AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
REQUIRED_SPACE=10

if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    log_warning "Espacio disponible: ${AVAILABLE_SPACE}GB (recomendado: ${REQUIRED_SPACE}GB+)"
else
    log_success "Espacio en disco: ${AVAILABLE_SPACE}GB"
fi

# Crear directorios necesarios
log_info "Creando directorios necesarios..."
mkdir -p "${UPLOADS_DIR:-./uploads}" "${OUTPUT_DIR:-./output}" "${MODELS_DIR:-./models}" "${MEDIA_SOURCE_PATH:-./video_source}"
log_success "Directorios creados"

# Verificar configuración NFS si está habilitada
if [ "${MEDIA_SOURCE_ENABLED}" = "true" ]; then
    log_info "Verificando configuración NFS..."
    
    if [ ! -d "${MEDIA_SOURCE_PATH}" ]; then
        log_warning "Directorio NFS no encontrado: ${MEDIA_SOURCE_PATH}"
        log_info "Creando directorio local como fallback..."
        mkdir -p "${MEDIA_SOURCE_PATH}"
    else
        log_success "Directorio NFS encontrado: ${MEDIA_SOURCE_PATH}"
    fi
    
    # Verificar permisos
    if [ -w "${MEDIA_SOURCE_PATH}" ]; then
        log_success "Permisos de escritura verificados"
    else
        log_warning "Sin permisos de escritura en ${MEDIA_SOURCE_PATH}"
    fi
fi

# Limpiar contenedores y volúmenes anteriores si existen
log_info "Limpiando instalación anterior..."
$DOCKER_COMPOSE_CMD down --remove-orphans 2>/dev/null || true

# Construir y ejecutar
log_info "Construyendo imagen Docker optimizada..."
$DOCKER_COMPOSE_CMD build --no-cache

log_info "Iniciando contenedores..."
$DOCKER_COMPOSE_CMD up -d

# Esperar a que el servicio esté disponible
log_info "Esperando a que el servicio esté disponible..."
TIMEOUT=120
COUNTER=0

while [ $COUNTER -lt $TIMEOUT ]; do
    if curl -f http://localhost:$PORT/api/health >/dev/null 2>&1; then
        break
    fi
    
    sleep 2
    COUNTER=$((COUNTER + 2))
    
    if [ $((COUNTER % 10)) -eq 0 ]; then
        log_info "Esperando... (${COUNTER}s/${TIMEOUT}s)"
    fi
done

if [ $COUNTER -ge $TIMEOUT ]; then
    log_error "Timeout esperando a que el servicio esté disponible"
    log_info "Verificando logs..."
    $DOCKER_COMPOSE_CMD logs --tail=20
    exit 1
fi

# Verificar estado del servicio
log_info "Verificando estado del servicio..."
HEALTH_STATUS=$(curl -s http://localhost:$PORT/api/health | grep -o '"status":"[^"]*' | cut -d'"' -f4 2>/dev/null || echo "unknown")

if [ "$HEALTH_STATUS" = "healthy" ]; then
    log_success "Servicio iniciado correctamente"
else
    log_warning "Servicio iniciado pero con advertencias (status: $HEALTH_STATUS)"
fi

# Mostrar información del sistema
log_info "Obteniendo información del sistema..."
curl -s http://localhost:$PORT/api/system-info | python3 -m json.tool 2>/dev/null || log_warning "No se pudo obtener información del sistema"

echo ""
echo "=================================================="
log_success "🎉 SyncDub MVP iniciado exitosamente!"
echo ""
echo "📋 Información de acceso:"
echo "   🌐 URL: http://localhost:$PORT"
echo "   🔧 API Health: http://localhost:$PORT/api/health"
echo "   📊 System Info: http://localhost:$PORT/api/system-info"
echo ""
echo "📁 Configuración:"
echo "   📤 Uploads: ${UPLOADS_DIR:-./uploads}"
echo "   📥 Output: ${OUTPUT_DIR:-./output}"
echo "   🎬 Media Source: ${MEDIA_SOURCE_PATH} (${MEDIA_SOURCE_ENABLED})"
echo "   🧠 Modelos: ${MODELS_DIR:-./models}"
echo ""
echo "⚙️ Recursos:"
echo "   💾 Memoria: ${MAX_MEMORY:-8G} (reservado: ${RESERVED_MEMORY:-2G})"
echo "   🖥️  CPU: ${MAX_CPUS:-4.0} (reservado: ${RESERVED_CPUS:-1.0})"
echo "   🎮 GPU: ${NVIDIA_VISIBLE_DEVICES:-all}"
echo ""
echo "🔧 Comandos útiles:"
echo "   📋 Ver logs: $DOCKER_COMPOSE_CMD logs -f"
echo "   🔄 Reiniciar: $DOCKER_COMPOSE_CMD restart"
echo "   🛑 Detener: $DOCKER_COMPOSE_CMD down"
echo "   📊 Estado GPU: docker exec ${CONTAINER_NAME:-syncdub-mvp} nvidia-smi"
echo ""
log_info "¡Listo para sincronizar videos con aceleración GPU! 🎬🚀"

