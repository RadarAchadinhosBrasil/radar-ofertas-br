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
SLOTS = {"0 12 * * *": 1, "0 15 * * *": 1, "0 18 * * *": 1, "0 21 * * *": 1}


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
    lines += [f"💰 Por: {current}", "", "🔗 Para acessar esta oferta, toque em @radarachadinhosbrasil e escolha Telegram ou WhatsApp nos links da bio.",
              "", "⚠️ Preço e disponibilidade podem mudar. Confira no anúncio.",
              "", "#RadarDeOfertas #Achadinhos #Ofertas"]
    return "\n".join(lines)


def best_image_url(session, original_url):
    """Tenta a variante original do CDN do Mercado Livre; mantém a imagem validada como fallback."""
    original_url = original_url.strip()
    # O sufixo -P costuma indicar imagem de prévia. -O solicita a versão original
    # quando o anúncio/CDN disponibiliza essa variante.
    candidate = original_url.replace("-P.", "-O.")
    if candidate == original_url:
        return original_url
    try:
        response = session.get(candidate, stream=True, timeout=25,
                               headers={"User-Agent": "Mozilla/5.0"})
        content_type = response.headers.get("Content-Type", "").lower()
        length = int(response.headers.get("Content-Length", "0") or 0)
        ok = response.status_code == 200 and content_type.startswith("image/") and (length == 0 or length >= 30000)
        response.close()
        return candidate if ok else original_url
    except requests.RequestException:
        return original_url


def publish(session, api, ig_id, token, product, media_type):
    image = best_image_url(session, product["imagem_url"])
    print(f"Imagem selecionada: {image}")
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
    # Limite opcional para teste controlado: 1 publica somente o primeiro item do lote.
    max_publications = os.getenv("IG_MAX_PUBLICATIONS", "lote").strip().lower()
    if max_publications == "1":
        selected = selected[:1]
    elif max_publications != "lote":
        raise SystemExit("IG_MAX_PUBLICATIONS deve ser 1 ou lote.")
    missing = [p["produto"] for p in selected
               if not valid_image(p.get("imagem_url", ""))]
    if missing:
        print("BLOQUEADO: o catálogo ainda não tem imagem_url válida para todos os produtos deste lote.")
        print("ATENÇÃO: este workflow apenas valida/publica; ele NÃO busca imagens.")
        print("Primeiro execute GitHub Actions > Instagram — buscar imagens do lote.")
        print("Selecione exatamente o mesmo lote UTC e aguarde a conclusão; depois execute esta validação novamente.")
        print("Sem imagens HTTPS públicas não é possível publicar Feed/Stories pela API oficial.")
        print("Produtos sem imagem: " + "; ".join(missing))
        sys.exit(2)
    # Prévia não exige credenciais da Meta e nunca publica.
    if os.getenv("IG_ACTION", "preview").strip().lower() != "publish":
        print(f"PRÉVIA SEGURA: {len(selected)} produtos validados. Nenhuma publicação enviada.")
        for p in selected:
            print("\\n--- " + p["produto"] + " ---")
            print("Imagem: " + p["imagem_url"])
            print(caption(p))
        print("\\nPara publicar de verdade, selecione a ação Publicar e configure os Secrets da Meta.")
        return

    if os.getenv("CONFIRMAR_PUBLICACAO") != "SIM":
        raise SystemExit("PUBLICAÇÃO BLOQUEADA: defina o Secret CONFIRMAR_PUBLICACAO=SIM somente após revisar a prévia.")
    token, ig_id = os.getenv("IG_ACCESS_TOKEN"), os.getenv("IG_USER_ID")
    version = os.getenv("IG_GRAPH_API_VERSION")
    if not token or not ig_id or not version:
        raise SystemExit("Configure IG_ACCESS_TOKEN, IG_USER_ID e IG_GRAPH_API_VERSION nos Secrets/Variables do GitHub.")
    api = f"https://graph.facebook.com/{version}"
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
