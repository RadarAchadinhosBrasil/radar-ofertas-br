import csv
import hashlib
import json
import os
import re
from pathlib import Path
from io import BytesIO
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site" / "instagram-assets"
SLOTS = ["0 12 * * *", "0 15 * * *", "0 18 * * *", "0 21 * * *"]
MIN_SIDE = 700


def image_candidates(url):
    # Mercado Livre costuma disponibilizar a imagem original com sufixo -O.
    # Testamos variantes maiores sem perder a URL original como fallback.
    candidates = []
    match = re.match(r"^(.*)-([A-Z])(.(?:webp|jpe?g|png))$", url, re.I)
    if match:
        prefix, _size, ext = match.groups()
        for size in ("O", "F", "V", "X", "W", "L", "P"):
            candidate = f"{prefix}-{size}{ext}"
            if candidate not in candidates:
                candidates.append(candidate)
    candidates.append(url)
    return candidates


def fetch_best_image(session, url):
    best = None
    best_area = -1
    failures = []

    for candidate in image_candidates(url):
        try:
            response = session.get(candidate, timeout=40)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            image.load()
            width, height = image.size
            area = width * height
            print(f"Imagem candidata: {width}x{height} | {candidate}")

            if area > best_area:
                best = (image.copy(), candidate, width, height)
                best_area = area

            # Compara todas as variantes: em alguns anúncios -F/-V pode ser maior que -O.
        except Exception as error:
            failures.append(f"{candidate}: {error}")

    if best is None:
        raise RuntimeError("Não foi possível baixar uma imagem válida. " + " | ".join(failures))

    image, chosen_url, width, height = best
    if min(width, height) < MIN_SIDE:
        print(f"AVISO: imagem de origem pequena ({width}x{height}); não será artificialmente ampliada.")
    print(f"Melhor imagem selecionada: {width}x{height} | {chosen_url}")
    return image


def main():
    slot = os.environ["SLOT_UTC"]
    if slot not in SLOTS:
        raise SystemExit("Horário inválido: " + slot)

    with (ROOT / "produtos.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = (line for line in f if line.strip())
        products = [
            {(k or "").strip(): (v or "").strip()
             for k, v in row.items() if k is not None}
            for row in csv.DictReader(rows)
        ]

    products = [p for p in products if p.get("produto")]
    if not products:
        raise SystemExit("Nenhum produto válido no catálogo.")

    start = SLOTS.index(slot)
    base = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).date().toordinal() % len(products)
    product = products[(base + start) % len(products)]

    original = product.get("imagem_url", "").strip()
    if not original.startswith("https://"):
        raise SystemExit("Produto sem imagem HTTPS válida.")

    OUT.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(original.encode()).hexdigest()[:24] + ".jpg"
    destination = OUT / name

    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0 RadarOfertasBR/1.0"})
        image = fetch_best_image(session, original)

    # Corrige orientação EXIF e prepara uma arte vertical 4:5 para o Feed.
    # A foto nunca é ampliada: preserva a resolução real da fonte e evita pixelização.
    image = ImageOps.exif_transpose(image).convert("RGB")
    source_size = image.size

    canvas_w, canvas_h = 1080, 1350
    background = Image.new("RGB", (canvas_w, canvas_h), (245, 246, 248))

    # Cartão branco com margem ampla para dar acabamento sem cortar o produto.
    card = Image.new("RGB", (980, 1190), (255, 255, 255))
    card_x = (canvas_w - card.width) // 2
    card_y = (canvas_h - card.height) // 2

    # Sombra suave atrás do cartão.
    shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    from PIL import ImageDraw, ImageFilter
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (card_x + 4, card_y + 12, card_x + card.width + 4, card_y + card.height + 12),
        radius=30, fill=(20, 25, 35, 28)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    background = Image.alpha_composite(background.convert("RGBA"), shadow).convert("RGB")

    # Redimensiona apenas para caber; jamais aumenta acima dos pixels originais.
    image.thumbnail((900, 1080), Image.Resampling.LANCZOS)
    image_x = (card.width - image.width) // 2
    image_y = (card.height - image.height) // 2
    card.paste(image, (image_x, image_y))

    # Cantos arredondados no cartão, com a foto inteira preservada.
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, card.width - 1, card.height - 1), radius=30, fill=255
    )
    background.paste(card, (card_x, card_y), mask)
    background.save(destination, "JPEG", quality=97, subsampling=0, optimize=True, progressive=True)

    print(f"Resolução real da origem: {source_size[0]}x{source_size[1]}")
    print("Arte final para Instagram:", (canvas_w, canvas_h))
    print("Foto do produto preservada em:", image.size)

    mapping = {original: "instagram-assets/" + name}
    (ROOT / "instagram_images.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("Produto preparado:", product["produto"])
    print("Imagem JPG otimizada:", destination)
    print("Dimensões finais:", image.size)
    print("Tamanho:", destination.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
