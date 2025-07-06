#!/usr/bin/env python3
"""
Test script para verificar la autenticación y base de datos
"""

import os
import sys
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

# Importar desde app.py directamente
import app as main_app
from app.models.database import db
from app.models.user import User

def test_database_setup():
    """Probar la configuración de la base de datos"""
    print("🔍 Probando configuración de base de datos...")
    
    app = main_app.create_app()
    
    with app.app_context():
        # Verificar que la base de datos se puede crear
        db.create_all()
        print("✅ Tablas de base de datos creadas")
        
        # Verificar que el usuario admin existe
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            print(f"✅ Usuario admin encontrado: {admin_user.username}")
            print(f"   - ID: {admin_user.id}")
            print(f"   - Creado: {admin_user.created_at}")
            print(f"   - Activo: {admin_user.is_active}")
        else:
            print("❌ Usuario admin no encontrado")
            return False
        
        # Probar autenticación de contraseña
        if admin_user.check_password('admin'):
            print("✅ Contraseña admin verificada correctamente")
        else:
            print("❌ Error verificando contraseña admin")
            return False
        
        # Probar contraseña incorrecta
        if not admin_user.check_password('wrong_password'):
            print("✅ Contraseña incorrecta rechazada correctamente")
        else:
            print("❌ Error: contraseña incorrecta aceptada")
            return False
        
        return True

def test_flask_login():
    """Probar Flask-Login"""
    print("\n🔍 Probando Flask-Login...")
    
    app = main_app.create_app()
    
    with app.app_context():
        from flask_login import LoginManager
        from app.models.user import User
        
        # Verificar que el login manager está configurado
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        # Probar user loader
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            loaded_user = login_manager.user_loader(str(admin_user.id))
            if loaded_user and loaded_user.id == admin_user.id:
                print("✅ User loader funciona correctamente")
            else:
                print("❌ Error en user loader")
                return False
        else:
            print("❌ No se puede probar user loader - usuario admin no encontrado")
            return False
        
        return True

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de autenticación y base de datos...")
    print("=" * 60)
    
    try:
        # Probar base de datos
        if not test_database_setup():
            print("\n❌ Falló la prueba de base de datos")
            return 1
        
        # Probar Flask-Login
        if not test_flask_login():
            print("\n❌ Falló la prueba de Flask-Login")
            return 1
        
        print("\n" + "=" * 60)
        print("✅ Todas las pruebas pasaron exitosamente!")
        print("\n🎉 La autenticación y base de datos están configuradas correctamente.")
        print("   Puedes acceder a la aplicación con:")
        print("   - Usuario: admin")
        print("   - Contraseña: admin")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main()) 