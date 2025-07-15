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
    
    # Duración máxima a extraer de cada audio (en segundos)
    AUDIO_EXTRACT_DURATION = int(os.environ.get('AUDIO_EXTRACT_DURATION', 900))  # 15 minutos por defecto

    # Configuración de limpieza de segmentos (puede ser un dict JSON en el entorno)
    SEGMENT_CLEANING_CONFIG = {
        "min_duration": 0.5,   # Permitir segmentos desde 0.5s
        "max_duration": 60.0,  # Hasta 1 minuto
        "min_words": 1         # Permitir segmentos de una sola palabra
    }

    # Opciones de inferencia de Whisper (puede ser extendido)
    WHISPER_OPTIONS = {
        'temperature': [float(x) for x in os.environ.get('WHISPER_TEMPERATURE', '0.0').split(',')],
        'beam_size': int(os.environ.get('WHISPER_BEAM_SIZE', 5)),
    }

    # Idioma de transcripción principal
    TRANSCRIPTION_LANGUAGE = os.environ.get('TRANSCRIPTION_LANGUAGE', 'es')

    # Modo test para transcripción (extraer solo fragmento)
    TRANSCRIPTION_TEST_MODE = os.environ.get('TRANSCRIPTION_TEST_MODE', 'false').lower() == 'true'

    # Porcentaje máximo de uso de memoria permitido (float entre 0 y 1)
    MAX_MEMORY_USAGE = float(os.environ.get('MAX_MEMORY_USAGE', 0.85))
    
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
    WHISPER_MODEL = 'tiny'  # Modelo más pequeño para desarrollo
    
class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False

# Configuraciones disponibles
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}

