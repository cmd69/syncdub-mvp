"""
Blueprint principal para las rutas de la aplicación
"""

from flask import Blueprint, render_template, current_app, request, redirect, url_for

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@bp.route('/upload')
def upload():
    """Página de subida de archivos"""
    # Verificar si el volumen de medios está habilitado
    media_enabled = current_app.config.get('MEDIA_SOURCE_ENABLED', False)
    media_path = current_app.config.get('MEDIA_SOURCE_PATH', '')
    
    return render_template('upload.html', 
                         media_enabled=media_enabled,
                         media_path=media_path)

@bp.route('/status')
def status():
    """Página de estado de tareas"""
    return render_template('status.html')

@bp.route('/result')
def result():
    """Página de resultados"""
    return render_template('result.html')

@bp.route('/operations')
def operations():
    return render_template('operations.html')

