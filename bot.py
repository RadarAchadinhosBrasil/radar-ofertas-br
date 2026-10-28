
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
HORARIO_AGENDADO = os.environ.get("SLOT_UTC", "").strip()
CSV_PATH = Path(__file__).with_name("produtos.csv")

HORARIOS = {
    "0 12 * * *": 8,
    "0 15 * * *": 8,
    "0 18 * * *": 7,
    "0 21 * * *": 7,
}

def carregar_produtos():
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def formatar_preco(valor):
    try:
        numero = float(str(valor).strip().replace(",", "."))
        return f"R$ {numero:,.2f}".replace(
            ",", "X"
        ).replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return valor or "Consultar anúncio"


def montar_mensagem(produto):
    nome = (produto.get("produto") or "Oferta").strip()
    atual = formatar_preco(produto.get("preco_atual_brl", ""))
    anterior_raw = (produto.get("preco_anterior_brl") or "").strip()
    link = (produto.get("link_afiliado") or "").strip()

    linhas = [f"🔥 {nome}", ""]

    if anterior_raw:
        anterior = formatar_preco(anterior_raw)
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

    if not HORARIO_AGENDADO:
        raise SystemExit(
            "Execução manual bloqueada para evitar publicações inesperadas."
        )

    if HORARIO_AGENDADO not in HORARIOS:
        raise SystemExit("Horário de agendamento não reconhecido.")

    produtos = carregar_produtos()

    if len(produtos) < 30:
        raise SystemExit(
            f"Esperados 30 produtos; encontrados {len(produtos)}."
        )

    for numero, produto in enumerate(produtos, start=2):
        campos_faltando = []

        if not (produto.get("produto") or "").strip():
            campos_faltando.append("nome")

        if not (produto.get("preco_atual_brl") or "").strip():
            campos_faltando.append("preço atual")

        if not (produto.get("link_afiliado") or "").strip():
            campos_faltando.append("link de afiliado")

        if campos_faltando:
            raise SystemExit(
                f"Erro na linha {numero} do produtos.csv: "
                f"falta(m) {', '.join(campos_faltando)}."
            )

    ordem = list(HORARIOS.keys())
    slot = ordem.index(HORARIO_AGENDADO)
    quantidade = HORARIOS[HORARIO_AGENDADO]
    inicio = sum(HORARIOS[h] for h in ordem[:slot])

    dia = datetime.now(timezone.utc).date().toordinal()
    base = dia % len(produtos)

    selecionados = [
        produtos[(base + inicio + i) % len(produtos)]
        for i in range(quantidade)
    ]

    bot = Bot(TOKEN)
    me = await bot.get_me()
    print(f"Bot conectado: @{me.username}")
    print(f"Ofertas neste período: {quantidade}")

    for i, produto in enumerate(selecionados):
        print(f"Publicando {i + 1}/{quantidade}: {produto['produto']}")

        await bot.send_message(
            chat_id=CHANNEL,
            text=montar_mensagem(produto),
        )

        print("Oferta enviada.")

        if i < len(selecionados) - 1:
            await asyncio.sleep(300)

    print("Todas as ofertas deste período foram publicadas.")

if __name__ == "__main__":
    asyncio.run(main())
