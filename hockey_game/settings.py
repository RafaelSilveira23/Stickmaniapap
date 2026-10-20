"""settings.py - todas as constantes do jogo num só sítio."""

# ---------- Janela ----------
WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "StickMania PAP — Hóquei em Patins 2D"

# ---------- Cores (R, G, B) ----------
COR_FUNDO       = (12, 18, 36)
COR_LINHA       = (30, 95, 210)
COR_MURO        = (235, 238, 245)
COR_MURO_SOMBRA = (130, 140, 168)
COR_BALIZA      = (210, 45, 45)
COR_REDE        = (215, 220, 230)
COR_TEXTO       = (240, 245, 255)

# ---------- Layout Vertical ----------
HUD_H           = 62   # Marcador no topo
BANCADA_CIMA_H  = 26   # Público / tabela publicitária superior
RINK_Y          = HUD_H + BANCADA_CIMA_H  # = 88

# ---------- Campo ----------
RINK_W          = 1140
RINK_X          = (WIDTH - RINK_W) // 2   # centrado = 70
RINK_H          = 440                     # vai de Y=88 até Y=528

CANTO           = 50   # raio dos cantos arredondados
MURO            = 10   # espessura do muro
LINHA           = 3    # espessura das linhas

RAIO_CENTRO     = 65   # círculo central
AREA_W          = 150  # largura da grande área
AREA_H          = 250  # altura da grande área
BALIZA_OFFSET   = 115  # distância da linha de golo à tabela (permite patinar atrás!)

# ---------- HUD Inferior (Mini-mapa, Cartão e Controlos) ----------
HUD_BAIXO_Y     = 536
HUD_BAIXO_H     = HEIGHT - HUD_BAIXO_Y    # = 184
