#!/usr/bin/env python3
"""Localiza imagens principais dos anúncios via URL afiliada, com validação conservadora.

Atualiza somente imagem_url. Preserva imagens válidas já cadastradas, preços,
nomes e links afiliados. Não publica no Instagram.
"""
import csv
import re
import sys
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image, UnidentifiedImageError

CSV_PATH = Path(__file__).with_name("produtos.csv")
SLOTS = {"0 12 * * *": 8, "0 15 * * *": 8, "0 18 * * *": 7, "0 21 * * *": 7}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RadarOfertasBR/1.0)"}
MIN_DIMENSION = 400
MAX_IMAGE_BYTES = 15 * 1024 * 1024


def clean_rows():
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(line for line in f if line.strip()))


def selected_indices(rows, slot):
    if slot == "todos":
        return list(range(len(rows)))
    if slot not in SLOTS:
        raise ValueError("Lote UTC inválido.")
    from datetime import datetime, timezone
    start = sum(list(SLOTS.values())[:list(SLOTS).index(slot)])
    base = datetime.now(timezone.utc).date().toordinal() % len(rows)
    return [(base + start + i) % len(rows) for i in range(SLOTS[slot])]


def tokens(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}


def validate_image(session, image_url):
    response = session.get(image_url, headers=HEADERS, timeout=30, stream=True)
    try:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if not content_type.startswith("image/"):
            return False, f"não é imagem ({content_type or 'sem Content-Type'})"
        data = bytearray()
        for chunk in response.iter_content(64 * 1024):
            if not chunk:
                continue
            data.extend(chunk)
            if len(data) > MAX_IMAGE_BYTES:
                return False, "arquivo excede 15 MB"
        try:
            with Image.open(BytesIO(data)) as image:
                width, height = image.size
                image.verify()
        except (UnidentifiedImageError, OSError):
            return False, "arquivo de imagem inválido"
        if min(width, height) < MIN_DIMENSION:
            return False, f"resolução baixa ({width}x{height})"
        return True, f"{width}x{height}"
    finally:
        response.close()


def resolve_image(session, product):
    link = product.get("link_afiliado", "").strip()
    title = product.get("produto", "").strip()
    if not link.startswith("https://"):
        return None, "link afiliado não HTTPS"
    try:
        page = session.get(link, headers=HEADERS, timeout=35, allow_redirects=True)
        page.raise_for_status()
        soup = BeautifulSoup(page.text, "html.parser")
        page_title = soup.find("meta", property="og:title")
        page_title = page_title.get("content", "") if page_title else (soup.title.string if soup.title else "")
        image = soup.find("meta", property="og:image")
        image_url = image.get("content", "").strip() if image else ""
        if not image_url.startswith("https://"):
            return None, "página não forneceu og:image HTTPS"
        wanted, found = tokens(title), tokens(page_title)
        if wanted and found:
            overlap = len(wanted & found) / len(wanted)
            if overlap < 0.30:
                return None, f"título divergente (similaridade {overlap:.0%})"

        # Se a URL entregue pelo anúncio for uma miniatura -P, tenta a versão
        # original -O; só a utiliza se a imagem original passar na validação.
        candidates = []
        parsed = urlparse(image_url)
        if "-P." in parsed.path:
            original = image_url.replace("-P.", "-O.", 1)
            if original != image_url:
                candidates.append(original)
        candidates.append(image_url)
        reasons = []
        for candidate in candidates:
            valid, detail = validate_image(session, candidate)
            if valid:
                return candidate, detail
            reasons.append(detail)
        return None, "imagem reprovada: " + "; ".join(reasons)
    except requests.RequestException as exc:
        return None, f"erro HTTP: {exc}"


def main():
    slot = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "0 12 * * *"
    rows = clean_rows()
    if not rows:
        raise SystemExit("Catálogo vazio.")
    for row in rows:
        row.setdefault("imagem_url", "")
    indices = selected_indices(rows, slot)
    success = 0
    pending = 0
    with requests.Session() as session:
        for index in indices:
            row = rows[index]
            if row.get("imagem_url", "").startswith("https://"):
                print(f"PRESERVADA: {row['produto']} (imagem já cadastrada)")
                success += 1
                continue
            url, status = resolve_image(session, row)
            if url:
                row["imagem_url"] = url
                success += 1
                print(f"IMAGEM VALIDADA: {row['produto']} -> {url} ({status})")
            else:
                pending += 1
                print(f"PENDENTE: {row['produto']} — {status}")
            time.sleep(1)
    fields = ["produto", "preco_anterior_brl", "preco_atual_brl", "link_afiliado", "imagem_url"]
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"RESULTADO: {success}/{len(indices)} produtos com imagem cadastrada; {pending} pendentes.")
    if pending:
        print("Produtos pendentes permanecem sem imagem; nenhum URL foi inventado.")
        sys.exit(2)


if __name__ == "__main__":
    main()
