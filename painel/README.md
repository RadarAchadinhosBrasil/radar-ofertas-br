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

## Central de automação
O painel agora exibe o estado dos três canais e os horários planejados. Telegram permanece ativo; Instagram e WhatsApp aparecem como aguardando conexão até que as contas e permissões oficiais sejam configuradas.

Consulte `INTEGRACOES-SOCIAIS.md` para os requisitos de cada plataforma. O arquivo `planejador_canais.py` gera prévias dos mesmos lotes do Telegram sem publicar. O workflow `Prévia dos lotes sociais (sem publicar)` permite testar os quatro horários pelo GitHub Actions.

**Limites importantes:** Instagram exige conta profissional elegível, permissões da Meta e imagens públicas HTTPS. WhatsApp Cloud API envia a contatos com opt-in e não publica em grupos comuns. Não automatizamos follows/unfollows em massa nem usamos WhatsApp Web não oficial.
