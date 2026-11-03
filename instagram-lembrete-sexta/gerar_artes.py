from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("instagram-reminder-assets")
OUT.mkdir(exist_ok=True)
W, H = 1080, 1350
YELLOW = (255, 196, 0)
WHITE = (255, 255, 255)
MUTED = (205, 208, 214)
BG = (14, 16, 20)
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Oito artes diferentes; a legenda do Instagram permanece igual em todas.
designs = [
    ("SEXTA-FEIRA", "DE OFERTAS!", "OFERTAS TODOS OS DIAS", "Economize com a gente", "frame"),
    ("SEU RADAR", "DE ECONOMIA", "DESCONTOS TODOS OS DIAS", "Confira as oportunidades", "split"),
    ("ACHADINHOS", "DA SEMANA", "PREÇO BOM É AQUI", "Não deixe passar", "circle"),
    ("ATENÇÃO!", "PROMOÇÕES", "OFERTAS NO TELEGRAM", "Receba direto no celular", "stripe"),
    ("LIGUE O", "RADAR!", "ECONOMIZE NAS COMPRAS", "Novas ofertas todos os dias", "grid"),
    ("OFERTA BOA", "NÃO ESPERA", "FIQUE DE OLHO", "Acompanhe nosso canal", "corner"),
    ("MAIS OFERTAS", "MENOS GASTOS", "SEU BOLSO AGRADECE", "Entre para o Radar", "stack"),
    ("RADAR DE", "OFERTAS BR", "PROMOÇÕES TODOS OS DIAS", "Telegram • link na bio", "badge"),
]

def font(size, bold=True):
    return ImageFont.truetype(BOLD if bold else REG, size)

def centered(draw, y, text, size, color, bold=True):
    draw.text((W//2, y), text, font=font(size,bold), fill=color, anchor="mm")

for i, (top, main, line, sub, style) in enumerate(designs, 1):
    im = Image.new("RGB", (W,H), BG)
    d = ImageDraw.Draw(im)
    # detalhes geométricos variam por arte
    if style == "frame":
        d.rounded_rectangle((48,48,1032,1302), radius=54, outline=YELLOW, width=10)
        d.rounded_rectangle((110,150,970,400), radius=42, fill=YELLOW)
    elif style == "split":
        d.rectangle((0,0, W,430), fill=YELLOW)
        d.polygon([(0,980),(W,760),(W,H),(0,H)], fill=(28,32,40))
        d.rectangle((70,70,1010,1280), outline=YELLOW, width=5)
    elif style == "circle":
        d.ellipse((130,100,950,920), outline=YELLOW, width=18)
        d.ellipse((205,175,875,845), outline=(70,75,84), width=5)
    elif style == "stripe":
        d.polygon([(0,160),(W,0),(W,330),(0,490)], fill=YELLOW)
        d.polygon([(0,960),(W,800),(W,1050),(0,1210)], fill=(35,39,48))
    elif style == "grid":
        for x in range(80,1000,180):
            for y in range(100,1250,180):
                d.rounded_rectangle((x,y,x+110,y+110), radius=18, outline=(55,61,70), width=3)
        d.rounded_rectangle((100,450,980,870), radius=40, fill=YELLOW)
    elif style == "corner":
        d.polygon([(0,0),(420,0),(0,420)], fill=YELLOW)
        d.polygon([(W,H),(650,H),(W,1000)], fill=YELLOW)
    elif style == "stack":
        d.rounded_rectangle((90,120,990,390), radius=35, fill=(35,39,48), outline=YELLOW, width=5)
        d.rounded_rectangle((90,440,990,850), radius=35, fill=YELLOW)
    else:
        d.rounded_rectangle((90,90,990,1260), radius=90, outline=YELLOW, width=8)
        d.ellipse((300,120,780,600), outline=YELLOW, width=10)

    dark = (15,17,20)
    top_color = dark if style in ("split","stack") else YELLOW
    centered(d, 300 if style not in ("split","stripe") else 250, top, 66, top_color)
    main_color = dark if style in ("grid","stack") else WHITE
    centered(d, 555, main, 94, main_color)
    d.rounded_rectangle((105,760,975,990), radius=35, outline=YELLOW, width=5)
    centered(d, 835, line, 42, WHITE)
    centered(d, 920, sub, 34, MUTED, False)
    centered(d, 1110, "ENTRE NO NOSSO TELEGRAM", 38, YELLOW)
    centered(d, 1180, "LINK NA BIO  •  @RADARACHADINHOSBRASIL", 25, WHITE)
    centered(d, 1260, "RADAR DE OFERTAS BR", 28, YELLOW)
    im.save(OUT / f"lembrete-sexta-{i:02d}.jpg", "JPEG", quality=94, optimize=True)
print("8 artes semanais geradas.")
