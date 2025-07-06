"""
Aplicación principal de SyncDub MVP - ROUTING CORREGIDO
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from app.main import bp as main_bp

def create_app(config_class=Config):
    """Factory para crear la aplicación Flask"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configurar base de datos
    from app.models.database import init_db
    init_db(app)
    
    # Configurar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

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
    
    # Rutas de autenticación
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Página de login"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Por favor ingresa usuario y contraseña', 'error')
                return render_template('login.html')
            
            from app.models.user import User
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user, remember=True)
                user.update_last_login()
                flash(f'¡Bienvenido, {user.username}!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Usuario o contraseña incorrectos', 'error')
        
        return render_template('login.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        """Cerrar sesión"""
        logout_user()
        flash('Has cerrado sesión correctamente', 'info')
        return redirect(url_for('login'))
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard del usuario"""
        # Obtener estadísticas del usuario
        from app.models.sync_job import SyncJob
        
        total_jobs = SyncJob.query.filter_by(user_id=current_user.id).count()
        completed_jobs = SyncJob.query.filter_by(user_id=current_user.id, status='completed').count()
        processing_jobs = SyncJob.query.filter_by(user_id=current_user.id, status='processing').count()
        failed_jobs = SyncJob.query.filter_by(user_id=current_user.id, status='failed').count()
        
        stats = {
            'total': total_jobs,
            'completed': completed_jobs,
            'processing': processing_jobs,
            'failed': failed_jobs
        }
        
        return render_template('dashboard.html', stats=stats)
    
    # Rutas principales (protegidas)
    @app.route('/')
    def index():
        """Página principal"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
    
    @app.route('/upload')
    @login_required
    def upload():
        """Página de subida de archivos"""
        return render_template('upload.html')
    
    @app.route('/status')
    @login_required
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
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

