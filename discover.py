"""Descobre ofertas candidatas no Mercado Livre Brasil.
Gera candidatos_ofertas.csv para revisão humana; não cria links afiliados nem publica.
"""
import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

QUERIES = [
    "fone bluetooth", "eletroportatil", "ferramentas", "casa cozinha",
    "beleza cuidados pessoais", "acessorios celular", "fitness",
    "organizacao casa", "utilidades domesticas", "informatica"
]
OUTPUT = "candidatos_ofertas.csv"
MIN_DISCOUNT = 15.0
MAX_PRICE = 1500.0
MAX_CANDIDATES = 100
HEADERS = {"User-Agent": "RadarDeOfertasBR/1.1 (offer discovery)"}


def fetch(query):
    params = urllib.parse.urlencode({
        "q": query, "limit": 50, "sort": "discount",
        "condition": "new"
    })
    url = "https://api.mercadolibre.com/sites/MLB/search?" + params
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def candidate(item):
    price = item.get("price")
    original = item.get("original_price")
    item_id = item.get("id")
    title = (item.get("title") or "").strip()
    if not item_id or not title or not isinstance(price, (int, float)):
        return None
    if not isinstance(original, (int, float)) or original <= price or price <= 0:
        return None
    if price > MAX_PRICE:
        return None
    discount = round((original - price) / original * 100, 1)
    if discount < MIN_DISCOUNT:
        return None
    if item.get("available_quantity", 0) <= 0:
        return None

    shipping = item.get("shipping") or {}
    seller = item.get("seller") or {}
    seller_rep = seller.get("seller_reputation") or {}
    transactions = seller_rep.get("transactions") or {}
    permalink = item.get("permalink") or ""
    if not permalink.startswith("https://www.mercadolivre.com.br/") and not permalink.startswith("https://produto.mercadolivre.com.br/"):
        return None

    return {
        "produto": title,
        "preco_anterior_brl": f"{original:.2f}",
        "preco_atual_brl": f"{price:.2f}",
        "desconto_percentual": discount,
        "envio_gratis": "sim" if shipping.get("free_shipping") else "nao",
        "unidades_disponiveis": item.get("available_quantity", ""),
        "vendidos_anunciados": item.get("sold_quantity", ""),
        "reputacao_vendedor": seller_rep.get("level_id") or "nao_informada",
        "vendas_concluidas_vendedor": transactions.get("completed", ""),
        "id_anuncio": item_id,
        "url_anuncio": permalink,
        "link_afiliado": "",
        "origem": "API pública Mercado Livre",
        "coletado_em_utc": datetime.now(timezone.utc).isoformat()
    }


def main():
    found = {}
    failures = 0
    for query in QUERIES:
        try:
            payload = fetch(query)
            for item in payload.get("results", []):
                row = candidate(item)
                if row:
                    found[row["id_anuncio"]] = row
        except Exception as exc:
            failures += 1
            print(f"Consulta '{query}' falhou: {exc}")

    rows = sorted(
        found.values(),
        key=lambda x: (
            x["desconto_percentual"],
            x["envio_gratis"] == "sim",
            int(x["vendidos_anunciados"] or 0)
        ),
        reverse=True
    )[:MAX_CANDIDATES]

    fields = [
        "produto", "preco_anterior_brl", "preco_atual_brl",
        "desconto_percentual", "envio_gratis", "unidades_disponiveis",
        "vendidos_anunciados", "reputacao_vendedor",
        "vendas_concluidas_vendedor", "id_anuncio", "url_anuncio",
        "link_afiliado", "origem", "coletado_em_utc"
    ]
    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} ofertas candidatas gravadas em {OUTPUT}.")
    print(f"Consultas com falha: {failures}/{len(QUERIES)}.")
    print("Revisao humana obrigatoria: confira preco, estoque, vendedor e anuncio.")
    print("Preencha link_afiliado com seu link oficial antes de incluir em produtos.csv.")
    print("Nenhuma oferta candidata e publicada automaticamente.")


if __name__ == "__main__":
    main()
