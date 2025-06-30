"""
Servicio real de sincronización de audio con IA
"""

import os
import uuid
import time
import threading
import subprocess
import json
import tempfile
from pathlib import Path
from flask import current_app
import numpy as np
from typing import List, Tuple, Dict, Optional

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
    """Servicio real de sincronización de audio con IA"""
    
    def __init__(self):
        self.tasks = {}
        self._lock = threading.Lock()
        self.app = None
        
        # Configuración de modelos IA
        self.whisper_model = None
        self.sentence_transformer = None
        self._models_loaded = False
    
    def set_app(self, app):
        """Establecer la instancia de la aplicación Flask"""
        self.app = app
    
    def _load_ai_models(self):
        """Cargar modelos de IA (lazy loading)"""
        if self._models_loaded:
            return
        
        try:
            # Cargar Whisper
            import whisper
            model_name = current_app.config.get('WHISPER_MODEL', 'base')
            self.whisper_model = whisper.load_model(model_name)
            current_app.logger.info(f"Whisper model '{model_name}' loaded successfully")
            
            # Cargar Sentence Transformer
            from sentence_transformers import SentenceTransformer
            st_model_name = current_app.config.get('SENTENCE_TRANSFORMER_MODEL', 'paraphrase-multilingual-MiniLM-L12-v2')
            self.sentence_transformer = SentenceTransformer(st_model_name)
            current_app.logger.info(f"Sentence Transformer '{st_model_name}' loaded successfully")
            
            self._models_loaded = True
            
        except ImportError as e:
            current_app.logger.warning(f"AI models not available: {e}. Using fallback mode.")
            self._models_loaded = False
        except Exception as e:
            current_app.logger.error(f"Error loading AI models: {e}")
            self._models_loaded = False
    
    def create_task(self, original_path: str, dubbed_path: str, custom_filename: str = '') -> str:
        """Crear una nueva tarea de sincronización"""
        task_id = str(uuid.uuid4())
        
        with self._lock:
            self.tasks[task_id] = {
                'id': task_id,
                'original_path': original_path,
                'dubbed_path': dubbed_path,
                'custom_filename': custom_filename,
                'status': 'pending',
                'progress': 0,
                'message': 'Tarea creada',
                'result_path': None,
                'created_at': time.time(),
                'error': None,
                'temp_files': []  # Para limpiar archivos temporales
            }
        
        # Iniciar procesamiento en hilo separado con contexto de aplicación
        thread = threading.Thread(target=self._process_with_context, args=(task_id,))
        thread.daemon = True
        thread.start()
        
        return task_id
    
    def _process_with_context(self, task_id: str):
        """Procesar tarea con contexto de aplicación Flask"""
        if not self.app:
            self._update_task_error(task_id, "Aplicación Flask no configurada")
            return
        
        with self.app.app_context():
            self._process_task_real(task_id)
    
    def _process_task_real(self, task_id: str):
        """Procesamiento real de sincronización de audio"""
        try:
            self._update_task_status(task_id, 'processing', 5, "Verificando archivos de entrada...")
            
            # Verificar archivos de entrada
            task = self.tasks[task_id]
            original_path = task['original_path']
            dubbed_path = task['dubbed_path']
            
            if not os.path.exists(original_path):
                raise Exception(f"Archivo original no encontrado: {original_path}")
            if not os.path.exists(dubbed_path):
                raise Exception(f"Archivo doblado no encontrado: {dubbed_path}")
            
            # Cargar modelos IA
            self._update_task_status(task_id, 'processing', 10, "Cargando modelos de IA...")
            self._load_ai_models()
            
            # Extraer audio de ambos videos
            self._update_task_status(task_id, 'processing', 15, "Extrayendo audio del video original...")
            original_audio = self._extract_audio(original_path, task_id, "original")
            
            self._update_task_status(task_id, 'processing', 25, "Extrayendo audio del video doblado...")
            dubbed_audio = self._extract_audio(dubbed_path, task_id, "dubbed")
            
            # Transcribir audios
            self._update_task_status(task_id, 'processing', 35, "Transcribiendo audio original...")
            original_segments = self._transcribe_audio(original_audio, task_id)
            
            self._update_task_status(task_id, 'processing', 50, "Transcribiendo audio doblado...")
            dubbed_segments = self._transcribe_audio(dubbed_audio, task_id)
            
            # Analizar correspondencias semánticas
            self._update_task_status(task_id, 'processing', 65, "Analizando correspondencias semánticas...")
            time_offset = self._calculate_sync_offset(original_segments, dubbed_segments, task_id)
            
            # Aplicar sincronización y generar MKV
            self._update_task_status(task_id, 'processing', 80, "Sincronizando audio...")
            synced_audio = self._apply_sync_offset(dubbed_audio, time_offset, task_id)
            
            self._update_task_status(task_id, 'processing', 90, "Generando archivo MKV final...")
            result_path = self._generate_mkv_output(original_path, original_audio, synced_audio, task_id)
            
            # Completar tarea
            self._update_task_status(task_id, 'completed', 100, "Sincronización completada exitosamente")
            with self._lock:
                self.tasks[task_id]['result_path'] = result_path
            
            # Limpiar archivos temporales
            self._cleanup_temp_files(task_id)
            
        except Exception as e:
            current_app.logger.error(f"Error processing task {task_id}: {str(e)}")
            self._update_task_error(task_id, f"Error en el procesamiento: {str(e)}")
            self._cleanup_temp_files(task_id)
    
    def _extract_audio(self, video_path: str, task_id: str, prefix: str) -> str:
        """Extraer audio de un video usando FFmpeg"""
        try:
            # Crear archivo temporal para el audio
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, f"{prefix}_{task_id}.wav")
            
            # Comando FFmpeg para extraer audio
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # Sin video
                '-acodec', 'pcm_s16le',  # Codec de audio
                '-ar', '16000',  # Sample rate
                '-ac', '1',  # Mono
                '-y',  # Sobrescribir
                audio_path
            ]
            
            # Ejecutar FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Error extrayendo audio: {result.stderr}")
            
            # Agregar a archivos temporales para limpieza
            with self._lock:
                self.tasks[task_id]['temp_files'].append(audio_path)
            
            current_app.logger.info(f"Audio extracted: {audio_path}")
            return audio_path
            
        except Exception as e:
            raise Exception(f"Error extrayendo audio de {video_path}: {str(e)}")
    
    def _transcribe_audio(self, audio_path: str, task_id: str) -> List[AudioSegment]:
        """Transcribir audio usando Whisper"""
        try:
            if not self._models_loaded or not self.whisper_model:
                # Fallback: crear segmentos simulados
                return self._create_fallback_segments(audio_path)
            
            # Transcribir con Whisper
            result = self.whisper_model.transcribe(
                audio_path,
                word_timestamps=True,
                language=None  # Auto-detectar idioma
            )
            
            segments = []
            for segment in result['segments']:
                audio_segment = AudioSegment(
                    start=segment['start'],
                    end=segment['end'],
                    text=segment['text'],
                    confidence=segment.get('avg_logprob', 0.0)
                )
                segments.append(audio_segment)
            
            current_app.logger.info(f"Transcribed {len(segments)} segments from {audio_path}")
            return segments
            
        except Exception as e:
            current_app.logger.warning(f"Error in Whisper transcription: {e}. Using fallback.")
            return self._create_fallback_segments(audio_path)
    
    def _create_fallback_segments(self, audio_path: str) -> List[AudioSegment]:
        """Crear segmentos de audio simulados cuando Whisper no está disponible"""
        try:
            # Obtener duración del audio usando FFprobe
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip()) if result.returncode == 0 else 60.0
            
            # Crear segmentos simulados cada 5 segundos
            segments = []
            for i in range(0, int(duration), 5):
                start = i
                end = min(i + 5, duration)
                text = f"Segmento de audio {i//5 + 1}"
                segments.append(AudioSegment(start, end, text))
            
            return segments
            
        except Exception as e:
            current_app.logger.error(f"Error creating fallback segments: {e}")
            # Crear al menos un segmento
            return [AudioSegment(0, 60, "Audio segment")]
    
    def _calculate_sync_offset(self, original_segments: List[AudioSegment], 
                             dubbed_segments: List[AudioSegment], task_id: str) -> float:
        """Calcular desfase temporal usando análisis semántico"""
        try:
            if not self._models_loaded or not self.sentence_transformer:
                # Fallback: calcular offset simple basado en duración
                return self._calculate_simple_offset(original_segments, dubbed_segments)
            
            # Extraer textos para análisis semántico
            original_texts = [seg.text for seg in original_segments if seg.text.strip()]
            dubbed_texts = [seg.text for seg in dubbed_segments if seg.text.strip()]
            
            if not original_texts or not dubbed_texts:
                return 0.0
            
            # Calcular embeddings
            original_embeddings = self.sentence_transformer.encode(original_texts)
            dubbed_embeddings = self.sentence_transformer.encode(dubbed_texts)
            
            # Encontrar mejores correspondencias
            best_matches = []
            similarity_threshold = current_app.config.get('SIMILARITY_THRESHOLD', 0.7)
            
            for i, orig_emb in enumerate(original_embeddings):
                best_similarity = -1
                best_match_idx = -1
                
                for j, dub_emb in enumerate(dubbed_embeddings):
                    similarity = np.dot(orig_emb, dub_emb) / (np.linalg.norm(orig_emb) * np.linalg.norm(dub_emb))
                    
                    if similarity > best_similarity and similarity > similarity_threshold:
                        best_similarity = similarity
                        best_match_idx = j
                
                if best_match_idx >= 0:
                    time_diff = dubbed_segments[best_match_idx].start - original_segments[i].start
                    best_matches.append((time_diff, best_similarity))
            
            if not best_matches:
                current_app.logger.warning("No semantic matches found, using simple offset")
                return self._calculate_simple_offset(original_segments, dubbed_segments)
            
            # Calcular offset promedio ponderado por similitud
            weighted_sum = sum(offset * similarity for offset, similarity in best_matches)
            total_weight = sum(similarity for _, similarity in best_matches)
            
            calculated_offset = weighted_sum / total_weight if total_weight > 0 else 0.0
            
            current_app.logger.info(f"Calculated sync offset: {calculated_offset:.3f}s from {len(best_matches)} matches")
            return calculated_offset
            
        except Exception as e:
            current_app.logger.warning(f"Error in semantic analysis: {e}. Using simple offset.")
            return self._calculate_simple_offset(original_segments, dubbed_segments)
    
    def _calculate_simple_offset(self, original_segments: List[AudioSegment], 
                                dubbed_segments: List[AudioSegment]) -> float:
        """Calcular offset simple basado en inicio de primer segmento"""
        if not original_segments or not dubbed_segments:
            return 0.0
        
        # Usar diferencia entre primeros segmentos
        offset = dubbed_segments[0].start - original_segments[0].start
        current_app.logger.info(f"Simple offset calculated: {offset:.3f}s")
        return offset
    
    def _apply_sync_offset(self, audio_path: str, offset: float, task_id: str) -> str:
        """Aplicar desfase temporal al audio doblado"""
        try:
            temp_dir = tempfile.gettempdir()
            synced_audio_path = os.path.join(temp_dir, f"synced_{task_id}.wav")
            
            # Comando FFmpeg para aplicar offset
            if offset > 0:
                # Retrasar audio (agregar silencio al inicio)
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-af', f'adelay={int(abs(offset) * 1000)}|{int(abs(offset) * 1000)}',
                    '-y', synced_audio_path
                ]
            elif offset < 0:
                # Adelantar audio (cortar desde el inicio)
                cmd = [
                    'ffmpeg', '-ss', str(abs(offset)), '-i', audio_path,
                    '-y', synced_audio_path
                ]
            else:
                # Sin offset, copiar archivo
                cmd = ['cp', audio_path, synced_audio_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Error aplicando sincronización: {result.stderr}")
            
            # Agregar a archivos temporales
            with self._lock:
                self.tasks[task_id]['temp_files'].append(synced_audio_path)
            
            current_app.logger.info(f"Sync applied: {offset:.3f}s offset to {synced_audio_path}")
            return synced_audio_path
            
        except Exception as e:
            raise Exception(f"Error aplicando sincronización: {str(e)}")
    
    def _generate_mkv_output(self, original_video: str, original_audio: str, 
                           synced_audio: str, task_id: str) -> str:
        """Generar archivo MKV final con video original y ambas pistas de audio"""
        try:
            # Determinar nombre del archivo de salida
            task = self.tasks[task_id]
            custom_filename = task.get('custom_filename', '')
            
            output_dir = Path(current_app.config['OUTPUT_FOLDER'])
            output_dir.mkdir(exist_ok=True)
            
            if custom_filename:
                if not custom_filename.lower().endswith('.mkv'):
                    custom_filename += '.mkv'
                result_filename = custom_filename
            else:
                result_filename = f"synced_{task_id}.mkv"
            
            result_path = output_dir / result_filename
            
            # Comando FFmpeg para crear MKV con múltiples pistas de audio
            cmd = [
                'ffmpeg',
                '-i', original_video,      # Video original
                '-i', original_audio,      # Audio original
                '-i', synced_audio,        # Audio doblado sincronizado
                '-map', '0:v',             # Video del primer input
                '-map', '1:a',             # Audio original del segundo input
                '-map', '2:a',             # Audio doblado del tercer input
                '-c:v', 'copy',            # Copiar video sin recodificar
                '-c:a', 'aac',             # Codec de audio AAC
                '-metadata:s:a:0', 'title=Original',
                '-metadata:s:a:1', 'title=Dubbed (Synced)',
                '-metadata:s:a:0', 'language=eng',
                '-metadata:s:a:1', 'language=spa',
                '-y',                      # Sobrescribir archivo existente
                str(result_path)
            ]
            
            # Ejecutar FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Error generando MKV: {result.stderr}")
            
            # Verificar que el archivo se creó correctamente
            if not result_path.exists():
                raise Exception("El archivo MKV no se generó correctamente")
            
            file_size = result_path.stat().st_size
            if file_size < 1024:  # Menos de 1KB indica error
                raise Exception(f"Archivo MKV demasiado pequeño: {file_size} bytes")
            
            current_app.logger.info(f"MKV generated successfully: {result_path} ({file_size} bytes)")
            return str(result_path)
            
        except Exception as e:
            raise Exception(f"Error generando archivo MKV: {str(e)}")
    
    def _cleanup_temp_files(self, task_id: str):
        """Limpiar archivos temporales"""
        try:
            with self._lock:
                temp_files = self.tasks.get(task_id, {}).get('temp_files', [])
            
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        current_app.logger.debug(f"Cleaned up temp file: {temp_file}")
                except OSError as e:
                    current_app.logger.warning(f"Could not remove temp file {temp_file}: {e}")
            
            # Limpiar lista de archivos temporales
            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id]['temp_files'] = []
                    
        except Exception as e:
            current_app.logger.error(f"Error cleaning up temp files for task {task_id}: {e}")
    
    def _update_task_status(self, task_id: str, status: str, progress: int, message: str):
        """Actualizar estado de una tarea"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = status
                self.tasks[task_id]['progress'] = progress
                self.tasks[task_id]['message'] = message
    
    def _update_task_error(self, task_id: str, error_message: str):
        """Actualizar tarea con error"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = 'error'
                self.tasks[task_id]['error'] = error_message
                self.tasks[task_id]['message'] = f'Error: {error_message}'
    
    def get_task_status(self, task_id: str) -> dict:
        """Obtener estado de una tarea"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return {'error': 'Tarea no encontrada'}
            
            return {
                'task_id': task_id,
                'status': task['status'],
                'progress': task['progress'],
                'message': task['message'],
                'error': task.get('error'),
                'created_at': task['created_at']
            }
    
    def get_result_path(self, task_id: str) -> tuple:
        """Obtener ruta del archivo resultado y nombre personalizado"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                result_path = task.get('result_path')
                custom_name = task.get('custom_filename', '')
                if custom_name and not custom_name.lower().endswith('.mkv'):
                    custom_name += '.mkv'
                return result_path, custom_name
            return None, None
    
    def list_all_tasks(self) -> list:
        """Listar todas las tareas"""
        with self._lock:
            return [
                {
                    'task_id': task_id,
                    'status': task['status'],
                    'progress': task['progress'],
                    'message': task['message'],
                    'created_at': task['created_at'],
                    'custom_filename': task.get('custom_filename', '')
                }
                for task_id, task in self.tasks.items()
            ]
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Limpiar tareas antiguas"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        with self._lock:
            old_tasks = [
                task_id for task_id, task in self.tasks.items()
                if current_time - task['created_at'] > max_age_seconds
            ]
            
            for task_id in old_tasks:
                # Limpiar archivos temporales
                self._cleanup_temp_files(task_id)
                
                # Eliminar archivo de resultado si existe
                task = self.tasks[task_id]
                result_path = task.get('result_path')
                if result_path and os.path.exists(result_path):
                    try:
                        os.remove(result_path)
                    except OSError:
                        pass
                
                # Eliminar tarea
                del self.tasks[task_id]
            
            return len(old_tasks)

