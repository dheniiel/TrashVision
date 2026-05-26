"""
core/image_utils.py
===================
Utilitários para conversão e manipulação de imagens entre
OpenCV (BGR numpy array) e tkinter (PhotoImage via PIL).
"""

import cv2
import numpy as np
from PIL import Image, ImageTk
from typing import Tuple


def cv2_to_pil(frame: np.ndarray) -> Image.Image:
    """Converte frame BGR do OpenCV para imagem PIL RGB."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def pil_to_photoimage(pil_image: Image.Image) -> ImageTk.PhotoImage:
    """Converte PIL Image para PhotoImage do tkinter."""
    return ImageTk.PhotoImage(pil_image)


def fit_image_to_canvas(
    frame: np.ndarray,
    canvas_width: int,
    canvas_height: int
) -> Tuple[ImageTk.PhotoImage, int, int]:
    """
    Redimensiona o frame mantendo proporção para caber no canvas.
    Retorna (PhotoImage, x_offset, y_offset) para centralização.
    """
    h, w = frame.shape[:2]
    scale = min(canvas_width / w, canvas_height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    pil = cv2_to_pil(frame)
    pil = pil.resize((new_w, new_h), Image.LANCZOS)
    photo = ImageTk.PhotoImage(pil)

    x_offset = (canvas_width - new_w) // 2
    y_offset = (canvas_height - new_h) // 2

    return photo, x_offset, y_offset


def load_image_file(path: str) -> Tuple[bool, np.ndarray, str]:
    """
    Lê uma imagem do disco com OpenCV.
    Retorna (sucesso, frame, mensagem).
    """
    frame = cv2.imread(path)
    if frame is None:
        return False, None, f"Não foi possível abrir: {path}"
    return True, frame, "OK"
