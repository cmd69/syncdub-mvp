"""
Blueprint principal para las rutas de la aplicación
"""

from flask import Blueprint, render_template, current_app
import os

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@bp.route('/upload')
def upload():
    """Página de subida de archivos"""
    # Verificar si el volumen de media está habilitado
    media_enabled = current_app.config.get('MEDIA_SOURCE_ENABLED', False)
    media_path = current_app.config.get('MEDIA_SOURCE_PATH', '')
    
    return render_template('upload.html', 
                         media_enabled=media_enabled,
                         media_path=media_path)

@bp.route('/status')
def status():
    """Página de estado del procesamiento"""
    return render_template('status.html')

@bp.route('/result')
def result():
    """Página de resultados"""
    return render_template('result.html')

@bp.route('/about')
def about():
    """Página acerca de"""
    return render_template('about.html')

