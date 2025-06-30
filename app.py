"""
Aplicación principal SyncDub MVP - Versión optimizada
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
            level=logging.INFO,
            format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
    
    # Inicializar configuración
    config[config_name].init_app(app)
    
    # Registrar blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Endpoint de salud para healthcheck
    @app.route('/api/health')
    def health_check():
        """Endpoint de salud para Docker healthcheck"""
        try:
            # Verificar directorios críticos
            critical_dirs = [
                app.config['UPLOAD_FOLDER'],
                app.config['OUTPUT_FOLDER'],
                app.config['MODELS_FOLDER']
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
    
    # Endpoint de información del sistema
    @app.route('/api/system-info')
    def system_info():
        """Información del sistema para debugging"""
        try:
            import psutil
            import platform
            
            return jsonify({
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': f'{psutil.virtual_memory().total / (1024**3):.1f}GB',
                'memory_available': f'{psutil.virtual_memory().available / (1024**3):.1f}GB',
                'memory_percent': f'{psutil.virtual_memory().percent:.1f}%',
                'disk_usage': f'{psutil.disk_usage("/").percent:.1f}%'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # Configurar el servicio de sincronización con la app
    from app.services.sync_service import sync_service
    sync_service.set_app(app)
    
    return app

# Crear aplicación
app = create_app()

if __name__ == '__main__':
    # Configuración optimizada para producción
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True,
        use_reloader=False  # Desactivar reloader en producción
    )

