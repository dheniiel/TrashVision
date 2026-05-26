"""
ui/app.py
=========
Janela principal do aplicativo.
Gerencia navegação entre painéis e estado global.
"""

import tkinter as tk
from tkinter import filedialog
from typing import Optional
import threading

from ui.theme import COLORS, FONTS, WINDOW, MODES, DEFAULTS
from ui.theme import ACCEPTED_IMAGES, ACCEPTED_VIDEOS, ACCEPTED_MODELS
from ui.widgets import (StyledButton, ModeCard, ConfidenceSlider,
                         StatsPanel, DetectionList, StatusBar, Toast)
from core.detector import TrashDetector, VideoProcessor
from core.image_utils import fit_image_to_canvas


# ══════════════════════════════════════════════════════════════════════
# Janela Principal
# ══════════════════════════════════════════════════════════════════════

class App(tk.Tk):
    """
    Raiz da aplicação. Inicializa detector, janela e roteamento de painéis.
    """

    def __init__(self):
        super().__init__()

        # --- Configuração da janela ---
        self.title("TrashVision — Detecção de Resíduos com IA")
        self.geometry(f"{WINDOW['width']}x{WINDOW['height']}")
        self.minsize(WINDOW["min_width"], WINDOW["min_height"])
        self.configure(bg=COLORS["bg_primary"])

        # Tentar centralizar na tela
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - WINDOW["width"])  // 2
        y = (self.winfo_screenheight() - WINDOW["height"]) // 2
        self.geometry(f"+{x}+{y}")

        # --- Estado global ---
        self._detector = TrashDetector()
        self._video_processor = VideoProcessor(self._detector)
        self._current_panel: Optional[str] = None

        # --- Construir UI ---
        self._build_header()
        self._build_status_bar()
        self._build_body()

        # Mostrar tela inicial
        self._show_home()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Layout estrutural
    # ------------------------------------------------------------------

    def _build_header(self):
        """Barra superior com logo, título e botão de carregar modelo."""
        bar = tk.Frame(self, bg=COLORS["bg_secondary"], height=56)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        # Logo + título
        left = tk.Frame(bar, bg=COLORS["bg_secondary"])
        left.pack(side="left", padx=18, fill="y")
        tk.Label(left, text="♻", font=("Helvetica", 22),
                 bg=COLORS["bg_secondary"], fg=COLORS["accent"]).pack(side="left", padx=(0, 8))
        title_frame = tk.Frame(left, bg=COLORS["bg_secondary"])
        title_frame.pack(side="left")
        tk.Label(title_frame, text="TrashVision",
                 font=FONTS["title_md"], bg=COLORS["bg_secondary"],
                 fg=COLORS["text_primary"]).pack(anchor="w")
        tk.Label(title_frame, text="Detecção de Resíduos com IA",
                 font=FONTS["small"], bg=COLORS["bg_secondary"],
                 fg=COLORS["text_secondary"]).pack(anchor="w")

        # Botões direita
        right = tk.Frame(bar, bg=COLORS["bg_secondary"])
        right.pack(side="right", padx=18, fill="y")

        self._model_btn = StyledButton(
            right, text="Carregar Modelo", icon="📂",
            command=self._load_model_dialog, style="outline"
        )
        self._model_btn.pack(side="right", padx=(8, 0))

        # Botão voltar (oculto inicialmente)
        self._back_btn = StyledButton(
            right, text="Início", icon="⬅",
            command=self._show_home, style="secondary"
        )
        # Será exibido quando estiver em um modo

    def _build_status_bar(self):
        """Barra de status na parte inferior."""
        self._status_bar = StatusBar(self)
        self._status_bar.pack(fill="x", side="bottom")

    def _build_body(self):
        """Área principal entre header e status bar."""
        self._body = tk.Frame(self, bg=COLORS["bg_primary"])
        self._body.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Navegação entre painéis
    # ------------------------------------------------------------------

    def _clear_body(self):
        """Remove todos os widgets do body."""
        for widget in self._body.winfo_children():
            widget.destroy()

    def _show_home(self):
        """Exibe a tela inicial com os três modos."""
        self._stop_video_if_running()
        self._clear_body()
        self._current_panel = "home"

        # Esconder botão voltar
        self._back_btn.pack_forget()

        HomePanel(self._body, on_mode_selected=self._navigate_to_mode)

    def _navigate_to_mode(self, mode_id: str):
        """Navega para um painel de modo específico."""
        self._clear_body()
        self._current_panel = mode_id

        # Mostrar botão voltar
        self._back_btn.pack(side="right")

        panels = {
            "image":  ImagePanel,
            "video":  VideoPanel,
            "webcam": WebcamPanel,
        }
        PanelClass = panels.get(mode_id)
        if PanelClass:
            PanelClass(
                self._body,
                detector=self._detector,
                video_processor=self._video_processor,
                status_bar=self._status_bar,
                on_toast=self._toast,
            )

    # ------------------------------------------------------------------
    # Ações globais
    # ------------------------------------------------------------------

    def _load_model_dialog(self):
        """Abre diálogo para selecionar arquivo .pt do modelo YOLO."""
        path = filedialog.askopenfilename(
            title="Selecionar modelo YOLO (.pt)",
            filetypes=ACCEPTED_MODELS
        )
        if not path:
            return

        self._status_bar.set_status("Carregando modelo...", "processing")
        self.update()

        def _load():
            ok, msg = self._detector.load_model(path)
            self.after(0, lambda: self._on_model_loaded(ok, msg))

        threading.Thread(target=_load, daemon=True).start()

    def _on_model_loaded(self, ok: bool, msg: str):
        if ok:
            self._status_bar.set_status(msg, "success")
            self._status_bar.set_model(self._detector.model_name)
            self._toast(msg, "success")
        else:
            self._status_bar.set_status(msg, "error")
            self._toast(msg, "error")

    def _toast(self, message: str, level: str = "info"):
        Toast.show(self, message, level)

    def _stop_video_if_running(self):
        if self._video_processor.is_running:
            self._video_processor.stop()

    def _on_close(self):
        self._stop_video_if_running()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════
# Painel: Tela Inicial
# ══════════════════════════════════════════════════════════════════════

class HomePanel(tk.Frame):
    """Tela inicial com cards de seleção de modo."""

    def __init__(self, parent, on_mode_selected, **kwargs):
        super().__init__(parent, bg=COLORS["bg_primary"], **kwargs)
        self.pack(fill="both", expand=True)

        # Título central
        hero = tk.Frame(self, bg=COLORS["bg_primary"])
        hero.pack(pady=(50, 10))

        tk.Label(hero, text="Selecione o modo de detecção",
                 font=FONTS["title_xl"], bg=COLORS["bg_primary"],
                 fg=COLORS["text_primary"]).pack()
        tk.Label(hero, text="Escolha como deseja fornecer a entrada para o sistema de IA",
                 font=FONTS["body"], bg=COLORS["bg_primary"],
                 fg=COLORS["text_secondary"]).pack(pady=(6, 0))

        # Cards
        cards_frame = tk.Frame(self, bg=COLORS["bg_primary"])
        cards_frame.pack(pady=36, padx=60)

        for mode in MODES.values():
            card = ModeCard(
                cards_frame,
                icon=mode["icon"],
                title=mode["label"],
                desc=mode["desc"],
                command=lambda mid=mode["id"]: on_mode_selected(mid)
            )
            card.pack(fill="x", pady=8, ipady=2)

        # Dica de modelo
        hint = tk.Frame(self, bg=COLORS["bg_primary"])
        hint.pack(pady=(0, 20))
        tk.Label(hint, text="💡  Carregue um modelo YOLO (.pt) pelo botão no topo antes de detectar",
                 font=FONTS["small"], bg=COLORS["bg_primary"],
                 fg=COLORS["text_muted"]).pack()


# ══════════════════════════════════════════════════════════════════════
# Mixin: Layout de Detecção (canvas + sidebar)
# ══════════════════════════════════════════════════════════════════════

class DetectionLayout(tk.Frame):
    """
    Layout base compartilhado pelos três modos.
    Composto por: área de visualização (canvas) + sidebar de controles.
    """

    def __init__(self, parent, title: str, icon: str, **kwargs):
        super().__init__(parent, bg=COLORS["bg_primary"], **kwargs)
        self.pack(fill="both", expand=True)

        # Divisão horizontal: canvas | sidebar
        left = tk.Frame(self, bg=COLORS["bg_primary"])
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(self, bg=COLORS["bg_secondary"],
                         width=WINDOW["sidebar_width"])
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # --- Canvas de visualização ---
        canvas_header = tk.Frame(left, bg=COLORS["bg_primary"])
        canvas_header.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(canvas_header, text=f"{icon} {title}",
                 font=FONTS["title_md"], bg=COLORS["bg_primary"],
                 fg=COLORS["text_primary"]).pack(side="left")

        self.canvas = tk.Canvas(
            left,
            bg=WINDOW["canvas_bg"],
            highlightthickness=1,
            highlightbackground=COLORS["border"]
        )
        self.canvas.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self._show_placeholder()

        # --- Sidebar ---
        self._build_sidebar(right, title)

    def _show_placeholder(self):
        """Mostra mensagem de placeholder no canvas vazio."""
        self.canvas.delete("all")
        w = self.canvas.winfo_width()  or 600
        h = self.canvas.winfo_height() or 400
        cx, cy = w // 2, h // 2
        self.canvas.create_text(cx, cy - 16, text="📭",
                                font=("Helvetica", 36),
                                fill=COLORS["text_muted"])
        self.canvas.create_text(cx, cy + 28,
                                text="Nenhuma imagem para exibir",
                                font=FONTS["body"],
                                fill=COLORS["text_muted"])

    def _build_sidebar(self, parent, title: str):
        """Constrói a sidebar — sobrescrito pelos subpainéis."""
        # Seção de estatísticas
        tk.Label(parent, text="Métricas", font=FONTS["small_bold"],
                 bg=COLORS["bg_secondary"], fg=COLORS["text_muted"],
                 padx=14, pady=8, anchor="w").pack(fill="x")

        self.stats = StatsPanel(parent)
        self.stats.pack(fill="x", pady=(0, 2))

        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)

        tk.Label(parent, text="Objetos detectados", font=FONTS["small_bold"],
                 bg=COLORS["bg_secondary"], fg=COLORS["text_muted"],
                 padx=14, anchor="w").pack(fill="x")

        self.detection_list = DetectionList(parent)
        self.detection_list.pack(fill="both", expand=True)

    def _display_frame(self, frame):
        """Atualiza o canvas com um frame numpy (BGR)."""
        w = self.canvas.winfo_width()  or 640
        h = self.canvas.winfo_height() or 480

        photo, x, y = fit_image_to_canvas(frame, w, h)

        # Manter referência para evitar GC
        self.canvas._photo = photo
        self.canvas.delete("all")
        self.canvas.create_image(x, y, anchor="nw", image=photo)


# ══════════════════════════════════════════════════════════════════════
# Painel: Detecção por Imagem
# ══════════════════════════════════════════════════════════════════════

class ImagePanel(DetectionLayout):
    """Painel para detecção em imagem estática."""

    def __init__(self, parent, detector, video_processor, status_bar, on_toast, **kwargs):
        self._detector = detector
        self._status_bar = status_bar
        self._on_toast = on_toast
        self._current_image_path: Optional[str] = None

        super().__init__(parent, title="Detecção por Imagem", icon="🖼", **kwargs)

    def _build_sidebar(self, parent, title):
        # Seção: Arquivo
        self._section_label(parent, "ARQUIVO")
        self._file_path_lbl = tk.Label(
            parent, text="Nenhuma imagem selecionada",
            font=FONTS["small"], bg=COLORS["bg_secondary"],
            fg=COLORS["text_muted"], wraplength=240,
            justify="left", padx=14, anchor="w"
        )
        self._file_path_lbl.pack(fill="x", pady=(0, 8))

        StyledButton(parent, text="Selecionar Imagem", icon="📂",
                     command=self._select_image, style="primary"
                    ).pack(fill="x", padx=12, pady=(0, 6))

        # Confiança
        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)
        self._section_label(parent, "CONFIGURAÇÕES")

        self._conf_slider = ConfidenceSlider(
            parent, initial=DEFAULTS["confidence"],
            on_change=None
        )
        self._conf_slider.pack(fill="x", padx=14, pady=6)

        # Botão detectar
        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)
        self._detect_btn = StyledButton(
            parent, text="Detectar", icon="🔍",
            command=self._run_detection, style="primary"
        )
        self._detect_btn.pack(fill="x", padx=12, pady=4)
        self._detect_btn.disable()

        # Stats e lista
        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)
        self._section_label(parent, "MÉTRICAS")
        self.stats = StatsPanel(parent)
        self.stats.pack(fill="x")

        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)
        self._section_label(parent, "OBJETOS DETECTADOS")
        self.detection_list = DetectionList(parent)
        self.detection_list.pack(fill="both", expand=True)

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, font=FONTS["small_bold"],
                 bg=COLORS["bg_secondary"], fg=COLORS["text_muted"],
                 padx=14, pady=4, anchor="w").pack(fill="x")

    def _select_image(self):
        path = filedialog.askopenfilename(
            title="Selecionar imagem",
            filetypes=ACCEPTED_IMAGES
        )
        if not path:
            return

        self._current_image_path = path
        import os
        name = os.path.basename(path)
        self._file_path_lbl.config(text=name, fg=COLORS["text_secondary"])

        # Mostrar prévia
        import cv2
        frame = cv2.imread(path)
        if frame is not None:
            self._display_frame(frame)

        if self._detector.is_loaded:
            self._detect_btn.enable()
        else:
            self._on_toast("Carregue um modelo YOLO antes de detectar.", "warning")

        self._status_bar.set_status(f"Imagem selecionada: {name}", "info")

    def _run_detection(self):
        if not self._current_image_path:
            return
        if not self._detector.is_loaded:
            self._on_toast("Nenhum modelo carregado.", "error")
            return

        self._status_bar.set_status("Processando...", "processing")
        self._detect_btn.disable()
        self.update()

        def _detect():
            result, msg = self._detector.detect_image(
                self._current_image_path,
                self._conf_slider.value
            )
            self.after(0, lambda: self._on_result(result, msg))

        threading.Thread(target=_detect, daemon=True).start()

    def _on_result(self, result, msg):
        self._detect_btn.enable()
        if result is None:
            self._status_bar.set_status(msg, "error")
            self._on_toast(msg, "error")
            return

        self._display_frame(result.annotated_frame)
        self.stats.update(time_ms=result.inference_time_ms, objects=result.count)
        self.detection_list.update_detections(result.detections)
        self._status_bar.set_status(
            f"✓ {result.count} objeto(s) detectado(s) em {result.inference_time_ms:.0f}ms",
            "success"
        )


# ══════════════════════════════════════════════════════════════════════
# Painel: Detecção por Vídeo
# ══════════════════════════════════════════════════════════════════════

class VideoPanel(DetectionLayout):
    """Painel para detecção em arquivo de vídeo."""

    def __init__(self, parent, detector, video_processor, status_bar, on_toast, **kwargs):
        self._detector = detector
        self._video_processor = video_processor
        self._status_bar = status_bar
        self._on_toast = on_toast
        self._is_playing = False
        self._is_paused = False
        self._conf = DEFAULTS["confidence"]

        super().__init__(parent, title="Detecção por Vídeo", icon="🎬", **kwargs)

    def _build_sidebar(self, parent, title):
        self._section_label(parent, "ARQUIVO")

        self._file_lbl = tk.Label(
            parent, text="Nenhum vídeo selecionado",
            font=FONTS["small"], bg=COLORS["bg_secondary"],
            fg=COLORS["text_muted"], wraplength=240,
            justify="left", padx=14, anchor="w"
        )
        self._file_lbl.pack(fill="x", pady=(0, 8))

        StyledButton(parent, text="Selecionar Vídeo", icon="📂",
                     command=self._select_video, style="primary"
                    ).pack(fill="x", padx=12, pady=(0, 6))

        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)
        self._section_label(parent, "CONFIGURAÇÕES")

        self._conf_slider = ConfidenceSlider(
            parent, initial=self._conf,
            on_change=self._on_conf_change
        )
        self._conf_slider.pack(fill="x", padx=14, pady=6)

        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)

        # Controles de playback
        ctrl = tk.Frame(parent, bg=COLORS["bg_secondary"])
        ctrl.pack(fill="x", padx=12, pady=4)

        self._play_btn = StyledButton(ctrl, text="Iniciar", icon="▶",
                                      command=self._toggle_play, style="primary")
        self._play_btn.pack(fill="x", pady=(0, 4))
        self._play_btn.disable()

        self._pause_btn = StyledButton(ctrl, text="Pausar", icon="⏸",
                                       command=self._toggle_pause, style="secondary")
        self._pause_btn.pack(fill="x", pady=(0, 4))
        self._pause_btn.disable()

        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)
        self._section_label(parent, "MÉTRICAS")
        self.stats = StatsPanel(parent)
        self.stats.pack(fill="x")

        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)
        self._section_label(parent, "ÚLTIMO FRAME")
        self.detection_list = DetectionList(parent)
        self.detection_list.pack(fill="both", expand=True)

        self._video_path = None

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, font=FONTS["small_bold"],
                 bg=COLORS["bg_secondary"], fg=COLORS["text_muted"],
                 padx=14, pady=4, anchor="w").pack(fill="x")

    def _select_video(self):
        path = filedialog.askopenfilename(
            title="Selecionar vídeo",
            filetypes=ACCEPTED_VIDEOS
        )
        if not path:
            return

        self._video_path = path
        import os
        self._file_lbl.config(text=os.path.basename(path), fg=COLORS["text_secondary"])

        if self._detector.is_loaded:
            self._play_btn.enable()
        else:
            self._on_toast("Carregue um modelo YOLO antes de reproduzir.", "warning")

        self._status_bar.set_status(f"Vídeo selecionado: {os.path.basename(path)}", "info")

    def _toggle_play(self):
        if self._is_playing:
            self._video_processor.stop()
            self._is_playing = False
            self._is_paused = False
            self._play_btn.set_text("Iniciar", "▶")
            self._pause_btn.disable()
            self._status_bar.set_status("Vídeo parado.", "info")
        else:
            if not self._video_path or not self._detector.is_loaded:
                return
            self._is_playing = True
            self._play_btn.set_text("Parar", "⏹")
            self._pause_btn.enable()
            self._video_processor.start(
                source=self._video_path,
                confidence=self._conf,
                on_frame_callback=self._on_frame,
                on_finish_callback=self._on_finish
            )
            self._status_bar.set_status("Reproduzindo vídeo...", "processing")

    def _toggle_pause(self):
        if self._is_paused:
            self._video_processor.resume()
            self._is_paused = False
            self._pause_btn.set_text("Pausar", "⏸")
        else:
            self._video_processor.pause()
            self._is_paused = True
            self._pause_btn.set_text("Retomar", "▶")

    def _on_frame(self, result, fps):
        self.after(0, lambda r=result, f=fps: self._update_ui(r, f))

    def _update_ui(self, result, fps):
        self._display_frame(result.annotated_frame)
        self.stats.update(fps=fps, time_ms=result.inference_time_ms, objects=result.count)
        self.detection_list.update_detections(result.detections)

    def _on_finish(self):
        self.after(0, self._on_video_finished)

    def _on_video_finished(self):
        self._is_playing = False
        self._is_paused = False
        self._play_btn.set_text("Iniciar", "▶")
        self._pause_btn.disable()
        self._status_bar.set_status("Vídeo concluído.", "success")

    def _on_conf_change(self, val):
        self._conf = val


# ══════════════════════════════════════════════════════════════════════
# Painel: Webcam em Tempo Real
# ══════════════════════════════════════════════════════════════════════

class WebcamPanel(DetectionLayout):
    """Painel para detecção em tempo real via webcam."""

    def __init__(self, parent, detector, video_processor, status_bar, on_toast, **kwargs):
        self._detector = detector
        self._video_processor = video_processor
        self._status_bar = status_bar
        self._on_toast = on_toast
        self._is_running = False
        self._is_paused = False
        self._conf = DEFAULTS["confidence"]
        self._camera_index = 0

        super().__init__(parent, title="Webcam em Tempo Real", icon="📷", **kwargs)

    def _build_sidebar(self, parent, title):
        self._section_label(parent, "CÂMERA")

        cam_row = tk.Frame(parent, bg=COLORS["bg_secondary"])
        cam_row.pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(cam_row, text="Índice:", font=FONTS["small"],
                 bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"]).pack(side="left")
        self._cam_var = tk.IntVar(value=0)
        cam_spin = tk.Spinbox(cam_row, from_=0, to=9, width=4,
                              textvariable=self._cam_var,
                              bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                              buttonbackground=COLORS["bg_hover"],
                              relief="flat", font=FONTS["mono"])
        cam_spin.pack(side="left", padx=8)

        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)
        self._section_label(parent, "CONFIGURAÇÕES")

        self._conf_slider = ConfidenceSlider(
            parent, initial=self._conf,
            on_change=self._on_conf_change
        )
        self._conf_slider.pack(fill="x", padx=14, pady=6)

        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)

        # Controles
        self._cam_btn = StyledButton(parent, text="Iniciar Câmera", icon="📷",
                                     command=self._toggle_camera, style="primary")
        self._cam_btn.pack(fill="x", padx=12, pady=(0, 4))

        self._pause_btn = StyledButton(parent, text="Pausar", icon="⏸",
                                       command=self._toggle_pause, style="secondary")
        self._pause_btn.pack(fill="x", padx=12, pady=(0, 4))
        self._pause_btn.disable()

        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)
        self._section_label(parent, "MÉTRICAS AO VIVO")
        self.stats = StatsPanel(parent)
        self.stats.pack(fill="x")

        tk.Frame(parent, bg=COLORS["border"], height=1).pack(fill="x", padx=12, pady=8)
        self._section_label(parent, "DETECÇÕES")
        self.detection_list = DetectionList(parent)
        self.detection_list.pack(fill="both", expand=True)

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, font=FONTS["small_bold"],
                 bg=COLORS["bg_secondary"], fg=COLORS["text_muted"],
                 padx=14, pady=4, anchor="w").pack(fill="x")

    def _toggle_camera(self):
        if self._is_running:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self):
        if not self._detector.is_loaded:
            self._on_toast("Carregue um modelo YOLO antes de iniciar a câmera.", "warning")
            return

        self._camera_index = self._cam_var.get()
        self._is_running = True
        self._cam_btn.set_text("Parar Câmera", "⏹")
        self._pause_btn.enable()

        self._video_processor.start(
            source=self._camera_index,
            confidence=self._conf,
            on_frame_callback=self._on_frame,
            on_finish_callback=self._on_camera_stopped
        )
        self._status_bar.set_status(f"Webcam ativa (índice {self._camera_index})", "processing")

    def _stop_camera(self):
        self._video_processor.stop()
        self._is_running = False
        self._is_paused = False
        self._cam_btn.set_text("Iniciar Câmera", "📷")
        self._pause_btn.disable()
        self._show_placeholder()
        self.stats.reset()
        self._status_bar.set_status("Câmera parada.", "info")

    def _toggle_pause(self):
        if self._is_paused:
            self._video_processor.resume()
            self._is_paused = False
            self._pause_btn.set_text("Pausar", "⏸")
        else:
            self._video_processor.pause()
            self._is_paused = True
            self._pause_btn.set_text("Retomar", "▶")

    def _on_frame(self, result, fps):
        self.after(0, lambda r=result, f=fps: self._update_ui(r, f))

    def _update_ui(self, result, fps):
        self._display_frame(result.annotated_frame)
        self.stats.update(fps=fps, time_ms=result.inference_time_ms, objects=result.count)
        self.detection_list.update_detections(result.detections)

    def _on_camera_stopped(self):
        self.after(0, lambda: self._status_bar.set_status("Câmera desconectada.", "warning"))

    def _on_conf_change(self, val):
        self._conf = val
