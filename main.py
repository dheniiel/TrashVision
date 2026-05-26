"""
main.py
=======
Ponto de entrada da aplicação TrashVision.

Uso:
    python main.py

Requisitos:
    pip install ultralytics opencv-python pillow customtkinter
"""

import sys
import os

# Garantir que os módulos locais sejam encontrados
sys.path.insert(0, os.path.dirname(__file__))

def check_dependencies():
    """Verifica dependências críticas antes de iniciar."""
    missing = []

    try:
        import tkinter
    except ImportError:
        missing.append("tkinter (instale python3-tk no Linux)")

    try:
        import PIL
    except ImportError:
        missing.append("Pillow  →  pip install Pillow")

    try:
        import cv2
    except ImportError:
        missing.append("opencv-python  →  pip install opencv-python")

    if missing:
        print("=" * 55)
        print("  TrashVision — Dependências faltando:")
        print("=" * 55)
        for dep in missing:
            print(f"  ✗  {dep}")
        print()
        print("  Instale as dependências e tente novamente.")
        print("=" * 55)
        sys.exit(1)

    # ultralytics é opcional na inicialização (pode ser carregado depois)
    try:
        import ultralytics
    except ImportError:
        print("[AVISO] ultralytics não encontrado.")
        print("        Para detecção funcionar, execute:")
        print("        pip install ultralytics")
        print()


def main():
    check_dependencies()

    from ui.app import App

    app = App()

    # Ícone da janela (se disponível)
    try:
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
        if os.path.exists(icon_path):
            from PIL import Image, ImageTk
            icon = ImageTk.PhotoImage(Image.open(icon_path))
            app.iconphoto(True, icon)
    except Exception:
        pass  # Ícone é opcional

    app.mainloop()


if __name__ == "__main__":
    main()
