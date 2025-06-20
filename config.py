import os
from pathlib import Path

class Config:
    """Configuración base de la aplicación SyncDub"""
    
    # Directorios base
    BASE_DIR = Path(__file__).parent.absolute()
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    OUTPUT_FOLDER = BASE_DIR / 'output'
    MODELS_FOLDER = BASE_DIR / 'models'
    
    # Configuración Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'syncdub-secret-key-2024')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB max file size
    
    # Configuración de archivos
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'}
    
    # Configuración de procesamiento
    WHISPER_MODEL = 'medium'  # Opciones: tiny, base, small, medium, large
    SENTENCE_TRANSFORMER_MODEL = 'paraphrase-multilingual-MiniLM-L12-v2'
    
    # Configuración de sincronización
    SIMILARITY_THRESHOLD = 0.7  # Umbral para considerar frases similares
    MAX_TIME_DRIFT = 10.0  # Máximo desfase permitido en segundos
    
    # Configuración de audio
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_FORMAT = 'wav'
    
    @staticmethod
    def init_app(app):
        """Inicializar configuración de la aplicación"""
        # Crear directorios si no existen
        for folder in [Config.UPLOAD_FOLDER, Config.OUTPUT_FOLDER, Config.MODELS_FOLDER]:
            folder.mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    
class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False

# Configuraciones disponibles
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

