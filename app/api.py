"""
Blueprint de API para el procesamiento de archivos - CORREGIDO
"""

import os
import uuid
import json
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from app.services.sync_service import sync_service
from app.utils.file_utils import allowed_file, get_file_extension
from flask_login import login_required
from app.models.task import SyncTask

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
        custom_name = request.form.get('custom_name', '').strip()
        
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
            custom_name=custom_name,
            source_type='local'
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
    """Listar todas las tareas (en memoria y en BBDD)"""
    try:
        # Tareas en memoria (en curso)
        tasks_in_memory = sync_service.list_all_tasks().get('tasks', [])
        # Tareas históricas en BBDD
        db_tasks = SyncTask.query.order_by(SyncTask.created_at.desc()).all()
        tasks_db = [t.to_dict() for t in db_tasks]
        return jsonify({
            'tasks_in_memory': tasks_in_memory,
            'tasks_db': tasks_db,
            'total': len(tasks_in_memory) + len(tasks_db)
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error en list_tasks: {str(e)}")
        return jsonify({'error': 'Error al listar tareas'}), 500

@bp.route('/test-transcription', methods=['POST'])
def test_transcription():
    """Endpoint para probar transcripción y offset"""
    try:
        from app.services.sync_service import SyncService
        import traceback
        from pathlib import Path
        
        sync_service_test = SyncService()
        sync_service_test.set_app(current_app._get_current_object())
        result = {}
        
        # Buscar la sesión más reciente
        sync_test_dir = Path("/tmp/sync_test")
        sessions = [d for d in sync_test_dir.iterdir() if d.is_dir()] if sync_test_dir.exists() else []
        if not sessions:
            return jsonify({'ok': False, 'error': 'No hay sesiones de prueba'}), 404
            
        latest_session = max(sessions, key=lambda x: x.stat().st_mtime)
        original_audio = latest_session / "original_audio.wav"
        dubbed_audio = latest_session / "dubbed_audio.wav"
        
        if not original_audio.exists() or not dubbed_audio.exists():
            return jsonify({'ok': False, 'error': 'No se encontraron los audios extraídos'}), 404
        
        # Cargar modelos
        sync_service_test._load_ai_models_safe()
        
        # Transcribir
        orig_segments = sync_service_test._transcribe_audio_safe(str(original_audio), "test")
        dub_segments = sync_service_test._transcribe_audio_safe(str(dubbed_audio), "test")
        
        # Calcular offset
        if sync_service_test.sentence_transformer:
            offset = sync_service_test._calculate_sync_offset_safe(orig_segments, dub_segments)
            method = 'semantic'
        else:
            offset = sync_service_test._calculate_simple_offset_segments(orig_segments, dub_segments)
            method = 'simple'
        
        # Resumir resultados
        result['ok'] = True
        result['original_segments'] = len(orig_segments)
        result['dubbed_segments'] = len(dub_segments)
        result['offset'] = offset
        result['method'] = method
        result['sample_original'] = [
            {'start': s.start, 'end': s.end, 'text': s.text} for s in orig_segments[:5]
        ]
        result['sample_dubbed'] = [
            {'start': s.start, 'end': s.end, 'text': s.text} for s in dub_segments[:5]
        ]
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error en test_transcription: {str(e)}")
        return jsonify({'ok': False, 'error': str(e), 'trace': traceback.format_exc()}), 500

# ===== ENDPOINTS PARA NAVEGACIÓN COMPLETA NFS =====

@bp.route('/nfs-config')
def nfs_config():
    """Obtener configuración del sistema NFS"""
    try:
        # Verificar configuración
        media_enabled = current_app.config.get('MEDIA_SOURCE_ENABLED', False)
        media_path = current_app.config.get('MEDIA_SOURCE_PATH', '/app/video_source')
        
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
def nfs_browse():
    """Navegar contenido del volumen NFS con soporte para subdirectorios"""
    try:
        # Verificar si está habilitado
        media_enabled = current_app.config.get('MEDIA_SOURCE_ENABLED', False)
        if not media_enabled:
            return jsonify({'error': 'Navegación NFS no habilitada'}), 403
        
        # Obtener ruta solicitada
        path = request.args.get('path', '').strip()
        media_path = Path(current_app.config.get('MEDIA_SOURCE_PATH', '/app/video_source'))
        
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
            if not str(full_path).startswith(str(media_path_resolved)):
                return jsonify({'error': 'Ruta no permitida por seguridad'}), 403
        except Exception:
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
            # Obtener todos los elementos del directorio
            all_items = list(full_path.iterdir())
            
            # Separar directorios y archivos
            directories = []
            video_files = []
            
            for item in sorted(all_items, key=lambda x: (not x.is_dir(), x.name.lower())):
                try:
                    # Calcular ruta relativa desde el directorio base
                    relative_path = item.relative_to(media_path)
                    
                    item_info = {
                        'name': item.name,
                        'path': str(relative_path),
                        'is_directory': item.is_dir(),
                        'is_video': False,
                        'size': 0,
                        'size_formatted': '',
                        'accessible': True
                    }
                    
                    if item.is_dir():
                        # Para directorios, intentar contar contenido
                        try:
                            dir_items = list(item.iterdir())
                            subdir_count = len([x for x in dir_items if x.is_dir()])
                            video_count = len([x for x in dir_items if x.is_file() and 
                                             any(x.name.lower().endswith(ext) for ext in video_extensions)])
                            
                            item_info['subdirectories'] = subdir_count
                            item_info['videos'] = video_count
                            item_info['total_items'] = len(dir_items)
                            
                        except PermissionError:
                            item_info['accessible'] = False
                            item_info['error'] = 'Sin permisos'
                        except Exception as e:
                            item_info['accessible'] = False
                            item_info['error'] = 'Error de acceso'
                        
                        directories.append(item_info)
                        
                    elif item.is_file():
                        # Verificar si es un archivo de video
                        is_video = any(item.name.lower().endswith(ext) for ext in video_extensions)
                        item_info['is_video'] = is_video
                        
                        if is_video:
                            try:
                                size = item.stat().st_size
                                item_info['size'] = size
                                item_info['size_formatted'] = format_file_size(size)
                            except:
                                item_info['size'] = 0
                                item_info['size_formatted'] = 'Desconocido'
                            
                            video_files.append(item_info)
                    
                    items.append(item_info)
                    
                except Exception as e:
                    current_app.logger.warning(f"Error procesando item {item}: {e}")
                    continue
                    
        except PermissionError:
            return jsonify({'error': 'Sin permisos para acceder al directorio'}), 403
        except Exception as e:
            current_app.logger.error(f"Error listando directorio: {e}")
            return jsonify({'error': f'Error listando directorio: {str(e)}'}), 500
        
        # Información de navegación
        current_path = str(full_path.relative_to(media_path)) if full_path != media_path else ''
        
        # Construir breadcrumb
        breadcrumb = []
        if current_path:
            parts = current_path.split('/')
            path_so_far = ''
            
            # Agregar raíz
            breadcrumb.append({
                'name': 'video_source',
                'path': '',
                'is_root': True
            })
            
            # Agregar cada parte del path
            for part in parts:
                if part:
                    path_so_far = f"{path_so_far}/{part}" if path_so_far else part
                    breadcrumb.append({
                        'name': part,
                        'path': path_so_far,
                        'is_root': False
                    })
        else:
            breadcrumb.append({
                'name': 'video_source',
                'path': '',
                'is_root': True
            })
        
        # Información del directorio padre
        parent_path = None
        if full_path != media_path:
            parent_relative = full_path.parent.relative_to(media_path)
            parent_path = str(parent_relative) if parent_relative != Path('.') else ''
        
        result = {
            'success': True,
            'current_path': current_path,
            'parent_path': parent_path,
            'breadcrumb': breadcrumb,
            'items': items,
            'summary': {
                'total_items': len(items),
                'directories': len(directories),
                'video_files': len(video_files),
                'other_files': len(items) - len(directories) - len(video_files)
            }
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en nfs_browse: {str(e)}")
        return jsonify({'error': f'Error navegando directorio: {str(e)}'}), 500

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
        media_enabled = current_app.config.get('MEDIA_SOURCE_ENABLED', False)
        if not media_enabled:
            return jsonify({'error': 'Navegación NFS no habilitada'}), 403
        
        media_base = Path(current_app.config.get('MEDIA_SOURCE_PATH', '/app/video_source'))
        
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
            'message': 'Procesamiento iniciado con archivos del servidor.',
            'status': 'processing',
            'original_file': original_path,
            'dubbed_file': dubbed_path,
            'custom_name': custom_name
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en nfs_upload: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

def format_file_size(bytes):
    """Formatear tamaño de archivo en formato legible"""
    if bytes == 0:
        return '0 B'
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    
    while bytes >= 1024 and i < len(units) - 1:
        bytes /= 1024
        i += 1
    
    return f"{bytes:.1f} {units[i]}"

