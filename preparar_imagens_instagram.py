
import csv
import hashlib
import json
import os
from pathlib import Path
from io import BytesIO
from urllib.parse import urlparse

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site" / "instagram-assets"
SLOTS = ["0 12 * * *", "0 15 * * *", "0 18 * * *", "0 21 * * *"]


def main():
    slot = os.environ["SLOT_UTC"]
    if slot not in SLOTS:
        raise SystemExit("Horário inválido: " + slot)

    with (ROOT / "produtos.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = (line for line in f if line.strip())
        products = [
            { (k or "").strip(): (v or "").strip()
              for k, v in row.items() if k is not None }
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

    response = requests.get(
        original,
        headers={"User-Agent": "Mozilla/5.0 RadarOfertasBR/1.0"},
        timeout=45
    )
    response.raise_for_status()

    image = Image.open(BytesIO(response.content))
    image = image.convert("RGB")
    image.thumbnail((1440, 1440))
    image.save(destination, "JPEG", quality=90, optimize=True)

    mapping = {
        original: "instagram-assets/" + name
    }
    (ROOT / "instagram_images.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("Produto preparado:", product["produto"])
    print("Imagem convertida para JPG:", destination)
    print("Tamanho:", destination.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
