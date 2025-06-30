#!/bin/bash

# Script de inicio optimizado para SyncDub MVP
# Versión mejorada con verificaciones de sistema y recursos

set -e

echo "🚀 Iniciando SyncDub MVP (Versión Optimizada)..."
echo "================================================"

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

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose no está instalado o no está disponible"
    exit 1
fi

# Verificar archivo .env
if [ ! -f .env ]; then
    log_warning "Archivo .env no encontrado, creando uno por defecto..."
    cat > .env << EOF
# Configuración SyncDub MVP
FLASK_ENV=production
SECRET_KEY=syncdub-secret-key-$(date +%s)
APP_PORT=5000

# Configuración NFS (opcional)
MEDIA_SOURCE_ENABLED=false
MEDIA_SOURCE_PATH=./video_source

# Configuración de usuario para NFS
PUID=1000
PGID=1000

# Configuración de recursos
MAX_MEMORY=4g
MAX_CPUS=2.0
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
    docker-compose down 2>/dev/null || true
    
    # Esperar un momento
    sleep 2
    
    # Verificar nuevamente
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_error "No se pudo liberar el puerto $PORT"
        log_info "Puedes cambiar el puerto editando APP_PORT en .env"
        exit 1
    fi
fi

# Verificar recursos del sistema
log_info "Verificando recursos del sistema..."

# Verificar memoria disponible
AVAILABLE_MEMORY=$(free -g | awk 'NR==2{printf "%.1f", $7}')
REQUIRED_MEMORY=2.0

if (( $(echo "$AVAILABLE_MEMORY < $REQUIRED_MEMORY" | bc -l) )); then
    log_warning "Memoria disponible: ${AVAILABLE_MEMORY}GB (recomendado: ${REQUIRED_MEMORY}GB+)"
    log_warning "El procesamiento puede ser más lento o fallar con archivos grandes"
else
    log_success "Memoria disponible: ${AVAILABLE_MEMORY}GB"
fi

# Verificar espacio en disco
AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
REQUIRED_SPACE=5

if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    log_warning "Espacio disponible: ${AVAILABLE_SPACE}GB (recomendado: ${REQUIRED_SPACE}GB+)"
else
    log_success "Espacio en disco: ${AVAILABLE_SPACE}GB"
fi

# Crear directorios necesarios
log_info "Creando directorios necesarios..."
mkdir -p uploads output models video_source
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
docker-compose down --remove-orphans 2>/dev/null || true

# Construir y ejecutar
log_info "Construyendo imagen Docker optimizada..."
docker-compose build --no-cache

log_info "Iniciando contenedores..."
docker-compose up -d

# Esperar a que el servicio esté disponible
log_info "Esperando a que el servicio esté disponible..."
TIMEOUT=60
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
    docker-compose logs --tail=20
    exit 1
fi

# Verificar estado del servicio
log_info "Verificando estado del servicio..."
HEALTH_STATUS=$(curl -s http://localhost:$PORT/api/health | grep -o '"status":"[^"]*' | cut -d'"' -f4)

if [ "$HEALTH_STATUS" = "healthy" ]; then
    log_success "Servicio iniciado correctamente"
else
    log_warning "Servicio iniciado pero con advertencias"
fi

# Mostrar información del sistema
log_info "Obteniendo información del sistema..."
curl -s http://localhost:$PORT/api/system-info | python3 -m json.tool 2>/dev/null || log_warning "No se pudo obtener información del sistema"

echo ""
echo "================================================"
log_success "🎉 SyncDub MVP iniciado exitosamente!"
echo ""
echo "📋 Información de acceso:"
echo "   🌐 URL: http://localhost:$PORT"
echo "   🔧 API Health: http://localhost:$PORT/api/health"
echo "   📊 System Info: http://localhost:$PORT/api/system-info"
echo ""
echo "📁 Configuración:"
echo "   📤 Uploads: ./uploads"
echo "   📥 Output: ./output"
echo "   🎬 Media Source: ${MEDIA_SOURCE_PATH} (${MEDIA_SOURCE_ENABLED})"
echo ""
echo "🔧 Comandos útiles:"
echo "   📋 Ver logs: docker-compose logs -f"
echo "   🔄 Reiniciar: docker-compose restart"
echo "   🛑 Detener: docker-compose down"
echo ""
log_info "¡Listo para sincronizar videos! 🎬"

