
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
    # Lê o CSV com detecção de separador e normalização dos cabeçalhos.
    # Isso evita falhas quando o arquivo é salvo com ;, BOM ou espaços.
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        conteudo = f.read()

    if not conteudo.strip():
        raise SystemExit("Erro: produtos.csv está vazio.")

    # Detecta o separador a partir da primeira linha não vazia (cabeçalho).
    # Isso evita falhas causadas por linhas em branco antes do cabeçalho.
    primeira_linha = next((linha for linha in conteudo.splitlines() if linha.strip()), "")
    candidatos = [",", ";", "\\t"]
    delimitador = max(candidatos, key=lambda sep: primeira_linha.count(sep))
    if primeira_linha.count(delimitador) == 0:
        raise SystemExit("Erro: não foi possível detectar o separador do CSV.")

    leitor = csv.DictReader(conteudo.splitlines(), delimiter=delimitador)
    if not leitor.fieldnames:
        raise SystemExit("Erro: o CSV está sem cabeçalho.")

    def normalizar_cabecalho(valor):
        return (valor or "").strip().lower().replace("\ufeff", "").replace(" ", "_")

    cabecalhos = [normalizar_cabecalho(nome) for nome in leitor.fieldnames]
    aliases = {
        "nome": "produto",
        "produto": "produto",
        "preco": "preco_atual_brl",
        "preco_atual": "preco_atual_brl",
        "preco_atual_brl": "preco_atual_brl",
        "preco_anterior": "preco_anterior_brl",
        "preco_anterior_brl": "preco_anterior_brl",
        "link": "link_afiliado",
        "link_afiliado": "link_afiliado",
        "url": "link_afiliado",
    }

    produtos = []
    for linha in leitor:
        produto = {}
        for chave, valor in linha.items():
            chave_normalizada = normalizar_cabecalho(chave)
            destino = aliases.get(chave_normalizada, chave_normalizada)
            if destino and valor is not None:
                produto[destino] = valor.strip() if isinstance(valor, str) else valor
        if any((valor or "").strip() for valor in produto.values() if isinstance(valor, str)):
            produtos.append(produto)

    print("SEPARADOR CSV:", repr(delimitador))
    print("CABEÇALHOS NORMALIZADOS:", repr(cabecalhos))
    print("TOTAL DE PRODUTOS LIDOS:", len(produtos))
    print("PRIMEIRO PRODUTO LIDO:", repr(produtos[0] if produtos else None))

    return produtos

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
    print("VERSAO DO BOT: diagnostico CSV v2")

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
