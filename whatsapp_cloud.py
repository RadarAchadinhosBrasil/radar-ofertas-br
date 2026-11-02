#!/usr/bin/env python3
"""WhatsApp Cloud API: teste individual e controlado com template aprovado.

Por padrão, apenas valida e mostra uma prévia. Nunca envia em modo padrão.
"""
import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "produtos.csv"


def load_first_product():
    with CATALOG.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if all((row.get(k) or "").strip() for k in ("produto", "preco_atual_brl", "link_afiliado")):
                return row
    raise SystemExit("ERRO: não há produto completo em produtos.csv.")


def brl(value):
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(value or "")


def required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"ERRO: configure o secret/variable {name}.")
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="envia uma única mensagem de teste")
    args = parser.parse_args()

    product = load_first_product()
    preview = {
        "mode": "SEND_ONE_TEST" if args.send else "PREVIEW_ONLY",
        "product": product["produto"],
        "price": brl(product["preco_atual_brl"]),
        "affiliate_link": product["link_afiliado"],
        "note": "O destinatário deve ter autorizado expressamente receber ofertas do Radar de Ofertas BR."
    }
    if not args.send:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        print("Prévia concluída. Nenhuma mensagem foi enviada.")
        return

    if os.getenv("WA_CONFIRM_SEND") != "SIM":
        raise SystemExit("BLOQUEADO: envio exige WA_CONFIRM_SEND=SIM.")
    if os.getenv("WA_TEST_RECIPIENT_OPT_IN") != "SIM":
        raise SystemExit("BLOQUEADO: confirme opt-in explícito do destinatário com WA_TEST_RECIPIENT_OPT_IN=SIM.")

    token = required("WA_ACCESS_TOKEN")
    phone_number_id = required("WA_PHONE_NUMBER_ID")
    graph_version = required("WA_GRAPH_API_VERSION")
    recipient = required("WA_TEST_RECIPIENT")
    template_name = required("WA_TEMPLATE_NAME")
    language = os.getenv("WA_TEMPLATE_LANGUAGE", "pt_BR").strip() or "pt_BR"

    if not re.fullmatch(r"\d{8,15}", recipient):
        raise SystemExit("ERRO: WA_TEST_RECIPIENT deve conter apenas dígitos, com código do país.")
    if not re.fullmatch(r"v\d+\.\d+", graph_version):
        raise SystemExit("ERRO: WA_GRAPH_API_VERSION deve ter formato como vXX.X.")

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": product["produto"][:1024]},
                    {"type": "text", "text": brl(product["preco_atual_brl"])},
                    {"type": "text", "text": product["link_afiliado"][:1024]}
                ]
            }]
        }
    }
    url = f"https://graph.facebook.com/{graph_version}/{phone_number_id}/messages"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(json.dumps({
                "mode": "SENT_ONE_TEST",
                "http_status": response.status,
                "message_id": (result.get("messages") or [{}])[0].get("id", "não informado"),
                "recipient_last4": recipient[-4:]
            }, ensure_ascii=False, indent=2))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"WhatsApp API retornou HTTP {exc.code}: {detail[:2000]}", file=sys.stderr)
        raise SystemExit(1)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Falha de conexão com a API: {exc.reason}")


if __name__ == "__main__":
    main()
