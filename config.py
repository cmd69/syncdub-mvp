"""
Configuración de la aplicación SyncDub MVP
"""

import os
from pathlib import Path

class Config:
    """Configuración base de la aplicación SyncDub"""
    
    # Directorios base
    BASE_DIR = Path(__file__).parent.absolute()
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    OUTPUT_FOLDER = BASE_DIR / 'output'
    MODELS_FOLDER = BASE_DIR / 'models'
    
    # Configuración de base de datos
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{BASE_DIR}/syncdub.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de autenticación
    DEFAULT_ADMIN_USER = os.environ.get('DEFAULT_ADMIN_USER', 'admin')
    DEFAULT_ADMIN_PASSWORD = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin')
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', 3600))  # 1 hora
    REMEMBER_COOKIE_DURATION = int(os.environ.get('REMEMBER_COOKIE_DURATION', 86400))  # 24 horas
    
    # Configuración de volumen de medios
    MEDIA_SOURCE_ENABLED = os.environ.get('MEDIA_SOURCE_ENABLED', 'false').lower() == 'true'
    MEDIA_SOURCE_PATH = os.environ.get('MEDIA_SOURCE_PATH', str(BASE_DIR / 'video_source'))
    
    # Configuración Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'syncdub-secret-key-2024')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 21474836480))  # 20GB por defecto
    
    # Configuración de archivos
    ALLOWED_VIDEO_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'mp4,avi,mkv,mov,wmv,flv,webm').split(','))
    
    # Configuración de modelos IA
    WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'base')
    SENTENCE_TRANSFORMER_MODEL = os.environ.get('SENTENCE_TRANSFORMER_MODEL', 'paraphrase-multilingual-MiniLM-L12-v2')
    
    # Configuración de sincronización
    SIMILARITY_THRESHOLD = float(os.environ.get('SIMILARITY_THRESHOLD', 0.7))
    MAX_TIME_DRIFT = float(os.environ.get('MAX_TIME_DRIFT', 10.0))
    
    # Configuración de audio
    AUDIO_SAMPLE_RATE = int(os.environ.get('AUDIO_SAMPLE_RATE', 16000))
    AUDIO_FORMAT = os.environ.get('AUDIO_FORMAT', 'wav')
    OUTPUT_AUDIO_BITRATE = os.environ.get('OUTPUT_AUDIO_BITRATE', '192k')
    
    # Configuración de procesamiento
    NUM_THREADS = int(os.environ.get('NUM_THREADS', 0))  # 0 = usar todos los cores
    AUDIO_CHUNK_SIZE = int(os.environ.get('AUDIO_CHUNK_SIZE', 60))  # segundos
    MAX_PROCESSING_TIME = int(os.environ.get('MAX_PROCESSING_TIME', 3600))  # 1 hora
    
    # Configuración de limpieza
    AUTO_CLEANUP = os.environ.get('AUTO_CLEANUP', 'true').lower() == 'true'
    TASK_RETENTION_HOURS = int(os.environ.get('TASK_RETENTION_HOURS', 24))
    
    # Configuración de logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    FFMPEG_VERBOSE = os.environ.get('FFMPEG_VERBOSE', 'false').lower() == 'true'
    MEMORY_MONITORING = os.environ.get('MEMORY_MONITORING', 'true').lower() == 'true'
    
    @staticmethod
    def init_app(app):
        """Inicializar configuración de la aplicación"""
        # Crear directorios si no existen
        for folder in [Config.UPLOAD_FOLDER, Config.OUTPUT_FOLDER, 
                      Config.MODELS_FOLDER]:
            folder.mkdir(exist_ok=True)
        
        # Crear directorio de medios si está habilitado
        if Config.MEDIA_SOURCE_ENABLED:
            media_path = Path(Config.MEDIA_SOURCE_PATH)
            media_path.mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Configurar logging para producción
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug and not app.testing:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            
            file_handler = RotatingFileHandler('logs/syncdub.log', maxBytes=10240000, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('SyncDub MVP startup')

# Configuraciones disponibles
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}

