"""
Blueprint principal para las rutas de la aplicación
"""

from flask import Blueprint, render_template, current_app
from flask_login import login_required

bp = Blueprint('main', __name__)

@bp.route('/about')
def about():
    """Página de información"""
    return render_template('about.html')

@bp.route('/result')
@login_required
def result():
    """Página de resultados"""
    return render_template('result.html')

