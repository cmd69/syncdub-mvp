"""
Utilidades para manejo de archivos
"""

import os
from pathlib import Path
from flask import current_app

def allowed_file(filename):
    """Verificar si el archivo tiene una extensión permitida"""
    if not filename:
        return False
    return '.' in filename and \
           get_file_extension(filename) in current_app.config['ALLOWED_VIDEO_EXTENSIONS']

def get_file_extension(filename):
    """Obtener la extensión del archivo en minúsculas"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def ensure_dir(directory):
    """Asegurar que el directorio existe"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def get_file_size(filepath):
    """Obtener el tamaño del archivo en bytes"""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0

def clean_filename(filename):
    """Limpiar nombre de archivo para uso seguro"""
    # Remover caracteres especiales y espacios
    import re
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    return filename

def get_safe_filename(original_name, prefix="", suffix=""):
    """Generar nombre de archivo seguro con prefijo y sufijo opcionales"""
    name, ext = os.path.splitext(original_name)
    safe_name = clean_filename(name)
    return f"{prefix}{safe_name}{suffix}{ext}"

