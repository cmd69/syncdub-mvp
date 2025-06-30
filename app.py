#!/usr/bin/env python3
"""
SyncDub MVP - Aplicación principal Flask
"""

import os
from flask import Flask
from config import config

def create_app(config_name=None):
    """Factory de aplicación Flask"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Inicializar configuración
    config[config_name].init_app(app)
    
    # Registrar blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Configurar servicio de sincronización con contexto de aplicación
    from app.services.sync_service import SyncService
    from app.api import sync_service
    sync_service.set_app(app)
    
    return app

# Crear aplicación
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('APP_PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )

