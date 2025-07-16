"""
Aplicación principal de SyncDub MVP - ROUTING CORREGIDO
"""

import os
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for
from config import Config
from app.main import bp as main_bp
from flask_login import LoginManager
from app.models.database import init_db
from app.models.user import User

def create_app(config_class=Config):
    """Factory para crear la aplicación Flask"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # [1]: Registrar el blueprint principal
    app.register_blueprint(main_bp)
    
    # Configurar logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = logging.FileHandler('logs/syncdub.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('SyncDub MVP startup')
    
    # Crear directorios necesarios
    app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
    app.config['OUTPUT_FOLDER'].mkdir(exist_ok=True)
    
    # Configurar el servicio de sincronización con la aplicación Flask
    from app.services.sync_service import sync_service
    sync_service.set_app(app)
    
    # Registrar blueprints
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Rutas principales
    @app.route('/')
    def index():
        """Página principal"""
        return render_template('index.html')
    
    @app.route('/upload')
    def upload():
        """Página de subida de archivos"""
        return render_template('upload.html')
    
    @app.route('/status')
    def status():
        """Página de estado de tareas"""
        return render_template('status.html')
    
    # CORREGIDO: Endpoint de salud que estaba faltando
    @app.route('/api/health')
    def health():
        """Endpoint de salud del sistema"""
        try:
            return jsonify({
                'status': 'healthy',
                'service': 'SyncDub MVP',
                'version': '1.0.0',
                'timestamp': str(datetime.now())
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    # CORREGIDO: Manejadores de error simplificados sin templates faltantes
    @app.errorhandler(404)
    def not_found_error(error):
        """Manejador de error 404 sin template"""
        return jsonify({
            'error': 'Página no encontrada',
            'status': 404,
            'message': 'La URL solicitada no existe en el servidor'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Manejador de error 500 sin template"""
        return jsonify({
            'error': 'Error interno del servidor',
            'status': 500,
            'message': 'Ha ocurrido un error interno'
        }), 500
    
    # Inicializar base de datos y usuario admin
    init_db(app)

    # Configurar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @app.route('/api/media/status')
    def media_status():
        return jsonify({"enabled": False, "accessible": False, "message": "No implementado"}), 200

    @app.route('/api/system-info')
    def system_info():
        return jsonify({"info": "No implementado"}), 200
    
    return app

if __name__ == '__main__':
    from datetime import datetime
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

