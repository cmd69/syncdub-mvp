"""
Blueprint de API para el procesamiento de archivos
"""

import os
import uuid
import json
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from app.services.sync_service import SyncService
from app.utils.file_utils import allowed_file, get_file_extension, list_directory_contents, check_directory_permissions

bp = Blueprint('api', __name__)

# Instancia del servicio de sincronización
sync_service = SyncService()

@bp.route('/media/status', methods=['GET'])
def check_media_status():
    """Verificar disponibilidad del volumen de media"""
    try:
        media_enabled = current_app.config.get('MEDIA_SOURCE_ENABLED', False)
        media_path = current_app.config.get('MEDIA_SOURCE_PATH', '')
        
        if not media_enabled:
            return jsonify({
                'accessible': False,
                'message': 'Volumen de media no configurado',
                'path': ''
            }), 200
        
        has_access, message = check_directory_permissions(media_path)
        
        return jsonify({
            'accessible': has_access,
            'message': message,
            'path': media_path
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error checking media status: {str(e)}")
        return jsonify({
            'accessible': False,
            'message': 'Error al verificar volumen de media',
            'path': ''
        }), 200

@bp.route('/media/list', methods=['GET'])
def list_media_files():
    """Listar archivos de media disponibles"""
    try:
        media_enabled = current_app.config.get('MEDIA_SOURCE_ENABLED', False)
        media_path = current_app.config.get('MEDIA_SOURCE_PATH', '')
        
        if not media_enabled:
            return jsonify({'error': 'Volumen de media no configurado'}), 400
        
        current_path = request.args.get('path', '')
        contents = list_directory_contents(media_path, current_path)
        
        return jsonify({
            'directories': contents['directories'],
            'videos': contents['videos'],
            'current_path': contents['current_path'],
            'parent_path': contents['parent_path'],
            'total_videos': len(contents['videos']),
            'total_directories': len(contents['directories'])
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error listing media files: {str(e)}")
        return jsonify({'error': 'Error al listar archivos de media'}), 500

@bp.route('/upload', methods=['POST'])
def upload_files():
    """Endpoint para procesar archivos de video"""
    try:
        # Obtener configuración de fuentes
        original_source = request.form.get('original_source', 'upload')
        dubbed_source = request.form.get('dubbed_source', 'upload')
        custom_filename = request.form.get('custom_filename', '')
        
        original_path = ''
        dubbed_path = ''
        
        # Procesar video original
        if original_source == 'upload':
            if 'original_video' not in request.files:
                return jsonify({'error': 'No se encontró el archivo de video original'}), 400
            
            original_file = request.files['original_video']
            if original_file.filename == '':
                return jsonify({'error': 'No se seleccionó archivo original'}), 400
            
            if not allowed_file(original_file.filename):
                return jsonify({'error': 'Formato de archivo original no válido'}), 400
            
            # Guardar archivo original
            filename = secure_filename(original_file.filename)
            original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"original_{uuid.uuid4()}_{filename}")
            original_file.save(original_path)
            
        elif original_source == 'volume':
            original_path = request.form.get('original_path', '')
            if not original_path:
                return jsonify({'error': 'No se especificó la ruta del archivo original'}), 400
            
            # Construir ruta completa
            media_base = current_app.config.get('MEDIA_SOURCE_PATH', '')
            original_path = os.path.join(media_base, original_path)
            
            if not os.path.exists(original_path):
                return jsonify({'error': 'El archivo original no existe en el volumen'}), 400
        
        # Procesar video doblado
        if dubbed_source == 'upload':
            if 'dubbed_video' not in request.files:
                return jsonify({'error': 'No se encontró el archivo de video doblado'}), 400
            
            dubbed_file = request.files['dubbed_video']
            if dubbed_file.filename == '':
                return jsonify({'error': 'No se seleccionó archivo doblado'}), 400
            
            if not allowed_file(dubbed_file.filename):
                return jsonify({'error': 'Formato de archivo doblado no válido'}), 400
            
            # Guardar archivo doblado
            filename = secure_filename(dubbed_file.filename)
            dubbed_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"dubbed_{uuid.uuid4()}_{filename}")
            dubbed_file.save(dubbed_path)
            
        elif dubbed_source == 'volume':
            dubbed_path = request.form.get('dubbed_path', '')
            if not dubbed_path:
                return jsonify({'error': 'No se especificó la ruta del archivo doblado'}), 400
            
            # Construir ruta completa
            media_base = current_app.config.get('MEDIA_SOURCE_PATH', '')
            dubbed_path = os.path.join(media_base, dubbed_path)
            
            if not os.path.exists(dubbed_path):
                return jsonify({'error': 'El archivo doblado no existe en el volumen'}), 400
        
        # Crear tarea de sincronización
        task_id = sync_service.create_task(original_path, dubbed_path, custom_filename)
        
        return jsonify({
            'task_id': task_id,
            'message': 'Procesamiento iniciado exitosamente'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in upload: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@bp.route('/status/<task_id>')
def get_status(task_id):
    """Obtener estado del procesamiento"""
    try:
        status = sync_service.get_task_status(task_id)
        return jsonify(status), 200
    except Exception as e:
        current_app.logger.error(f"Error in get_status: {str(e)}")
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
        current_app.logger.error(f"Error in download_result: {str(e)}")
        return jsonify({'error': 'Error al descargar archivo'}), 500

@bp.route('/tasks')
def list_tasks():
    """Listar todas las tareas"""
    try:
        tasks = sync_service.list_all_tasks()
        return jsonify(tasks), 200
    except Exception as e:
        current_app.logger.error(f"Error in list_tasks: {str(e)}")
        return jsonify({'error': 'Error al listar tareas'}), 500

