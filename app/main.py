"""
Blueprint principal para las rutas de la aplicación
"""

from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@bp.route('/upload')
@login_required
def upload():
    """Página de subida de archivos"""
    # Verificar si el volumen de medios está habilitado
    media_enabled = current_app.config.get('MEDIA_SOURCE_ENABLED', False)
    media_path = current_app.config.get('MEDIA_SOURCE_PATH', '')
    
    return render_template('upload.html', 
                         media_enabled=media_enabled,
                         media_path=media_path)

@bp.route('/status')
@login_required
def status():
    """Página de estado de tareas"""
    return render_template('status.html')

@bp.route('/result')
@login_required
def result():
    """Página de resultados"""
    return render_template('result.html')

@bp.route('/operations')
@login_required
def operations():
    return render_template('operations.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            user.update_last_login()
            return redirect(url_for('main.index'))
        else:
            error = 'Usuario o contraseña incorrectos'
    return render_template('login.html', error=error)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

