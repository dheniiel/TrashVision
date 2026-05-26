"""
ui/widgets.py
=============
Componentes reutilizáveis da interface.
Cada widget é independente e pode ser usado em qualquer painel.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
from ui.theme import COLORS, FONTS


# ------------------------------------------------------------------
# Botão estilizado principal
# ------------------------------------------------------------------

class StyledButton(tk.Frame):
    """
    Botão customizado com hover effect, ícone e cor configurável.
    Suporta estados: normal, hover, disabled.
    """

    def __init__(self, parent, text: str, command: Callable = None,
                 icon: str = "", style: str = "primary",
                 width: int = 180, height: int = 42, **kwargs):
        super().__init__(parent, bg=COLORS["bg_card"], **kwargs)

        # Mapear estilos
        styles = {
            "primary":   (COLORS["accent"],    "#000000"),
            "secondary": (COLORS["bg_hover"],  COLORS["text_primary"]),
            "danger":    (COLORS["danger"],     "#ffffff"),
            "blue":      (COLORS["blue"],       "#ffffff"),
            "outline":   (COLORS["bg_card"],    COLORS["accent"]),
        }
        self._bg_normal, self._fg = styles.get(style, styles["primary"])
        self._bg_hover = self._lighten(self._bg_normal)
        self._command = command
        self._disabled = False

        self._btn = tk.Label(
            self,
            text=f"{icon}  {text}" if icon else text,
            font=FONTS["body_bold"],
            bg=self._bg_normal,
            fg=self._fg,
            cursor="hand2",
            width=width // 8,
            padx=14, pady=10,
            relief="flat"
        )
        self._btn.pack(fill="both", expand=True)

        # Efeitos de hover
        self._btn.bind("<Enter>", self._on_enter)
        self._btn.bind("<Leave>", self._on_leave)
        self._btn.bind("<Button-1>", self._on_click)
        self._btn.bind("<ButtonRelease-1>", self._on_release)

    def _lighten(self, hex_color: str) -> str:
        """Clareia levemente uma cor hex."""
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            r = min(255, r + 30)
            g = min(255, g + 30)
            b = min(255, b + 30)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    def _on_enter(self, e):
        if not self._disabled:
            self._btn.config(bg=self._bg_hover)

    def _on_leave(self, e):
        if not self._disabled:
            self._btn.config(bg=self._bg_normal)

    def _on_click(self, e):
        if not self._disabled:
            self._btn.config(bg=COLORS["accent_dim"] if "accent" in self._bg_normal else self._bg_normal)

    def _on_release(self, e):
        if not self._disabled:
            self._btn.config(bg=self._bg_hover)
            if self._command:
                self._command()

    def set_text(self, text: str, icon: str = ""):
        self._btn.config(text=f"{icon}  {text}" if icon else text)

    def disable(self):
        self._disabled = True
        self._btn.config(bg=COLORS["text_muted"], fg=COLORS["bg_card"], cursor="")

    def enable(self):
        self._disabled = False
        self._btn.config(bg=self._bg_normal, fg=self._fg, cursor="hand2")


# ------------------------------------------------------------------
# Card de modo (tela inicial)
# ------------------------------------------------------------------

class ModeCard(tk.Frame):
    """
    Card grande para seleção de modo na tela inicial.
    Exibe ícone, título e descrição com efeito hover.
    """

    def __init__(self, parent, icon: str, title: str, desc: str,
                 command: Callable, **kwargs):
        super().__init__(
            parent,
            bg=COLORS["bg_card"],
            relief="flat",
            cursor="hand2",
            **kwargs
        )

        self._command = command
        self._is_hovered = False

        # Borda decorativa esquerda (accent)
        self._accent_bar = tk.Frame(self, bg=COLORS["accent"], width=3)
        self._accent_bar.pack(side="left", fill="y")

        # Conteúdo
        content = tk.Frame(self, bg=COLORS["bg_card"])
        content.pack(side="left", fill="both", expand=True, padx=20, pady=22)

        # Ícone
        tk.Label(content, text=icon, font=("Helvetica", 32),
                 bg=COLORS["bg_card"], fg=COLORS["accent"]).pack(anchor="w")

        # Título
        tk.Label(content, text=title, font=FONTS["title_md"],
                 bg=COLORS["bg_card"], fg=COLORS["text_primary"]).pack(anchor="w", pady=(6, 2))

        # Descrição
        tk.Label(content, text=desc, font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 wraplength=200, justify="left").pack(anchor="w")

        # Seta →
        tk.Label(self, text="→", font=("Helvetica", 18, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 padx=16).pack(side="right")

        # Bind recursivo em todos os filhos
        self._bind_all_children(self)

    def _bind_all_children(self, widget):
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<Button-1>", self._on_click)
        for child in widget.winfo_children():
            self._bind_all_children(child)

    def _set_bg(self, color: str):
        """Muda o background de todos os widgets internos."""
        self._recursive_bg(self, color)

    def _recursive_bg(self, widget, color: str):
        try:
            widget.config(bg=color)
        except Exception:
            pass
        for child in widget.winfo_children():
            if child != self._accent_bar:
                self._recursive_bg(child, color)

    def _on_enter(self, e):
        self._set_bg(COLORS["bg_hover"])

    def _on_leave(self, e):
        self._set_bg(COLORS["bg_card"])

    def _on_click(self, e):
        if self._command:
            self._command()


# ------------------------------------------------------------------
# Slider de confiança
# ------------------------------------------------------------------

class ConfidenceSlider(tk.Frame):
    """
    Slider interativo para ajustar o limiar de confiança (0.05 – 0.95).
    """

    def __init__(self, parent, initial: float = 0.25,
                 on_change: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg=COLORS["bg_card"], **kwargs)
        self._on_change = on_change
        self._var = tk.DoubleVar(value=initial)

        # Label topo
        header = tk.Frame(self, bg=COLORS["bg_card"])
        header.pack(fill="x", padx=2, pady=(0, 4))
        tk.Label(header, text="Confiança", font=FONTS["small_bold"],
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(side="left")
        self._value_label = tk.Label(header, text=f"{initial:.0%}",
                                     font=FONTS["mono_lg"],
                                     bg=COLORS["bg_card"], fg=COLORS["accent"])
        self._value_label.pack(side="right")

        # Slider
        self._slider = ttk.Scale(
            self, from_=0.05, to=0.95, orient="horizontal",
            variable=self._var, command=self._on_slider
        )
        self._slider.pack(fill="x")

        # Estilizar ttk Scale
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Horizontal.TScale",
                        background=COLORS["bg_card"],
                        troughcolor=COLORS["bg_primary"],
                        sliderthickness=18)

    def _on_slider(self, val):
        v = float(val)
        # Snap para incrementos de 0.05
        snapped = round(round(v / 0.05) * 0.05, 2)
        self._var.set(snapped)
        self._value_label.config(text=f"{snapped:.0%}")
        if self._on_change:
            self._on_change(snapped)

    @property
    def value(self) -> float:
        return self._var.get()

    def set_value(self, v: float):
        self._var.set(v)
        self._value_label.config(text=f"{v:.0%}")


# ------------------------------------------------------------------
# Painel de estatísticas
# ------------------------------------------------------------------

class StatsPanel(tk.Frame):
    """
    Exibe métricas de detecção: FPS, tempo de inferência, total detectado.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg_secondary"], **kwargs)

        self._metrics = {}
        fields = [
            ("fps",      "FPS",        "—"),
            ("time_ms",  "Inferência", "—"),
            ("objects",  "Detectados", "0"),
        ]

        for key, label, default in fields:
            row = tk.Frame(self, bg=COLORS["bg_secondary"])
            row.pack(fill="x", padx=14, pady=5)

            tk.Label(row, text=label, font=FONTS["small"],
                     bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
                     width=12, anchor="w").pack(side="left")

            val_lbl = tk.Label(row, text=default, font=FONTS["mono"],
                               bg=COLORS["bg_secondary"], fg=COLORS["accent"],
                               anchor="e")
            val_lbl.pack(side="right")
            self._metrics[key] = val_lbl

    def update(self, fps: Optional[float] = None,
               time_ms: Optional[float] = None,
               objects: Optional[int] = None):
        if fps is not None:
            self._metrics["fps"].config(text=f"{fps:.1f}")
        if time_ms is not None:
            self._metrics["time_ms"].config(text=f"{time_ms:.0f} ms")
        if objects is not None:
            color = COLORS["warning"] if objects > 0 else COLORS["text_secondary"]
            self._metrics["objects"].config(text=str(objects), fg=color)

    def reset(self):
        for key, lbl in self._metrics.items():
            lbl.config(text="—" if key != "objects" else "0",
                       fg=COLORS["accent"])


# ------------------------------------------------------------------
# Lista de detecções
# ------------------------------------------------------------------

class DetectionList(tk.Frame):
    """
    Lista scrollável das detecções com label e percentual de confiança.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg_secondary"], **kwargs)

        # Cabeçalho
        header = tk.Frame(self, bg=COLORS["bg_secondary"])
        header.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(header, text="Detecções", font=FONTS["small_bold"],
                 bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"]).pack(side="left")
        self._count_lbl = tk.Label(header, text="0", font=FONTS["small_bold"],
                                   bg=COLORS["bg_secondary"], fg=COLORS["accent"])
        self._count_lbl.pack(side="right")

        # Frame scrollável
        container = tk.Frame(self, bg=COLORS["bg_secondary"])
        container.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(container, bg=COLORS["bg_secondary"],
                                 highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical",
                                  command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, bg=COLORS["bg_secondary"])
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw"
        )
        self._inner.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_frame_configure(self, e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self._canvas.itemconfig(self._canvas_window, width=e.width)

    def update_detections(self, detections: list):
        """Atualiza a lista com novas detecções."""
        # Limpar
        for widget in self._inner.winfo_children():
            widget.destroy()

        self._count_lbl.config(text=str(len(detections)))

        for det in detections:
            label = det["label"]
            conf = det["confidence"]

            row = tk.Frame(self._inner, bg=COLORS["bg_card"],
                           relief="flat")
            row.pack(fill="x", padx=8, pady=2)

            # Barra de confiança colorida
            bar_color = self._conf_color(conf)
            bar = tk.Frame(row, bg=bar_color, width=3)
            bar.pack(side="left", fill="y")

            info = tk.Frame(row, bg=COLORS["bg_card"])
            info.pack(side="left", fill="both", expand=True, padx=10, pady=6)

            tk.Label(info, text=label.capitalize(), font=FONTS["small_bold"],
                     bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                     anchor="w").pack(anchor="w")

            # Mini barra de progresso de confiança
            prog_frame = tk.Frame(info, bg=COLORS["bg_primary"], height=4)
            prog_frame.pack(fill="x", pady=(2, 0))
            prog_frame.pack_propagate(False)

            fill_width = max(4, int(conf * 100))
            tk.Frame(prog_frame, bg=bar_color, height=4,
                     width=fill_width).place(x=0, y=0, relheight=1)

            tk.Label(row, text=f"{conf:.0%}", font=FONTS["mono_sm"],
                     bg=COLORS["bg_card"], fg=bar_color,
                     padx=8).pack(side="right")

    def _conf_color(self, conf: float) -> str:
        """Retorna cor baseada na confiança."""
        if conf >= 0.75:
            return COLORS["accent"]
        elif conf >= 0.50:
            return COLORS["blue"]
        elif conf >= 0.25:
            return COLORS["warning"]
        else:
            return COLORS["danger"]

    def clear(self):
        for widget in self._inner.winfo_children():
            widget.destroy()
        self._count_lbl.config(text="0")


# ------------------------------------------------------------------
# Barra de status inferior
# ------------------------------------------------------------------

class StatusBar(tk.Frame):
    """Barra de status na parte inferior da janela."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg_secondary"],
                         height=28, **kwargs)
        self.pack_propagate(False)

        self._dot = tk.Label(self, text="●", font=FONTS["small"],
                             bg=COLORS["bg_secondary"], fg=COLORS["text_muted"])
        self._dot.pack(side="left", padx=(10, 4))

        self._msg = tk.Label(self, text="Pronto", font=FONTS["small"],
                             bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
                             anchor="w")
        self._msg.pack(side="left", fill="x", expand=True)

        self._model_lbl = tk.Label(self, text="Sem modelo", font=FONTS["small"],
                                   bg=COLORS["bg_secondary"], fg=COLORS["text_muted"],
                                   padx=12)
        self._model_lbl.pack(side="right")

    def set_status(self, msg: str, level: str = "info"):
        """level: info | success | warning | error | processing"""
        colors = {
            "info":       (COLORS["text_secondary"], COLORS["blue"]),
            "success":    (COLORS["accent"],         COLORS["accent"]),
            "warning":    (COLORS["warning"],        COLORS["warning"]),
            "error":      (COLORS["danger"],         COLORS["danger"]),
            "processing": (COLORS["text_secondary"], COLORS["warning"]),
        }
        fg, dot_color = colors.get(level, colors["info"])
        self._msg.config(text=msg, fg=fg)
        self._dot.config(fg=dot_color)

    def set_model(self, name: str):
        self._model_lbl.config(text=f"🤖 {name}")


# ------------------------------------------------------------------
# Toast notification
# ------------------------------------------------------------------

class Toast:
    """Notificação temporária que aparece no canto da tela."""

    @staticmethod
    def show(parent, message: str, level: str = "info", duration_ms: int = 3000):
        colors = {
            "info":    COLORS["blue"],
            "success": COLORS["accent"],
            "error":   COLORS["danger"],
            "warning": COLORS["warning"],
        }
        color = colors.get(level, COLORS["blue"])

        toast = tk.Toplevel(parent)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=color)

        # Posicionar no canto inferior direito
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        tw, th = 320, 48
        toast.geometry(f"{tw}x{th}+{px + pw - tw - 20}+{py + ph - th - 40}")

        tk.Label(toast, text=message, font=FONTS["small_bold"],
                 bg=color, fg="#000000" if level in ("success", "warning") else "#ffffff",
                 padx=16, pady=12, wraplength=280, justify="left").pack(fill="both")

        toast.after(duration_ms, toast.destroy)
