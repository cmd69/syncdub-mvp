"""
Servicio de sincronización de audio con IA - Versión con persistencia en base de datos
"""

import os
import gc
import uuid
import time
import threading
import subprocess
import json
import tempfile
import psutil
from pathlib import Path
from flask import current_app
from flask_login import current_user
import numpy as np
from typing import List, Tuple, Dict, Optional
from datetime import datetime

from app.models.database import db
from app.models.sync_job import SyncJob

class AudioSegment:
    """Representa un segmento de audio transcrito"""
    def __init__(self, start: float, end: float, text: str, confidence: float = 1.0):
        self.start = start
        self.end = end
        self.text = text.strip()
        self.confidence = confidence
        self.duration = end - start
    
    def __repr__(self):
        return f"AudioSegment({self.start:.2f}-{self.end:.2f}: '{self.text[:50]}...')"

class SyncService:
    """Servicio de sincronización de audio con IA optimizado para GPU y persistencia"""
    
    def __init__(self):
        self.tasks = {}  # Cache en memoria para acceso rápido
        self._lock = threading.Lock()
        self.app = None
        
        # Configuración de modelos IA
        self.whisper_model = None
        self.sentence_transformer = None
        self._models_loaded = False
        
        # Configuración de recursos
        self.max_memory_usage = 0.85  # 85% de memoria máxima
        self.chunk_size = 60  # Procesar audio en chunks de 60 segundos para archivos grandes
    
    def set_app(self, app):
        """Establecer la instancia de la aplicación Flask"""
        self.app = app
    
    def _check_memory_usage(self) -> bool:
        """Verificar uso de memoria del sistema"""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent / 100.0
            
            if usage_percent > self.max_memory_usage:
                current_app.logger.warning(f"High memory usage: {usage_percent:.1%}")
                return False
            return True
        except Exception:
            return True
    
    def _cleanup_memory(self):
        """Limpiar memoria y forzar garbage collection"""
        try:
            # Limpiar modelos si están cargados
            if self.whisper_model is not None:
                del self.whisper_model
                self.whisper_model = None
            
            if self.sentence_transformer is not None:
                del self.sentence_transformer
                self.sentence_transformer = None
            
            self._models_loaded = False
            
            # Forzar garbage collection
            gc.collect()
            
            # Limpiar cache de GPU si está disponible
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            
            current_app.logger.info("Memory cleanup completed")
        except Exception as e:
            current_app.logger.warning(f"Error during memory cleanup: {e}")
    
    def _load_ai_models_safe(self):
        """Cargar modelos de IA de forma segura con soporte GPU"""
        if self._models_loaded:
            return True
        
        try:
            # Verificar memoria disponible antes de cargar
            if not self._check_memory_usage():
                current_app.logger.warning("Insufficient memory for AI models")
                return False
            
            # Cargar Whisper con soporte GPU
            try:
                import whisper
                import torch
                
                # Determinar dispositivo (GPU si está disponible)
                device = "cuda" if torch.cuda.is_available() else "cpu"
                current_app.logger.info(f"Using device: {device}")
                
                # Usar modelo configurado
                model_name = current_app.config.get('WHISPER_MODEL', 'base')
                current_app.logger.info(f"Loading Whisper model: {model_name}")
                
                self.whisper_model = whisper.load_model(model_name, device=device)
                current_app.logger.info(f"Whisper model '{model_name}' loaded successfully on {device}")
            except Exception as e:
                current_app.logger.warning(f"Failed to load Whisper: {e}")
                return False
            
            # Verificar memoria después de cargar Whisper
            if not self._check_memory_usage():
                current_app.logger.warning("Memory limit reached after loading Whisper")
                del self.whisper_model
                self.whisper_model = None
                return False
            
            # Cargar Sentence Transformer
            try:
                from sentence_transformers import SentenceTransformer
                st_model_name = current_app.config.get('SENTENCE_TRANSFORMER_MODEL', 'paraphrase-multilingual-MiniLM-L12-v2')
                current_app.logger.info(f"Loading Sentence Transformer: {st_model_name}")
                
                self.sentence_transformer = SentenceTransformer(st_model_name)
                current_app.logger.info(f"Sentence Transformer loaded successfully")
            except Exception as e:
                current_app.logger.warning(f"Failed to load Sentence Transformer: {e}")
                # Continuar sin sentence transformer
            
            self._models_loaded = True
            return True
            
        except ImportError as e:
            current_app.logger.warning(f"AI libraries not available: {e}")
            return False
        except Exception as e:
            current_app.logger.error(f"Error loading AI models: {e}")
            self._cleanup_memory()
            return False
    
    def start_sync_task(self, task_id: str, original_path: str, dubbed_path: str, custom_name: str = '', source_type: str = 'local'):
        """Iniciar tarea de sincronización de forma asíncrona con persistencia en BD"""
        
        # Obtener usuario actual
        user_id = current_user.id if current_user.is_authenticated else None
        if not user_id:
            raise Exception("Usuario no autenticado")
        
        # Crear registro en base de datos
        sync_job = SyncJob(
            task_id=task_id,
            user_id=user_id,
            original_file_path=original_path,
            dubbed_file_path=dubbed_path,
            custom_filename=custom_name
        )
        
        db.session.add(sync_job)
        db.session.commit()
        
        # Agregar al cache en memoria
        with self._lock:
            self.tasks[task_id] = {
                'id': task_id,
                'status': 'pending',
                'progress': 0,
                'message': 'Tarea creada, esperando procesamiento...',
                'sync_job': sync_job
            }
        
        current_app.logger.info(f"Created sync job {task_id} for user {user_id}")
        
        # Ejecutar en hilo separado con contexto de aplicación
        thread = threading.Thread(target=self._process_with_context, args=(task_id,))
        thread.daemon = True
        thread.start()
    
    def _process_with_context(self, task_id: str):
        """Procesar tarea con contexto de aplicación Flask"""
        if not self.app:
            self._update_task_error(task_id, "Aplicación Flask no configurada")
            return
        
        with self.app.app_context():
            self._process_sync_task(task_id)
    
    def _process_sync_task(self, task_id: str):
        """Procesamiento optimizado de sincronización de audio"""
        try:
            current_app.logger.info(f"Starting sync task: {task_id}")
            
            # Obtener trabajo de la base de datos
            sync_job = SyncJob.get_by_task_id(task_id)
            if not sync_job:
                raise Exception("Trabajo no encontrado en base de datos")
            
            # Marcar como iniciado
            sync_job.start_processing()
            self._update_task_status(task_id, 'processing', 5, "Iniciando procesamiento...")
            
            original_path = sync_job.original_file_path
            dubbed_path = sync_job.dubbed_file_path
            
            # Verificar archivos de entrada
            self._update_task_status(task_id, 'processing', 10, "Verificando archivos de entrada...")
            if not os.path.exists(original_path):
                raise Exception(f"Archivo original no encontrado: {original_path}")
            if not os.path.exists(dubbed_path):
                raise Exception(f"Archivo doblado no encontrado: {dubbed_path}")
            
            # Verificar memoria disponible
            if not self._check_memory_usage():
                self._cleanup_memory()
            
            # Extraer audio de ambos videos
            self._update_task_status(task_id, 'processing', 20, "Extrayendo audio del video original...")
            original_audio = self._extract_audio(original_path, task_id, "original")
            
            self._update_task_status(task_id, 'processing', 35, "Extrayendo audio del video doblado...")
            dubbed_audio = self._extract_audio(dubbed_path, task_id, "dubbed")
            
            # Cargar modelos IA de forma segura
            self._update_task_status(task_id, 'processing', 50, "Preparando modelos de IA...")
            ai_available = self._load_ai_models_safe()
            
            if ai_available:
                # Transcribir audios con IA
                self._update_task_status(task_id, 'processing', 60, "Transcribiendo audio original...")
                original_segments = self._transcribe_audio(original_audio)
                
                self._update_task_status(task_id, 'processing', 70, "Transcribiendo audio doblado...")
                dubbed_segments = self._transcribe_audio(dubbed_audio)
                
                # Calcular offset con análisis semántico
                self._update_task_status(task_id, 'processing', 80, "Calculando sincronización...")
                time_offset = self._calculate_sync_offset(original_segments, dubbed_segments)
            else:
                # Modo fallback sin IA
                self._update_task_status(task_id, 'processing', 70, "Usando modo de compatibilidad...")
                time_offset = 0.0  # Sin offset por defecto
            
            # Aplicar sincronización
            self._update_task_status(task_id, 'processing', 85, "Aplicando sincronización...")
            synced_audio = self._apply_sync_offset(dubbed_audio, time_offset, task_id)
            
            # Generar archivo MKV final
            self._update_task_status(task_id, 'processing', 95, "Generando archivo MKV final...")
            result_path = self._generate_mkv_final(original_path, original_audio, synced_audio, task_id)
            
            # Completar tarea en base de datos
            sync_job.complete_successfully(result_path)
            self._update_task_status(task_id, 'completed', 100, '¡Sincronización completada exitosamente!')
            
            current_app.logger.info(f"Task completed successfully: {task_id}")
            
        except Exception as e:
            current_app.logger.error(f"Error processing task {task_id}: {str(e)}")
            
            # Marcar error en base de datos
            sync_job = SyncJob.get_by_task_id(task_id)
            if sync_job:
                sync_job.mark_error(str(e))
            
            self._update_task_error(task_id, f"Error en el procesamiento: {str(e)}")
        finally:
            # Limpiar archivos temporales y memoria
            self._cleanup_task_files(task_id)
            self._cleanup_memory()
    
    def _extract_audio(self, video_path: str, task_id: str, prefix: str) -> str:
        """Extraer audio de video usando FFmpeg"""
        try:
            audio_path = os.path.join(tempfile.gettempdir(), f"{prefix}_{task_id}.wav")
            
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # Sin video
                '-acodec', 'pcm_s16le',  # Codec de audio
                '-ar', '16000',  # Sample rate
                '-ac', '1',  # Mono
                '-y',  # Sobrescribir
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            if result.returncode != 0:
                raise Exception(f"Error extrayendo audio: {result.stderr}")
            
            return audio_path
            
        except subprocess.TimeoutExpired:
            raise Exception("Timeout extrayendo audio - archivo demasiado grande")
        except Exception as e:
            raise Exception(f"Error extrayendo audio: {str(e)}")
    
    def _transcribe_audio(self, audio_path: str) -> List[AudioSegment]:
        """Transcribir audio usando Whisper"""
        try:
            if not self.whisper_model:
                return []
            
            result = self.whisper_model.transcribe(audio_path)
            
            segments = []
            for segment in result.get('segments', []):
                audio_segment = AudioSegment(
                    start=segment['start'],
                    end=segment['end'],
                    text=segment['text'],
                    confidence=1.0
                )
                segments.append(audio_segment)
            
            return segments
            
        except Exception as e:
            current_app.logger.warning(f"Transcription failed: {e}")
            return []
    
    def _calculate_sync_offset(self, original_segments: List[AudioSegment], 
                              dubbed_segments: List[AudioSegment]) -> float:
        """Calcular offset de sincronización"""
        try:
            if not self.sentence_transformer or not original_segments or not dubbed_segments:
                return 0.0
            
            # Usar solo los primeros segmentos para análisis
            orig_texts = [seg.text for seg in original_segments[:10] if seg.text.strip()]
            dub_texts = [seg.text for seg in dubbed_segments[:10] if seg.text.strip()]
            
            if not orig_texts or not dub_texts:
                return 0.0
            
            # Calcular embeddings
            orig_embeddings = self.sentence_transformer.encode(orig_texts)
            dub_embeddings = self.sentence_transformer.encode(dub_texts)
            
            # Encontrar mejor correspondencia
            best_offset = 0.0
            best_similarity = 0.0
            
            for i, orig_emb in enumerate(orig_embeddings):
                for j, dub_emb in enumerate(dub_embeddings):
                    similarity = np.dot(orig_emb, dub_emb) / (np.linalg.norm(orig_emb) * np.linalg.norm(dub_emb))
                    
                    if similarity > best_similarity and similarity > 0.6:
                        best_similarity = similarity
                        best_offset = dubbed_segments[j].start - original_segments[i].start
            
            current_app.logger.info(f"Calculated offset: {best_offset:.3f}s (similarity: {best_similarity:.3f})")
            return best_offset
            
        except Exception as e:
            current_app.logger.warning(f"Offset calculation failed: {e}")
            return 0.0
    
    def _apply_sync_offset(self, audio_path: str, offset: float, task_id: str) -> str:
        """Aplicar desfase temporal al audio"""
        try:
            synced_audio_path = os.path.join(tempfile.gettempdir(), f"synced_{task_id}.wav")
            
            if abs(offset) < 0.1:  # Offset muy pequeño, copiar archivo
                import shutil
                shutil.copy2(audio_path, synced_audio_path)
            elif offset > 0:  # Retrasar audio
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-af', f'adelay={int(abs(offset) * 1000)}|{int(abs(offset) * 1000)}',
                    '-y', synced_audio_path
                ]
            else:  # Adelantar audio
                cmd = [
                    'ffmpeg', '-ss', str(abs(offset)), '-i', audio_path,
                    '-y', synced_audio_path
                ]
            
            if abs(offset) >= 0.1:  # Solo ejecutar FFmpeg si hay offset significativo
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode != 0:
                    raise Exception(f"Error aplicando sincronización: {result.stderr}")
            
            return synced_audio_path
            
        except Exception as e:
            raise Exception(f"Error aplicando sincronización: {str(e)}")
    
    def _generate_mkv_final(self, original_video: str, original_audio: str, 
                           synced_audio: str, task_id: str) -> str:
        """Generar archivo MKV final con video original y ambas pistas de audio"""
        try:
            output_dir = current_app.config['OUTPUT_FOLDER']
            output_dir.mkdir(exist_ok=True)
            
            # Determinar nombre del archivo
            sync_job = SyncJob.get_by_task_id(task_id)
            custom_filename = sync_job.custom_filename if sync_job else ''
            
            if custom_filename:
                if not custom_filename.lower().endswith('.mkv'):
                    custom_filename += '.mkv'
                result_filename = custom_filename
            else:
                result_filename = f"synced_{task_id}.mkv"
            
            result_path = output_dir / result_filename
            
            # Comando FFmpeg para generar MKV
            cmd = [
                'ffmpeg',
                '-i', original_video,    # Video original
                '-i', original_audio,    # Audio original
                '-i', synced_audio,      # Audio sincronizado
                '-map', '0:v',           # Video del primer input
                '-map', '1:a',           # Audio original
                '-map', '2:a',           # Audio sincronizado
                '-c:v', 'copy',          # Copiar video sin recodificar
                '-c:a', 'aac',           # Codec de audio
                '-b:a', '192k',          # Bitrate de audio
                '-metadata:s:a:0', 'title=Original',
                '-metadata:s:a:0', 'language=eng',
                '-metadata:s:a:1', 'title=Doblado',
                '-metadata:s:a:1', 'language=spa',
                '-y',                    # Sobrescribir
                str(result_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            if result.returncode != 0:
                raise Exception(f"Error generando MKV: {result.stderr}")
            
            return str(result_path)
            
        except Exception as e:
            raise Exception(f"Error generando archivo MKV: {str(e)}")
    
    def _update_task_status(self, task_id: str, status: str, progress: int, message: str):
        """Actualizar estado de la tarea en memoria y BD"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].update({
                    'status': status,
                    'progress': progress,
                    'message': message
                })
        
        # Actualizar en base de datos
        sync_job = SyncJob.get_by_task_id(task_id)
        if sync_job:
            sync_job.update_progress(progress, message)
    
    def _update_task_error(self, task_id: str, error_message: str):
        """Actualizar tarea con error"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].update({
                    'status': 'error',
                    'error': error_message,
                    'message': f'Error: {error_message}'
                })
    
    def _cleanup_task_files(self, task_id: str):
        """Limpiar archivos temporales de una tarea"""
        try:
            temp_files = [
                f"original_{task_id}.wav",
                f"dubbed_{task_id}.wav",
                f"synced_{task_id}.wav"
            ]
            
            for filename in temp_files:
                file_path = os.path.join(tempfile.gettempdir(), filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
        except Exception as e:
            current_app.logger.warning(f"Error during cleanup: {e}")
    
    def get_task_status(self, task_id: str):
        """Obtener estado de una tarea desde BD"""
        sync_job = SyncJob.get_by_task_id(task_id)
        if not sync_job:
            return {'status': 'not_found', 'error': 'Tarea no encontrada'}
        
        return sync_job.to_dict()
    
    def get_result_path(self, task_id: str) -> str:
        """Obtener ruta del archivo resultado"""
        sync_job = SyncJob.get_by_task_id(task_id)
        if sync_job and sync_job.output_file_path:
            return sync_job.output_file_path
        return None
    
    def list_user_tasks(self, user_id: int, limit: int = None):
        """Listar tareas de un usuario"""
        jobs = SyncJob.get_user_jobs(user_id, limit)
        return {
            'tasks': [job.to_dict() for job in jobs],
            'total': len(jobs)
        }
    
    def list_all_tasks(self):
        """Listar todas las tareas (para compatibilidad)"""
        if current_user.is_authenticated:
            return self.list_user_tasks(current_user.id)
        return {'tasks': [], 'total': 0}

# Instancia global del servicio
sync_service = SyncService()

