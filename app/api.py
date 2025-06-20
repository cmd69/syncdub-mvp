"""
Blueprint de API para el procesamiento de archivos
"""

import os
import uuid
import json
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from app.services.sync_service import SyncService
from app.utils.file_utils import allowed_file, get_file_extension

bp = Blueprint('api', __name__)

# Instancia del servicio de sincronización
sync_service = SyncService()

@bp.route('/upload', methods=['POST'])
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
        
        # Iniciar procesamiento asíncrono
        sync_service.start_sync_task(task_id, str(original_path), str(dubbed_path))
        
        return jsonify({
            'task_id': task_id,
            'message': 'Archivos subidos correctamente. Procesamiento iniciado.',
            'status': 'processing'
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
        result_path = sync_service.get_result_path(task_id)
        if result_path and os.path.exists(result_path):
            return send_file(result_path, as_attachment=True)
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

