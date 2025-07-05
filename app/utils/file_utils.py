"""
Utilidades para manejo de archivos con soporte NFS
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

def list_video_files(directory, current_path=""):
    """Listar archivos de video y directorios en un directorio con navegación"""
    items = []
    try:
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            return items
        
        # Agregar opción para subir un nivel si no estamos en la raíz
        if current_path:
            items.append({
                'name': '..',
                'type': 'directory',
                'path': str(Path(current_path).parent) if Path(current_path).parent != Path(current_path) else '',
                'size': 0,
                'size_formatted': '-',
                'is_parent': True
            })
        
        # Listar contenido del directorio
        for item_path in sorted(directory.iterdir()):
            try:
                if item_path.is_dir():
                    # Directorio
                    item_info = {
                        'name': item_path.name,
                        'type': 'directory',
                        'path': str(Path(current_path) / item_path.name) if current_path else item_path.name,
                        'size': 0,
                        'size_formatted': '-',
                        'is_parent': False
                    }
                    items.append(item_info)
                elif item_path.is_file() and allowed_file(item_path.name):
                    # Archivo de video
                    file_size = get_file_size(str(item_path))
                    item_info = {
                        'name': item_path.name,
                        'type': 'file',
                        'path': str(Path(current_path) / item_path.name) if current_path else item_path.name,
                        'size': file_size,
                        'size_formatted': format_file_size(file_size),
                        'extension': get_file_extension(item_path.name),
                        'is_parent': False
                    }
                    items.append(item_info)
            except (PermissionError, OSError):
                # Ignorar archivos/directorios sin permisos
                continue
        
    except Exception as e:
        current_app.logger.error(f"Error listando archivos en {directory}: {e}")
    
    return items

def get_full_path(base_directory, relative_path):
    """Obtener ruta completa y segura combinando directorio base con ruta relativa"""
    try:
        base_dir = Path(base_directory).resolve()
        if not relative_path or relative_path == ".":
            return str(base_dir)
        
        # Construir ruta completa
        full_path = (base_dir / relative_path).resolve()
        
        # Verificar que la ruta esté dentro del directorio base (seguridad)
        if not str(full_path).startswith(str(base_dir)):
            return str(base_dir)
        
        return str(full_path)
    except Exception:
        return str(Path(base_directory).resolve())

def check_media_source_access(media_path):
    """Verificar acceso al directorio de medios"""
    try:
        path = Path(media_path)
        if not path.exists():
            return False, "Directorio no existe"
        
        if not path.is_dir():
            return False, "La ruta no es un directorio"
        
        # Verificar permisos de lectura
        try:
            list(path.iterdir())
        except PermissionError:
            return False, "Sin permisos de lectura"
        
        return True, "Acceso correcto"
    except Exception as e:
        return False, f"Error: {str(e)}"

def ensure_dir(directory):
    """Asegurar que el directorio existe"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def get_file_size(filepath):
    """Obtener el tamaño del archivo en bytes"""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0

def format_file_size(bytes_size):
    """Formatear tamaño de archivo en formato legible"""
    if bytes_size == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while bytes_size >= 1024 and i < len(size_names) - 1:
        bytes_size /= 1024.0
        i += 1
    
    return f"{bytes_size:.1f} {size_names[i]}"

def clean_filename(filename):
    """Limpiar nombre de archivo para uso seguro"""
    import re
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    return filename

def get_safe_filename(original_name, prefix="", suffix=""):
    """Generar nombre de archivo seguro con prefijo y sufijo opcionales"""
    name, ext = os.path.splitext(original_name)
    safe_name = clean_filename(name)
    return f"{prefix}{safe_name}{suffix}{ext}"

def validate_custom_filename(filename):
    """Validar nombre personalizado de archivo"""
    if not filename:
        return True, ""
    
    # Limpiar caracteres no válidos
    clean_name = clean_filename(filename)
    
    # Verificar longitud
    if len(clean_name) > 100:
        return False, "El nombre es demasiado largo (máximo 100 caracteres)"
    
    # Verificar que no esté vacío después de limpiar
    if not clean_name.strip():
        return False, "El nombre no puede estar vacío"
    
    return True, clean_name

