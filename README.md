# 🎬 SyncDub MVP

**Sincronizador de pistas de audio para versiones dobladas de películas**

SyncDub MVP es una aplicación web que utiliza inteligencia artificial local para sincronizar automáticamente las pistas de audio entre versiones originales y dobladas de películas. La aplicación procesa ambos videos, transcribe los audios, empareja las frases por significado semántico y genera un archivo MKV final con ambas pistas de audio sincronizadas.

## ✨ Características Principales

- **🤖 IA Local**: Procesamiento completamente local usando Whisper y sentence-transformers
- **🌍 Multilingüe**: Soporte para múltiples idiomas con emparejamiento semántico inteligente
- **🎥 Formatos Múltiples**: Acepta MP4, AVI, MKV, MOV, WMV, FLV, WebM
- **📦 Containerizado**: Fácil despliegue con Docker
- **🔄 Procesamiento Asíncrono**: Interfaz web con indicadores de progreso en tiempo real
- **💾 Sin APIs Externas**: Todo el procesamiento se realiza localmente

## 🚀 Inicio Rápido

### Prerrequisitos

- Docker y Docker Compose instalados
- Al menos 4GB de RAM disponible
- Espacio en disco suficiente para los videos y modelos de IA

### Instalación

1. **Clonar o descargar el proyecto**
   ```bash
   # Si tienes git instalado
   git clone <repository-url>
   cd syncdub-mvp
   
   # O simplemente descomprime el archivo ZIP
   ```

2. **Ejecutar la aplicación**
   ```bash
   # Método 1: Usar el script de inicio (recomendado)
   ./start.sh
   
   # Método 2: Usar Docker Compose directamente
   docker-compose up --build -d
   ```

3. **Acceder a la aplicación**
   - Abrir navegador en: http://localhost:5000
   - La primera ejecución puede tardar más tiempo debido a la descarga de modelos de IA

## 📖 Cómo Usar

### Paso 1: Subir Videos
1. Ve a la página "Subir Videos"
2. Selecciona el video original (versión en idioma original)
3. Selecciona el video doblado (versión doblada)
4. Haz clic en "Iniciar Sincronización"

### Paso 2: Monitorear Progreso
- La aplicación mostrará el progreso en tiempo real
- El procesamiento incluye:
  - Extracción de audio
  - Transcripción con Whisper
  - Emparejamiento semántico
  - Aplicación de sincronización

### Paso 3: Descargar Resultado
- Una vez completado, descarga el archivo MKV resultante
- El archivo incluye el video original con ambas pistas de audio sincronizadas

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Procesamiento │
│   (HTML/CSS/JS) │◄──►│   (Flask)       │◄──►│   (IA Local)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Almacenamiento│
                       │   (Volúmenes)   │
                       └─────────────────┘
```

### Componentes Principales

- **Frontend**: Interfaz web responsiva con Bootstrap
- **Backend**: API REST con Flask
- **Procesamiento IA**: Whisper + Sentence Transformers
- **Procesamiento Audio**: FFmpeg + PyDub
- **Containerización**: Docker + Docker Compose

## 🔧 Configuración Avanzada

### Variables de Entorno

```bash
# En docker-compose.yml o archivo .env
FLASK_ENV=production
SECRET_KEY=tu-clave-secreta
WHISPER_MODEL=base  # tiny, base, small, medium, large
SIMILARITY_THRESHOLD=0.7
MAX_TIME_DRIFT=10.0
```

### Modelos de IA Disponibles

**Whisper Models:**
- `tiny`: Más rápido, menos preciso (~39 MB)
- `base`: Balance entre velocidad y precisión (~74 MB) - **Por defecto**
- `small`: Mejor precisión (~244 MB)
- `medium`: Alta precisión (~769 MB)
- `large`: Máxima precisión (~1550 MB)

### Personalización de Umbrales

```python
# En config.py
SIMILARITY_THRESHOLD = 0.7  # Umbral para considerar frases similares (0.0-1.0)
MAX_TIME_DRIFT = 10.0      # Máximo desfase permitido en segundos
```

## 🛠️ Comandos Útiles

```bash
# Ver logs de la aplicación
docker logs syncdub-mvp

# Detener la aplicación
docker-compose down

# Reiniciar la aplicación
docker-compose restart

# Reconstruir la imagen
docker-compose build --no-cache

# Ver contenedores en ejecución
docker ps

# Ver nombre, estado y puertos de contenedores
docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"

# Limpiar archivos temporales
docker-compose down -v
```

## 📁 Estructura del Proyecto

```
syncdub-mvp/
├── app/                    # Código de la aplicación
│   ├── services/          # Lógica de negocio
│   ├── utils/             # Utilidades
│   ├── main.py            # Blueprint principal
│   └── api.py             # API REST
├── static/                # Archivos estáticos
│   ├── css/              # Estilos CSS
│   └── js/               # JavaScript
├── templates/             # Plantillas HTML
├── uploads/               # Archivos subidos (volumen)
├── output/                # Archivos generados (volumen)
├── models/                # Modelos de IA (volumen)
├── config.py              # Configuración
├── app.py                 # Aplicación principal
├── requirements.txt       # Dependencias Python
├── Dockerfile            # Imagen Docker
├── docker-compose.yml    # Orquestación
└── start.sh              # Script de inicio
```

## 🔍 Solución de Problemas

### Problemas Comunes

**Error: "No se puede conectar al puerto 5000"**
- Verifica que Docker esté ejecutándose
- Asegúrate de que el puerto 5000 no esté en uso
- Ejecuta: `docker-compose logs` para ver errores

**Error: "Memoria insuficiente"**
- Los modelos de IA requieren RAM significativa
- Considera usar el modelo `tiny` de Whisper
- Cierra otras aplicaciones que consuman memoria

**Error: "Formato de archivo no soportado"**
- Verifica que los archivos sean videos válidos
- Formatos soportados: MP4, AVI, MKV, MOV, WMV, FLV, WebM
- Intenta convertir el archivo con FFmpeg

**Procesamiento muy lento**
- El tiempo depende del tamaño del video y hardware
- Considera usar un modelo Whisper más pequeño
- Videos de 2 horas pueden tardar 10-30 minutos

### Logs y Depuración

```bash
# Ver logs detallados
docker-compose logs -f syncdub-app

# Acceder al contenedor para depuración
docker exec -it syncdub-mvp bash

# Ver uso de recursos
docker stats syncdub-mvp
```

## 🚧 Limitaciones Actuales

- **Tamaño de archivo**: Máximo 2GB por video
- **Formatos de salida**: Solo MKV
- **Procesamiento**: Secuencial (un video a la vez)
- **Persistencia**: Las tareas no persisten entre reinicios
- **Interfaz**: Solo web (no CLI independiente)

## 🔮 Mejoras Futuras (Roadmap)

### Versión 1.1
- [ ] Sincronización dinámica (DTW) para drift progresivo
- [ ] Interfaz de corrección manual
- [ ] Previsualización de audio sincronizado
- [ ] Soporte para múltiples pistas (3+ idiomas)

### Versión 1.2
- [ ] Procesamiento por lotes (series completas)
- [ ] Historial de trabajos
- [ ] API REST completa
- [ ] Integración con Jellyfin/Plex

### Versión 2.0
- [ ] Detección automática de idioma
- [ ] Diarización y reconocimiento de hablantes
- [ ] Generación automática de subtítulos
- [ ] Interfaz de administración

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Para cambios importantes:

1. Abre un issue para discutir el cambio
2. Fork el repositorio
3. Crea una rama para tu feature
4. Realiza los cambios con tests
5. Envía un pull request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## 🙏 Reconocimientos

- **OpenAI Whisper**: Transcripción de audio
- **Sentence Transformers**: Embeddings semánticos
- **FFmpeg**: Procesamiento de video/audio
- **Flask**: Framework web
- **Bootstrap**: Framework CSS

## 📞 Soporte

Para reportar bugs o solicitar features:
- Abre un issue en el repositorio
- Incluye logs relevantes y pasos para reproducir
- Especifica tu sistema operativo y versión de Docker

---

**¡Disfruta sincronizando tus películas con SyncDub MVP! 🎬✨**

