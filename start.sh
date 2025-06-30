#!/bin/bash

# SyncDub MVP - Script de inicio optimizado

echo "🎬 Iniciando SyncDub MVP..."

# Verificar que Docker esté instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Por favor instala Docker primero."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose no está instalado. Por favor instala Docker Compose primero."
    exit 1
fi

# Verificar archivo .env
if [ ! -f .env ]; then
    echo "📝 Creando archivo .env desde .env.example..."
    cp .env.example .env
    echo "⚠️  Por favor edita el archivo .env con tus configuraciones antes de continuar."
    echo "   Especialmente MEDIA_SOURCE_PATH para tu volumen NFS."
    read -p "Presiona Enter cuando hayas configurado .env..."
fi

# Cargar variables de entorno
source .env

# Verificar volumen de media si está configurado
if [ "$MEDIA_SOURCE_ENABLED" = "true" ] && [ -n "$MEDIA_SOURCE_PATH" ]; then
    if [ ! -d "$MEDIA_SOURCE_PATH" ]; then
        echo "⚠️  Advertencia: El directorio de media $MEDIA_SOURCE_PATH no existe."
        echo "   La aplicación funcionará solo con subida de archivos."
    else
        echo "✅ Volumen de media configurado: $MEDIA_SOURCE_PATH"
    fi
fi

# Detener contenedores existentes
echo "🛑 Deteniendo contenedores existentes..."
docker-compose down

# Construir y ejecutar
echo "🔨 Construyendo imagen Docker..."
docker-compose build

echo "🚀 Iniciando SyncDub MVP..."
docker-compose up -d

# Verificar estado
sleep 5
if docker-compose ps | grep -q "Up"; then
    echo "✅ SyncDub MVP iniciado exitosamente!"
    echo ""
    echo "🌐 Accede a la aplicación en:"
    echo "   http://localhost:${APP_PORT:-5000}"
    echo ""
    echo "📋 Comandos útiles:"
    echo "   docker-compose logs -f    # Ver logs"
    echo "   docker-compose down       # Detener"
    echo "   docker-compose restart    # Reiniciar"
    echo ""
    
    # Mostrar información del volumen
    if [ "$MEDIA_SOURCE_ENABLED" = "true" ]; then
        echo "📁 Volumen de media: $MEDIA_SOURCE_PATH"
        echo "   Los archivos en este directorio estarán disponibles para selección."
    else
        echo "📁 Solo subida de archivos habilitada."
        echo "   Para habilitar volumen de media, configura MEDIA_SOURCE_ENABLED=true en .env"
    fi
else
    echo "❌ Error al iniciar SyncDub MVP"
    echo "📋 Verifica los logs con: docker-compose logs"
    exit 1
fi
