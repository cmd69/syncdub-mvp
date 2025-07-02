"""
Servicio de sincronización de audio con IA - Versión GPU optimizada
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
import numpy as np
from typing import List, Tuple, Dict, Optional
from datetime import datetime

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
    """Servicio de sincronización de audio con IA optimizado para GPU"""
    
    def __init__(self):
        self.tasks = {}
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
                current_app.logger.warning("Insufficient memory for AI models, using fallback mode")
                return False
            
            # Cargar Whisper con soporte GPU
            try:
                import whisper
                import torch
                
                # Determinar dispositivo (GPU si está disponible)
                device = "cuda" if torch.cuda.is_available() else "cpu"
                current_app.logger.info(f"Using device: {device}")
                
                # Usar modelo base para balance entre calidad y recursos
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
                
                # Configurar dispositivo para sentence transformer
                device_st = "cuda" if torch.cuda.is_available() else "cpu"
                self.sentence_transformer = SentenceTransformer(st_model_name, device=device_st)
                current_app.logger.info(f"Sentence Transformer loaded successfully on {device_st}")
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
    
    def start_sync_task(self, task_id: str, original_path: str, dubbed_path: str, custom_filename: str = ''):
        """Iniciar tarea de sincronización de forma asíncrona"""
        with self._lock:
            self.tasks[task_id] = {
                'id': task_id,
                'status': 'processing',
                'progress': 0,
                'message': 'Iniciando procesamiento...',
                'original_path': original_path,
                'dubbed_path': dubbed_path,
                'custom_filename': custom_filename,
                'result_path': None,
                'created_at': datetime.now().isoformat(),
                'error': None,
                'temp_files': []
            }
        
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
        """Procesamiento optimizado de sincronización de audio para archivos grandes"""
        try:
            current_app.logger.info(f"Starting sync task: {task_id}")
            
            # Verificar archivos de entrada
            self._update_task_status(task_id, 'processing', 5, "Verificando archivos de entrada...")
            task = self.tasks[task_id]
            original_path = task['original_path']
            dubbed_path = task['dubbed_path']
            
            if not os.path.exists(original_path):
                raise Exception(f"Archivo original no encontrado: {original_path}")
            if not os.path.exists(dubbed_path):
                raise Exception(f"Archivo doblado no encontrado: {dubbed_path}")
            
            # Verificar tamaño de archivos (máximo 20GB)
            max_size = 20 * 1024 * 1024 * 1024  # 20GB
            orig_size = os.path.getsize(original_path)
            dub_size = os.path.getsize(dubbed_path)
            
            if orig_size > max_size or dub_size > max_size:
                raise Exception(f"Archivo demasiado grande. Máximo permitido: 20GB")
            
            current_app.logger.info(f"File sizes - Original: {orig_size/(1024**3):.2f}GB, Dubbed: {dub_size/(1024**3):.2f}GB")
            
            # Verificar memoria disponible
            if not self._check_memory_usage():
                self._cleanup_memory()
            
            # Extraer audio de ambos videos
            self._update_task_status(task_id, 'processing', 15, "Extrayendo audio del video original...")
            original_audio = self._extract_audio_optimized(original_path, task_id, "original")
            
            self._update_task_status(task_id, 'processing', 25, "Extrayendo audio del video doblado...")
            dubbed_audio = self._extract_audio_optimized(dubbed_path, task_id, "dubbed")
            
            # Cargar modelos IA de forma segura
            self._update_task_status(task_id, 'processing', 35, "Preparando modelos de IA...")
            ai_available = self._load_ai_models_safe()
            
            if ai_available:
                # Transcribir audios con IA
                self._update_task_status(task_id, 'processing', 45, "Transcribiendo audio original...")
                original_segments = self._transcribe_audio_safe(original_audio, task_id)
                
                self._update_task_status(task_id, 'processing', 60, "Transcribiendo audio doblado...")
                dubbed_segments = self._transcribe_audio_safe(dubbed_audio, task_id)
                
                # Calcular offset con análisis semántico
                self._update_task_status(task_id, 'processing', 75, "Calculando sincronización...")
                time_offset = self._calculate_sync_offset_safe(original_segments, dubbed_segments)
            else:
                # Modo fallback sin IA
                self._update_task_status(task_id, 'processing', 60, "Usando modo de compatibilidad...")
                time_offset = self._calculate_simple_offset_from_audio(original_audio, dubbed_audio)
            
            # Aplicar sincronización
            self._update_task_status(task_id, 'processing', 85, "Aplicando sincronización...")
            synced_audio = self._apply_sync_offset(dubbed_audio, time_offset, task_id)
            
            # Generar archivo MKV final
            self._update_task_status(task_id, 'processing', 95, "Generando archivo MKV final...")
            result_path = self._generate_mkv_final(original_path, original_audio, synced_audio, task_id)
            
            # Completar tarea
            with self._lock:
                self.tasks[task_id]['result_path'] = result_path
                self.tasks[task_id]['status'] = 'completed'
                self.tasks[task_id]['progress'] = 100
                self.tasks[task_id]['message'] = '¡Sincronización completada exitosamente!'
            
            current_app.logger.info(f"Task completed successfully: {task_id}")
            
        except Exception as e:
            current_app.logger.error(f"Error processing task {task_id}: {str(e)}")
            self._update_task_error(task_id, f"Error en el procesamiento: {str(e)}")
        finally:
            # Limpiar archivos temporales y memoria
            self._cleanup_task_files(task_id)
            self._cleanup_memory()
    
    def _extract_audio_optimized(self, video_path: str, task_id: str, prefix: str) -> str:
        """Extraer audio de forma optimizada para archivos grandes"""
        try:
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, f"{prefix}_{task_id}.wav")
            
            # Comando FFmpeg optimizado para archivos grandes
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # Sin video
                '-acodec', 'pcm_s16le',  # Codec de audio
                '-ar', '16000',  # Sample rate
                '-ac', '1',  # Mono
                '-map_metadata', '-1',  # Sin metadatos
                '-fflags', '+bitexact',  # Reproducible
                '-threads', '0',  # Usar todos los cores disponibles
                '-y',  # Sobrescribir
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 min timeout
            if result.returncode != 0:
                raise Exception(f"Error extrayendo audio: {result.stderr}")
            
            # Agregar a archivos temporales
            with self._lock:
                self.tasks[task_id]['temp_files'].append(audio_path)
            
            current_app.logger.info(f"Audio extracted successfully: {audio_path}")
            return audio_path
            
        except subprocess.TimeoutExpired:
            raise Exception("Timeout extrayendo audio - archivo demasiado grande o proceso bloqueado")
        except Exception as e:
            raise Exception(f"Error extrayendo audio: {str(e)}")
    
    def _transcribe_audio_safe(self, audio_path: str, task_id: str) -> List[AudioSegment]:
        """Transcribir audio de forma segura con manejo de memoria y archivos grandes"""
        try:
            if not self.whisper_model:
                return self._create_fallback_segments(audio_path)
            
            # Verificar memoria antes de transcribir
            if not self._check_memory_usage():
                current_app.logger.warning("Insufficient memory for transcription, using fallback")
                return self._create_fallback_segments(audio_path)
            
            # Transcribir con configuración optimizada para archivos grandes
            result = self.whisper_model.transcribe(
                audio_path,
                word_timestamps=False,  # Reducir uso de memoria
                language=None,  # Auto-detectar idioma
                verbose=False,
                temperature=0.0,  # Determinístico
                beam_size=1,  # Reducir complejidad
                best_of=1,  # Reducir complejidad
                patience=1.0
            )
            
            segments = []
            for segment in result.get('segments', []):
                audio_segment = AudioSegment(
                    start=segment['start'],
                    end=segment['end'],
                    text=segment['text'],
                    confidence=1.0
                )
                segments.append(audio_segment)
            
            current_app.logger.info(f"Transcribed {len(segments)} segments")
            return segments
            
        except Exception as e:
            current_app.logger.warning(f"Transcription failed: {e}, using fallback")
            return self._create_fallback_segments(audio_path)
    
    def _create_fallback_segments(self, audio_path: str) -> List[AudioSegment]:
        """Crear segmentos simulados cuando la IA no está disponible"""
        try:
            # Obtener duración del audio
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            duration = float(result.stdout.strip()) if result.returncode == 0 else 60.0
            
            # Crear segmentos cada 15 segundos para archivos grandes
            segments = []
            segment_duration = 15
            for i in range(0, int(duration), segment_duration):
                start = i
                end = min(i + segment_duration, duration)
                text = f"Segmento de audio {i//segment_duration + 1}"
                segments.append(AudioSegment(start, end, text))
            
            return segments
            
        except Exception:
            return [AudioSegment(0, 60, "Audio segment")]
    
    def _calculate_sync_offset_safe(self, original_segments: List[AudioSegment], 
                                   dubbed_segments: List[AudioSegment]) -> float:
        """Calcular offset de forma segura con análisis semántico optimizado"""
        try:
            if not self.sentence_transformer or not original_segments or not dubbed_segments:
                return self._calculate_simple_offset_segments(original_segments, dubbed_segments)
            
            # Verificar memoria
            if not self._check_memory_usage():
                return self._calculate_simple_offset_segments(original_segments, dubbed_segments)
            
            # Usar solo los primeros segmentos para reducir carga en archivos grandes
            max_segments = min(20, len(original_segments), len(dubbed_segments))
            orig_texts = [seg.text for seg in original_segments[:max_segments] if seg.text.strip()]
            dub_texts = [seg.text for seg in dubbed_segments[:max_segments] if seg.text.strip()]
            
            if not orig_texts or not dub_texts:
                return 0.0
            
            # Calcular embeddings en lotes pequeños para manejar memoria
            batch_size = 5
            best_offset = 0.0
            best_similarity = 0.0
            
            for i in range(0, len(orig_texts), batch_size):
                orig_batch = orig_texts[i:i+batch_size]
                orig_embeddings = self.sentence_transformer.encode(orig_batch)
                
                for j in range(0, len(dub_texts), batch_size):
                    dub_batch = dub_texts[j:j+batch_size]
                    dub_embeddings = self.sentence_transformer.encode(dub_batch)
                    
                    # Encontrar mejor correspondencia en este lote
                    for oi, orig_emb in enumerate(orig_embeddings):
                        for di, dub_emb in enumerate(dub_embeddings):
                            similarity = np.dot(orig_emb, dub_emb) / (np.linalg.norm(orig_emb) * np.linalg.norm(dub_emb))
                            
                            if similarity > best_similarity and similarity > 0.6:
                                best_similarity = similarity
                                orig_idx = i + oi
                                dub_idx = j + di
                                if orig_idx < len(original_segments) and dub_idx < len(dubbed_segments):
                                    best_offset = dubbed_segments[dub_idx].start - original_segments[orig_idx].start
            
            current_app.logger.info(f"Calculated offset: {best_offset:.3f}s (similarity: {best_similarity:.3f})")
            return best_offset
            
        except Exception as e:
            current_app.logger.warning(f"Semantic analysis failed: {e}")
            return self._calculate_simple_offset_segments(original_segments, dubbed_segments)
    
    def _calculate_simple_offset_segments(self, original_segments: List[AudioSegment], 
                                        dubbed_segments: List[AudioSegment]) -> float:
        """Calcular offset simple basado en segmentos"""
        if not original_segments or not dubbed_segments:
            return 0.0
        return dubbed_segments[0].start - original_segments[0].start
    
    def _calculate_simple_offset_from_audio(self, original_audio: str, dubbed_audio: str) -> float:
        """Calcular offset simple comparando archivos de audio"""
        try:
            # Obtener duración de ambos audios
            def get_duration(audio_path):
                cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio_path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                return float(result.stdout.strip()) if result.returncode == 0 else 0.0
            
            orig_duration = get_duration(original_audio)
            dub_duration = get_duration(dubbed_audio)
            
            # Calcular offset basado en diferencia de duración
            offset = (dub_duration - orig_duration) / 2.0
            current_app.logger.info(f"Simple offset calculated: {offset:.3f}s")
            return offset
            
        except Exception:
            return 0.0
    
    def _apply_sync_offset(self, audio_path: str, offset: float, task_id: str) -> str:
        """Aplicar desfase temporal al audio"""
        try:
            temp_dir = tempfile.gettempdir()
            synced_audio_path = os.path.join(temp_dir, f"synced_{task_id}.wav")
            
            if abs(offset) < 0.1:  # Offset muy pequeño, copiar archivo
                cmd = ['cp', audio_path, synced_audio_path]
            elif offset > 0:  # Retrasar audio
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-af', f'adelay={int(abs(offset) * 1000)}|{int(abs(offset) * 1000)}',
                    '-threads', '0',
                    '-y', synced_audio_path
                ]
            else:  # Adelantar audio
                cmd = [
                    'ffmpeg', '-ss', str(abs(offset)), '-i', audio_path,
                    '-threads', '0',
                    '-y', synced_audio_path
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                raise Exception(f"Error aplicando sincronización: {result.stderr}")
            
            with self._lock:
                self.tasks[task_id]['temp_files'].append(synced_audio_path)
            
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
            task = self.tasks.get(task_id, {})
            custom_filename = task.get('custom_filename', '')
            
            if custom_filename:
                if not custom_filename.lower().endswith('.mkv'):
                    custom_filename += '.mkv'
                result_filename = custom_filename
            else:
                result_filename = f"synced_{task_id}.mkv"
            
            result_path = output_dir / result_filename
            
            # Comando FFmpeg optimizado para archivos grandes
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
                '-b:a', '192k',          # Bitrate de audio más alto para calidad
                '-metadata:s:a:0', 'title=Original',
                '-metadata:s:a:0', 'language=eng',
                '-metadata:s:a:1', 'title=Doblado',
                '-metadata:s:a:1', 'language=spa',
                '-threads', '0',         # Usar todos los cores
                '-movflags', '+faststart',  # Optimizar para streaming
                '-y',                    # Sobrescribir
                str(result_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hora timeout
            if result.returncode != 0:
                raise Exception(f"Error generando MKV: {result.stderr}")
            
            # Verificar que el archivo se creó correctamente
            if not result_path.exists() or result_path.stat().st_size < 1000:
                raise Exception("El archivo MKV generado está vacío o corrupto")
            
            file_size = result_path.stat().st_size
            current_app.logger.info(f"MKV generated successfully: {result_path} ({file_size/(1024**2):.1f} MB)")
            return str(result_path)
            
        except Exception as e:
            raise Exception(f"Error generando archivo MKV: {str(e)}")
    
    def _update_task_status(self, task_id: str, status: str, progress: int, message: str):
        """Actualizar estado de la tarea"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].update({
                    'status': status,
                    'progress': progress,
                    'message': message
                })
    
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
            with self._lock:
                task = self.tasks.get(task_id, {})
                temp_files = task.get('temp_files', [])
            
            for file_path in temp_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    current_app.logger.warning(f"Error removing temp file {file_path}: {e}")
            
            current_app.logger.info(f"Cleaned up {len(temp_files)} temp files for task {task_id}")
            
        except Exception as e:
            current_app.logger.warning(f"Error during cleanup: {e}")
    
    def get_task_status(self, task_id: str):
        """Obtener estado de una tarea"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return {'status': 'not_found', 'error': 'Tarea no encontrada'}
            
            return {
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
    
    def list_all_tasks(self):
        """Listar todas las tareas"""
        with self._lock:
            return {
                'tasks': [
                    {
                        'task_id': task_id,
                        'status': task['status'],
                        'progress': task['progress'],
                        'message': task['message'],
                        'created_at': task['created_at']
                    }
                    for task_id, task in self.tasks.items()
                ],
                'total': len(self.tasks)
            }

# Instancia global del servicio
sync_service = SyncService()

