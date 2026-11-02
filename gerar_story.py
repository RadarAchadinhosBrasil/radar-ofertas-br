#!/usr/bin/env python3
"""Gera artes verticais 1080x1920 para Stories; não publica nem altera o catálogo."""
import csv, os, re, sys
from pathlib import Path
from io import BytesIO
from urllib.parse import urlparse
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "story-preview"
W, H = 1080, 1920
BG, WHITE, MUTED = (12,18,32), (248,250,252), (174,187,205)
ACCENT, GREEN = (255,190,45), (33,205,126)

def font(size, bold=False):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(p, size) if Path(p).exists() else ImageFont.load_default()

def money(value):
    try:
        return ("R$ {:,.2f}".format(float(str(value).replace(",", "."))).replace(",", "X").replace(".", ",").replace("X", "."))
    except (ValueError, TypeError):
        return str(value or "").strip()

def wrap(draw, text, fnt, max_width):
    lines, line = [], ""
    for word in str(text).split():
        test = (line + " " + word).strip()
        if draw.textbbox((0,0), test, font=fnt)[2] <= max_width: line = test
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

def load_products():
    with (ROOT / "produtos.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(line for line in f if line.strip()))
    rows = [r for r in rows if (r.get("produto") or "").strip()]
    if not rows: raise RuntimeError("produtos.csv sem produtos válidos")
    return rows

def get_image(url):
    p = urlparse(url or "")
    if p.scheme != "https" or not p.netloc: raise ValueError("imagem_url não é HTTPS")
    r = requests.get(url, timeout=30, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    if not r.headers.get("Content-Type","").lower().startswith("image/"): raise ValueError("URL não retornou imagem")
    return ImageOps.fit(Image.open(BytesIO(r.content)).convert("RGB"), (900,760), method=Image.Resampling.LANCZOS)

def make_story(p, index):
    im = Image.new("RGB",(W,H),BG); d = ImageDraw.Draw(im)
    d.rounded_rectangle((55,55,1025,235),radius=38,fill=(24,34,54))
    d.text((95,82),"RADAR DE OFERTAS BR",font=font(54,True),fill=WHITE)
    d.text((98,158),"ACHADOS QUE VALEM A PENA",font=font(27,True),fill=ACCENT)
    d.text((75,300),"OFERTA EM DESTAQUE",font=font(34,True),fill=ACCENT)
    photo = get_image(p.get("imagem_url",""))
    # Foto menor para reservar espaço legível para descrição e chamadas de ação.
    photo = ImageOps.fit(photo, (800, 610), method=Image.Resampling.LANCZOS)
    im.paste(photo,(140,340)); d.rounded_rectangle((140,340,940,950),radius=28,outline=(65,82,110),width=5)
    y=1000
    title=(p.get("produto") or "Oferta").strip()
    for line in wrap(d,title,font(43,True),930)[:2]:
        d.text((75,y),line,font=font(43,True),fill=WHITE); y+=57
    description=(p.get("descricao") or p.get("description") or "Confira os detalhes e as características deste produto no anúncio.").strip()
    y=max(y+12,1135)
    for line in wrap(d,description,font(27),920)[:2]:
        d.text((80,y),line,font=font(27),fill=MUTED); y+=39
    old,current=money(p.get("preco_anterior_brl","")),money(p.get("preco_atual_brl",""))
    if old:
        label="DE "+old; d.text((80,1260),label,font=font(34),fill=MUTED)
        box=d.textbbox((80,1260),label,font=font(34)); d.line((box[0],(box[1]+box[3])//2,box[2],(box[1]+box[3])//2),fill=(255,100,100),width=5)
    d.rounded_rectangle((65,1320,1015,1510),radius=34,fill=GREEN)
    d.text((105,1340),"POR APENAS",font=font(29,True),fill=(5,45,31))
    d.text((105,1378),current or "Confira no anúncio",font=font(72,True),fill=(5,45,31))
    d.rounded_rectangle((65,1530,1015,1715),radius=30,fill=ACCENT)
    d.text((540,1575),"QUER RECEBER MAIS OFERTAS?",font=font(34,True),fill=(34,29,18),anchor="mm")
    d.text((540,1640),'ENVIE "OFERTAS" NO DIRECT',font=font(39,True),fill=(34,29,18),anchor="mm")
    d.text((540,1690),"e receba o link do nosso Telegram",font=font(25,True),fill=(34,29,18),anchor="mm")
    d.text((540,1840),"Preço e disponibilidade podem mudar. Confira no anúncio.",font=font(21),fill=MUTED,anchor="mm")
    OUT.mkdir(exist_ok=True)
    safe=re.sub(r"[^a-zA-Z0-9_-]+","-",(p.get("produto") or "")).strip("-")[:45] or f"oferta-{index}"
    path=OUT/f"story-{index:02d}-{safe}.jpg"; im.save(path,quality=92,optimize=True); print(f"ARTE GERADA: {path}")

def main():
    min_count = int(os.getenv("STORY_COUNT_MIN", "3"))
    max_count = int(os.getenv("STORY_COUNT_MAX", "5"))
    if min_count < 1 or max_count < min_count or max_count > 10:
        raise SystemExit("Faixa STORY_COUNT_MIN/MAX inválida")
    rows = load_products()
    # Evita repetir o mesmo produto dentro da rodada.
    unique, seen = [], set()
    for row in rows:
        key = (row.get("produto") or "").strip().casefold()
        if key and key not in seen:
            seen.add(key)
            unique.append(row)
    rows = unique
    if len(rows) < max_count:
        raise SystemExit(f"Catálogo tem apenas {len(rows)} produtos diferentes; são necessários {max_count}.")
    if os.getenv("STORY_ROTATE", "").strip() == "1":
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        scheduled = os.getenv("STORY_SLOT_UTC", "").strip()
        slots = {
            "30 12 * * *": 0,
            "30 15 * * *": 1,
            "30 18 * * *": 2,
            "30 21 * * *": 3,
        }
        if scheduled:
            if scheduled not in slots:
                raise SystemExit(f"Horário cron de Story não reconhecido: {scheduled}")
            slot_index = slots[scheduled]
        else:
            # Prévia/manual sem cron: usa o horário atual apenas como fallback.
            slot_index = min(3, max(0, (now.hour - 12) // 3))
        # Cada horário recebe um bloco fixo de até 5 itens; usa o cron real
        # para não repetir o bloco quando o GitHub atrasar o início do job.
        offset = ((now.timetuple().tm_yday - 1) * 20 + slot_index * 5) % len(rows)
        rows = rows[offset:] + rows[:offset]
        print(f"ROTAÇÃO DO HORÁRIO: slot={slot_index + 1}/4; bloco iniciado no produto {offset + 1}/{len(rows)}")
    import secrets
    count = secrets.SystemRandom().randint(min_count, max_count)
    rows = rows[:count]
    if OUT.exists():
        for old in OUT.glob("*.jpg"):
            old.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"QUANTIDADE DE STORIES NESTA RODADA: {count}")
    for i, p in enumerate(rows, 1):
        make_story(p, i)
    generated = sorted(OUT.glob("*.jpg"))
    print(f"RESULTADO: {len(generated)}/{count} artes geradas. Nenhuma publicação foi feita.")
    if len(generated) != count:
        sys.exit(2)
    (OUT / "story_count.txt").write_text(str(count), encoding="utf-8")

if __name__=="__main__": main()
