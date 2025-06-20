#!/bin/bash

# SyncDub MVP - Script de inicio
echo "🎬 SyncDub MVP - Iniciando aplicación..."

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Por favor instala Docker primero."
    exit 1
fi

# Verificar si Docker Compose está disponible
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose no está disponible. Por favor instala Docker Compose."
    exit 1
fi

# Crear directorios si no existen
mkdir -p uploads output models

# Construir y ejecutar con Docker Compose
echo "🔨 Construyendo imagen Docker..."
if command -v docker-compose &> /dev/null; then
    docker-compose build
    echo "🚀 Iniciando SyncDub MVP..."
    docker-compose up -d
else
    docker compose build
    echo "🚀 Iniciando SyncDub MVP..."
    docker compose up -d
fi

# Verificar que el contenedor esté ejecutándose
sleep 5
if docker ps | grep -q syncdub-mvp; then
    echo "✅ SyncDub MVP está ejecutándose correctamente!"
    echo "🌐 Accede a la aplicación en: http://localhost:5000"
    echo ""
    echo "📋 Comandos útiles:"
    echo "   Ver logs: docker logs syncdub-mvp"
    echo "   Detener: docker-compose down"
    echo "   Reiniciar: docker-compose restart"
else
    echo "❌ Error al iniciar SyncDub MVP"
    echo "📋 Verifica los logs con: docker logs syncdub-mvp"
    exit 1
fi

