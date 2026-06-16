"""
app.py — TrashVision Flask Web Interface
Adaptado ao repositório dheniiel/TrashVision

Caminhos do modelo (em ordem de prioridade):
  1. runs/detect/yolo_taco_cpu_v1-6/weights/best.pt  (modelo treinado no TACO)
  2. runs/detect/yolo_taco_cpu_v2/weights/best.pt     (modelo v2 se existir)
  3. Qualquer best.pt encontrado em runs/detect/
  4. yolo11s.pt / yolo11n.pt / yolov8n.pt             (modelos base do repo)
"""

import os
import sys
import uuid
import base64
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import threading
import glob

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
DEFAULT_CONF = 0.25   # mesmo padrão usado em webcam_detection.py

# Ordem de busca de modelos — espelha a estrutura real do repositório
CANDIDATE_PATHS = [
    # Melhor modelo treinado (v1-6 — usado no webcam_detection.py)
    r'runs\detect\yolo_taco_cpu_v1-6\weights\best.pt',
    'runs/detect/yolo_taco_cpu_v1-6/weights/best.pt',
    # Modelo v2 (train.py mais recente)
    r'runs\detect\yolo_taco_cpu_v2\weights\best.pt',
    'runs/detect/yolo_taco_cpu_v2/weights/best.pt',
    # Qualquer best.pt em runs/detect/
    'runs/detect/*/weights/best.pt',
    # Modelos base incluídos no repo
    'yolo11s.pt',
    'yolo11n.pt',
    'yolov8n.pt',
]

def find_model():
    """Retorna o primeiro caminho de modelo válido encontrado."""
    for pattern in CANDIDATE_PATHS:
        if '*' in pattern:
            matches = sorted(glob.glob(pattern), reverse=True)  # mais recente primeiro
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
            "runs/detect/yolo_taco_cpu_v/weights/best.pt, yolo11s.pt, etc."
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
    conf: limiar de confiança (padrão: DEFAULT_CONF, igual ao webcam_detection.py)
    """
    if conf is None:
        conf = DEFAULT_CONF

    if MODEL and MODEL_LOADED:
        # Usa o mesmo padrão do webcam_detection.py: model.predict(source=frame, conf=conf)
        results = MODEL.predict(source=frame, conf=conf, verbose=False)
        annotated = results[0].plot()   # mesmo método usado no webcam_detection.py
        detections = []
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            label  = results[0].names.get(cls_id, f'classe_{cls_id}')
            c      = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detections.append({'label': label, 'confidence': round(c, 3),
                                'bbox': [x1, y1, x2, y2]})
        return annotated, detections

    # ── Modo demonstração (sem modelo) ──────────────────────────────────────
    DEMO_LABELS = [
        'Aluminium foil', 'Battery', 'Bottle', 'Bottle cap', 'Can',
        'Carton', 'Cigarette', 'Cup', 'Lid', 'Paper', 'Plastic bag',
        'Plastic film', 'Pop tab', 'Straw', 'Styrofoam piece', 'Wrapper'
    ]
    annotated = frame.copy()
    h, w = frame.shape[:2]
    labels = np.random.choice(DEMO_LABELS, size=np.random.randint(1, 4), replace=False)
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
        detections.append({'label': label, 'confidence': c,
                           'bbox': [x1, y1, x2, y2]})
    return annotated, detections

# ──────────────────────────────────────────────────────────────────────────────
# Utilitários
# ──────────────────────────────────────────────────────────────────────────────

def allowed_image(f): return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE
def allowed_video(f): return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO

def frame_to_b64(frame):
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode('utf-8')

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
    conf = max(0.05, min(0.95, conf))   # clamp igual ao webcam_detection.py

    try:
        b64 = data['frame'].split(',')[-1]
        img_bytes = base64.b64decode(b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'error': 'Frame inválido'}), 400

        annotated, detections = run_inference(frame, conf=conf)
        return jsonify({
            'annotated_frame': 'data:image/jpeg;base64,' + frame_to_b64(annotated),
            'detections': detections,
            'count': len(detections),
            'demo_mode': not MODEL_LOADED,
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
        uid  = str(uuid.uuid4())[:8]
        ext  = file.filename.rsplit('.', 1)[1].lower()
        src  = os.path.join(app.config['UPLOAD_FOLDER'], f'{uid}.{ext}')
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


# ── Processamento de vídeo assíncrono ─────────────────────────────────────────

video_jobs = {}

def process_video_job(job_id, input_path, conf):
    job = video_jobs[job_id]
    try:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            job.update({'status': 'error', 'error': 'Não foi possível abrir o vídeo'})
            return

        fps    = cap.get(cv2.CAP_PROP_FPS) or 25
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

        out_name = f'result_{job_id}.mp4'
        out_path = os.path.join(app.config['RESULTS_FOLDER'], out_name)
        fourcc   = cv2.VideoWriter_fourcc(*'mp4v')
        writer   = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

        all_dets  = []
        frame_idx = 0
        SKIP = max(1, int(fps // 5))  # ~5 inferências/seg

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % SKIP == 0:
                annotated, dets = run_inference(frame, conf=conf)
                for _ in range(SKIP):
                    writer.write(annotated)
                all_dets.extend(dets)
            frame_idx += 1
            job['progress'] = min(99, int(frame_idx / total * 100))

        cap.release()
        writer.release()

        summary = {}
        for d in all_dets:
            summary[d['label']] = summary.get(d['label'], 0) + 1

        job.update({
            'status':     'done',
            'progress':   100,
            'result_url': f'/static/results/{out_name}',
            'detections': all_dets[:300],
            'summary':    summary,
            'count':      len(all_dets),
            'demo_mode':  not MODEL_LOADED,
        })
    except Exception as e:
        job.update({'status': 'error', 'error': str(e)})


@app.route('/api/detect/video', methods=['POST'])
def detect_video():
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

        video_jobs[job_id] = {'status': 'processing', 'progress': 0}
        t = threading.Thread(target=process_video_job, args=(job_id, fpath, conf))
        t.daemon = True
        t.start()

        return jsonify({'job_id': job_id, 'status': 'processing'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/job/<job_id>')
def job_status(job_id):
    job = video_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404
    return jsonify(job)


@app.route('/static/results/<path:filename>')
def serve_result(filename):
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'],  exist_ok=True)
    os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
