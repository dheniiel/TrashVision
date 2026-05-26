from ultralytics import YOLO
import cv2
import time

MODEL_PATH = r'.\runs\detect\yolo_taco_cpu_v1-6\weights\best.pt'
CONFIDENCE = 0.25
WINDOW_NAME = 'Detecção de Lixo (Webcam)'

def load_model(path):
    try:
        model = YOLO(path)
        print(f"Modelo carregado: {path}")
        return model
    except Exception as e:
        print(f"Erro ao carregar modelo: {e}")
        exit(1)

def open_camera(index=0):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print("Erro: Não foi possível abrir a webcam.")
        exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap

def draw_info(frame, fps, conf, paused):
    color = (0, 255, 0) if not paused else (0, 0, 255)
    status = "PAUSADO" if paused else f"FPS: {fps:.1f}"
    cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(frame, f"Conf: {conf:.2f} | Q=Sair P=Pausar +/-=Conf",
                (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

def main():
    model = load_model(MODEL_PATH)
    cap = open_camera()

    conf = CONFIDENCE
    paused = False
    prev_time = time.time()
    last_frame = None

    print("Controles: Q=Sair | P=Pausar | +=Aumentar confiança | -=Diminuir confiança")

    while True:
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('p'):
            paused = not paused
        elif key == ord('+') and conf < 0.95:
            conf = round(conf + 0.05, 2)
            print(f"Confiança: {conf}")
        elif key == ord('-') and conf > 0.05:
            conf = round(conf - 0.05, 2)
            print(f"Confiança: {conf}")

        if paused and last_frame is not None:
            cv2.imshow(WINDOW_NAME, last_frame)
            continue

        ret, frame = cap.read()
        if not ret:
            print("Erro: Não foi possível ler o frame.")
            break

        results = model.predict(source=frame, show=False, conf=conf, verbose=False)
        annotated_frame = results[0].plot()

        # Calcular FPS
        curr_time = time.time()
        fps = 1.0 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
        prev_time = curr_time

        draw_info(annotated_frame, fps, conf, paused)
        last_frame = annotated_frame.copy()
        cv2.imshow(WINDOW_NAME, annotated_frame)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()