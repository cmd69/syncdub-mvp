#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de SyncDub MVP
"""

import os
import sys
import time
import requests
import json
from pathlib import Path

def test_health_endpoint():
    """Probar endpoint de salud"""
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=10)
        if response.status_code == 200:
            print("✅ Health endpoint: OK")
            return True
        else:
            print(f"❌ Health endpoint: Error {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint: {e}")
        return False

def test_system_info():
    """Probar endpoint de información del sistema"""
    try:
        response = requests.get('http://localhost:5000/api/system-info', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ System info endpoint: OK")
            print(f"   - Python: {data.get('python_version', 'N/A')}")
            print(f"   - Memory: {data.get('memory_usage', 'N/A')}")
            print(f"   - GPU: {data.get('gpu_available', 'N/A')}")
            return True
        else:
            print(f"❌ System info endpoint: Error {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ System info endpoint: {e}")
        return False

def test_media_status():
    """Probar endpoint de estado de medios"""
    try:
        response = requests.get('http://localhost:5000/api/media/status', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Media status endpoint: OK")
            print(f"   - Enabled: {data.get('enabled', 'N/A')}")
            print(f"   - Path: {data.get('path', 'N/A')}")
            print(f"   - Accessible: {data.get('accessible', 'N/A')}")
            return True
        else:
            print(f"❌ Media status endpoint: Error {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Media status endpoint: {e}")
        return False

def test_file_validation():
    """Probar validación de archivos"""
    print("\n🧪 Probando validación de archivos...")
    
    # Crear archivo de prueba
    test_dir = Path("test_files")
    test_dir.mkdir(exist_ok=True)
    
    # Crear archivo de texto (debería fallar)
    text_file = test_dir / "test.txt"
    text_file.write_text("Este es un archivo de texto")
    
    # Crear archivo vacío (debería fallar)
    empty_file = test_dir / "empty.mp4"
    empty_file.touch()
    
    print(f"   - Archivo de texto: {text_file}")
    print(f"   - Archivo vacío: {empty_file}")
    
    return True

def create_sample_video():
    """Crear video de muestra para pruebas"""
    try:
        test_dir = Path("test_files")
        test_dir.mkdir(exist_ok=True)
        
        sample_video = test_dir / "sample.mp4"
        
        # Crear video de muestra de 10 segundos con FFmpeg
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=10:size=320x240:rate=1',
            '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=10',
            '-c:v', 'libx264', '-c:a', 'aac', '-shortest',
            '-y', str(sample_video)
        ]
        
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and sample_video.exists():
            print(f"✅ Video de muestra creado: {sample_video}")
            return str(sample_video)
        else:
            print(f"❌ Error creando video de muestra: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error creando video de muestra: {e}")
        return None

def test_upload_validation():
    """Probar validación de upload"""
    print("\n🧪 Probando validación de upload...")
    
    # Crear video de muestra
    sample_video = create_sample_video()
    if not sample_video:
        print("❌ No se pudo crear video de muestra")
        return False
    
    try:
        # Probar upload con archivo válido
        with open(sample_video, 'rb') as f:
            files = {
                'original_file': f,
                'dubbed_file': f
            }
            data = {
                'custom_filename': 'test_output'
            }
            
            response = requests.post(
                'http://localhost:5000/api/upload',
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get('task_id')
                print(f"✅ Upload iniciado: Task ID {task_id}")
                return task_id
            else:
                print(f"❌ Error en upload: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error en upload: {e}")
        return False

def test_task_status(task_id):
    """Probar seguimiento de estado de tarea"""
    if not task_id:
        return False
        
    print(f"\n🧪 Probando seguimiento de tarea {task_id}...")
    
    try:
        for i in range(10):  # Máximo 10 intentos
            response = requests.get(f'http://localhost:5000/api/status/{task_id}', timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                progress = data.get('progress', 0)
                message = data.get('message', '')
                
                print(f"   - Estado: {status} ({progress}%) - {message}")
                
                if status == 'completed':
                    print("✅ Tarea completada exitosamente")
                    return True
                elif status == 'error':
                    error = data.get('error', 'Error desconocido')
                    print(f"❌ Tarea falló: {error}")
                    return False
                
                time.sleep(5)  # Esperar 5 segundos antes del siguiente check
            else:
                print(f"❌ Error consultando estado: {response.status_code}")
                return False
        
        print("⏰ Timeout esperando completar tarea")
        return False
        
    except Exception as e:
        print(f"❌ Error consultando estado: {e}")
        return False

def cleanup_test_files():
    """Limpiar archivos de prueba"""
    try:
        import shutil
        test_dir = Path("test_files")
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("🧹 Archivos de prueba limpiados")
    except Exception as e:
        print(f"⚠️  Error limpiando archivos: {e}")

def main():
    """Función principal de pruebas"""
    print("🧪 Iniciando pruebas de SyncDub MVP")
    print("=" * 50)
    
    # Verificar que la aplicación esté ejecutándose
    print("\n📡 Probando conectividad...")
    if not test_health_endpoint():
        print("❌ La aplicación no está ejecutándose o no es accesible")
        print("   Ejecuta: ./start-fixed.sh")
        return False
    
    # Probar endpoints básicos
    print("\n🔍 Probando endpoints básicos...")
    test_system_info()
    test_media_status()
    
    # Probar validación de archivos
    test_file_validation()
    
    # Probar upload y procesamiento (opcional)
    print("\n⚠️  Las siguientes pruebas requieren FFmpeg y pueden tomar tiempo...")
    response = input("¿Deseas probar upload y procesamiento? (y/N): ")
    
    if response.lower() == 'y':
        task_id = test_upload_validation()
        if task_id:
            test_task_status(task_id)
    
    # Limpiar archivos de prueba
    cleanup_test_files()
    
    print("\n✅ Pruebas completadas")
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Pruebas interrumpidas por el usuario")
        cleanup_test_files()
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        cleanup_test_files()

