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

            # A variante original do Mercado Livre normalmente é -O.
            if candidate.endswith("-O" + Path(urlparse(candidate).path).suffix) and min(width, height) >= MIN_SIDE:
                break
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

    # Corrige orientação EXIF e mantém a foto inteira, sem esticar nem cortar.
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((2160, 2700), Image.Resampling.LANCZOS)

    # JPEG de alta qualidade; sem ampliar artificialmente imagens pequenas.
    image.save(destination, "JPEG", quality=95, subsampling=0, optimize=True)

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
