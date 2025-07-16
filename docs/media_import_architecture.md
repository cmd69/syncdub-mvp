# Media Import & Management - Arquitectura y Funcionalidad

## Objetivo

Centralizar y visualizar el estado de los archivos multimedia descargados (películas y series), agrupando versiones por título, idioma y calidad, y detectar si han sido importados a la librería principal (gestionada por Sonarr/Radarr) mediante hardlinks. Permitir la gestión eficiente de duplicados y variantes.

---

## Funcionalidad principal

### 1. Escaneo de directorios
- **Rutas configurables**: Todas las rutas de descargas y media se definen en `.env` y `config.py`.
- **Escaneo recursivo** de:
  - Descargas: `downloads/completed/movies`, `peliculas`, `series`, `tv`
  - Media: `movies`, `peliculas`, `series`, `tv`
- **Filtrado** por extensiones de vídeo habituales.

### 2. Extracción y normalización de metadatos
- **Parsing inicial**: Regex para extraer título y año del nombre del archivo.
- **Consulta a TMDB**:
  - Se busca el título y año en TMDB para obtener el nombre en inglés y el año oficial.
  - Si el archivo está en castellano, se traduce y normaliza el nombre.
  - Si está en inglés, se estandariza igualmente.
- **Campos clave por archivo**:
  - `original_title`: Título extraído del archivo
  - `year`: Año extraído
  - `clean_name`: `"NombreEnIngles (Año)"` (para agrupación y visualización)
  - `tmdb_type`: 'movie', 'series' o 'unknown'
  - Otros: tamaño, calidad, codec, inodo, ruta, etc.

### 3. Detección de importación
- **Comparación por inodo**:
  - Si un archivo en descargas tiene el mismo inodo que uno en media, está importado (hardlink Sonarr/Radarr).
  - Se marca cada archivo con `imported: True/False`.

### 4. Agrupación y visualización
- **Agrupación por**: `clean_name` y `tmdb_type`.
- **Visualización web**:
  - Tabla Bootstrap agrupada por título (en inglés y año).
  - Estado de importación resaltado.
  - Detalles de cada versión (idioma, calidad, codec, ruta).

### 5. Logging y trazabilidad
- Se añaden logs en las rutas API/web para depuración y auditoría.

---

## Peculiaridades y retos

- **Nombres en varios idiomas**: Necesidad de traducir y normalizar para agrupar correctamente.
- **Hardlinks**: Uso de inodos para detectar importación real, no solo por nombre.
- **Versiones y duplicados**: Detección de variantes innecesarias para limpieza manual.
- **Configurabilidad**: Todas las rutas y claves API se gestionan por configuración.
- **Integración con TMDB**: Puede haber falsos positivos/negativos si el parsing es ambiguo.
- **Escalabilidad**: El escaneo y las consultas a TMDB pueden ser costosos en grandes librerías.

---

## Arquitectura y aplicaciones implicadas

```mermaid
graph TD;
    subgraph NFS
        A[Almacenamiento NFS: /mnt/nfs/media]
    end
    subgraph Descargas
        B[Descargas (qBittorrent, etc.)]
    end
    subgraph Gestores
        C[Sonarr/Radarr]
    end
    subgraph App
        D[SyncDub MVP (Flask)]
    end
    subgraph Externos
        E[TMDB API]
    end

    B --> A
    C --> A
    D --> A
    D --> E
    C -. crea hardlinks .-> A
    D -. consulta inodos .-> A
```

### Componentes principales
- **NFS**: Almacenamiento central de media y descargas.
- **Descargadores**: qBittorrent, etc. descargan a carpetas de descargas.
- **Sonarr/Radarr**: Importan y renombran, creando hardlinks en media.
- **SyncDub MVP (Flask)**: Escanea, agrupa, consulta TMDB y visualiza el estado.
- **TMDB API**: Fuente de metadatos y traducciones.

---

## Futuras ampliaciones
- Integración con Ollama para parsing avanzado de nombres.
- Sugerencias automáticas de limpieza de duplicados.
- Filtros y búsqueda avanzada en la web.
- Notificaciones o acciones automáticas (opcional).

---

## Resumen visual
- Todo el flujo es **configurable** y **modular**.
- El agrupamiento por nombre en inglés y año permite gestión multi-idioma y multi-versión.
- El uso de inodos garantiza detección fiable de importación.
- La arquitectura es extensible para nuevas fuentes, reglas y visualizaciones. 