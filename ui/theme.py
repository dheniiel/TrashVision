"""
ui/theme.py
===========
Paleta de cores, fontes e constantes de design do aplicativo.
Centralizado aqui para facilitar customização futura.
"""

# ------------------------------------------------------------------
# Paleta principal — Dark industrial / AI aesthetic
# ------------------------------------------------------------------
COLORS = {
    # Backgrounds
    "bg_primary":    "#0D0F14",   # fundo principal quase preto
    "bg_secondary":  "#13161E",   # painéis secundários
    "bg_card":       "#1A1E2A",   # cards e painéis
    "bg_hover":      "#222638",   # hover states

    # Accents
    "accent":        "#00E5A0",   # verde-teal vibrante (ação primária)
    "accent_dim":    "#00A370",   # versão mais escura do accent
    "accent_glow":   "#00E5A020", # versão transparente para glow

    # Secundário
    "blue":          "#4C9EFF",   # informações / links
    "blue_dim":      "#2D6CC0",
    "warning":       "#FFB84C",   # avisos
    "danger":        "#FF5C6A",   # erros

    # Texto
    "text_primary":  "#E8ECF5",   # texto principal
    "text_secondary":"#8891A8",   # texto secundário / labels
    "text_muted":    "#4A5168",   # texto desativado

    # Bordas
    "border":        "#252A3A",   # bordas sutis
    "border_active": "#00E5A060", # bordas ativas
}

# ------------------------------------------------------------------
# Configuração de fontes
# Usa fontes nativas para compatibilidade cross-platform
# ------------------------------------------------------------------
FONTS = {
    # Títulos
    "title_xl":   ("Helvetica", 22, "bold"),
    "title_lg":   ("Helvetica", 16, "bold"),
    "title_md":   ("Helvetica", 13, "bold"),

    # Corpo
    "body":       ("Helvetica", 11),
    "body_bold":  ("Helvetica", 11, "bold"),
    "small":      ("Helvetica", 9),
    "small_bold": ("Helvetica", 9, "bold"),

    # Monospace (para stats/métricas)
    "mono":       ("Courier", 11),
    "mono_lg":    ("Courier", 14, "bold"),
    "mono_sm":    ("Courier", 9),
}

# ------------------------------------------------------------------
# Dimensões da janela
# ------------------------------------------------------------------
WINDOW = {
    "width":         1200,
    "height":        760,
    "min_width":     900,
    "min_height":    600,
    "canvas_bg":     "#090B10",   # fundo da área de visualização
    "sidebar_width": 300,
}

# ------------------------------------------------------------------
# Configurações padrão de detecção
# ------------------------------------------------------------------
DEFAULTS = {
    "confidence":    0.25,
    "conf_min":      0.05,
    "conf_max":      0.95,
    "conf_step":     0.05,
}

# ------------------------------------------------------------------
# Modos de operação
# ------------------------------------------------------------------
MODES = {
    "image":   {"id": "image",  "label": "Imagem",      "icon": "🖼",  "desc": "Analise fotos e arquivos de imagem"},
    "video":   {"id": "video",  "label": "Vídeo",       "icon": "🎬",  "desc": "Processe arquivos de vídeo"},
    "webcam":  {"id": "webcam", "label": "Webcam",      "icon": "📷",  "desc": "Detecção em tempo real"},
}

# Extensões de arquivo aceitas
ACCEPTED_IMAGES = [("Imagens", "*.jpg *.jpeg *.png *.bmp *.webp *.tiff")]
ACCEPTED_VIDEOS = [("Vídeos", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv")]
ACCEPTED_MODELS = [("Modelos YOLO", "*.pt")]
