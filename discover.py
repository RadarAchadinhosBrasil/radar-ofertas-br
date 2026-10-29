"""Descobre ofertas públicas no Mercado Livre Brasil sem criar links afiliados.
Gera candidatos_ofertas.csv para revisão humana; nunca publica automaticamente.
"""
import csv
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

QUERIES = [
    "fone bluetooth", "eletroportatil", "ferramentas", "casa cozinha",
    "beleza cuidados pessoais", "acessorios celular", "fitness"
]
OUTPUT = "candidatos_ofertas.csv"
HEADERS = {"User-Agent": "RadarDeOfertasBR/1.0 (offer discovery)"}


def fetch(query):
    params = urllib.parse.urlencode({
        "q": query, "limit": 50, "sort": "price",
        "shipping_cost": "free"
    })
    url = "https://api.mercadolibre.com/sites/MLB/search?" + params
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    found = {}
    for query in QUERIES:
        try:
            payload = fetch(query)
            for item in payload.get("results", []):
                price = item.get("price")
                original = item.get("original_price")
                if not price or not original or original <= price:
                    continue
                discount = round((original - price) / original * 100, 1)
                if discount < 15:
                    continue
                item_id = item.get("id")
                if not item_id:
                    continue
                found[item_id] = {
                    "produto": item.get("title", ""),
                    "preco_anterior_brl": f"{original:.2f}",
                    "preco_atual_brl": f"{price:.2f}",
                    "desconto_percentual": discount,
                    "url_anuncio": item.get("permalink", ""),
                    "link_afiliado": "",
                    "origem": "API pública Mercado Livre",
                    "coletado_em_utc": datetime.now(timezone.utc).isoformat()
                }
        except Exception as exc:
            print(f"Consulta '{query}' falhou: {exc}")

    rows = sorted(found.values(), key=lambda x: x["desconto_percentual"], reverse=True)
    fields = ["produto", "preco_anterior_brl", "preco_atual_brl",
              "desconto_percentual", "url_anuncio", "link_afiliado",
              "origem", "coletado_em_utc"]
    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} ofertas candidatas gravadas em {OUTPUT}.")
    print("ATENÇÃO: adicione e valide manualmente o link afiliado antes de publicar.")


if __name__ == "__main__":
    main()
