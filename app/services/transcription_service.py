"""
Servicio de transcripción optimizado para SyncDub MVP
Basado en las pruebas exitosas con el modelo medium
"""

import os
import gc
import time
import subprocess
import tempfile
import psutil
import json
import shutil
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import whisper
import numpy as np  # type: ignore
from flask import current_app  # type: ignore

# Eliminar: from transcription_config import TranscriptionConfig
# Sustituir todos los usos de TranscriptionConfig.WHISPER_MODEL por current_app.config['WHISPER_MODEL']
# Sustituir TranscriptionConfig.TRANSCRIPTION_TEST_DURATION por current_app.config.get('AUDIO_EXTRACT_DURATION', 900)
# Sustituir TranscriptionConfig.get_segment_cleaning_config() por current_app.config.get('SEGMENT_CLEANING_CONFIG', {'min_duration': 1.0, 'max_duration': 30.0, 'min_words': 3})
# Sustituir TranscriptionConfig.get_whisper_options() por current_app.config.get('WHISPER_OPTIONS', {'temperature': [0.0], 'beam_size': 5})
# Sustituir TranscriptionConfig.TRANSCRIPTION_LANGUAGE por current_app.config.get('TRANSCRIPTION_LANGUAGE', 'es')
# Sustituir TranscriptionConfig.MAX_MEMORY_USAGE por current_app.config.get('MAX_MEMORY_USAGE', 0.85)
# Sustituir TranscriptionConfig.TRANSCRIPTION_TEST_MODE por current_app.config.get('TRANSCRIPTION_TEST_MODE', False)

class TranscriptionService:
    """Servicio de transcripción optimizado para audio en español"""
    
    def __init__(self):
        self.whisper_model = None
        self._model_loaded = False
        self.log_prefix = "[TRANSCRIPTION_SERVICE]"
        
    def _log(self, message: str, level: str = "INFO"):
        """Logging centralizado con timestamp y prefijo"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Solo mostrar logs importantes para reducir verbosidad
        if level in ["ERROR", "WARNING"] or "completed" in message.lower() or "starting" in message.lower():
            print(f"{timestamp} {self.log_prefix} {level}: {message}")
        
    def _check_memory_usage(self) -> bool:
        """Verificar uso de memoria del sistema"""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent / 100.0
            memory_gb = memory.used / (1024**3)
            total_gb = memory.total / (1024**3)
            
            # Solo log si hay problemas de memoria
            if usage_percent > current_app.config.get('MAX_MEMORY_USAGE', 0.85):
                self._log(f"WARNING: High memory usage detected: {usage_percent:.1%} > {current_app.config.get('MAX_MEMORY_USAGE', 0.85):.1%}", "WARNING")
                return False
            return True
        except Exception as e:
            self._log(f"Error checking memory: {e}", "ERROR")
            return True
    
    def _cleanup_memory(self):
        """Limpiar memoria y forzar garbage collection"""
        try:
            self._log("Starting memory cleanup...")
            
            if self.whisper_model is not None:
                self._log("Unloading Whisper model...")
                del self.whisper_model
                self.whisper_model = None
            
            self._model_loaded = False
            gc.collect()
            
            # Limpiar cache de GPU si está disponible
            try:
                import torch  # type: ignore
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    self._log("GPU cache cleared")
            except (ImportError, AttributeError):
                pass
            
            self._log("Memory cleanup completed")
        except Exception as e:
            self._log(f"Error during memory cleanup: {e}", "ERROR")
    
    def _load_whisper_model(self) -> bool:
        """Cargar modelo Whisper de forma segura"""
        if self._model_loaded and self.whisper_model is not None:
            self._log("Whisper model already loaded")
            return True
        
        try:
            # Verificar memoria antes de cargar
            if not self._check_memory_usage():
                self._log("Skipping model load due to high memory usage", "WARNING")
                return False
            
            model_name = current_app.config['WHISPER_MODEL']
            self._log(f"Loading Whisper model: {model_name}")
            
            start_time = time.time()
            self.whisper_model = whisper.load_model(model_name)
            load_time = time.time() - start_time
            
            # Verificar memoria después de cargar
            self._check_memory_usage()
            
            self._model_loaded = True
            self._log(f"Whisper model '{model_name}' loaded successfully in {load_time:.1f}s")
            return True
            
        except Exception as e:
            self._log(f"Error loading Whisper model: {e}", "ERROR")
            self._cleanup_memory()
            return False
    
    def _save_debug_files(self, audio_path: str, result: Dict, task_id: Optional[str] = None):
        """Guardar archivos de debug en /tmp para revisión manual"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_suffix = f"_{task_id}" if task_id else ""
            debug_dir = f"/tmp/transcription_debug_{timestamp}{task_suffix}"
            
            os.makedirs(debug_dir, exist_ok=True)
            self._log(f"Saving debug files to: {debug_dir}")
            
            # Copiar audio original
            audio_filename = os.path.basename(audio_path)
            debug_audio_path = os.path.join(debug_dir, f"audio_{audio_filename}")
            shutil.copy2(audio_path, debug_audio_path)
            self._log(f"Audio copied to: {debug_audio_path}")
            
            # Guardar resultado completo
            result_file = os.path.join(debug_dir, "transcription_result.json")
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            self._log(f"Full result saved to: {result_file}")
            
            # Guardar solo segmentos limpios
            segments_file = os.path.join(debug_dir, "cleaned_segments.json")
            with open(segments_file, 'w', encoding='utf-8') as f:
                json.dump(result.get('segments', []), f, ensure_ascii=False, indent=2)
            self._log(f"Cleaned segments saved to: {segments_file}")
            
            # Crear archivo de resumen
            summary_file = os.path.join(debug_dir, "summary.txt")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"TRANSCRIPTION SUMMARY\n")
                f.write(f"====================\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Task ID: {task_id or 'N/A'}\n")
                f.write(f"Audio file: {audio_filename}\n")
                f.write(f"Audio size: {os.path.getsize(audio_path) / (1024*1024):.1f} MB\n")
                f.write(f"Model: {current_app.config['WHISPER_MODEL']}\n")
                f.write(f"Temperature: {result.get('temperature', 'N/A')}\n")
                f.write(f"Test mode: {result.get('test_mode', 'N/A')}\n")
                f.write(f"Total segments: {len(result.get('segments', []))}\n")
                f.write(f"Total duration: {result.get('total_duration', 0):.1f}s\n")
                f.write(f"Avg segment duration: {result.get('avg_duration', 0):.1f}s\n")
                f.write(f"Total words: {result.get('total_words', 0)}\n")
                f.write(f"Transcription time: {result.get('transcribe_time', 0):.1f}s\n")
                f.write(f"\nFIRST 5 SEGMENTS:\n")
                for i, segment in enumerate(result.get('segments', [])[:5], 1):
                    f.write(f"{i}. [{segment['start']:.1f}-{segment['end']:.1f}] {segment['text']}\n")
            
            self._log(f"Summary saved to: {summary_file}")
            self._log(f"All debug files saved to: {debug_dir}")
            
        except Exception as e:
            self._log(f"Error saving debug files: {e}", "ERROR")
    
    def extract_audio(self, video_path: str, output_path: str, test_mode: bool = False) -> bool:
        """Extraer audio del video con opción de modo de prueba"""
        self._log(f"Extracting audio from: {video_path}")
        self._log(f"Output: {output_path}")
        self._log(f"Test mode: {test_mode}")
        
        try:
            if test_mode:
                # Extraer solo los primeros 15 minutos para pruebas
                cmd = [
                    'ffmpeg', '-i', video_path,
                    '-vn', '-acodec', 'pcm_s16le',
                    '-ar', '16000', '-ac', '1',
                    '-t', str(current_app.config.get('AUDIO_EXTRACT_DURATION', 900)),
                    '-y', output_path
                ]
                self._log(f"TEST MODE: Extracting only first {current_app.config.get('AUDIO_EXTRACT_DURATION', 900)//60} minutes")
            else:
                cmd = [
                    'ffmpeg', '-i', video_path,
                    '-vn', '-acodec', 'pcm_s16le',
                    '-ar', '16000', '-ac', '1',
                    '-y', output_path
                ]
            
            self._log(f"Running ffmpeg command: {' '.join(cmd)}")
            start_time = time.time()
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            extract_time = time.time() - start_time
            
            if result.returncode == 0:
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                self._log(f"Audio extraction completed successfully in {extract_time:.1f}s")
                self._log(f"File size: {file_size:.1f} MB")
                return True
            else:
                self._log(f"Audio extraction failed: {result.stderr}", "ERROR")
                return False
        except Exception as e:
            self._log(f"Error extracting audio: {e}", "ERROR")
            return False
    
    def clean_segments_for_sync(self, segments: List[Dict]) -> List[Dict]:
        """Limpiar segmentos optimizados para sincronización"""
        if not segments:
            self._log("No segments to clean")
            return []
        
        self._log(f"Starting segment cleaning for {len(segments)} segments")
        
        config = current_app.config.get('SEGMENT_CLEANING_CONFIG', {'min_duration': 1.0, 'max_duration': 30.0, 'min_words': 3})
        min_duration = config['min_duration']
        max_duration = config['max_duration']
        min_words = config['min_words']
        
        self._log(f"Cleaning config - Min duration: {min_duration}s, Max duration: {max_duration}s, Min words: {min_words}")
        
        # Paso 1: Fusionar segmentos muy cortos
        self._log("Step 1: Merging short segments...")
        merged = []
        current_segment = segments[0].copy()
        
        for i, segment in enumerate(segments[1:], 1):
            # Si el segmento actual es muy corto, intentar fusionar con el siguiente
            if current_segment['end'] - current_segment['start'] < min_duration:
                # Verificar si los segmentos están cerca en tiempo (dentro de 2 segundos)
                if segment['start'] - current_segment['end'] <= 2.0:
                    # Fusionar texto
                    current_segment['text'] = current_segment['text'].strip() + ' ' + segment['text'].strip()
                    current_segment['end'] = segment['end']
                    self._log(f"Merged segment {i} with previous")
                else:
                    # Si no están cerca, finalizar el actual y empezar nuevo
                    if current_segment['end'] - current_segment['start'] >= 2.0:  # Mantener segmentos >= 2s
                        merged.append(current_segment)
                    current_segment = segment.copy()
            else:
                # El segmento actual es suficientemente largo, finalizarlo
                merged.append(current_segment)
                current_segment = segment.copy()
        
        # Agregar el último segmento
        if current_segment['end'] - current_segment['start'] >= 2.0:
            merged.append(current_segment)
        
        self._log(f"After merging: {len(merged)} segments")
        
        # Paso 2: Filtrar por duración y calidad de contenido
        self._log("Step 2: Filtering segments by duration and quality...")
        filtered = []
        for i, segment in enumerate(merged):
            duration = segment['end'] - segment['start']
            word_count = len(segment['text'].split())
            
            # Mantener segmentos que:
            # - Estén entre min_duration y max_duration
            # - Tengan suficientes palabras
            # - No contengan repetición excesiva
            if (min_duration <= duration <= max_duration and 
                word_count >= min_words and
                not self._is_excessively_repetitive(segment['text'])):
                filtered.append(segment)
            else:
                self._log(f"Filtered out segment {i}: duration={duration:.1f}s, words={word_count}")
        
        self._log(f"After filtering: {len(filtered)} segments")
        return filtered
    
    def _is_excessively_repetitive(self, text: str, max_repetition_ratio: float = 0.3) -> bool:
        """Verificar si el texto contiene repetición excesiva"""
        words = text.lower().split()
        if len(words) < 3:
            return True
        
        # Contar frecuencias de palabras
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Verificar si alguna palabra aparece demasiado frecuentemente
        max_count = max(word_counts.values())
        repetition_ratio = max_count / len(words)
        
        if repetition_ratio > max_repetition_ratio:
            self._log(f"Text marked as repetitive: ratio={repetition_ratio:.2f} > {max_repetition_ratio}")
            return True
        
        return False
    
    def transcribe_audio(self, audio_path: str, test_mode: bool = False, task_id: Optional[str] = None) -> Optional[Dict]:
        """Transcribir audio con configuración optimizada"""
        self._log(f"Starting transcription of: {audio_path}")
        self._log(f"Test mode: {test_mode}")
        
        # Verificar memoria antes de transcribir
        if not self._check_memory_usage():
            self._log("Skipping transcription due to high memory usage", "WARNING")
            return None
        
        # Cargar modelo si no está cargado
        if not self._load_whisper_model():
            self._log("Failed to load Whisper model", "ERROR")
            return None
        
        try:
            # Obtener opciones de Whisper
            options = current_app.config.get('WHISPER_OPTIONS', {'temperature': [0.0], 'beam_size': 5})
            temperature = options['temperature'][0]
            self._log(f"Transcribing with temperature {temperature}...")
            
            start_time = time.time()
            
            language = current_app.config.get('TRANSCRIPTION_LANGUAGE', 'es')
            initial_prompt = None
            if language == 'es':
                initial_prompt = current_app.config.get('TRANSCRIPTION_INITIAL_PROMPT', None)

            if self.whisper_model is not None:
                # Configurar opciones sin verbose para reducir logs
                whisper_options = {k: v for k, v in options.items() if k != 'temperature'}
                whisper_options['verbose'] = False  # Reducir output verbose
                if initial_prompt:
                    whisper_options['initial_prompt'] = initial_prompt
                whisper_options['language'] = language
                result = self.whisper_model.transcribe(
                    audio_path, 
                    temperature=temperature,
                    **whisper_options
                )
                # Guardar el JSON crudo de Whisper para debug
                try:
                    if task_id:
                        raw_path = f"/tmp/whisper_raw_{task_id}.json"
                        with open(raw_path, "w", encoding="utf-8") as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                        self._log(f"Raw Whisper JSON saved: {raw_path}")
                except Exception as e:
                    self._log(f"Failed to save raw Whisper JSON: {e}", "WARNING")
            else:
                self._log("Whisper model is not loaded", "ERROR")
                return None
            
            transcribe_time = time.time() - start_time
            self._log(f"Whisper transcription completed in {transcribe_time:.1f}s")
            
            # Limpiar segmentos para sincronización
            segments = result.get('segments', [])
            self._log(f"Raw segments from Whisper: {len(segments)}")
            cleaned_segments = self.clean_segments_for_sync(segments)
            self._log(f"Segments after cleaning: {len(cleaned_segments)}")
            
            if cleaned_segments:
                # Calcular estadísticas
                total_duration = sum(s['end'] - s['start'] for s in cleaned_segments)
                avg_duration = total_duration / len(cleaned_segments)
                total_words = sum(len(s['text'].split()) for s in cleaned_segments)
                
                self._log("=== TRANSCRIPTION RESULTS ===")
                self._log(f"Original segments: {len(segments)}")
                self._log(f"Cleaned segments: {len(cleaned_segments)}")
                self._log(f"Total duration: {total_duration:.1f}s")
                self._log(f"Avg segment duration: {avg_duration:.1f}s")
                self._log(f"Total words: {total_words}")
                self._log(f"Transcription time: {transcribe_time:.1f}s")
                
                # Crear resultado
                result_data = {
                    'segments': cleaned_segments,
                    'total_duration': total_duration,
                    'avg_duration': avg_duration,
                    'total_words': total_words,
                    'transcribe_time': transcribe_time,
                    'temperature': temperature,
                    'test_mode': test_mode,
                    'model': current_app.config['WHISPER_MODEL'],
                    'language': current_app.config.get('TRANSCRIPTION_LANGUAGE', 'es'),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Guardar archivos de debug
                self._save_debug_files(audio_path, result_data, task_id)
                # Limpiar memoria y liberar modelo Whisper de la GPU
                self._cleanup_memory()
                if self.whisper_model is not None:
                    del self.whisper_model
                    self.whisper_model = None
                    try:
                        import torch  # type: ignore
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except Exception:
                        pass
                self._log("Transcription completed successfully!")
                return result_data
            else:
                self._log("No valid segments found", "WARNING")
                self._cleanup_memory()
                return None
                
        except Exception as e:
            self._log(f"Error during transcription: {e}", "ERROR")
            self._cleanup_memory()
            return None
    
    def transcribe_video(self, video_path: str, test_mode: Optional[bool] = None, task_id: Optional[str] = None) -> Optional[Dict]:
        """Transcribir video completo (extraer audio + transcribir)"""
        if test_mode is None:
            test_mode = bool(current_app.config.get('TRANSCRIPTION_TEST_MODE', False))
        
        self._log(f"Starting video transcription: {video_path}")
        self._log(f"Test mode: {test_mode}")
        self._log(f"Task ID: {task_id or 'N/A'}")
        
        # Extraer audio
        temp_audio = tempfile.mktemp(suffix='.wav')
        if not self.extract_audio(video_path, temp_audio, test_mode=test_mode):
            return None
        
        try:
            # Transcribir audio
            result = self.transcribe_audio(temp_audio, test_mode=test_mode, task_id=task_id)
            return result
        finally:
            # Limpiar archivo temporal
            try:
                os.remove(temp_audio)
                self._log(f"Temporary audio file removed: {temp_audio}")
            except:
                pass 