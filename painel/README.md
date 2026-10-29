# Radar de Ofertas BR

## Painel de catálogo (v1)

Abra `painel/index.html` no navegador. O painel permite:
- importar o `produtos.csv` atual;
- adicionar, editar, excluir e pesquisar produtos;
- sinalizar registros sem dados mínimos e detectar links repetidos;
- visualizar/copiar a mensagem de oferta;
- exportar um novo `produtos.csv`.

### Importante
Esta primeira versão é um painel local: os dados editados ficam no armazenamento do navegador. Para atualizar o bot na nuvem, exporte o CSV e substitua `produtos.csv` no repositório. Não coloque token do Telegram, senha ou credenciais do Mercado Livre neste painel.

O painel ainda não busca produtos nem cria links de afiliado sozinho. Isso depende de integração oficial/autorizada com o Mercado Livre e acesso aos dados de afiliado. Também não publica diretamente em Instagram/WhatsApp. Esses módulos serão integrados após validar as permissões e APIs disponíveis.

## Bot Telegram
O fluxo atual de publicação continua independente e não foi alterado por esta entrega.
