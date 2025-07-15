"""
Servicio de sincronización de audio con IA - Versión GPU optimizada CORREGIDA
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
from flask import current_app  # type: ignore
import numpy as np  # type: ignore
from typing import List, Tuple, Dict, Optional
from datetime import datetime
import shutil

# Importar el nuevo servicio de transcripción
from .transcription_service import TranscriptionService

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
        
        # Servicio de transcripción optimizado
        self.transcription_service = TranscriptionService()
    
    def set_app(self, app):
        """Establecer la instancia de la aplicación Flask"""
        self.app = app
    
    def _check_memory_usage(self) -> bool:
        """Verificar uso de memoria del sistema"""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent / 100.0
            
            if usage_percent > self.max_memory_usage:
                if self.app:
                    with self.app.app_context():
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
            
            if self.app:
                with self.app.app_context():
                    current_app.logger.info("Memory cleanup completed")
        except Exception as e:
            if self.app:
                with self.app.app_context():
                    current_app.logger.warning(f"Error during memory cleanup: {e}")
    
    def _load_ai_models_safe(self):
        """Cargar modelos de IA de forma segura con soporte GPU"""
        if self._models_loaded:
            return True
        
        try:
            # Verificar memoria disponible antes de cargar
            if not self._check_memory_usage():
                if self.app:
                    with self.app.app_context():
                        current_app.logger.warning("Insufficient memory for AI models, using fallback mode")
                return False
            
            # Cargar Whisper con soporte GPU
            try:
                import whisper
                import torch
                
                # Determinar dispositivo (GPU si está disponible)
                device = "cuda" if torch.cuda.is_available() else "cpu"
                if self.app:
                    with self.app.app_context():
                        current_app.logger.info(f"Using device: {device}")
                
                # Usar modelo base para balance entre calidad y recursos
                model_name = 'base'
                if self.app:
                    with self.app.app_context():
                        model_name = current_app.config.get('WHISPER_MODEL', 'base')
                        current_app.logger.info(f"Loading Whisper model: {model_name}")
                
                self.whisper_model = whisper.load_model(model_name, device=device)
                if self.app:
                    with self.app.app_context():
                        current_app.logger.info(f"Whisper model '{model_name}' loaded successfully on {device}")
            except Exception as e:
                if self.app:
                    with self.app.app_context():
                        current_app.logger.warning(f"Failed to load Whisper: {e}")
                return False
            
            # Verificar memoria después de cargar Whisper
            if not self._check_memory_usage():
                if self.app:
                    with self.app.app_context():
                        current_app.logger.warning("Memory limit reached after loading Whisper")
                del self.whisper_model
                self.whisper_model = None
                return False
            
            # Cargar Sentence Transformer
            try:
                from sentence_transformers import SentenceTransformer
                st_model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
                if self.app:
                    with self.app.app_context():
                        st_model_name = current_app.config.get('SENTENCE_TRANSFORMER_MODEL', 'paraphrase-multilingual-MiniLM-L12-v2')
                        current_app.logger.info(f"Loading Sentence Transformer: {st_model_name}")
                
                # Configurar dispositivo para sentence transformer
                device_st = "cuda" if torch.cuda.is_available() else "cpu"
                current_app.logger.info(f"CUDA available: {torch.cuda.is_available()}")
                current_app.logger.info(f"CUDA device count: {torch.cuda.device_count()}")
                current_app.logger.info(f"Loading Sentence Transformer on device: {device_st}")
                
                self.sentence_transformer = SentenceTransformer(st_model_name, device=device_st)
                
                # Verificar que el modelo esté en el dispositivo correcto
                actual_device = str(self.sentence_transformer.device)
                current_app.logger.info(f"Sentence Transformer loaded successfully on {actual_device}")
                
                # Verificar que realmente esté en GPU si CUDA está disponible
                if torch.cuda.is_available() and 'cpu' in actual_device:
                    current_app.logger.warning("⚠️  Sentence Transformer loaded on CPU despite CUDA being available")
                    current_app.logger.warning("Attempting to move model to GPU manually...")
                    self.sentence_transformer = self.sentence_transformer.to('cuda')
                    current_app.logger.info(f"Model moved to: {self.sentence_transformer.device}")
                elif torch.cuda.is_available() and 'cuda' in actual_device:
                    current_app.logger.info("✅ Sentence Transformer successfully loaded on GPU")
                    
            except Exception as e:
                if self.app:
                    with self.app.app_context():
                        current_app.logger.warning(f"Failed to load Sentence Transformer: {e}")
                # Continuar sin sentence transformer
            
            self._models_loaded = True
            return True
            
        except ImportError as e:
            if self.app:
                with self.app.app_context():
                    current_app.logger.warning(f"AI libraries not available: {e}")
            return False
        except Exception as e:
            if self.app:
                with self.app.app_context():
                    current_app.logger.error(f"Error loading AI models: {e}")
            self._cleanup_memory()
            return False
    
    def start_sync_task(self, task_id: str, original_path: str, dubbed_path: str, 
                       custom_filename: str = '', custom_name: str = '', source_type: str = 'local'):
        """Iniciar tarea de sincronización de forma asíncrona"""
        # Usar custom_name si se proporciona, sino usar custom_filename
        final_custom_name = custom_name if custom_name else custom_filename
        # Generar sufijo de fecha y hora
        from datetime import datetime
        now = datetime.now().strftime('%y%m%d_%H%M')
        # Nombre archivo final sin extensión
        base_name = final_custom_name or f"synced_{task_id}"
        if base_name.lower().endswith('.mkv'):
            base_name = base_name[:-4]
        task_name = f"{base_name}_{now}"
        # Obtener info de archivos
        def get_file_info(path):
            import subprocess, os
            info = {'path': path, 'size': 0, 'duration': 0, 'audio_streams': [], 'video_streams': []}
            if not os.path.exists(path):
                return info
            info['size'] = os.path.getsize(path)
            # ffprobe para duración y streams
            try:
                cmd = [
                    'ffprobe', '-v', 'error', '-show_entries',
                    'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                info['duration'] = float(result.stdout.strip()) if result.returncode == 0 else 0
                # Streams
                cmd2 = [
                    'ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries',
                    'stream=index,codec_name,channels,sample_rate,bit_rate', '-of', 'json', path
                ]
                result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=10)
                import json
                streams = json.loads(result2.stdout).get('streams', [])
                info['audio_streams'] = streams
                # Video info
                cmd3 = [
                    'ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries',
                    'stream=index,codec_name,width,height,bit_rate', '-of', 'json', path
                ]
                result3 = subprocess.run(cmd3, capture_output=True, text=True, timeout=10)
                vstreams = json.loads(result3.stdout).get('streams', [])
                info['video_streams'] = vstreams
            except Exception:
                pass
            return info
        orig_info = get_file_info(original_path)
        dub_info = get_file_info(dubbed_path)
        with self._lock:
            self.tasks[task_id] = {
                'id': task_id,
                'name': task_name,
                'status': 'processing',
                'progress': 0,
                'message': 'Iniciando procesamiento...',
                'original_path': original_path,
                'dubbed_path': dubbed_path,
                'custom_filename': final_custom_name,  # Mantener nombre original del campo
                'custom_name': final_custom_name,      # Agregar campo adicional para compatibilidad
                'source_type': source_type,
                'result_path': None,
                'created_at': datetime.now().isoformat(),
                'error': None,
                'temp_files': [],
                'original_info': orig_info,
                'dubbed_info': dub_info
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
            current_app.logger.info(f"=== STARTING SYNC TASK: {task_id} ===")
            self._update_task_status(task_id, 'processing', 5, "Verificando archivos de entrada...")
            task = self.tasks[task_id]
            original_path = task['original_path']
            dubbed_path = task['dubbed_path']
            custom_filename = task.get('custom_filename', '') or task.get('custom_name', '')

            # Corregido: El directorio de salida nunca debe tener extensión .mkv
            base_name = custom_filename or f"synced_{task_id}"
            if base_name.lower().endswith('.mkv'):
                base_name = base_name[:-4]
            output_dir = current_app.config['OUTPUT_FOLDER'] / base_name
            output_dir.mkdir(parents=True, exist_ok=True)
            current_app.logger.info(f"Output directory for task: {output_dir}")

            # Extraer audio de ambos videos
            self._update_task_status(task_id, 'processing', 15, "Extrayendo audio del video original...")
            current_app.logger.info("Extracting audio from original video...")
            original_audio = self._extract_audio_optimized(original_path, task_id, "original")
            current_app.logger.info(f"Original audio extracted: {original_audio}")
            shutil.copy2(original_audio, output_dir / "original_audio.wav")

            self._update_task_status(task_id, 'processing', 25, "Extrayendo audio del video doblado...")
            current_app.logger.info("Extracting audio from dubbed video...")
            dubbed_audio = self._extract_audio_optimized(dubbed_path, task_id, "dubbed")
            current_app.logger.info(f"Dubbed audio extracted: {dubbed_audio}")
            shutil.copy2(dubbed_audio, output_dir / "dubbed_audio.wav")

            # Cargar modelos IA de forma segura
            self._update_task_status(task_id, 'processing', 35, "Preparando modelos de IA...")
            current_app.logger.info("Loading AI models...")
            # Forzar modelo medium
            current_app.config['WHISPER_MODEL'] = 'medium'
            ai_available = self._load_ai_models_safe()
            current_app.logger.info(f"AI models available: {ai_available}")

            orig_es = orig_en = dub_es = dub_en = None
            if ai_available:
                # Transcribir ambos audios a español y a inglés
                self._update_task_status(task_id, 'processing', 45, "Transcribiendo audio original a ES...")
                current_app.logger.info("Transcribing original audio to ES...")
                orig_es = self.transcription_service.transcribe_audio(original_audio, task_id=task_id, test_mode=False)
                if orig_es:
                    with open(output_dir / "spanish.json", "w", encoding="utf-8") as f:
                        json.dump(orig_es, f, ensure_ascii=False, indent=2)
                else:
                    current_app.logger.warning("No segments found in original_es transcription!")

                self._update_task_status(task_id, 'processing', 47, "Transcribiendo audio original a EN...")
                current_app.logger.info("Transcribing original audio to EN...")
                prev_lang = current_app.config.get('TRANSCRIPTION_LANGUAGE', 'es')
                current_app.config['TRANSCRIPTION_LANGUAGE'] = 'en'
                orig_en = self.transcription_service.transcribe_audio(original_audio, task_id=task_id, test_mode=False)
                current_app.config['TRANSCRIPTION_LANGUAGE'] = prev_lang
                if orig_en:
                    with open(output_dir / "english.json", "w", encoding="utf-8") as f:
                        json.dump(orig_en, f, ensure_ascii=False, indent=2)
                else:
                    current_app.logger.warning("No segments found in original_en transcription!")

                self._update_task_status(task_id, 'processing', 60, "Transcribiendo audio doblado a ES...")
                current_app.logger.info("Transcribing dubbed audio to ES...")
                dub_es = self.transcription_service.transcribe_audio(dubbed_audio, task_id=task_id, test_mode=False)
                if dub_es:
                    with open(output_dir / "dubbed_spanish.json", "w", encoding="utf-8") as f:
                        json.dump(dub_es, f, ensure_ascii=False, indent=2)
                else:
                    current_app.logger.warning("No segments found in dubbed_es transcription!")

                self._update_task_status(task_id, 'processing', 62, "Transcribiendo audio doblado a EN...")
                current_app.logger.info("Transcribing dubbed audio to EN...")
                current_app.config['TRANSCRIPTION_LANGUAGE'] = 'en'
                dub_en = self.transcription_service.transcribe_audio(dubbed_audio, task_id=task_id, test_mode=False)
                current_app.config['TRANSCRIPTION_LANGUAGE'] = prev_lang
                if dub_en:
                    with open(output_dir / "dubbed_english.json", "w", encoding="utf-8") as f:
                        json.dump(dub_en, f, ensure_ascii=False, indent=2)
                else:
                    current_app.logger.warning("No segments found in dubbed_en transcription!")

                # Calcular offset usando los segmentos en español
                self._update_task_status(task_id, 'processing', 75, "Calculando sincronización...")
                current_app.logger.info("Calculating sync offset with semantic analysis...")
                orig_segments = [AudioSegment(s['start'], s['end'], s['text']) for s in (orig_es['segments'] if orig_es else [])]
                dub_segments = [AudioSegment(s['start'], s['end'], s['text']) for s in (dub_es['segments'] if dub_es else [])]
                time_offset = self._calculate_sync_offset_safe(orig_segments, dub_segments)
            else:
                # Modo fallback sin IA
                self._update_task_status(task_id, 'processing', 60, "Usando modo de compatibilidad...")
                current_app.logger.info("Using fallback mode without AI...")
                time_offset = self._calculate_simple_offset_from_audio(original_audio, dubbed_audio)

            current_app.logger.info(f"=== CALCULATED TIME OFFSET: {time_offset:.3f} seconds ===")

            # Aplicar sincronización
            self._update_task_status(task_id, 'processing', 85, "Aplicando sincronización...")
            current_app.logger.info(f"Applying sync offset: {time_offset:.3f}s")
            synced_audio = self._apply_sync_offset(dubbed_audio, time_offset, task_id)
            current_app.logger.info(f"Synced audio created: {synced_audio}")
            shutil.copy2(synced_audio, output_dir / "dubbed_audio_synced.wav")

            # Generar archivo MKV final SOLO dentro de la carpeta de output
            self._update_task_status(task_id, 'processing', 95, "Generando archivo MKV final...")
            current_app.logger.info("Generating final MKV file...")
            result_path = self._generate_mkv_final(original_path, original_audio, synced_audio, task_id, output_dir)
            current_app.logger.info(f"Final MKV generated: {result_path}")
            final_filename = (custom_filename if custom_filename.lower().endswith('.mkv') else f"{base_name}.mkv")
            # No copiar fuera, solo dejar en output_dir
            # shutil.copy2(result_path, output_dir / final_filename)  # ELIMINADO

            # Completar tarea
            with self._lock:
                self.tasks[task_id]['result_path'] = str(result_path)
                self.tasks[task_id]['status'] = 'completed'
                self.tasks[task_id]['progress'] = 100
                self.tasks[task_id]['message'] = '¡Sincronización completada exitosamente!'

            current_app.logger.info(f"=== TASK COMPLETED SUCCESSFULLY: {task_id} ===")

        except Exception as e:
            current_app.logger.error(f"=== ERROR PROCESSING TASK {task_id}: {str(e)} ===")
            self._update_task_error(task_id, f"Error en el procesamiento: {str(e)}")
        finally:
            # Limpiar archivos temporales y memoria
            self._cleanup_task_files(task_id)
            self._cleanup_memory()
    
    def _extract_audio_optimized(self, video_path: str, task_id: str, prefix: str) -> str:
        """Extraer audio de forma optimizada para archivos grandes"""
        try:
            current_app.logger.info(f"=== EXTRACTING AUDIO: {prefix} ===")
            current_app.logger.info(f"Input video: {video_path}")
            
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, f"{prefix}_{task_id}.wav")
            current_app.logger.info(f"Output audio: {audio_path}")
            
            # Comando FFmpeg optimizado para archivos grandes - MEJORADO para calidad
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # Sin video
                '-acodec', 'pcm_s24le',  # Codec de audio de mayor calidad (24-bit)
                '-ar', '48000',  # Sample rate más alto para mejor calidad
                '-ac', '2',  # Estéreo para mantener calidad original
                '-map_metadata', '-1',  # Sin metadatos
                '-fflags', '+bitexact',  # Reproducible
                '-threads', '0',  # Usar todos los cores disponibles
                '-y',  # Sobrescribir
                audio_path
            ]
            
            current_app.logger.info(f"FFmpeg audio extraction command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 min timeout
            if result.returncode != 0:
                current_app.logger.error(f"FFmpeg audio extraction error: {result.stderr}")
                raise Exception(f"Error extrayendo audio: {result.stderr}")
            
            current_app.logger.info(f"Audio extraction completed successfully for {prefix}")
            
            # Agregar a archivos temporales
            with self._lock:
                self.tasks[task_id]['temp_files'].append(audio_path)
            
            current_app.logger.info(f"Audio extracted successfully: {audio_path}")
            return audio_path
            
        except subprocess.TimeoutExpired:
            current_app.logger.error(f"Timeout extracting audio for {prefix}")
            raise Exception("Timeout extrayendo audio - archivo demasiado grande o proceso bloqueado")
        except Exception as e:
            current_app.logger.error(f"Error extracting audio for {prefix}: {str(e)}")
            raise Exception(f"Error extrayendo audio: {str(e)}")
    
    def _transcribe_audio_safe(self, audio_path: str, task_id: str) -> List[AudioSegment]:
        """Transcribir audio usando el servicio de transcripción optimizado"""
        try:
            current_app.logger.info(f"Starting optimized transcription of: {audio_path}")
            
            # Usar el nuevo servicio de transcripción optimizado
            result = self.transcription_service.transcribe_audio(audio_path, task_id=task_id)
            
            if result is None:
                current_app.logger.warning("Optimized transcription failed, using fallback")
                return self._create_fallback_segments(audio_path)
            
            segments = result.get('segments', [])
            if not segments:
                current_app.logger.warning("No segments found in optimized transcription")
                return self._create_fallback_segments(audio_path)
            
            # Convertir a AudioSegment
            audio_segments = []
            for segment in segments:
                audio_segment = AudioSegment(
                    start=segment['start'],
                    end=segment['end'],
                    text=segment['text'],
                    confidence=segment.get('avg_logprob', 1.0)
                )
                audio_segments.append(audio_segment)
            
            current_app.logger.info(f"Optimized transcription completed: {len(audio_segments)} segments")
            current_app.logger.info(f"Total duration: {result.get('total_duration', 0):.1f}s")
            current_app.logger.info(f"Average segment duration: {result.get('avg_duration', 0):.1f}s")
            current_app.logger.info(f"Total words: {result.get('total_words', 0)}")
            current_app.logger.info(f"Transcription time: {result.get('transcribe_time', 0):.1f}s")
            
            # Guardar transcripción permanentemente
            self._save_transcription_permanently(result, task_id, audio_path)
            
            # Mostrar algunos ejemplos de transcripción
            if audio_segments:
                current_app.logger.info("=== SAMPLE TRANSCRIPTIONS (OPTIMIZED) ===")
                for i, seg in enumerate(audio_segments[:3]):
                    current_app.logger.info(f"Segment {i} ({seg.start:.1f}s-{seg.end:.1f}s): '{seg.text}'")
            
            return audio_segments
            
        except Exception as e:
            current_app.logger.warning(f"Optimized transcription failed: {e}, using fallback")
            return self._create_fallback_segments(audio_path)
    
    def _save_transcription_permanently(self, result: Dict, task_id: str, audio_path: str):
        """Guardar transcripción permanentemente en /tmp para revisión manual"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            transcription_dir = f"/tmp/transcriptions_{timestamp}_{task_id}"
            
            os.makedirs(transcription_dir, exist_ok=True)
            current_app.logger.info(f"Saving permanent transcription to: {transcription_dir}")
            
            # Guardar resultado completo
            result_file = os.path.join(transcription_dir, "transcription_result.json")
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # Guardar solo segmentos
            segments_file = os.path.join(transcription_dir, "segments.json")
            with open(segments_file, 'w', encoding='utf-8') as f:
                json.dump(result.get('segments', []), f, ensure_ascii=False, indent=2)
            
            # Crear archivo de resumen
            summary_file = os.path.join(transcription_dir, "summary.txt")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"TRANSCRIPTION SUMMARY\n")
                f.write(f"====================\n")
                f.write(f"Task ID: {task_id}\n")
                f.write(f"Audio file: {os.path.basename(audio_path)}\n")
                f.write(f"Model: {result.get('model', 'N/A')}\n")
                f.write(f"Total segments: {len(result.get('segments', []))}\n")
                f.write(f"Total duration: {result.get('total_duration', 0):.1f}s\n")
                f.write(f"Transcription time: {result.get('transcribe_time', 0):.1f}s\n")
                f.write(f"Test mode: {result.get('test_mode', 'N/A')}\n")
                f.write(f"\nFIRST 5 SEGMENTS:\n")
                for i, segment in enumerate(result.get('segments', [])[:5], 1):
                    f.write(f"{i}. [{segment['start']:.1f}-{segment['end']:.1f}] {segment['text']}\n")
            
            current_app.logger.info(f"Permanent transcription saved to: {transcription_dir}")
            
            # Agregar a la lista de archivos temporales para preservación
            with self._lock:
                if task_id in self.tasks:
                    if 'transcription_files' not in self.tasks[task_id]:
                        self.tasks[task_id]['transcription_files'] = []
                    self.tasks[task_id]['transcription_files'].append(transcription_dir)
            
        except Exception as e:
            current_app.logger.error(f"Error saving permanent transcription: {e}")
    
    def _clean_transcript_segments(self, segments: List[Dict]) -> List[Dict]:
        """Limpiar segmentos duplicados y muy cortos de la transcripción"""
        cleaned = []
        seen_texts = set()
        
        for segment in segments:
            text = segment['text'].strip()
            
            # Filtrar segmentos muy cortos (menos de 2 caracteres)
            if len(text) < 2:
                continue
                
            # Filtrar duplicados consecutivos
            if text in seen_texts:
                continue
                
            # Filtrar segmentos muy cortos temporalmente (menos de 1 segundo)
            duration = segment['end'] - segment['start']
            if duration < 1.0:
                continue
                
            # Filtrar texto que parece ser ruido o repetición
            noise_patterns = ['David!', 'What?', 'No.', 'Yeah.', 'Hey, Mom.', '¡David!', '¿Qué?', 'No.', 'Sí.']
            if text in noise_patterns and len(cleaned) > 0:
                # Solo agregar si no es una repetición inmediata
                last_text = cleaned[-1]['text'].strip()
                if text != last_text:
                    cleaned.append(segment)
                    seen_texts.add(text)
            else:
                cleaned.append(segment)
                seen_texts.add(text)
        
        return cleaned
    
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
            current_app.logger.info(f"=== CALCULATING SYNC OFFSET ===")
            current_app.logger.info(f"Original segments: {len(original_segments)}")
            current_app.logger.info(f"Dubbed segments: {len(dubbed_segments)}")
            
            if not self.sentence_transformer or not original_segments or not dubbed_segments:
                current_app.logger.info("Falling back to simple offset calculation")
                return self._calculate_simple_offset_segments(original_segments, dubbed_segments)
            
            # Verificar memoria
            if not self._check_memory_usage():
                current_app.logger.info("Insufficient memory, falling back to simple offset calculation")
                return self._calculate_simple_offset_segments(original_segments, dubbed_segments)
            
            # MEJORADO: Usar menos segmentos para evitar sobrecarga
            max_segments = min(50, len(original_segments), len(dubbed_segments))
            current_app.logger.info(f"Using {max_segments} segments for analysis")
            
            # Seleccionar segmentos distribuidos uniformemente
            orig_indices = []
            dub_indices = []
            
            if len(original_segments) > max_segments:
                step = len(original_segments) // max_segments
                orig_indices = list(range(step, len(original_segments) - step, step))[:max_segments]
            else:
                orig_indices = list(range(len(original_segments)))
            
            if len(dubbed_segments) > max_segments:
                step = len(dubbed_segments) // max_segments
                dub_indices = list(range(step, len(dubbed_segments) - step, step))[:max_segments]
            else:
                dub_indices = list(range(len(dubbed_segments)))
            
            # Filtrar segmentos con texto válido
            orig_texts = []
            orig_selected_indices = []
            seen_texts = set()
            
            for idx in orig_indices:
                if idx < len(original_segments):
                    text = original_segments[idx].text.strip()
                    if text and len(text) > 3 and text not in seen_texts:
                        orig_texts.append(text)
                        orig_selected_indices.append(idx)
                        seen_texts.add(text)
            
            dub_texts = []
            dub_selected_indices = []
            seen_texts = set()
            
            for idx in dub_indices:
                if idx < len(dubbed_segments):
                    text = dubbed_segments[idx].text.strip()
                    if text and len(text) > 3 and text not in seen_texts:
                        dub_texts.append(text)
                        dub_selected_indices.append(idx)
                        seen_texts.add(text)
            
            current_app.logger.info(f"Original unique texts: {len(orig_texts)}")
            current_app.logger.info(f"Dubbed unique texts: {len(dub_texts)}")
            
            if not orig_texts or not dub_texts:
                current_app.logger.info("No valid texts found, using simple offset calculation")
                return self._calculate_simple_offset_segments(original_segments, dubbed_segments)
            
            # Calcular embeddings en lotes
            batch_size = 10
            best_offset = 0.0
            best_similarity = 0.0
            
            current_app.logger.info("Starting semantic similarity analysis...")
            
            for i in range(0, len(orig_texts), batch_size):
                orig_batch = orig_texts[i:i+batch_size]
                orig_embeddings = self.sentence_transformer.encode(orig_batch)
                
                for j in range(0, len(dub_texts), batch_size):
                    dub_batch = dub_texts[j:j+batch_size]
                    dub_embeddings = self.sentence_transformer.encode(dub_batch)
                    
                    for oi, orig_emb in enumerate(orig_embeddings):
                        for di, dub_emb in enumerate(dub_embeddings):
                            similarity = np.dot(orig_emb, dub_emb) / (np.linalg.norm(orig_emb) * np.linalg.norm(dub_emb))
                            
                            if similarity > best_similarity and similarity > 0.3:
                                best_similarity = similarity
                                orig_idx = orig_selected_indices[i + oi]
                                dub_idx = dub_selected_indices[j + di]
                                if orig_idx < len(original_segments) and dub_idx < len(dubbed_segments):
                                    best_offset = dubbed_segments[dub_idx].start - original_segments[orig_idx].start
            
            current_app.logger.info(f"Best similarity: {best_similarity:.3f}")
            current_app.logger.info(f"Calculated offset: {best_offset:.3f}s")
            
            # Validar offset
            max_reasonable_offset = 60.0
            if abs(best_offset) > max_reasonable_offset:
                current_app.logger.warning(f"Offset too large: {best_offset:.3f}s, using simple calculation")
                return self._calculate_simple_offset_segments(original_segments, dubbed_segments)
            
            if best_similarity < 0.3:
                current_app.logger.info("Low similarity, using simple offset calculation")
                return self._calculate_simple_offset_segments(original_segments, dubbed_segments)
            
            return best_offset
            
        except Exception as e:
            current_app.logger.warning(f"Semantic analysis failed: {e}")
            return self._calculate_simple_offset_segments(original_segments, dubbed_segments)
    
    def _calculate_simple_offset_segments(self, original_segments: List[AudioSegment], 
                                        dubbed_segments: List[AudioSegment]) -> float:
        """Calcular offset simple basado en segmentos con manejo de offsets variables"""
        current_app.logger.info("=== CALCULATING SIMPLE OFFSET ===")
        
        if not original_segments or not dubbed_segments:
            current_app.logger.info("No segments available, returning 0.0")
            return 0.0
        
        # MEJORADO: Calcular offset usando múltiples estrategias distribuidas en 15 minutos
        offsets = []
        
        # Estrategia 1: Segmentos distribuidos uniformemente a lo largo de todo el tramo
        # Usar más segmentos para aprovechar los 15 minutos completos
        total_segments = min(len(original_segments), len(dubbed_segments))
        if total_segments >= 20:
            # Usar hasta 15 segmentos distribuidos uniformemente
            num_sample_segments = min(15, total_segments)
            step = total_segments // num_sample_segments
            
            current_app.logger.info(f"Using {num_sample_segments} segments distributed across {total_segments} total segments")
            
            for i in range(num_sample_segments):
                idx = i * step
                if idx < total_segments:
                    offset = dubbed_segments[idx].start - original_segments[idx].start
                    offsets.append(offset)
                    current_app.logger.info(f"Segment {idx} (distributed): offset = {offset:.3f}s")
        else:
            # Si hay pocos segmentos, usar todos
            for i in range(total_segments):
                offset = dubbed_segments[i].start - original_segments[i].start
                offsets.append(offset)
                current_app.logger.info(f"Segment {i}: offset = {offset:.3f}s")
        
        # Estrategia 2: Segmentos del medio (si hay suficientes)
        if len(original_segments) > 20 and len(dubbed_segments) > 20:
            mid_orig = len(original_segments) // 2
            mid_dub = len(dubbed_segments) // 2
            mid_offset = dubbed_segments[mid_dub].start - original_segments[mid_orig].start
            offsets.append(mid_offset)
            current_app.logger.info(f"Mid segment offset: {mid_offset:.3f}s")
        
        # Estrategia 3: Últimos segmentos (si hay suficientes)
        if len(original_segments) > 10 and len(dubbed_segments) > 10:
            last_orig = min(len(original_segments) - 1, len(dubbed_segments) - 1)
            last_dub = last_orig
            last_offset = dubbed_segments[last_dub].start - original_segments[last_orig].start
            offsets.append(last_offset)
            current_app.logger.info(f"Last segment offset: {last_offset:.3f}s")
        
        current_app.logger.info(f"Calculated {len(offsets)} offsets from distributed sampling")
        
        # NUEVA ESTRATEGIA: Analizar la variación del offset
        if len(offsets) > 1:
            import statistics
            median_offset = statistics.median(offsets)
            mean_offset = statistics.mean(offsets)
            std_offset = statistics.stdev(offsets) if len(offsets) > 1 else 0
            
            current_app.logger.info(f"Offset analysis - Median: {median_offset:.3f}s, Mean: {mean_offset:.3f}s, Std: {std_offset:.3f}s")
            
            # Si hay mucha variación, usar una muestra más grande pero aún distribuida
            max_variation = 30.0  # 30 segundos de variación máxima
            if std_offset > max_variation:
                current_app.logger.warning(f"High offset variation ({std_offset:.3f}s), using larger distributed sample")
                # Usar más segmentos distribuidos pero con mayor espaciado
                if total_segments >= 30:
                    num_large_sample = min(20, total_segments)
                    step_large = total_segments // num_large_sample
                    large_sample_offsets = []
                    
                    for i in range(num_large_sample):
                        idx = i * step_large
                        if idx < total_segments:
                            offset = dubbed_segments[idx].start - original_segments[idx].start
                            large_sample_offsets.append(offset)
                    
                    final_offset = statistics.median(large_sample_offsets)
                    current_app.logger.info(f"Using median of {len(large_sample_offsets)} distributed segments: {final_offset:.3f}s")
                    return final_offset
                else:
                    # Si no hay suficientes segmentos, usar todos
                    final_offset = statistics.median(offsets)
                    current_app.logger.info(f"Using median of all available segments: {final_offset:.3f}s")
                    return final_offset
            else:
                # Usar la mediana de todos los offsets calculados (distribuidos)
                current_app.logger.info(f"Using median of distributed offsets: {median_offset:.3f}s")
                return median_offset
        else:
            # Solo un offset disponible
            final_offset = offsets[0] if offsets else 0.0
            current_app.logger.info(f"Using single offset: {final_offset:.3f}s")
            return final_offset
    
    def _calculate_simple_offset_from_audio(self, original_audio: str, dubbed_audio: str) -> float:
        """Calcular offset simple comparando archivos de audio"""
        try:
            current_app.logger.info("=== CALCULATING SIMPLE OFFSET FROM AUDIO FILES ===")
            
            # Obtener duración de ambos audios
            def get_duration(audio_path):
                cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio_path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                duration = float(result.stdout.strip()) if result.returncode == 0 else 0.0
                current_app.logger.info(f"Duration for {audio_path}: {duration:.3f}s")
                return duration
            
            orig_duration = get_duration(original_audio)
            dub_duration = get_duration(dubbed_audio)
            
            # Calcular offset basado en diferencia de duración
            offset = (dub_duration - orig_duration) / 2.0
            current_app.logger.info(f"Simple offset calculated: {offset:.3f}s")
            current_app.logger.info(f"Duration difference: {dub_duration - orig_duration:.3f}s")
            return offset
            
        except Exception as e:
            current_app.logger.error(f"Error calculating simple offset: {e}")
            return 0.0
    
    def _apply_sync_offset(self, audio_path: str, offset: float, task_id: str) -> str:
        """Aplicar desfase temporal al audio"""
        try:
            temp_dir = tempfile.gettempdir()
            synced_audio_path = os.path.join(temp_dir, f"synced_{task_id}.wav")
            
            current_app.logger.info(f"=== APPLYING SYNC OFFSET ===")
            current_app.logger.info(f"Input audio: {audio_path}")
            current_app.logger.info(f"Offset value: {offset:.3f}s")
            current_app.logger.info(f"Output audio: {synced_audio_path}")
            
            if abs(offset) < 0.1:  # Offset muy pequeño, copiar archivo
                current_app.logger.info("Offset too small (< 0.1s), copying file without changes")
                cmd = ['cp', audio_path, synced_audio_path]
            elif offset > 0:  # Dubbed audio is DELAYED (starts later), need to ADD silence at beginning
                delay_ms = int(offset * 1000)
                current_app.logger.info(f"Positive offset detected: {offset:.3f}s - Dubbed audio is DELAYED, ADDING {offset:.3f}s silence")
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-af', f'adelay={delay_ms}|{delay_ms}',
                    '-threads', '0',
                    '-y', synced_audio_path
                ]
            else:  # Dubbed audio is AHEAD (starts earlier), need to CUT the beginning
                current_app.logger.info(f"Negative offset detected: {offset:.3f}s - Dubbed audio is AHEAD, CUTTING first {abs(offset):.3f}s")
                cmd = [
                    'ffmpeg', '-ss', str(abs(offset)), '-i', audio_path,
                    '-threads', '0',
                    '-y', synced_audio_path
                ]
            
            current_app.logger.info(f"FFmpeg command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                current_app.logger.error(f"FFmpeg error output: {result.stderr}")
                raise Exception(f"Error aplicando sincronización: {result.stderr}")
            
            current_app.logger.info("FFmpeg command executed successfully")
            
            with self._lock:
                self.tasks[task_id]['temp_files'].append(synced_audio_path)
            
            return synced_audio_path
            
        except Exception as e:
            current_app.logger.error(f"Error in _apply_sync_offset: {str(e)}")
            raise Exception(f"Error aplicando sincronización: {str(e)}")
    
    def _generate_mkv_final(self, original_video: str, original_audio: str, synced_audio: str, task_id: str, output_dir=None) -> str:
        """Generar archivo MKV final con video original y ambas pistas de audio en la carpeta de output_dir"""
        try:
            current_app.logger.info(f"=== GENERATING FINAL MKV ===")
            current_app.logger.info(f"Original video: {original_video}")
            current_app.logger.info(f"Original audio: {original_audio}")
            current_app.logger.info(f"Synced audio: {synced_audio}")

            if output_dir is None:
                output_dir = current_app.config['OUTPUT_FOLDER']
            output_dir.mkdir(exist_ok=True)
            current_app.logger.info(f"Output directory: {output_dir}")

            # Determinar nombre del archivo
            task = self.tasks.get(task_id, {})
            custom_filename = task.get('custom_filename', '') or task.get('custom_name', '')

            if custom_filename:
                if not custom_filename.lower().endswith('.mkv'):
                    custom_filename += '.mkv'
                result_filename = custom_filename
            else:
                result_filename = f"synced_{task_id}.mkv"

            result_path = output_dir / result_filename
            current_app.logger.info(f"Result filename: {result_filename}")
            current_app.logger.info(f"Result path: {result_path}")

            # MEJORADO: Comando FFmpeg optimizado para conservar calidad original del audio
            cmd = [
                'ffmpeg',
                '-i', original_video,    # Video original
                '-i', original_audio,    # Audio original
                '-i', synced_audio,      # Audio sincronizado
                '-map', '0:v',           # Video del primer input
                '-map', '1:a',           # Audio original
                '-map', '2:a',           # Audio sincronizado
                '-c:v', 'copy',          # Copiar video sin recodificar
                '-c:a:0', 'copy',        # Copiar audio original sin recodificar (conservar calidad)
                '-c:a:1', 'copy',        # Copiar audio sincronizado sin recodificar (conservar calidad)
                '-metadata:s:a:0', 'title=Original',
                '-metadata:s:a:0', 'language=eng',
                '-metadata:s:a:1', 'title=Doblado',
                '-metadata:s:a:1', 'language=spa',
                '-threads', '0',         # Usar todos los cores
                '-movflags', '+faststart',  # Optimizar para streaming
                '-y',                    # Sobrescribir
                str(result_path)
            ]

            current_app.logger.info(f"FFmpeg MKV command: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hora timeout
            if result.returncode != 0:
                current_app.logger.error(f"FFmpeg MKV error output: {result.stderr}")
                raise Exception(f"Error generando MKV: {result.stderr}")

            current_app.logger.info("FFmpeg MKV command executed successfully")

            # Verificar que el archivo se creó correctamente
            if not result_path.exists() or result_path.stat().st_size < 1000:
                current_app.logger.error(f"Generated MKV file is empty or corrupted: {result_path}")
                raise Exception("El archivo MKV generado está vacío o corrupto")

            file_size = result_path.stat().st_size
            current_app.logger.info(f"MKV generated successfully: {result_path} ({file_size/(1024**2):.1f} MB)")
            current_app.logger.info(f"=== MKV GENERATION COMPLETE ===")
            return result_path
        except Exception as e:
            current_app.logger.error(f"Error in _generate_mkv_final: {str(e)}")
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
        """Limpiar archivos temporales de una tarea, preservando transcripciones"""
        try:
            with self._lock:
                task = self.tasks.get(task_id, {})
                temp_files = task.get('temp_files', [])
                transcription_files = task.get('transcription_files', [])
            
            # Preservar TODAS las transcripciones en /tmp para revisión manual
            preserved_count = 0
            for file_path in transcription_files:
                try:
                    if os.path.exists(file_path):
                        preserved_count += 1
                        if self.app:
                            with self.app.app_context():
                                current_app.logger.info(f"Preserving transcription: {file_path}")
                except Exception as e:
                    if self.app:
                        with self.app.app_context():
                            current_app.logger.warning(f"Error checking transcription file {file_path}: {e}")
            
            # Limpiar solo archivos de audio/video temporales
            removed_count = 0
            for file_path in temp_files:
                try:
                    if os.path.exists(file_path):
                        # NO eliminar archivos que contengan 'transcription' o 'debug'
                        if 'transcription' not in file_path.lower() and 'debug' not in file_path.lower():
                            os.remove(file_path)
                            removed_count += 1
                            if self.app:
                                with self.app.app_context():
                                    current_app.logger.info(f"Removed temp file: {file_path}")
                except Exception as e:
                    if self.app:
                        with self.app.app_context():
                            current_app.logger.warning(f"Error removing temp file {file_path}: {e}")
            
            if self.app:
                with self.app.app_context():
                    current_app.logger.info(f"Cleanup completed - Removed: {removed_count}, Preserved: {preserved_count}")
            
        except Exception as e:
            if self.app:
                with self.app.app_context():
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
    
    def get_result_path(self, task_id: str):
        """Obtener ruta del archivo resultado
        
        CORREGIDO: Devuelve solo la ruta como string para compatibilidad con la API
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.get('result_path'):
                return task['result_path']
            return None
    
    def list_all_tasks(self):
        """Listar todas las tareas"""
        with self._lock:
            return {
                'tasks': [
                    {
                        'task_id': task_id,
                        'name': task.get('name'),
                        'status': task['status'],
                        'progress': task['progress'],
                        'message': task['message'],
                        'created_at': task['created_at'],
                        'original_path': task.get('original_path'),
                        'dubbed_path': task.get('dubbed_path'),
                        'original_info': task.get('original_info'),
                        'dubbed_info': task.get('dubbed_info'),
                        'custom_filename': task.get('custom_filename'),
                        'custom_name': task.get('custom_name'),
                        'result_path': task.get('result_path'),
                        'error': task.get('error'),
                    }
                    for task_id, task in self.tasks.items()
                ],
                'total': len(self.tasks)
            }

# Instancia global del servicio
sync_service = SyncService()

