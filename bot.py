import os
import csv
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from telegram import Bot

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL = os.environ.get(
    "TELEGRAM_CHANNEL", "@radardeofertasbr_oficial"
).strip()
CSV_PATH = Path(__file__).with_name("produtos.csv")

# Horários UTC do agendamento: 12h, 15h, 18h e 21h.
# No horário de Brasília, correspondem a 9h, 12h, 15h e 18h.
INDICE_POR_HORA_UTC = {
    12: 0,
    15: 1,
    18: 2,
    21: 3,
}


def carregar_produtos():
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def formatar_preco(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(
            ",", "X"
        ).replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return valor or "Consultar anúncio"


def montar_mensagem(produto):
    nome = (produto.get("produto") or "Oferta").strip()
    atual = formatar_preco(produto.get("preco_atual_brl", ""))
    anterior_raw = produto.get("preco_anterior_brl", "")
    link = (produto.get("link_afiliado") or "").strip()
    anterior = formatar_preco(anterior_raw) if anterior_raw else ""

    linhas = [nome, ""]
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
        raise SystemExit("Falta configurar o segredo TELEGRAM_BOT_TOKEN.")

    produtos = carregar_produtos()
    if not produtos:
        raise SystemExit("O arquivo produtos.csv não tem produtos.")

    agora = datetime.now(timezone.utc)
    indice = INDICE_POR_HORA_UTC.get(agora.hour, 0)

    if indice >= len(produtos):
        raise SystemExit(
            "Não há produto cadastrado para este horário. "
            "Confira o arquivo produtos.csv."
        )

    produto = produtos[indice]
    if not produto.get("link_afiliado", "").strip():
        raise SystemExit("O produto selecionado não tem link de afiliado.")

    bot = Bot(TOKEN)
    me = await bot.get_me()
    print(f"Bot conectado: @{me.username}")
    print(f"Produto selecionado: {produto.get('produto', 'Oferta')}")

    await bot.send_message(
        chat_id=CHANNEL,
        text=montar_mensagem(produto),
    )
    print("Oferta enviada ao canal.")


if __name__ == "__main__":
    asyncio.run(main())
