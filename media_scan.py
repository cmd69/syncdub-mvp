import os
import re
from typing import List, Dict
from config import DOWNLOADS_DIRS, MEDIA_DIRS
from tmdbv3api import TMDb, Movie, TV

# Extensiones de vídeo aceptadas
VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}

_tmdb = None
_movie = None
_tv = None

def get_tmdb_english_title_year(title: str, year: int = None):
    """
    Busca en TMDB el nombre en inglés y el año oficial de una película o serie.
    Devuelve (titulo_en_ingles, año_oficial, tipo) o (None, None, None) si no encuentra.
    """
    global _tmdb, _movie, _tv
    if _tmdb is None:
        _tmdb = TMDb()
        _tmdb.api_key = os.environ.get('TMDB_API_KEY')
        _movie = Movie()
        _tv = TV()
    # Primero busca como película
    results = _movie.search(title)
    for r in results:
        if year and hasattr(r, 'release_date') and r.release_date:
            if str(year) not in r.release_date:
                continue
        # Coincidencia aceptable
        return getattr(r, 'original_title', None), int(r.release_date[:4]) if r.release_date else None, 'movie'
    # Si no, busca como serie
    results = _tv.search(title)
    for r in results:
        if year and hasattr(r, 'first_air_date') and r.first_air_date:
            if str(year) not in r.first_air_date:
                continue
        return getattr(r, 'original_name', None), int(r.first_air_date[:4]) if r.first_air_date else None, 'series'
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

def scan_media_dirs(downloads_dirs: list, media_dirs: list) -> list:
    """
    Escanea los directorios de descargas y media, devolviendo una lista de archivos de vídeo con metadatos relevantes.
    Añade los campos: original_title, year, clean_name (por ahora igual a original_title + año).
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
                    quality, codec = extract_quality_codec(fname)
                    original_title, year = extract_title_year(fname)
                    # Consulta TMDB para obtener el nombre en inglés y año oficial
                    tmdb_title, tmdb_year, tmdb_type = get_tmdb_english_title_year(original_title, year)
                    if tmdb_title:
                        if tmdb_year:
                            clean_name = f"{tmdb_title} ({tmdb_year})"
                        else:
                            clean_name = tmdb_title
                    else:
                        if year:
                            clean_name = f"{original_title} ({year})"
                        else:
                            clean_name = original_title
                    results.append({
                        'path': fpath,
                        'name': fname,
                        'inode': stat.st_ino,
                        'size_mb': size_mb,
                        'location': location,
                        'quality': quality,
                        'codec': codec,
                        'original_title': original_title,
                        'year': year,
                        'clean_name': clean_name,
                        'tmdb_type': tmdb_type,
                    })
    return results

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