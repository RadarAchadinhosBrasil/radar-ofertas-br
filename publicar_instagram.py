#!/usr/bin/env python3
"""Publicador oficial do Instagram Graph API para o Radar de Ofertas BR.

Seguro por padrão: sem CONFIRMAR_PUBLICACAO=SIM, apenas valida e mostra prévia.
Requer imagem_url HTTPS em cada produto selecionado e secrets no ambiente.
"""
import csv, os, sys, time
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
import requests

CSV = Path(__file__).with_name("produtos.csv")
SLOTS = {"0 12 * * *": 8, "0 15 * * *": 8, "0 18 * * *": 7, "0 21 * * *": 7}


def load_products():
    # O catálogo possui uma linha vazia antes do cabeçalho.
    # Remover linhas vazias antes de entregar o conteúdo ao DictReader
    # evita que os nomes e preços sejam lidos como campos sem cabeçalho.
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        rows = (line for line in f if line.strip())
        reader = csv.DictReader(rows)
        products = []
        for row in reader:
            clean = {
                (key or "").strip(): (value or "").strip()
                for key, value in row.items()
                if key is not None
            }
            if clean.get("produto"):
                products.append(clean)
        if not products:
            raise ValueError("O catálogo produtos.csv não contém produtos válidos.")
        return products


def choose(products, slot):
    if slot not in SLOTS:
        raise ValueError("Horário inválido.")
    start = sum(list(SLOTS.values())[:list(SLOTS).index(slot)])
    base = datetime.now(timezone.utc).date().toordinal() % len(products)
    return [products[(base + start + i) % len(products)] for i in range(SLOTS[slot])]


def valid_image(url):
    p = urlparse(url or "")
    return p.scheme == "https" and bool(p.netloc)


def caption(p):
    old = p.get("preco_anterior_brl", "").strip()
    try:
        current = f"R$ {float(p.get('preco_atual_brl','')):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        current = p.get("preco_atual_brl", "")
    lines = [f"🔥 {p.get('produto','Oferta')}", ""]
    if old:
        try:
            old = f"R$ {float(old):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except ValueError:
            old = f"R$ {old}"
        lines.append(f"De: {old}")
    lines += [f"💰 Por: {current}", "", f"🛒 Acesse pelo link da bio: {p.get('link_afiliado','')}",
              "", "⚠️ Preço e disponibilidade podem mudar. Confira no anúncio.",
              "", "#RadarDeOfertas #Achadinhos #Ofertas"]
    return "\n".join(lines)


def publish(session, api, ig_id, token, product, media_type):
    image = product["imagem_url"].strip()
    payload = {"image_url": image, "caption": caption(product), "access_token": token}
    if media_type == "STORIES":
        payload["media_type"] = "STORIES"
    r = session.post(f"{api}/{ig_id}/media", data=payload, timeout=40)
    r.raise_for_status()
    creation_id = r.json().get("id")
    if not creation_id:
        raise RuntimeError(f"Meta não retornou creation_id: {r.text[:500]}")
    for _ in range(12):
        status = session.get(f"{api}/{creation_id}", params={
            "fields": "status_code", "access_token": token}, timeout=30)
        status.raise_for_status()
        code = status.json().get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError("Meta informou erro ao processar a mídia.")
        time.sleep(5)
    else:
        raise RuntimeError("Tempo esgotado aguardando processamento da mídia.")
    r = session.post(f"{api}/{ig_id}/media_publish",
                     data={"creation_id": creation_id, "access_token": token}, timeout=40)
    r.raise_for_status()
    return r.json().get("id")


def main():
    slot = os.getenv("SLOT_UTC", "0 12 * * *")
    products = load_products()
    selected = choose(products, slot)
    missing = [p["produto"] for p in selected
               if not valid_image(p.get("imagem_url", ""))]
    if missing:
        print("BLOQUEADO: adicione uma coluna imagem_url com URL HTTPS pública para cada produto selecionado.")
        print("Sem imagens não é possível publicar Feed/Stories pela API oficial.")
        print("Produtos sem imagem: " + "; ".join(missing))
        sys.exit(2)
    token, ig_id = os.getenv("IG_ACCESS_TOKEN"), os.getenv("IG_USER_ID")
    version = os.getenv("IG_GRAPH_API_VERSION")
    if not token or not ig_id or not version:
        raise SystemExit("Configure IG_ACCESS_TOKEN, IG_USER_ID e IG_GRAPH_API_VERSION nos Secrets/Variables do GitHub.")
    api = f"https://graph.facebook.com/{version}"
    if os.getenv("CONFIRMAR_PUBLICACAO") != "SIM":
        print(f"PRÉVIA: {len(selected)} produtos validados. Nenhuma publicação enviada.")
        for p in selected:
            print("- " + p["produto"] + " | " + p["imagem_url"])
        print("Para publicar, use execução manual autorizada e CONFIRMAR_PUBLICACAO=SIM.")
        return
    mode = os.getenv("IG_MEDIA_TYPE", "IMAGE")
    if mode not in ("IMAGE", "STORIES"):
        raise SystemExit("IG_MEDIA_TYPE deve ser IMAGE ou STORIES.")
    with requests.Session() as session:
        for p in selected:
            media_id = publish(session, api, ig_id, token, p, mode)
            print(f"Publicado ({mode}): {p['produto']} | media_id={media_id}")
            time.sleep(5)


if __name__ == "__main__":
    main()
