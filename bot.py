
import os
import csv
import asyncio
from pathlib import Path
from telegram import Bot

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "@radardeofertasbr_oficial").strip()
CSV_PATH = Path(__file__).with_name("produtos.csv")


def carregar_produtos():
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def formatar_preco(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return valor or "Consultar anúncio"


def montar_mensagem(p):
    nome = (p.get("produto") or "Oferta").strip()
    atual = formatar_preco(p.get("preco_atual_brl", ""))
    anterior_raw = p.get("preco_anterior_brl", "")
    link = (p.get("link_afiliado") or "").strip()
    anterior = formatar_preco(anterior_raw) if anterior_raw else ""

    linhas = [f"🔥 {nome}", ""]
    if anterior:
        linhas.append(f"De: ~{anterior}~")

    linhas += [
        f"💰 Por: {atual}",
        "",
        f"🛒 Ver oferta: {link}",
        "",
        "⚠️ Preço e disponibilidade podem mudar. Confira no anúncio.",
    ]
    return "\n".join(linhas)


async def main():
    if not TOKEN:
        raise SystemExit("Falta configurar a variável secreta TELEGRAM_BOT_TOKEN.")

    produtos = carregar_produtos()
    if not produtos:
        raise SystemExit("O arquivo produtos.csv não tem produtos.")

    bot = Bot(TOKEN)
    me = await bot.get_me()
    print(f"Bot conectado: @{me.username}")
    print(f"Canal configurado: {CHANNEL}")
    print(f"Produtos disponíveis: {len(produtos)}")

    mensagem = montar_mensagem(produtos[0])
    await bot.send_message(chat_id=CHANNEL, text=mensagem)
    print("Teste enviado ao canal.")


if __name__ == "__main__":
    asyncio.run(main())
