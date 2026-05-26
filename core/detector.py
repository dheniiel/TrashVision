"""
core/detector.py
================
Módulo responsável por toda a lógica de detecção com YOLO.
Mantido separado da interface para facilitar manutenção e testes.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import threading


class DetectionResult:
    """Encapsula o resultado de uma detecção."""
    
    def __init__(self, annotated_frame: np.ndarray, detections: List[Dict[str, Any]],
                 inference_time_ms: float):
        self.annotated_frame = annotated_frame
        self.detections = detections          # lista de {label, confidence, bbox}
        self.inference_time_ms = inference_time_ms
        self.count = len(detections)


class TrashDetector:
    """
    Wrapper em torno do modelo YOLO.
    Expõe métodos simples para detecção em imagem, vídeo e webcam.
    """

    def __init__(self):
        self._model = None
        self._model_path: Optional[str] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Carregamento do modelo
    # ------------------------------------------------------------------

    def load_model(self, model_path: str) -> Tuple[bool, str]:
        """
        Carrega o modelo YOLO a partir de um arquivo .pt.
        Retorna (sucesso, mensagem).
        """
        path = Path(model_path)
        if not path.exists():
            return False, f"Arquivo não encontrado: {model_path}"
        if path.suffix.lower() != ".pt":
            return False, "O arquivo deve ter extensão .pt"

        try:
            from ultralytics import YOLO
            with self._lock:
                self._model = YOLO(str(path))
                self._model_path = str(path)
            return True, f"Modelo carregado: {path.name}"
        except ImportError:
            return False, "ultralytics não está instalado. Execute: pip install ultralytics"
        except Exception as e:
            return False, f"Erro ao carregar modelo: {e}"

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def model_name(self) -> str:
        if self._model_path:
            return Path(self._model_path).name
        return "Nenhum modelo carregado"

    # ------------------------------------------------------------------
    # Detecção em imagem estática
    # ------------------------------------------------------------------

    def detect_image(self, image_path: str, confidence: float = 0.25) -> Tuple[Optional[DetectionResult], str]:
        """
        Realiza detecção em uma imagem e retorna o resultado anotado.
        """
        if not self.is_loaded:
            return None, "Modelo não carregado."

        frame = cv2.imread(image_path)
        if frame is None:
            return None, f"Não foi possível abrir a imagem: {image_path}"

        return self._run_inference(frame, confidence)

    # ------------------------------------------------------------------
    # Detecção em frame individual (usado por vídeo e webcam)
    # ------------------------------------------------------------------

    def detect_frame(self, frame: np.ndarray, confidence: float = 0.25) -> Tuple[Optional[DetectionResult], str]:
        """
        Realiza detecção em um frame OpenCV (numpy array BGR).
        """
        if not self.is_loaded:
            return None, "Modelo não carregado."
        return self._run_inference(frame, confidence)

    # ------------------------------------------------------------------
    # Lógica interna de inferência
    # ------------------------------------------------------------------

    def _run_inference(self, frame: np.ndarray, confidence: float) -> Tuple[Optional[DetectionResult], str]:
        """Executa a inferência YOLO e extrai os resultados."""
        import time
        try:
            with self._lock:
                t0 = time.perf_counter()
                results = self._model.predict(
                    source=frame,
                    conf=confidence,
                    show=False,
                    verbose=False
                )
                elapsed_ms = (time.perf_counter() - t0) * 1000

            annotated = results[0].plot()

            # Extrair detecções individuais
            detections = []
            boxes = results[0].boxes
            if boxes is not None:
                names = results[0].names
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].tolist()
                    detections.append({
                        "label": names.get(cls_id, str(cls_id)),
                        "confidence": conf,
                        "bbox": xyxy
                    })

            return DetectionResult(annotated, detections, elapsed_ms), "OK"

        except Exception as e:
            return None, f"Erro durante inferência: {e}"


# ------------------------------------------------------------------
# Processador de vídeo em thread separada
# ------------------------------------------------------------------

class VideoProcessor:
    """
    Itera sobre frames de um arquivo de vídeo ou webcam em uma thread
    de background, chamando um callback com o DetectionResult.
    """

    def __init__(self, detector: TrashDetector):
        self._detector = detector
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._paused = threading.Event()
        self._paused.set()  # inicia rodando (não pausado)

    # ------------------------------------------------------------------
    # Controles públicos
    # ------------------------------------------------------------------

    def start(self, source, confidence: float, on_frame_callback, on_finish_callback=None):
        """
        Inicia o processamento de vídeo/webcam.
        source: caminho do arquivo ou índice inteiro da câmera.
        on_frame_callback(result: DetectionResult, fps: float) -> None
        on_finish_callback() -> None
        """
        self._stop_event.clear()
        self._paused.set()
        self._thread = threading.Thread(
            target=self._run,
            args=(source, confidence, on_frame_callback, on_finish_callback),
            daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def pause(self):
        self._paused.clear()

    def resume(self):
        self._paused.set()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Loop interno
    # ------------------------------------------------------------------

    def _run(self, source, confidence, on_frame_callback, on_finish_callback):
        import time

        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            if on_finish_callback:
                on_finish_callback()
            return

        # Configurar resolução para webcam
        if isinstance(source, int):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        prev_time = time.time()

        while not self._stop_event.is_set():
            # Espera se pausado
            self._paused.wait()

            ret, frame = cap.read()
            if not ret:
                break

            result, msg = self._detector.detect_frame(frame, confidence)
            if result is None:
                continue

            # Calcular FPS
            curr_time = time.time()
            delta = curr_time - prev_time
            fps = 1.0 / delta if delta > 0 else 0.0
            prev_time = curr_time

            on_frame_callback(result, fps)

        cap.release()
        if on_finish_callback:
            on_finish_callback()
