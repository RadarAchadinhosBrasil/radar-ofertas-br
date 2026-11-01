#!/usr/bin/env python3
"""Planeja o mesmo lote diário do Telegram para Instagram/WhatsApp.
Modo seguro: apenas prévia; não envia mensagens nem chama APIs externas.
"""
import csv, json, os
from datetime import datetime, timezone
from pathlib import Path

CSV = Path(__file__).with_name("produtos.csv")
SLOTS = {"0 12 * * *": 8, "0 15 * * *": 8, "0 18 * * *": 7, "0 21 * * *": 7}

def load_products():
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def plan(slot, products, day=None):
    if slot not in SLOTS:
        raise ValueError("SLOT_UTC deve ser um dos horários configurados.")
    if not products:
        raise ValueError("Catálogo vazio.")
    ordered = list(SLOTS)
    idx = ordered.index(slot)
    count = SLOTS[slot]
    start = sum(SLOTS[s] for s in ordered[:idx])
    ordinal = (day or datetime.now(timezone.utc).date()).toordinal()
    daily_total = sum(SLOTS.values())
    # Mantém a prévia alinhada à rotação do bot: avança o lote diário inteiro.
    base = (ordinal * daily_total) % len(products)
    return [products[(base + start + i) % len(products)] for i in range(count)]

def brl(value):
    if not value:
        return ""
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        return value

def message(p):
    lines = [f"🔥 {p.get('produto','Oferta')}", ""]
    if p.get("preco_anterior_brl"):
        lines.append(f"De: ~{brl(p['preco_anterior_brl'])}~")
    lines += [f"💰 Por: {brl(p.get('preco_atual_brl',''))}", "",
              f"🛒 Ver oferta: {p.get('link_afiliado','')}", "",
              "⚠️ Preço e disponibilidade podem mudar. Confira no anúncio."]
    return "\n".join(lines)

if __name__ == "__main__":
    slot = os.getenv("SLOT_UTC", "0 12 * * *")
    products = load_products()
    for n, p in enumerate(products, 2):
        if not all((p.get(k) or "").strip() for k in ("produto", "preco_atual_brl", "link_afiliado")):
            raise SystemExit(f"Produto incompleto na linha {n}.")
    selected = plan(slot, products)
    print(json.dumps({"mode":"PREVIEW_ONLY","slot_utc":slot,"count":len(selected),
        "products":[{"produto":p["produto"],"mensagem":message(p)} for p in selected]},
        ensure_ascii=False, indent=2))
