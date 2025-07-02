"""
Blueprint de API para el procesamiento de archivos
"""

import os
import uuid
import json
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from app.services.sync_service import sync_service
from app.utils.file_utils import (
    allowed_file, get_file_extension, list_video_files, 
    get_full_path, check_media_source_access, validate_custom_filename
)

bp = Blueprint('api', __name__)

@bp.route('/health')
def health_check():
    """Endpoint de salud para Docker healthcheck"""
    try:
        # Verificar directorios críticos
        critical_dirs = [
            current_app.config['UPLOAD_FOLDER'],
            current_app.config['OUTPUT_FOLDER'],
            current_app.config['MODELS_FOLDER']
        ]
        
        for directory in critical_dirs:
            if not directory.exists():
                return jsonify({
                    'status': 'unhealthy',
                    'error': f'Directory not found: {directory}'
                }), 503
        
        # Verificar memoria disponible
        import psutil
        memory = psutil.virtual_memory()
        if memory.percent > 95:
            return jsonify({
                'status': 'warning',
                'message': f'High memory usage: {memory.percent:.1f}%'
            }), 200
        
        return jsonify({
            'status': 'healthy',
            'memory_usage': f'{memory.percent:.1f}%',
            'available_memory': f'{memory.available / (1024**3):.1f}GB'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

@bp.route('/system-info')
def system_info():
    """Información del sistema para debugging"""
    try:
        import psutil
        import platform
        import torch
        
        gpu_info = "No disponible"
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3) if gpu_count > 0 else 0
            gpu_info = f"{gpu_count}x {gpu_name} ({gpu_memory:.1f}GB)"
        
        return jsonify({
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': f'{psutil.virtual_memory().total / (1024**3):.1f}GB',
            'memory_available': f'{psutil.virtual_memory().available / (1024**3):.1f}GB',
            'memory_percent': f'{psutil.virtual_memory().percent:.1f}%',
            'disk_usage': f'{psutil.disk_usage("/").percent:.1f}%',
            'gpu_info': gpu_info,
            'torch_version': torch.__version__ if 'torch' in globals() else 'No disponible'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/media/status')
def media_status():
    """Verificar estado del volumen de medios"""
    try:
        media_enabled = current_app.config.get('MEDIA_SOURCE_ENABLED', False)
        
        if not media_enabled:
            return jsonify({
                'enabled': False,
                'message': 'Volumen de medios no configurado'
            })
        
        media_path = current_app.config.get('MEDIA_SOURCE_PATH')
        if not media_path:
            return jsonify({
                'enabled': False,
                'error': 'MEDIA_SOURCE_PATH no configurado'
            })
        
        # Verificar acceso al directorio
        accessible, message = check_media_source_access(media_path)
        
        if accessible:
            # Contar archivos de video
            try:
                items = list_video_files(media_path)
                video_count = len([item for item in items if item['type'] == 'file'])
                dir_count = len([item for item in items if item['type'] == 'directory' and not item.get('is_parent', False)])
                
                return jsonify({
                    'enabled': True,
                    'accessible': True,
                    'path': media_path,
                    'video_count': video_count,
                    'directory_count': dir_count,
                    'message': f'{video_count} videos encontrados'
                })
            except Exception as e:
                return jsonify({
                    'enabled': True,
                    'accessible': False,
                    'path': media_path,
                    'error': f'Error listando contenido: {str(e)}'
                })
        else:
            return jsonify({
                'enabled': True,
                'accessible': False,
                'path': media_path,
                'error': message
            })
            
    except Exception as e:
        current_app.logger.error(f"Error checking media status: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@bp.route('/media/list')
def list_media_files():
    """Listar archivos de video en el volumen de medios"""
    try:
        media_enabled = current_app.config.get('MEDIA_SOURCE_ENABLED', False)
        if not media_enabled:
            return jsonify({'error': 'Volumen de medios no habilitado'}), 400
        
        media_base_path = current_app.config.get('MEDIA_SOURCE_PATH')
        if not media_base_path:
            return jsonify({'error': 'MEDIA_SOURCE_PATH no configurado'}), 400
        
        # Obtener ruta relativa del parámetro
        relative_path = request.args.get('path', '')
        
        # Construir ruta completa y segura
        full_path = get_full_path(media_base_path, relative_path)
        
        # Verificar acceso
        accessible, message = check_media_source_access(full_path)
        if not accessible:
            return jsonify({'error': message}), 403
        
        # Listar archivos y directorios
        items = list_video_files(full_path, relative_path)
        
        # Información de navegación
        current_path_parts = relative_path.split('/') if relative_path else []
        breadcrumbs = []
        path_so_far = ""
        
        # Agregar raíz
        breadcrumbs.append({'name': 'Inicio', 'path': ''})
        
        # Agregar partes del path actual
        for part in current_path_parts:
            if part:
                path_so_far = f"{path_so_far}/{part}" if path_so_far else part
                breadcrumbs.append({'name': part, 'path': path_so_far})
        
        return jsonify({
            'items': items,
            'current_path': relative_path,
            'breadcrumbs': breadcrumbs,
            'total_items': len(items)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing media files: {str(e)}")
        return jsonify({'error': 'Error listando archivos'}), 500

@bp.route('/upload', methods=['POST'])
def upload_files():
    """Endpoint para subir archivos de video o seleccionar desde volumen"""
    try:
        # Obtener configuración de fuentes
        original_source = request.form.get('original_source', 'upload')  # 'upload' o 'volume'
        dubbed_source = request.form.get('dubbed_source', 'upload')
        
        # Nombre personalizado para archivo destino
        custom_filename = request.form.get('custom_filename', '').strip()
        
        # Validar nombre personalizado si se proporciona
        if custom_filename:
            is_valid, clean_name = validate_custom_filename(custom_filename)
            if not is_valid:
                return jsonify({'error': f'Nombre de archivo inválido: {clean_name}'}), 400
            custom_filename = clean_name
        
        # Generar ID único para la tarea
        task_id = str(uuid.uuid4())
        
        # Crear directorio para esta tarea
        task_dir = current_app.config['UPLOAD_FOLDER'] / task_id
        task_dir.mkdir(exist_ok=True)
        
        # Procesar archivo original
        if original_source == 'upload':
            if 'original_video' not in request.files:
                return jsonify({'error': 'Se requiere archivo original'}), 400
            original_file = request.files['original_video']
            if original_file.filename == '':
                return jsonify({'error': 'No se seleccionó archivo original'}), 400
            if not allowed_file(original_file.filename):
                return jsonify({'error': 'Formato de archivo original no soportado'}), 400
            
            original_filename = secure_filename(original_file.filename)
            original_path = task_dir / f"original_{original_filename}"
            original_file.save(str(original_path))
            
        else:  # volume
            original_filename = request.form.get('original_volume_file')
            if not original_filename:
                return jsonify({'error': 'Se requiere seleccionar archivo original del volumen'}), 400
            
            media_base_path = current_app.config.get('MEDIA_SOURCE_PATH')
            if not media_base_path:
                return jsonify({'error': 'Volumen de medios no configurado'}), 400
            
            original_path = get_full_path(media_base_path, original_filename)
            if not os.path.exists(original_path) or not os.path.isfile(original_path):
                return jsonify({'error': 'Archivo original no encontrado en volumen'}), 400
        
        # Procesar archivo doblado
        if dubbed_source == 'upload':
            if 'dubbed_video' not in request.files:
                return jsonify({'error': 'Se requiere archivo doblado'}), 400
            dubbed_file = request.files['dubbed_video']
            if dubbed_file.filename == '':
                return jsonify({'error': 'No se seleccionó archivo doblado'}), 400
            if not allowed_file(dubbed_file.filename):
                return jsonify({'error': 'Formato de archivo doblado no soportado'}), 400
            
            dubbed_filename = secure_filename(dubbed_file.filename)
            dubbed_path = task_dir / f"dubbed_{dubbed_filename}"
            dubbed_file.save(str(dubbed_path))
            
        else:  # volume
            dubbed_filename = request.form.get('dubbed_volume_file')
            if not dubbed_filename:
                return jsonify({'error': 'Se requiere seleccionar archivo doblado del volumen'}), 400
            
            media_base_path = current_app.config.get('MEDIA_SOURCE_PATH')
            if not media_base_path:
                return jsonify({'error': 'Volumen de medios no configurado'}), 400
            
            dubbed_path = get_full_path(media_base_path, dubbed_filename)
            if not os.path.exists(dubbed_path) or not os.path.isfile(dubbed_path):
                return jsonify({'error': 'Archivo doblado no encontrado en volumen'}), 400
        
        # Verificar tamaño de archivos (máximo 20GB)
        max_size = 20 * 1024 * 1024 * 1024  # 20GB
        
        try:
            orig_size = os.path.getsize(original_path)
            dub_size = os.path.getsize(dubbed_path)
            
            if orig_size > max_size:
                return jsonify({'error': f'Archivo original demasiado grande. Máximo: 20GB'}), 400
            if dub_size > max_size:
                return jsonify({'error': f'Archivo doblado demasiado grande. Máximo: 20GB'}), 400
                
        except OSError as e:
            return jsonify({'error': f'Error verificando tamaño de archivos: {str(e)}'}), 400
        
        # Iniciar procesamiento asíncrono
        sync_service.start_sync_task(
            task_id, 
            str(original_path), 
            str(dubbed_path),
            custom_filename=custom_filename
        )
        
        return jsonify({
            'task_id': task_id,
            'message': 'Procesamiento iniciado correctamente.',
            'status': 'processing',
            'custom_filename': custom_filename,
            'original_source': original_source,
            'dubbed_source': dubbed_source
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error en upload_files: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@bp.route('/status/<task_id>')
def get_status(task_id):
    """Obtener estado del procesamiento"""
    try:
        status = sync_service.get_task_status(task_id)
        return jsonify(status), 200
    except Exception as e:
        current_app.logger.error(f"Error en get_status: {str(e)}")
        return jsonify({'error': 'Error al obtener estado'}), 500

@bp.route('/download/<task_id>')
def download_result(task_id):
    """Descargar archivo resultado"""
    try:
        result_path, custom_name = sync_service.get_result_path(task_id)
        if result_path and os.path.exists(result_path):
            download_name = custom_name if custom_name else f"synced_{task_id}.mkv"
            return send_file(result_path, as_attachment=True, download_name=download_name)
        else:
            return jsonify({'error': 'Archivo no encontrado'}), 404
    except Exception as e:
        current_app.logger.error(f"Error en download_result: {str(e)}")
        return jsonify({'error': 'Error al descargar archivo'}), 500

@bp.route('/tasks')
def list_tasks():
    """Listar todas las tareas"""
    try:
        tasks = sync_service.list_all_tasks()
        return jsonify(tasks), 200
    except Exception as e:
        current_app.logger.error(f"Error en list_tasks: {str(e)}")
        return jsonify({'error': 'Error al listar tareas'}), 500

