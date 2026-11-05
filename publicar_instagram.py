
#!/usr/bin/env python3
import csv
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent
CSV = ROOT / "produtos.csv"
SLOTS = ["17 11 * * *","17 13 * * *","17 15 * * *","17 17 * * *","17 19 * * *","17 21 * * *","17 23 * * *","17 1 * * *"]


def load_products():
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        rows = (line for line in f if line.strip())
        reader = csv.DictReader(rows)
        products = []
        for row in reader:
            clean = {
                (key or "").strip(): (value or "").strip()
                for key, value in row.items() if key is not None
            }
            if clean.get("produto"):
                products.append(clean)
    if not products:
        raise ValueError("produtos.csv não contém produtos válidos.")
    return products


def choose(products, slot):
    if slot not in SLOTS:
        raise ValueError('Horário inválido.')
    return next_feed_product()[0]

def next_feed_product():
    products = load_products()
    eligible = [p for p in products if p.get("link_afiliado", "").startswith("https://") and p.get("imagem_url", "").startswith("https://")]
    if not eligible:
        raise ValueError("Nenhum produto com link e imagem HTTPS válidos.")
    state_path = ROOT / "instagram_feed_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"cycle": 1, "posted_links": []}
    posted = set(state.get("posted_links", []))
    remaining = [p for p in eligible if p.get("link_afiliado") not in posted]
    if not remaining:
        state = {"cycle": int(state.get("cycle", 1)) + 1, "posted_links": []}
        remaining = eligible
    return remaining[0], state


def hashtags(p):
    """Hashtags específicas por produto, combinadas com a identidade da marca."""
    nome = (p.get("produto") or "").lower()

    categorias = [
        (("barbeador", "oneblade", "aparador", "depilador"),
         ("#CuidadosPessoais", "#BarbeadorEletrico")),
        (("arvore de natal", "árvore de natal", "pisca", "enfeite natalino"),
         ("#DecoracaoNatalina", "#Natal")),
        (("power bank", "carregador", "cabo usb", "fone", "headset"),
         ("#AcessoriosParaCelular", "#Tecnologia")),
        (("tenis", "tênis", "sapato", "sandalia", "chinelo"),
         ("#Moda", "#Calcados")),
        (("frigideira", "panela", "air fryer", "cafeteira", "liquidificador"),
         ("#Cozinha", "#UtilidadesDomesticas")),
        (("ventilador", "ar-condicionado", "umidificador"),
         ("#CasaConfortavel", "#Eletroportateis")),
        (("limpeza", "mop", "aspirador", "extratora"),
         ("#LimpezaDaCasa", "#CasaOrganizada")),
        (("creatina", "whey", "halter", "academia", "fitness"),
         ("#VidaFitness", "#Treino")),
        (("toalha", "lixeira", "organizador", "tapete", "cortina"),
         ("#CasaEDecoracao", "#UtilidadesParaCasa")),
    ]

    especificas = None
    for termos, tags in categorias:
        if any(termo in nome for termo in termos):
            especificas = tags
            break

    if especificas is None:
        especificas = ("#AchadosDoDia", "#ComprasInteligentes")

    return " ".join((
        "#RadarDeOfertasBR",
        "#Achadinhos",
        especificas[0],
        especificas[1],
        "#OfertasMercadoLivre",
    ))


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

    lines += [
        f"💰 Por: {current}", "",
        "🔗 Para acessar esta oferta, toque em @radarachadinhosbrasil e escolha Telegram ou WhatsApp nos links da bio.",
        "",
        "⚠️ Preço e disponibilidade podem mudar. Confira no anúncio.",
        "",
        hashtags(p)
    ]
    return "\n".join(lines)

def meta_error(response, operation):
    try:
        data = response.json()
        error = data.get("error", {})
        details = (
            f"mensagem={error.get('message')}; "
            f"tipo={error.get('type')}; "
            f"código={error.get('code')}; "
            f"subcódigo={error.get('error_subcode')}; "
            f"trace_id={error.get('fbtrace_id')}"
        )
    except Exception:
        details = response.text[:1500]

    raise RuntimeError(
        f"Erro da Meta em {operation}. HTTP {response.status_code}. {details}"
    )


def publish(session, api, ig_id, token, product, media_type, image_url):
    print("Imagem JPG pública:", image_url)

    payload = {
        "image_url": image_url,
        "caption": caption(product),
        "access_token": token
    }
    if media_type == "STORIES":
        payload["media_type"] = "STORIES"

    response = session.post(
        f"{api}/{ig_id}/media", data=payload, timeout=45
    )
    if not response.ok:
        meta_error(response, "criação do contêiner de mídia")

    creation_id = response.json().get("id")
    if not creation_id:
        raise RuntimeError(
            "Meta não retornou creation_id: " + response.text[:1000]
        )

    for _ in range(18):
        status = session.get(
            f"{api}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30
        )
        if not status.ok:
            meta_error(status, "consulta do processamento da imagem")

        code = status.json().get("status_code")
        print("Status de processamento:", code)

        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(
                "Meta informou erro ao processar a imagem."
            )
        time.sleep(5)
    else:
        raise RuntimeError(
            "Tempo esgotado aguardando processamento da imagem."
        )

    response = session.post(
        f"{api}/{ig_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=45
    )
    if not response.ok:
        meta_error(response, "publicação da mídia")

    return response.json().get("id")


def main():
    slot = os.getenv("SLOT_UTC", "")
    product, rotation_state = next_feed_product()

    if os.getenv("IG_ACTION", "preview").lower() != "publish":
        print("Prévia segura. Nenhuma publicação enviada.")
        print(product["produto"])
        print(caption(product))
        print('Prévia: rodízio não avançado.')
        return

    if os.getenv("CONFIRMAR_PUBLICACAO") != "SIM":
        raise SystemExit("Publicação bloqueada: confirmação ausente.")

    token = os.getenv("IG_ACCESS_TOKEN")
    ig_id = os.getenv("IG_USER_ID")
    version = os.getenv("IG_GRAPH_API_VERSION")
    pages_url = os.getenv("PAGES_URL", "").rstrip("/")

    if not all((token, ig_id, version, pages_url)):
        raise SystemExit("Faltam credenciais ou URL do GitHub Pages.")

    mapping_file = ROOT / "instagram_images.json"
    if not mapping_file.exists():
        raise SystemExit("Arquivo de imagens preparadas não encontrado.")

    mapping = json.loads(mapping_file.read_text(encoding="utf-8"))
    original = product.get("imagem_url", "").strip()
    relative = mapping.get(original)

    if not relative:
        raise SystemExit(
            "Não foi encontrada imagem JPG preparada para: "
            + product.get("produto", "produto")
        )

    image_url = pages_url + "/" + relative.lstrip("/")
    if urlparse(image_url).scheme != "https":
        raise SystemExit("A imagem final não possui URL HTTPS.")

    mode = os.getenv("IG_MEDIA_TYPE", "IMAGE")
    if mode not in ("IMAGE", "STORIES"):
        raise SystemExit("IG_MEDIA_TYPE deve ser IMAGE ou STORIES.")

    api = f"https://graph.facebook.com/{version}"

    with requests.Session() as session:
        check = session.get(image_url, timeout=45)
        check.raise_for_status()
        if not check.headers.get("Content-Type", "").lower().startswith("image/jpeg"):
            raise SystemExit("A URL pública não está entregando uma imagem JPG.")
        if len(check.content) < 10000:
            raise SystemExit("A imagem JPG pública parece incompleta.")

        media_id = publish(
            session, api, ig_id, token, product, mode, image_url
        )
        print(f"PUBLICADO ({mode}): {product['produto']} | media_id={media_id}")
        rotation_state.setdefault("posted_links", []).append(product["link_afiliado"])
        (ROOT / "instagram_feed_state.json").write_text(
            json.dumps(rotation_state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )
        print("Rodízio atualizado:", len(rotation_state["posted_links"]), "itens publicados nesta volta.")


if __name__ == "__main__":
    main()
