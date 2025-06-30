import os
from pathlib import Path

class Config:
    """Configuración base de la aplicación SyncDub"""
    
    # Directorios base
    BASE_DIR = Path(__file__).parent.absolute()
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    OUTPUT_FOLDER = BASE_DIR / 'output'
    MODELS_FOLDER = BASE_DIR / 'models'
    MEDIA_FOLDER = BASE_DIR / 'media'
    
    # Configuración Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'syncdub-secret-key-2024')
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024 * 1024  # 8GB max file size

    # Configuración de archivos
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'}
    
    # Configuración de Media/NFS
    MEDIA_SOURCE_ENABLED = os.environ.get('MEDIA_SOURCE_ENABLED', 'false').lower() == 'true'
    MEDIA_SOURCE_PATH = os.environ.get('MEDIA_SOURCE_PATH', str(MEDIA_FOLDER))
    
    # Configuración de procesamiento
    WHISPER_MODEL = 'base'
    SENTENCE_TRANSFORMER_MODEL = 'paraphrase-multilingual-MiniLM-L12-v2'
    
    # Configuración de sincronización
    SIMILARITY_THRESHOLD = 0.7
    MAX_TIME_DRIFT = 10.0
    
    # Configuración de audio
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_FORMAT = 'wav'
    
    @staticmethod
    def init_app(app):
        """Inicializar configuración de la aplicación"""
        # Crear directorios si no existen
        for folder in [Config.UPLOAD_FOLDER, Config.OUTPUT_FOLDER, 
                      Config.MODELS_FOLDER, Config.MEDIA_FOLDER]:
            folder.mkdir(exist_ok=True)
        
        # Verificar acceso al volumen de media si está habilitado
        if Config.MEDIA_SOURCE_ENABLED:
            media_path = Path(Config.MEDIA_SOURCE_PATH)
            if not media_path.exists():
                app.logger.warning(f"Media source path does not exist: {media_path}")
            elif not os.access(media_path, os.R_OK):
                app.logger.warning(f"No read access to media source path: {media_path}")

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

