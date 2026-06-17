"""
app.py — TrashVision Flask Web Interface
Adaptado ao repositório dheniiel/TrashVision

Alterações em relação ao original:
  1. Modelo yolo_taco_cpu_v2 definido como PRIMEIRA prioridade de busca.
  2. Detecção de vídeo via streaming (SSE/multipart) — sem salvar o vídeo
     processado em disco nem exigir download pelo usuário.
     O cliente recebe os frames anotados em tempo real pelo endpoint
     GET /api/detect/video/stream/<job_id> (multipart/x-mixed-replace).
"""

import os
import sys
import uuid
import base64
import io
import cv2
import numpy as np
from flask import (
    Flask, render_template, request, jsonify,
    send_from_directory, Response, stream_with_context,
)
from werkzeug.utils import secure_filename
import threading
import glob
import queue
import time

# ── garante que módulos locais (core/, ui/) sejam encontrados ──────────────
sys.path.insert(0, os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trashvision-flask'
app.config['UPLOAD_FOLDER']  = os.path.join('static', 'uploads')
app.config['RESULTS_FOLDER'] = os.path.join('static', 'results')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB

ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
ALLOWED_VIDEO = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}

# ──────────────────────────────────────────────────────────────────────────────
# Busca e carregamento do modelo YOLO
# ──────────────────────────────────────────────────────────────────────────────

MODEL        = None
MODEL_LOADED = False
MODEL_ERROR  = None
MODEL_PATH   = None
DEFAULT_CONF = 0.25

# ALTERAÇÃO 1 — yolo_taco_cpu_v2 é a PRIMEIRA opção na lista de candidatos.
CANDIDATE_PATHS = [
    # ── PRIORIDADE 1: modelo v2 (nova versão treinada) ──────────────────────
    r'runs\detect\yolo_taco_cpu_v2\weights\best.pt',
    'runs/detect/yolo_taco_cpu_v2/weights/best.pt',
    # ── PRIORIDADE 2: modelo v1-6 (versão anterior) ─────────────────────────
    r'runs\detect\yolo_taco_cpu_v1-6\weights\best.pt',
    'runs/detect/yolo_taco_cpu_v1-6/weights/best.pt',
    # ── PRIORIDADE 3: qualquer best.pt em runs/detect/ ──────────────────────
    'runs/detect/*/weights/best.pt',
    # ── PRIORIDADE 4: modelos base incluídos no repositório ─────────────────
    'yolo11s.pt',
    'yolo11n.pt',
    'yolov8n.pt',
]


def find_model():
    """Retorna o primeiro caminho de modelo válido encontrado."""
    for pattern in CANDIDATE_PATHS:
        if '*' in pattern:
            matches = sorted(glob.glob(pattern), reverse=True)
            for m in matches:
                if os.path.exists(m):
                    return m
        else:
            if os.path.exists(pattern):
                return pattern
    return None


def load_model():
    global MODEL, MODEL_LOADED, MODEL_ERROR, MODEL_PATH
    path = find_model()
    if not path:
        MODEL_ERROR = (
            "Nenhum modelo encontrado. Caminhos verificados: "
            "runs/detect/yolo_taco_cpu_v2/weights/best.pt, "
            "runs/detect/yolo_taco_cpu_v1-6/weights/best.pt, "
            "yolo11s.pt, etc."
        )
        print(f"⚠  {MODEL_ERROR}")
        return

    try:
        from ultralytics import YOLO
        MODEL = YOLO(path)
        MODEL_PATH   = path
        MODEL_LOADED = True
        print(f"✅ Modelo carregado: {path}")
    except ImportError:
        MODEL_ERROR = "ultralytics não instalado. Execute: pip install ultralytics"
        print(f"⚠  {MODEL_ERROR}")
    except Exception as e:
        MODEL_ERROR = str(e)
        print(f"❌ Erro ao carregar modelo: {e}")


load_model()

# ──────────────────────────────────────────────────────────────────────────────
# Inferência
# ──────────────────────────────────────────────────────────────────────────────

def run_inference(frame, conf=None):
    """
    Roda o modelo no frame e retorna (frame_anotado, lista_de_detecções).
    """
    if conf is None:
        conf = DEFAULT_CONF

    if MODEL and MODEL_LOADED:
        results    = MODEL.predict(source=frame, conf=conf, verbose=False)
        annotated  = results[0].plot()
        detections = []
        for box in results[0].boxes:
            cls_id        = int(box.cls[0])
            label         = results[0].names.get(cls_id, f'classe_{cls_id}')
            c             = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detections.append({
                'label': label, 'confidence': round(c, 3),
                'bbox':  [x1, y1, x2, y2],
            })
        return annotated, detections

    # ── Modo demonstração (sem modelo) ──────────────────────────────────────
    DEMO_LABELS = [
        'Aluminium foil', 'Battery', 'Bottle', 'Bottle cap', 'Can',
        'Carton', 'Cigarette', 'Cup', 'Lid', 'Paper', 'Plastic bag',
        'Plastic film', 'Pop tab', 'Straw', 'Styrofoam piece', 'Wrapper',
    ]
    annotated  = frame.copy()
    h, w       = frame.shape[:2]
    labels     = np.random.choice(DEMO_LABELS, size=np.random.randint(1, 4), replace=False)
    detections = []
    for label in labels:
        x1 = np.random.randint(0, w // 2)
        y1 = np.random.randint(0, h // 2)
        x2 = min(x1 + np.random.randint(60, w // 3), w - 1)
        y2 = min(y1 + np.random.randint(60, h // 3), h - 1)
        c  = round(np.random.uniform(0.55, 0.99), 3)
        color = (0, 200, 80)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        tag = f"{label} {c:.0%}"
        (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
        cv2.putText(annotated, tag, (x1 + 3, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
        detections.append({'label': label, 'confidence': c, 'bbox': [x1, y1, x2, y2]})
    return annotated, detections

# ──────────────────────────────────────────────────────────────────────────────
# Utilitários
# ──────────────────────────────────────────────────────────────────────────────

def allowed_image(f): return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE
def allowed_video(f): return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO

def frame_to_b64(frame):
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode('utf-8')

def frame_to_jpg_bytes(frame):
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return buf.tobytes()

# ──────────────────────────────────────────────────────────────────────────────
# Rotas — páginas
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html',
                           model_loaded=MODEL_LOADED,
                           model_error=MODEL_ERROR,
                           model_path=MODEL_PATH)

@app.route('/camera')
def camera():
    return render_template('camera.html',
                           model_loaded=MODEL_LOADED,
                           model_error=MODEL_ERROR)

@app.route('/image')
def image():
    return render_template('image.html',
                           model_loaded=MODEL_LOADED,
                           model_error=MODEL_ERROR)

@app.route('/video')
def video():
    return render_template('video.html',
                           model_loaded=MODEL_LOADED,
                           model_error=MODEL_ERROR)

# ──────────────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/api/status')
def api_status():
    return jsonify({
        'model_loaded': MODEL_LOADED,
        'model_path':   MODEL_PATH,
        'model_error':  MODEL_ERROR,
        'demo_mode':    not MODEL_LOADED,
        'default_conf': DEFAULT_CONF,
    })


@app.route('/api/detect/frame', methods=['POST'])
def detect_frame():
    """Câmera ao vivo — recebe frame base64, retorna frame anotado."""
    data = request.get_json()
    if not data or 'frame' not in data:
        return jsonify({'error': 'Frame não fornecido'}), 400

    conf = float(data.get('conf', DEFAULT_CONF))
    conf = max(0.05, min(0.95, conf))

    try:
        b64       = data['frame'].split(',')[-1]
        img_bytes = base64.b64decode(b64)
        nparr     = np.frombuffer(img_bytes, np.uint8)
        frame     = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'error': 'Frame inválido'}), 400

        annotated, detections = run_inference(frame, conf=conf)
        return jsonify({
            'annotated_frame': 'data:image/jpeg;base64,' + frame_to_b64(annotated),
            'detections':      detections,
            'count':           len(detections),
            'demo_mode':       not MODEL_LOADED,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detect/image', methods=['POST'])
def detect_image():
    """Imagem — upload, inferência, retorna imagem anotada."""
    if 'image' not in request.files:
        return jsonify({'error': 'Nenhuma imagem enviada'}), 400

    file = request.files['image']
    if not file.filename or not allowed_image(file.filename):
        return jsonify({'error': 'Formato inválido'}), 400

    conf = float(request.form.get('conf', DEFAULT_CONF))
    conf = max(0.05, min(0.95, conf))

    try:
        uid   = str(uuid.uuid4())[:8]
        ext   = file.filename.rsplit('.', 1)[1].lower()
        src   = os.path.join(app.config['UPLOAD_FOLDER'], f'{uid}.{ext}')
        file.save(src)

        frame = cv2.imread(src)
        if frame is None:
            return jsonify({'error': 'Não foi possível ler a imagem'}), 400

        annotated, detections = run_inference(frame, conf=conf)

        out = os.path.join(app.config['RESULTS_FOLDER'], f'result_{uid}.jpg')
        cv2.imwrite(out, annotated)

        summary = {}
        for d in detections:
            summary[d['label']] = summary.get(d['label'], 0) + 1

        return jsonify({
            'result_url': f'/static/results/result_{uid}.jpg',
            'detections': detections,
            'count':      len(detections),
            'summary':    summary,
            'demo_mode':  not MODEL_LOADED,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# ALTERAÇÃO 2 — Detecção de vídeo via streaming (sem download do vídeo)
#
# Fluxo:
#   1. POST /api/detect/video        → recebe o arquivo, cria um job e inicia
#                                       uma thread que produz frames anotados
#                                       numa Queue.
#   2. GET  /api/detect/video/stream/<job_id>
#                                    → abre uma resposta multipart/x-mixed-replace
#                                       e envia os JPEGs da fila em tempo real,
#                                       sem que o cliente precise baixar nada.
#   3. GET  /api/job/<job_id>        → retorna metadados (progresso, resumo,
#                                       detecções) SEM URL de vídeo.
# ──────────────────────────────────────────────────────────────────────────────

# Dicionário global de jobs  {job_id: {...}}
video_jobs: dict[str, dict] = {}

# Tamanho máximo da fila de frames por job (limita uso de memória)
FRAME_QUEUE_MAX = 60


def process_video_streaming(job_id: str, input_path: str, conf: float):
    """
    Lê o vídeo, roda inferência e empurra frames anotados (JPEG bytes)
    para a fila do job.  Não grava nenhum arquivo de resultado em disco.
    """
    job = video_jobs[job_id]
    try:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            job.update({'status': 'error', 'error': 'Não foi possível abrir o vídeo'})
            return

        fps       = cap.get(cv2.CAP_PROP_FPS) or 25
        total     = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        SKIP      = max(1, int(fps // 5))   # ~5 inferências/seg

        all_dets  = []
        frame_idx = 0
        last_annotated = None

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % SKIP == 0:
                annotated, dets = run_inference(frame, conf=conf)
                last_annotated  = annotated
                all_dets.extend(dets)
            else:
                # repete o último frame anotado para manter a fluidez
                annotated = last_annotated if last_annotated is not None else frame

            # Envia para a fila (bloqueia se cheia para não consumir memória)
            jpg = frame_to_jpg_bytes(annotated)
            job['frame_queue'].put(jpg, timeout=10)

            frame_idx          += 1
            job['progress']     = min(99, int(frame_idx / total * 100))

        cap.release()

        # Sinaliza fim da stream
        job['frame_queue'].put(None)

        summary = {}
        for d in all_dets:
            summary[d['label']] = summary.get(d['label'], 0) + 1

        job.update({
            'status':     'done',
            'progress':   100,
            'detections': all_dets[:300],
            'summary':    summary,
            'count':      len(all_dets),
            'demo_mode':  not MODEL_LOADED,
        })

    except Exception as e:
        job.update({'status': 'error', 'error': str(e)})
        job['frame_queue'].put(None)   # desbloqueia consumidores


@app.route('/api/detect/video', methods=['POST'])
def detect_video():
    """
    Recebe o vídeo, cria job de streaming e retorna o job_id.
    O cliente deve abrir GET /api/detect/video/stream/<job_id> para
    visualizar os frames em tempo real — sem baixar o vídeo processado.
    """
    if 'video' not in request.files:
        return jsonify({'error': 'Nenhum vídeo enviado'}), 400

    file = request.files['video']
    if not file.filename or not allowed_video(file.filename):
        return jsonify({'error': 'Formato inválido'}), 400

    conf = float(request.form.get('conf', DEFAULT_CONF))
    conf = max(0.05, min(0.95, conf))

    try:
        job_id = str(uuid.uuid4())[:8]
        ext    = file.filename.rsplit('.', 1)[1].lower()
        fpath  = os.path.join(app.config['UPLOAD_FOLDER'], f'{job_id}.{ext}')
        file.save(fpath)

        video_jobs[job_id] = {
            'status':      'processing',
            'progress':    0,
            'frame_queue': queue.Queue(maxsize=FRAME_QUEUE_MAX),
            # URL da stream para o cliente usar
            'stream_url':  f'/api/detect/video/stream/{job_id}',
        }

        t = threading.Thread(
            target=process_video_streaming,
            args=(job_id, fpath, conf),
            daemon=True,
        )
        t.start()

        return jsonify({
            'job_id':     job_id,
            'status':     'processing',
            'stream_url': f'/api/detect/video/stream/{job_id}',
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detect/video/stream/<job_id>')
def video_stream(job_id: str):
    """
    Endpoint de streaming multipart/x-mixed-replace.
    O cliente (tag <img> ou fetch com ReadableStream) recebe os frames
    anotados em tempo real, sem precisar baixar o vídeo resultante.

    Exemplo de uso no template HTML:
        <img id="stream" src="/api/detect/video/stream/{{ job_id }}">
    """
    job = video_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404

    def generate():
        fq: queue.Queue = job['frame_queue']
        while True:
            try:
                jpg = fq.get(timeout=30)   # aguarda até 30 s pelo próximo frame
            except queue.Empty:
                break                      # timeout — encerra stream

            if jpg is None:                # sentinela de fim
                break

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n'
                + jpg +
                b'\r\n'
            )

    return Response(
        stream_with_context(generate()),
        mimetype='multipart/x-mixed-replace; boundary=frame',
    )


@app.route('/api/job/<job_id>')
def job_status(job_id: str):
    """Retorna metadados do job (progresso, resumo de detecções, etc.)."""
    job = video_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404

    # Remove a fila (não serializável) antes de retornar
    safe = {k: v for k, v in job.items() if k != 'frame_queue'}
    return jsonify(safe)


@app.route('/static/results/<path:filename>')
def serve_result(filename):
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'],  exist_ok=True)
    os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)