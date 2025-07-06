"""
Blueprint de API para el procesamiento de archivos - CORREGIDO
"""

import os
import uuid
import json
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.services.sync_service import sync_service
from app.utils.file_utils import allowed_file, get_file_extension

bp = Blueprint('api', __name__)

@bp.route('/upload', methods=['POST'])
@login_required
def upload_files():
    """Endpoint para subir archivos de video"""
    try:
        # Verificar que se enviaron ambos archivos
        if 'original_video' not in request.files or 'dubbed_video' not in request.files:
            return jsonify({
                'error': 'Se requieren ambos archivos: original_video y dubbed_video'
            }), 400
        
        original_file = request.files['original_video']
        dubbed_file = request.files['dubbed_video']
        
        # Verificar que los archivos no estén vacíos
        if original_file.filename == '' or dubbed_file.filename == '':
            return jsonify({'error': 'No se seleccionaron archivos'}), 400
        
        # Verificar extensiones de archivo
        if not (allowed_file(original_file.filename) and allowed_file(dubbed_file.filename)):
            return jsonify({
                'error': 'Formato de archivo no soportado. Use: mp4, avi, mkv, mov, wmv, flv, webm'
            }), 400
        
        # Obtener nombre personalizado opcional
        custom_name = request.form.get('custom_name', '').strip() or request.form.get('output_name', '').strip()
        
        # Generar ID único para la tarea
        task_id = str(uuid.uuid4())
        
        # Crear directorio para esta tarea
        task_dir = current_app.config['UPLOAD_FOLDER'] / task_id
        task_dir.mkdir(exist_ok=True)
        
        # Guardar archivos
        original_filename = secure_filename(original_file.filename)
        dubbed_filename = secure_filename(dubbed_file.filename)
        
        original_path = task_dir / f"original_{original_filename}"
        dubbed_path = task_dir / f"dubbed_{dubbed_filename}"
        
        original_file.save(str(original_path))
        dubbed_file.save(str(dubbed_path))
        
        # CORREGIDO: Usar custom_name en lugar de custom_filename para consistencia
        sync_service.start_sync_task(
            task_id, 
            str(original_path), 
            str(dubbed_path),
            custom_name=custom_name
        )
        
        return jsonify({
            'task_id': task_id,
            'message': 'Archivos subidos correctamente. Procesamiento iniciado.',
            'status': 'processing'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en upload_files: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@bp.route('/status/<task_id>')
@login_required
def get_status(task_id):
    """Obtener estado del procesamiento"""
    try:
        status = sync_service.get_task_status(task_id)
        return jsonify(status), 200
    except Exception as e:
        current_app.logger.error(f"Error en get_status: {str(e)}")
        return jsonify({'error': 'Error al obtener estado'}), 500

@bp.route('/download/<task_id>')
@login_required
def download_result(task_id):
    """Descargar archivo resultado"""
    try:
        # CORREGIDO: get_result_path ahora devuelve solo la ruta como string
        result_path = sync_service.get_result_path(task_id)
        if result_path and os.path.exists(result_path):
            return send_file(result_path, as_attachment=True)
        else:
            return jsonify({'error': 'Archivo no encontrado'}), 404
    except Exception as e:
        current_app.logger.error(f"Error en download_result: {str(e)}")
        return jsonify({'error': 'Error al descargar archivo'}), 500

@bp.route('/tasks')
@login_required
def list_tasks():
    """Listar todas las tareas"""
    try:
        tasks = sync_service.list_all_tasks()
        return jsonify(tasks), 200
    except Exception as e:
        current_app.logger.error(f"Error en list_tasks: {str(e)}")
        return jsonify({'error': 'Error al listar tareas'}), 500

# ===== ENDPOINTS PARA NAVEGACIÓN COMPLETA NFS =====

@bp.route('/nfs-config')
@login_required
def nfs_config():
    """Obtener configuración del sistema NFS"""
    try:
        # Verificar configuración
        media_enabled = os.environ.get('MEDIA_SOURCE_ENABLED', 'false').lower() == 'true'
        media_path = os.environ.get('MEDIA_SOURCE_PATH', '/app/video_source')
        
        result = {
            'enabled': media_enabled,
            'path': media_path,
            'accessible': False,
            'readable': False,
            'total_videos': 0,
            'extensions': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'],
            'error': None
        }
        
        if media_enabled:
            volume_path = Path(media_path)
            
            # Verificar si existe y es accesible
            if volume_path.exists() and volume_path.is_dir():
                result['accessible'] = True
                
                try:
                    # Intentar listar contenido
                    list(volume_path.iterdir())
                    result['readable'] = True
                    
                    # Contar videos recursivamente (limitado para performance)
                    video_count = 0
                    video_extensions = result['extensions']
                    
                    try:
                        for root, dirs, files in os.walk(volume_path):
                            # Limitar profundidad para evitar timeouts
                            level = root.replace(str(volume_path), '').count(os.sep)
                            if level < 5:  # Máximo 5 niveles de profundidad
                                for file in files:
                                    if any(file.lower().endswith(ext) for ext in video_extensions):
                                        video_count += 1
                                        if video_count >= 100:  # Limitar conteo para performance
                                            break
                            if video_count >= 100:
                                break
                        
                        result['total_videos'] = video_count
                        if video_count >= 100:
                            result['total_videos_note'] = '100+ (conteo limitado por performance)'
                            
                    except Exception as e:
                        current_app.logger.warning(f"Error contando videos: {e}")
                        result['total_videos'] = 0
                        result['count_error'] = str(e)
                    
                except PermissionError:
                    result['error'] = 'Sin permisos para leer el directorio'
                except Exception as e:
                    result['error'] = f'Error accediendo al directorio: {str(e)}'
            else:
                result['error'] = 'El directorio no existe o no es accesible'
        
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en nfs_config: {str(e)}")
        return jsonify({'error': 'Error obteniendo configuración NFS'}), 500

@bp.route('/nfs-browse')
@login_required
def nfs_browse():
    """Navegar contenido del volumen NFS con soporte para subdirectorios"""
    try:
        # Verificar si está habilitado
        media_enabled = os.environ.get('MEDIA_SOURCE_ENABLED', 'false').lower() == 'true'
        if not media_enabled:
            return jsonify({'error': 'Navegación NFS no habilitada'}), 403
        
        # Obtener ruta solicitada
        path = request.args.get('path', '').strip()
        media_path = Path(os.environ.get('MEDIA_SOURCE_PATH', '/app/video_source'))
        
        # Construir ruta completa
        if path:
            # Limpiar la ruta de caracteres peligrosos
            path = path.replace('..', '').replace('//', '/').strip('/')
            full_path = media_path / path
        else:
            full_path = media_path
        
        # Verificar seguridad (no salir del directorio base)
        try:
            full_path = full_path.resolve()
            media_path_resolved = media_path.resolve()
            
            # Verificar que la ruta está dentro del directorio base
            # Si media_path no existe, crear el directorio
            if not media_path_resolved.exists():
                media_path_resolved.mkdir(parents=True, exist_ok=True)
            
            # Verificar que full_path está dentro de media_path
            if not str(full_path).startswith(str(media_path_resolved)):
                return jsonify({'error': 'Ruta no permitida por seguridad'}), 403
        except Exception as e:
            current_app.logger.error(f"Error en validación de ruta: {e}")
            return jsonify({'error': 'Ruta no válida'}), 400
        
        # Verificar que existe
        if not full_path.exists():
            return jsonify({'error': 'Directorio no encontrado'}), 404
            
        if not full_path.is_dir():
            return jsonify({'error': 'La ruta no es un directorio'}), 400
        
        # Listar contenido
        items = []
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
        
        try:
            for item in full_path.iterdir():
                try:
                    item_info = {
                        'name': item.name,
                        'path': str(item.relative_to(media_path)),
                        'is_dir': item.is_dir(),
                        'is_file': item.is_file(),
                        'is_video': False,
                        'size': None,
                        'modified': None
                    }
                    
                    if item.is_file():
                        # Obtener información del archivo
                        try:
                            stat = item.stat()
                            item_info['size'] = stat.st_size
                            item_info['modified'] = stat.st_mtime
                            
                            # Verificar si es video
                            if any(item.name.lower().endswith(ext) for ext in video_extensions):
                                item_info['is_video'] = True
                        except (OSError, PermissionError):
                            # Archivo no accesible, continuar
                            pass
                    
                    items.append(item_info)
                    
                except (OSError, PermissionError):
                    # Item no accesible, continuar
                    continue
            
            # Ordenar: directorios primero, luego archivos
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            return jsonify({
                'path': str(full_path.relative_to(media_path)) if full_path != media_path else '',
                'parent_path': str(full_path.parent.relative_to(media_path)) if full_path.parent != media_path else '',
                'items': items,
                'total_items': len(items),
                'video_count': sum(1 for item in items if item['is_video'])
            }), 200
            
        except PermissionError:
            return jsonify({'error': 'Sin permisos para leer el directorio'}), 403
        except Exception as e:
            current_app.logger.error(f"Error listando contenido: {e}")
            return jsonify({'error': 'Error listando contenido del directorio'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Error en nfs_browse: {str(e)}")
        return jsonify({'error': 'Error navegando directorio'}), 500

@bp.route('/nfs-upload', methods=['POST'])
@login_required
def nfs_upload():
    """Procesar archivos seleccionados desde NFS"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se enviaron datos'}), 400
        
        original_path = data.get('original_path')
        dubbed_path = data.get('dubbed_path')
        custom_name = data.get('custom_name', '')
        
        if not original_path or not dubbed_path:
            return jsonify({'error': 'Se requieren ambas rutas de archivos'}), 400
        
        # Verificar que está habilitado
        media_enabled = os.environ.get('MEDIA_SOURCE_ENABLED', 'false').lower() == 'true'
        if not media_enabled:
            return jsonify({'error': 'Navegación NFS no habilitada'}), 403
        
        media_base = Path(os.environ.get('MEDIA_SOURCE_PATH', '/app/video_source'))
        
        # Construir rutas completas
        original_full = media_base / original_path
        dubbed_full = media_base / dubbed_path
        
        # Verificar seguridad
        try:
            original_resolved = original_full.resolve()
            dubbed_resolved = dubbed_full.resolve()
            media_resolved = media_base.resolve()
            
            if not (str(original_resolved).startswith(str(media_resolved)) and 
                    str(dubbed_resolved).startswith(str(media_resolved))):
                return jsonify({'error': 'Rutas no permitidas por seguridad'}), 403
        except Exception:
            return jsonify({'error': 'Rutas no válidas'}), 400
        
        # Verificar que los archivos existen
        if not original_full.exists() or not original_full.is_file():
            return jsonify({'error': f'Archivo original no encontrado: {original_path}'}), 404
            
        if not dubbed_full.exists() or not dubbed_full.is_file():
            return jsonify({'error': f'Archivo doblado no encontrado: {dubbed_path}'}), 404
        
        # Verificar que son archivos de video
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
        
        if not any(original_full.name.lower().endswith(ext) for ext in video_extensions):
            return jsonify({'error': 'El archivo original no es un video válido'}), 400
            
        if not any(dubbed_full.name.lower().endswith(ext) for ext in video_extensions):
            return jsonify({'error': 'El archivo doblado no es un video válido'}), 400
        
        # Generar ID único para la tarea
        task_id = str(uuid.uuid4())
        
        # CORREGIDO: Usar custom_name en lugar de custom_filename para consistencia
        sync_service.start_sync_task(
            task_id, 
            str(original_full), 
            str(dubbed_full),
            custom_name=custom_name,
            source_type='nfs'
        )
        
        return jsonify({
            'task_id': task_id,
            'message': 'Procesamiento iniciado desde NFS.',
            'status': 'processing',
            'original_file': original_path,
            'dubbed_file': dubbed_path
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en nfs_upload: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# ===== ENDPOINTS DE SISTEMA =====

@bp.route('/system-info')
def system_info():
    """Información del sistema"""
    try:
        import psutil
        
        # Información del sistema
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Información de la aplicación
        app_info = {
            'name': 'SyncDub MVP',
            'version': '1.0.0',
            'environment': current_app.config.get('FLASK_ENV', 'production'),
            'debug': current_app.debug
        }
        
        # Información del sistema
        system_info = {
            'cpu_percent': cpu_percent,
            'memory_total': memory.total,
            'memory_available': memory.available,
            'memory_percent': memory.percent,
            'disk_total': disk.total,
            'disk_free': disk.free,
            'disk_percent': disk.percent
        }
        
        # Información de configuración
        config_info = {
            'media_source_enabled': current_app.config.get('MEDIA_SOURCE_ENABLED', False),
            'media_source_path': current_app.config.get('MEDIA_SOURCE_PATH', ''),
            'max_content_length': current_app.config.get('MAX_CONTENT_LENGTH', 0),
            'allowed_extensions': list(current_app.config.get('ALLOWED_VIDEO_EXTENSIONS', set())),
            'whisper_model': current_app.config.get('WHISPER_MODEL', 'base'),
            'upload_folder': str(current_app.config.get('UPLOAD_FOLDER', '')),
            'output_folder': str(current_app.config.get('OUTPUT_FOLDER', ''))
        }
        
        return jsonify({
            'app': app_info,
            'system': system_info,
            'config': config_info,
            'timestamp': str(datetime.now())
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en system_info: {str(e)}")
        return jsonify({'error': 'Error obteniendo información del sistema'}), 500

def format_file_size(bytes):
    """Formatear tamaño de archivo en formato legible"""
    if bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while bytes >= 1024 and i < len(size_names) - 1:
        bytes /= 1024.0
        i += 1
    
    return f"{bytes:.1f} {size_names[i]}"

