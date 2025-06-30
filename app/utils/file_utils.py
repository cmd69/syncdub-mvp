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

def get_file_size(file_path):
    """Obtener el tamaño del archivo en bytes"""
    try:
        return os.path.getsize(file_path)
    except (OSError, IOError):
        return 0

def format_file_size(bytes_size):
    """Formatear el tamaño del archivo en formato legible"""
    if bytes_size == 0:
        return '0 B'
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def check_directory_permissions(directory_path):
    """Verificar permisos de acceso a un directorio"""
    try:
        directory = Path(directory_path)
        
        if not directory.exists():
            return False, f"Directorio no existe: {directory_path}"
        
        if not directory.is_dir():
            return False, f"La ruta no es un directorio: {directory_path}"
        
        if not os.access(directory, os.R_OK):
            return False, f"Sin permisos de lectura: {directory_path}"
        
        # Intentar listar el contenido
        try:
            list(directory.iterdir())
            return True, f"Acceso correcto a: {directory_path}"
        except PermissionError:
            return False, f"Sin permisos para listar contenido: {directory_path}"
        except Exception as e:
            return False, f"Error al acceder al directorio: {str(e)}"
            
    except Exception as e:
        return False, f"Error verificando directorio: {str(e)}"

def list_directory_contents(base_directory, current_path=""):
    """
    Listar contenido de directorio con navegación
    Retorna tanto archivos como subdirectorios
    """
    contents = {
        'directories': [],
        'videos': [],
        'current_path': current_path,
        'parent_path': None
    }
    
    try:
        base_directory = Path(base_directory)
        target_directory = base_directory / current_path if current_path else base_directory
        
        # Verificar que el directorio existe y es accesible
        if not target_directory.exists():
            raise Exception(f"Directorio no existe: {target_directory}")
        
        if not target_directory.is_dir():
            raise Exception(f"La ruta no es un directorio: {target_directory}")
        
        if not os.access(target_directory, os.R_OK):
            raise Exception(f"Sin permisos de lectura: {target_directory}")
        
        # Calcular ruta padre
        if current_path:
            parent_parts = current_path.split('/')
            if len(parent_parts) > 1:
                contents['parent_path'] = '/'.join(parent_parts[:-1])
            else:
                contents['parent_path'] = ''
        
        # Listar contenido del directorio
        try:
            items = list(target_directory.iterdir())
        except PermissionError:
            raise Exception(f"Sin permisos para listar: {target_directory}")
        
        # Procesar elementos
        for item in sorted(items, key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                if item.is_dir():
                    # Es un directorio
                    relative_path = str(item.relative_to(base_directory))
                    contents['directories'].append({
                        'name': item.name,
                        'path': relative_path
                    })
                    
                elif item.is_file() and allowed_file(item.name):
                    # Es un archivo de video válido
                    relative_path = str(item.relative_to(base_directory))
                    file_size = get_file_size(str(item))
                    
                    contents['videos'].append({
                        'name': item.name,
                        'path': relative_path,
                        'size': file_size,
                        'size_formatted': format_file_size(file_size),
                        'extension': get_file_extension(item.name)
                    })
                    
            except (OSError, IOError, PermissionError) as e:
                # Saltar archivos/directorios inaccesibles
                current_app.logger.warning(f"Skipping inaccessible item {item}: {e}")
                continue
        
        return contents
        
    except Exception as e:
        current_app.logger.error(f"Error listing directory contents: {str(e)}")
        raise Exception(f"Error al listar contenido del directorio: {str(e)}")

def is_safe_path(base_path, target_path):
    """Verificar que la ruta objetivo está dentro del directorio base (seguridad)"""
    try:
        base = Path(base_path).resolve()
        target = (base / target_path).resolve()
        return target.is_relative_to(base)
    except (ValueError, OSError):
        return False

def get_media_file_path(relative_path):
    """Obtener la ruta completa de un archivo de media"""
    try:
        media_base = current_app.config.get('MEDIA_SOURCE_PATH', '')
        if not media_base:
            raise Exception("Ruta base de media no configurada")
        
        if not is_safe_path(media_base, relative_path):
            raise Exception("Ruta no segura detectada")
        
        full_path = Path(media_base) / relative_path
        
        if not full_path.exists():
            raise Exception(f"Archivo no encontrado: {relative_path}")
        
        if not full_path.is_file():
            raise Exception(f"La ruta no es un archivo: {relative_path}")
        
        return str(full_path)
        
    except Exception as e:
        current_app.logger.error(f"Error getting media file path: {str(e)}")
        raise Exception(f"Error al obtener ruta del archivo: {str(e)}")

