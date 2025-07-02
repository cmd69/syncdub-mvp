"""
Aplicación principal SyncDub MVP - Versión GPU optimizada
"""

import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from config import config
from app.main import bp as main_bp
from app.api import bp as api_bp

def create_app(config_name=None):
    """Factory para crear la aplicación Flask"""
    
    # Determinar configuración
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')
    
    # Crear aplicación Flask
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))
    
    # Configurar CORS para permitir requests desde frontend
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Configurar logging optimizado
    if not app.debug:
        logging.basicConfig(
            level=getattr(logging, app.config.get('LOG_LEVEL', 'INFO')),
            format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
    
    # Inicializar configuración
    config[config_name].init_app(app)
    
    # Registrar blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Configurar el servicio de sincronización con la app
    from app.services.sync_service import sync_service
    sync_service.set_app(app)
    
    return app

# Crear aplicación
app = create_app()

if __name__ == '__main__':
    # Configuración optimizada para producción
    port = int(os.environ.get('APP_PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True,
        use_reloader=False  # Desactivar reloader en producción
    )

