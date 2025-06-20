"""
Blueprint principal para las rutas de la interfaz web
"""

from flask import Blueprint, render_template, current_app

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Página principal de la aplicación"""
    return render_template('index.html')

@bp.route('/upload')
def upload():
    """Página de subida de archivos"""
    return render_template('upload.html')

@bp.route('/status/<task_id>')
def status(task_id):
    """Página de estado del procesamiento"""
    return render_template('status.html', task_id=task_id)

@bp.route('/result/<task_id>')
def result(task_id):
    """Página de resultados"""
    return render_template('result.html', task_id=task_id)

