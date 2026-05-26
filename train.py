from ultralytics import YOLO

if __name__ == '__main__':
    model = YOLO('yolo11s.pt')
    results = model.train(
        data=r'C:\projetos\yoloDeteccaoLixo\datasets\taco_yolo\data.yaml',

        # --- Épocas e paciência ---
        epochs=80,          # Mais épocas = mais aprendizado (era 30)
        patience=15,        # Para automaticamente se não melhorar em 15 épocas

        # --- Imagem e batch ---
        imgsz=640,          # 640 é o padrão do YOLO, mais contexto visual
        batch=4,            # Reduzido para 4 (CPU com 640px exige mais RAM)

        # --- Hardware ---
        device='cpu',
        workers=0,

        # --- Otimizador ---
        optimizer='AdamW',  # Converge melhor que SGD padrão
        lr0=0.001,          # Taxa de aprendizado inicial
        lrf=0.01,           # Fator de decaimento da lr (lr final = lr0 * lrf)
        weight_decay=0.0005,

        # --- Data augmentation (melhora generalização) ---
        hsv_h=0.015,        # Variação de matiz
        hsv_s=0.7,          # Variação de saturação
        hsv_v=0.4,          # Variação de brilho
        flipud=0.1,         # Flip vertical (10% das imagens)
        fliplr=0.5,         # Flip horizontal (50%)
        mosaic=1.0,         # Combina 4 imagens em 1 (muito eficaz)
        mixup=0.1,          # Mistura leve entre imagens

        # --- Regularização ---
        dropout=0.1,        # Evita overfitting

        # --- Outros ---
        name='yolo_taco_cpu_v2',
        exist_ok=False,     # Cria nova pasta, não sobrescreve
        plots=True,         # Gera gráficos de métricas ao final
        save_period=10,     # Salva checkpoint a cada 10 épocas
    )