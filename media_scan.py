import os
import re
from typing import List, Dict, Optional
from config import DOWNLOADS_DIRS, MEDIA_DIRS
from tmdbv3api import TMDb, Movie, TV

# Extensiones de vídeo aceptadas
VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}

_tmdb = None
_movie = None
_tv = None

def get_tmdb_english_title_year(title: str, year: Optional[int] = None):
    """
    Busca en TMDB el nombre en inglés y el año oficial de una película o serie.
    Devuelve (titulo_en_ingles, año_oficial, tipo) o (None, None, None) si no encuentra.
    """
    # global _tmdb, _movie, _tv
    # if _tmdb is None:
    #     _tmdb = TMDb()
    #     _tmdb.api_key = os.environ.get('TMDB_API_KEY')
    #     _movie = Movie()
    #     _tv = TV()
    # # Primero busca como película
    # results = _movie.search(title)
    # for r in results:
    #     # Solo procesa si r tiene los atributos esperados
    #     if not hasattr(r, 'original_title') or not hasattr(r, 'release_date'):
    #         continue
    #     if year and r.release_date:
    #         if str(year) not in r.release_date:
    #             continue
    #     # Coincidencia aceptable
    #     return getattr(r, 'original_title', None), int(r.release_date[:4]) if r.release_date else None, 'movie'
    # # Si no, busca como serie
    # results = _tv.search(title)
    # for r in results:
    #     if not hasattr(r, 'original_name') or not hasattr(r, 'first_air_date'):
    #         continue
    #     if year and r.first_air_date:
    #         if str(year) not in r.first_air_date:
    #             continue
    #     return getattr(r, 'original_name', None), int(r.first_air_date[:4]) if r.first_air_date else None, 'series'
    return None, None, None

def extract_quality_codec(filename: str):
    """
    Extrae calidad (1080p, 2160p, 720p, etc.) y codec (x264, x265, h264, hevc, etc.) del nombre del archivo.
    """
    # Calidad
    quality_match = re.search(r'(2160p|1080p|720p|480p|4K|8K)', filename, re.IGNORECASE)
    quality = quality_match.group(1) if quality_match else None
    # Codec
    codec_match = re.search(r'(x265|x264|h265|h264|hevc|avc)', filename, re.IGNORECASE)
    codec = codec_match.group(1) if codec_match else None
    return quality, codec

def extract_title_year(filename: str):
    """
    Extrae título y año del nombre del archivo usando regex.
    Devuelve (titulo, año) o (titulo, None) si no hay año.
    """
    # Busca año (19xx o 20xx)
    m = re.search(r'^(.*?)[. _\-]*(19\d{2}|20\d{2})', filename)
    if m:
        title = m.group(1).replace('.', ' ').replace('_', ' ').strip()
        year = int(m.group(2))
    else:
        title = os.path.splitext(filename)[0].replace('.', ' ').replace('_', ' ').strip()
        year = None
    return title, year

def scan_video_files(downloads_dirs: list, media_dirs: list) -> list:
    """
    Escanea recursivamente los directorios de descargas y media, devolviendo una lista de archivos de vídeo con metadatos básicos.
    """
    results = []
    for base_dir, location in [
        (downloads_dirs, 'downloads'),
        (media_dirs, 'media'),
    ]:
        for root_dir in base_dir:
            for dirpath, _, filenames in os.walk(root_dir):
                for fname in filenames:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in VIDEO_EXTENSIONS:
                        continue
                    fpath = os.path.join(dirpath, fname)
                    try:
                        stat = os.stat(fpath)
                    except Exception:
                        continue  # Ignora archivos inaccesibles
                    size_mb = round(stat.st_size / (1024 * 1024), 1)
                    results.append({
                        'path': fpath,
                        'name': fname,
                        'inode': stat.st_ino,
                        'size_mb': size_mb,
                        'location': location,
                    })
    return results

# Mock de formateo de títulos usando Ollama (simulado)
def format_title_ollama_mock(filename: str) -> dict:
    """
    Simula una petición a Ollama para formatear el nombre del archivo.
    Devuelve un dict con 'title', 'year', 'type' ('movie' o 'series').
    """
    # Regex simple para extraer título y año
    m = re.search(r'^(.*?)[. _\-]*(19\d{2}|20\d{2})', filename)
    if m:
        title = m.group(1).replace('.', ' ').replace('_', ' ').strip()
        year = int(m.group(2))
        # Heurística simple: si contiene 'S0' o 'E0' es serie
        if re.search(r'[Ss]\d{1,2}[Ee]\d{1,2}', filename):
            ttype = 'series'
        else:
            ttype = 'movie'
    else:
        title = os.path.splitext(filename)[0].replace('.', ' ').replace('_', ' ').strip()
        year = None
        ttype = 'unknown'
    return {'title': title, 'year': year, 'type': ttype}

# Mock de traducción de títulos a inglés usando TMDB/IMDB (no hace nada por ahora)
def translate_title_to_english_mock(title: str) -> str:
    """
    Simula la traducción de un título a inglés. Por ahora, retorna el título tal cual.
    """
    return title

def mark_imported_files(files: list) -> list:
    """
    Dada la lista de archivos (output de scan_media_dirs), devuelve la lista de archivos de descargas
    con un campo 'imported' (True/False) según si su inodo está presente en media.
    """
    downloads = [f for f in files if f['location'] == 'downloads']
    media_inodes = {f['inode'] for f in files if f['location'] == 'media'}
    for f in downloads:
        f['imported'] = f['inode'] in media_inodes
    return downloads

def group_by_clean_name(downloads: list) -> dict:
    """
    Agrupa archivos por clean_name y tmdb_type.
    Devuelve un dict: {(tmdb_type, clean_name): [archivos]}
    """
    groups = {}
    for f in downloads:
        key = (f.get('tmdb_type') or 'unknown', f['clean_name'])
        groups.setdefault(key, []).append(f)
    return groups 

def build_downloads_structure(downloads_dirs, media_dirs):
    """
    Escanea archivos, aplica formateo mock y agrupa por título y tipo (película/serie),
    cada grupo contiene todas las versiones encontradas (agrupadas por inodo).
    """
    files = scan_video_files(downloads_dirs, media_dirs)
    # Aplica formateo mock a cada archivo
    for f in files:
        fmt = format_title_ollama_mock(f['name'])
        f['title'] = fmt['title']
        f['year'] = fmt['year']
        f['type'] = fmt['type']
    # Agrupa por (type, title, year)
    groups = {}
    for f in files:
        key = (f['type'], f['title'], f['year'])
        if key not in groups:
            groups[key] = []
        groups[key].append(f)
    # Dentro de cada grupo, agrupa por inodo (versiones)
    downloads = []
    for (ttype, title, year), files_in_group in groups.items():
        # Agrupa por inodo
        versions = {}
        for f in files_in_group:
            inode = f['inode']
            if inode not in versions:
                versions[inode] = []
            versions[inode].append(f)
        downloads.append({
            'type': ttype,
            'title': title,
            'year': year,
            'versions': list(versions.values())  # cada versión es una lista de archivos con el mismo inodo
        })
    return downloads 