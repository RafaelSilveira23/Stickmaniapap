"""settings.py - todas as constantes do jogo num só sítio."""

# ---------- Janela ----------
WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "Hóquei em Patins 2D"

# ---------- Cores (R, G, B) ----------
COR_FUNDO       = (14, 24, 44)
COR_LINHA       = (30, 90, 200)
COR_MURO        = (235, 238, 245)
COR_MURO_SOMBRA = (140, 150, 175)
COR_BALIZA      = (200, 40, 40)
COR_REDE        = (205, 208, 215)
COR_TEXTO       = (240, 244, 255)

# ---------- HUD ----------
HUD_H = 90          # altura da barra do marcador no topo

# ---------- Bancadas de cima ----------
# Faixa de público entre o HUD e o campo (como no mockup)
BANCADA_CIMA_H = 60  # altura visível das bancadas acima do campo

# ---------- Campo ----------
# Posição Y do topo do campo: logo a seguir ao HUD + bancada
RINK_Y = HUD_H + BANCADA_CIMA_H        # = 150

# Largura: ocupa quase toda a janela (com pequena margem para as balizas)
RINK_W = 1100
RINK_X = (WIDTH - RINK_W) // 2         # centrado, = 90

# Altura: o campo vai de RINK_Y até ~80px do fundo (espaço para bancadas inferiores)
BANCADA_BAIXO_H = 60
RINK_H = HEIGHT - RINK_Y - BANCADA_BAIXO_H   # = 720 - 150 - 60 = 510

CANTO = 55          # raio dos cantos arredondados
MURO  = 12          # espessura do muro
LINHA = 4           # espessura das linhas pintadas

RAIO_CENTRO = 75                  # círculo do meio
AREA_W, AREA_H = 160, 310         # área de cada baliza
BALIZA_W, BALIZA_H = 20, 80       # geometria da baliza (para deteção de golos)
