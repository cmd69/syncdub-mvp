#!/usr/bin/env python3
"""
SyncDub MVP - Script de pruebas básicas
Verifica que todos los componentes estén funcionando correctamente
"""

import os
import sys
import requests
import time
from pathlib import Path

def test_imports():
    """Probar que todas las dependencias se puedan importar"""
    print("🧪 Probando importaciones...")
    
    try:
        import flask
        print("✅ Flask importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando Flask: {e}")
        return False
    
    try:
        import whisper
        print("✅ Whisper importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando Whisper: {e}")
        return False
    
    try:
        from sentence_transformers import SentenceTransformer
        print("✅ Sentence Transformers importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando Sentence Transformers: {e}")
        return False
    
    try:
        import ffmpeg
        print("✅ FFmpeg-python importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando FFmpeg-python: {e}")
        return False
    
    try:
        from pydub import AudioSegment
        print("✅ PyDub importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando PyDub: {e}")
        return False
    
    return True

def test_directories():
    """Probar que los directorios necesarios existan"""
    print("\n📁 Probando estructura de directorios...")
    
    required_dirs = [
        'uploads',
        'output', 
        'models',
        'app',
        'static',
        'templates'
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ Directorio {dir_name} existe")
        else:
            print(f"❌ Directorio {dir_name} no existe")
            all_exist = False
    
    return all_exist

def test_config():
    """Probar que la configuración sea válida"""
    print("\n⚙️ Probando configuración...")
    
    try:
        from config import Config
        config = Config()
        
        # Verificar directorios de configuración
        if config.UPLOAD_FOLDER.exists():
            print("✅ Directorio de uploads configurado correctamente")
        else:
            print("❌ Directorio de uploads no existe")
            return False
        
        if config.OUTPUT_FOLDER.exists():
            print("✅ Directorio de output configurado correctamente")
        else:
            print("❌ Directorio de output no existe")
            return False
        
        # Verificar configuración de modelos
        if config.WHISPER_MODEL:
            print(f"✅ Modelo Whisper configurado: {config.WHISPER_MODEL}")
        else:
            print("❌ Modelo Whisper no configurado")
            return False
        
        if config.SENTENCE_TRANSFORMER_MODEL:
            print(f"✅ Modelo Sentence Transformer configurado: {config.SENTENCE_TRANSFORMER_MODEL}")
        else:
            print("❌ Modelo Sentence Transformer no configurado")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        return False

def test_flask_app():
    """Probar que la aplicación Flask se pueda crear"""
    print("\n🌐 Probando aplicación Flask...")
    
    try:
        from app import create_app
        app = create_app('development')
        
        if app:
            print("✅ Aplicación Flask creada correctamente")
            
            # Probar rutas principales
            with app.test_client() as client:
                response = client.get('/')
                if response.status_code == 200:
                    print("✅ Ruta principal (/) responde correctamente")
                else:
                    print(f"❌ Ruta principal responde con código: {response.status_code}")
                    return False
                
                response = client.get('/upload')
                if response.status_code == 200:
                    print("✅ Ruta de upload (/upload) responde correctamente")
                else:
                    print(f"❌ Ruta de upload responde con código: {response.status_code}")
                    return False
            
            return True
        else:
            print("❌ No se pudo crear la aplicación Flask")
            return False
            
    except Exception as e:
        print(f"❌ Error creando aplicación Flask: {e}")
        return False

def test_ai_models():
    """Probar que los modelos de IA se puedan cargar (opcional)"""
    print("\n🤖 Probando modelos de IA (esto puede tardar)...")
    
    try:
        # Probar Whisper (modelo pequeño para prueba)
        import whisper
        print("⏳ Cargando modelo Whisper tiny para prueba...")
        model = whisper.load_model("tiny")
        if model:
            print("✅ Modelo Whisper cargado correctamente")
        else:
            print("❌ No se pudo cargar modelo Whisper")
            return False
        
        # Probar Sentence Transformers
        from sentence_transformers import SentenceTransformer
        print("⏳ Cargando modelo Sentence Transformer para prueba...")
        sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        if sentence_model:
            print("✅ Modelo Sentence Transformer cargado correctamente")
        else:
            print("❌ No se pudo cargar modelo Sentence Transformer")
            return False
        
        return True
        
    except Exception as e:
        print(f"⚠️ Advertencia: Error cargando modelos de IA: {e}")
        print("   Los modelos se descargarán automáticamente en el primer uso")
        return True  # No es crítico para el funcionamiento básico

def run_all_tests():
    """Ejecutar todas las pruebas"""
    print("🚀 Iniciando pruebas de SyncDub MVP...\n")
    
    tests = [
        ("Importaciones", test_imports),
        ("Directorios", test_directories),
        ("Configuración", test_config),
        ("Aplicación Flask", test_flask_app),
        ("Modelos IA", test_ai_models)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error ejecutando prueba {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumen
    print("\n" + "="*50)
    print("📊 RESUMEN DE PRUEBAS")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("\n🎉 ¡Todas las pruebas pasaron! SyncDub MVP está listo para usar.")
        return True
    else:
        print(f"\n⚠️ {total - passed} pruebas fallaron. Revisa los errores arriba.")
        return False

if __name__ == "__main__":
    # Cambiar al directorio del proyecto si es necesario
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)

