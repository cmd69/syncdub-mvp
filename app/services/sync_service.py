"""
Servicio principal de sincronización de audio
Maneja el procesamiento completo desde la extracción de audio hasta la generación del archivo final
"""

import os
import json
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import whisper
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import ffmpeg
from pydub import AudioSegment

from flask import current_app


class SyncService:
    """Servicio de sincronización de audio"""
    
    def __init__(self):
        self.tasks = {}  # Almacén de tareas en memoria
        self.whisper_model = None
        self.sentence_model = None
        self._lock = threading.Lock()
    
    def _load_models(self):
        """Cargar modelos de IA de forma lazy"""
        if self.whisper_model is None:
            print("Cargando modelo Whisper...")
            model_name = current_app.config.get('WHISPER_MODEL', 'base')
            self.whisper_model = whisper.load_model(model_name)
        
        if self.sentence_model is None:
            print("Cargando modelo de embeddings...")
            model_name = current_app.config.get('SENTENCE_TRANSFORMER_MODEL', 
                                               'paraphrase-multilingual-MiniLM-L12-v2')
            self.sentence_model = SentenceTransformer(model_name)
    
    def start_sync_task(self, task_id: str, original_path: str, dubbed_path: str):
        """Iniciar tarea de sincronización de forma asíncrona"""
        with self._lock:
            self.tasks[task_id] = {
                'id': task_id,
                'status': 'processing',
                'progress': 0,
                'message': 'Iniciando procesamiento...',
                'original_path': original_path,
                'dubbed_path': dubbed_path,
                'result_path': None,
                'created_at': datetime.now().isoformat(),
                'error': None
            }
        
        # Ejecutar en hilo separado
        thread = threading.Thread(target=self._process_sync_task, args=(task_id,))
        thread.daemon = True
        thread.start()
    
    def _process_sync_task(self, task_id: str):
        """Procesar tarea de sincronización"""
        try:
            self._update_task_status(task_id, 'processing', 10, 'Cargando modelos de IA...')
            self._load_models()
            
            task = self.tasks[task_id]
            original_path = task['original_path']
            dubbed_path = task['dubbed_path']
            
            # Paso 1: Extraer audio
            self._update_task_status(task_id, 'processing', 20, 'Extrayendo audio de los videos...')
            original_audio_path = self._extract_audio(original_path, task_id, 'original')
            dubbed_audio_path = self._extract_audio(dubbed_path, task_id, 'dubbed')
            
            # Paso 2: Transcribir audio
            self._update_task_status(task_id, 'processing', 40, 'Transcribiendo audio original...')
            original_transcript = self._transcribe_audio(original_audio_path)
            
            self._update_task_status(task_id, 'processing', 60, 'Transcribiendo audio doblado...')
            dubbed_transcript = self._transcribe_audio(dubbed_audio_path)
            
            # Paso 3: Emparejar frases
            self._update_task_status(task_id, 'processing', 70, 'Emparejando frases por significado...')
            matches = self._match_sentences(original_transcript, dubbed_transcript)
            
            # Paso 4: Calcular desfase
            self._update_task_status(task_id, 'processing', 80, 'Calculando desfase temporal...')
            time_offset = self._calculate_time_offset(matches)
            
            # Paso 5: Aplicar sincronización
            self._update_task_status(task_id, 'processing', 90, 'Aplicando sincronización...')
            result_path = self._apply_sync(original_path, dubbed_audio_path, time_offset, task_id)
            
            # Completar tarea
            self._update_task_status(task_id, 'completed', 100, 'Procesamiento completado', result_path)
            
        except Exception as e:
            error_msg = f"Error en procesamiento: {str(e)}"
            self._update_task_status(task_id, 'error', 0, error_msg, error=error_msg)
            current_app.logger.error(f"Error en tarea {task_id}: {str(e)}")
    
    def _update_task_status(self, task_id: str, status: str, progress: int, 
                           message: str, result_path: str = None, error: str = None):
        """Actualizar estado de la tarea"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].update({
                    'status': status,
                    'progress': progress,
                    'message': message,
                    'updated_at': datetime.now().isoformat()
                })
                if result_path:
                    self.tasks[task_id]['result_path'] = result_path
                if error:
                    self.tasks[task_id]['error'] = error
    
    def _extract_audio(self, video_path: str, task_id: str, prefix: str) -> str:
        """Extraer audio del video usando ffmpeg"""
        output_dir = current_app.config['UPLOAD_FOLDER'] / task_id
        audio_path = output_dir / f"{prefix}_audio.wav"
        
        try:
            (
                ffmpeg
                .input(video_path)
                .output(str(audio_path), 
                       acodec='pcm_s16le', 
                       ac=1, 
                       ar=current_app.config.get('AUDIO_SAMPLE_RATE', 16000))
                .overwrite_output()
                .run(quiet=True)
            )
            return str(audio_path)
        except ffmpeg.Error as e:
            raise Exception(f"Error extrayendo audio: {e}")
    
    def _transcribe_audio(self, audio_path: str) -> List[Dict]:
        """Transcribir audio usando Whisper"""
        try:
            result = self.whisper_model.transcribe(audio_path)
            return result['segments']
        except Exception as e:
            raise Exception(f"Error en transcripción: {e}")
    
    def _match_sentences(self, original_segments: List[Dict], 
                        dubbed_segments: List[Dict]) -> List[Tuple]:
        """Emparejar frases usando embeddings semánticos"""
        try:
            # Extraer textos
            original_texts = [seg['text'].strip() for seg in original_segments if seg['text'].strip()]
            dubbed_texts = [seg['text'].strip() for seg in dubbed_segments if seg['text'].strip()]
            
            if not original_texts or not dubbed_texts:
                raise Exception("No se encontró texto en las transcripciones")
            
            # Generar embeddings
            original_embeddings = self.sentence_model.encode(original_texts)
            dubbed_embeddings = self.sentence_model.encode(dubbed_texts)
            
            # Calcular similitudes
            similarities = cosine_similarity(original_embeddings, dubbed_embeddings)
            
            # Encontrar mejores coincidencias
            matches = []
            threshold = current_app.config.get('SIMILARITY_THRESHOLD', 0.7)
            
            for i, orig_seg in enumerate(original_segments):
                if i >= len(similarities):
                    continue
                    
                best_match_idx = np.argmax(similarities[i])
                best_similarity = similarities[i][best_match_idx]
                
                if best_similarity >= threshold:
                    matches.append((
                        orig_seg,
                        dubbed_segments[best_match_idx],
                        best_similarity
                    ))
            
            return matches
            
        except Exception as e:
            raise Exception(f"Error emparejando frases: {e}")
    
    def _calculate_time_offset(self, matches: List[Tuple]) -> float:
        """Calcular desfase temporal promedio"""
        if not matches:
            return 0.0
        
        offsets = []
        for orig_seg, dubbed_seg, similarity in matches:
            offset = orig_seg['start'] - dubbed_seg['start']
            offsets.append(offset)
        
        # Usar mediana para ser más robusto ante outliers
        return float(np.median(offsets))
    
    def _apply_sync(self, original_video_path: str, dubbed_audio_path: str, 
                   time_offset: float, task_id: str) -> str:
        """Aplicar sincronización y generar archivo final"""
        try:
            output_dir = current_app.config['OUTPUT_FOLDER']
            output_dir.mkdir(exist_ok=True)
            
            result_filename = f"synced_{task_id}.mkv"
            result_path = output_dir / result_filename
            
            # Cargar audio doblado y aplicar offset
            dubbed_audio = AudioSegment.from_wav(dubbed_audio_path)
            
            if time_offset > 0:
                # Agregar silencio al inicio
                silence = AudioSegment.silent(duration=int(time_offset * 1000))
                dubbed_audio = silence + dubbed_audio
            elif time_offset < 0:
                # Recortar del inicio
                dubbed_audio = dubbed_audio[int(-time_offset * 1000):]
            
            # Guardar audio sincronizado temporalmente
            temp_audio_path = output_dir / f"temp_synced_audio_{task_id}.wav"
            dubbed_audio.export(str(temp_audio_path), format="wav")
            
            # Combinar video original con audio sincronizado
            (
                ffmpeg
                .output(
                    ffmpeg.input(original_video_path)['v'],
                    ffmpeg.input(original_video_path)['a'],
                    ffmpeg.input(str(temp_audio_path))['a'],
                    str(result_path),
                    vcodec='copy',
                    acodec='aac',
                    map=['0:v', '0:a', '1:a']
                )
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Limpiar archivo temporal
            temp_audio_path.unlink(missing_ok=True)
            
            return str(result_path)
            
        except Exception as e:
            raise Exception(f"Error aplicando sincronización: {e}")
    
    def get_task_status(self, task_id: str) -> Dict:
        """Obtener estado de una tarea"""
        with self._lock:
            return self.tasks.get(task_id, {'error': 'Tarea no encontrada'})
    
    def get_result_path(self, task_id: str) -> Optional[str]:
        """Obtener ruta del archivo resultado"""
        with self._lock:
            task = self.tasks.get(task_id)
            return task.get('result_path') if task else None
    
    def list_all_tasks(self) -> List[Dict]:
        """Listar todas las tareas"""
        with self._lock:
            return list(self.tasks.values())

