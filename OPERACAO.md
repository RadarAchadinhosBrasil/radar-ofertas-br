# Operação do Radar de Ofertas BR

## O que está automatizado
- Publicação no Telegram pelo workflow `.github/workflows/testar-bot.yml`.
- Descoberta de ofertas públicas pelo endpoint de busca do Mercado Livre, duas vezes ao dia, via `discover.py`.
- Candidatos ficam em um artefato CSV por 14 dias para revisão; não são publicados automaticamente.
- Painel estático em `painel/index.html`; workflow Pages tenta publicar o painel após mudanças.

## Fluxo seguro de novos produtos
1. Abra Actions → **Descobrir ofertas candidatas** → último run → baixe `ofertas-candidatas`.
2. Confira manualmente preço, estoque, reputação do vendedor, frete e se o desconto é real.
3. Gere/obtenha o link afiliado dentro da ferramenta oficial da sua conta de afiliado Mercado Livre.
4. Preencha `link_afiliado` no CSV e copie os produtos aprovados para `produtos.csv`.
5. Rode o diagnóstico manual do workflow do bot. Ele não publica.
6. O bot programado usa somente `produtos.csv` e publica nos horários existentes.

## Limites e credenciais
- A busca pública não autentica como afiliado e não cria links de comissão.
- Não há integração de vendas/comissões nesta versão. Não foi presumida uma API pública de relatórios.
- Instagram/WhatsApp não são conectados; automação exige contas, permissões e APIs oficiais.
- Nunca grave token, senha ou chave em arquivos do repositório. Use GitHub Secrets.
- O painel atual guarda alterações no navegador local. GitHub Pages hospeda a interface, mas não cria banco de dados nem sincroniza alterações de volta ao GitHub.
- Não envie mensagens em massa não solicitadas pelo WhatsApp.

## Configuração do GitHub Pages
O workflow `.github/workflows/pages.yml` foi adicionado. No GitHub, abra Settings → Pages e selecione **GitHub Actions** como Build and deployment. Depois, execute o workflow Pages manualmente ou faça uma alteração em `painel/**`. A URL só estará ativa quando o deploy terminar com sucesso.


## Prévia visual dos Stories (novo)
- O script `gerar_story.py` cria artes verticais 1080×1920 usando os dados e a imagem já cadastrados em `produtos.csv`.
- Para gerar a prévia: GitHub → Actions → **Instagram — gerar prévia visual dos Stories** → Run workflow. Escolha 1, 2, 4 ou 8 artes.
- Ao terminar, abra o run e baixe o artefato **radar-stories-preview** para revisar as imagens.
- Esta etapa é somente de geração e revisão: não publica no Instagram, não altera preços e não modifica o catálogo.
- Se uma imagem estiver indisponível ou inválida, aquela arte fica pendente e o workflow sinaliza falha; não inventa imagem.
- Antes de qualquer publicação, confira manualmente nome, preço atual, preço anterior e correspondência da foto com o anúncio.
- Stories ainda não estão agendados automaticamente. A publicação continua manual e controlada até validar uma hospedagem pública estável para as artes e o fluxo completo da API da Meta.
