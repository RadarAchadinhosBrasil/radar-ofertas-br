# Integrações sociais — Radar de Ofertas BR

## Estado desta entrega
- Telegram: automação existente preservada (09h, 12h, 15h e 18h de Brasília).
- Planejador compartilhado: `planejador_canais.py` replica a seleção de produtos e o texto do Telegram, em modo **somente prévia**.
- Instagram e WhatsApp: ainda não publicam. Nenhuma credencial foi criada, solicitada ou exposta.
- Painel: continua em GitHub Pages; esta documentação descreve o caminho de conexão.

## Instagram (API oficial da Meta)
Requisitos:
1. Conta Instagram profissional (Business ou Creator) ligada a uma Página do Facebook.
2. Aplicativo Meta configurado com Instagram Graph API e permissões de publicação apropriadas.
3. Token de acesso e ID da conta profissional guardados como GitHub Actions Secrets (nunca no CSV, HTML ou código).
4. Imagens públicas HTTPS dos produtos. A API de publicação do Instagram exige mídia; o catálogo atual contém apenas nome, preços e link, portanto não inventaremos fotos.
5. Aprovação/revisão de permissões da Meta quando exigida.

Feed e Stories podem ser publicados pela API em contas elegíveis. A automação de seguir/deixar de seguir perfis em massa não será implementada: é comportamento de spam e pode causar restrições. O crescimento será por conteúdo e chamadas claras para o Telegram.

## WhatsApp
A Cloud API oficial envia mensagens para números que deram consentimento (opt-in), com regras de janela de atendimento e modelos aprovados quando aplicável. Ela **não publica em grupos comuns** como o bot do Telegram. Para o grupo atual, use publicação manual ou uma solução oficial compatível com grupos, se disponível para a conta e aprovada pela Meta; não usaremos automação não oficial de WhatsApp Web.

## Horários planejados
09:00, 12:00, 15:00 e 18:00 — America/Sao_Paulo (cron UTC correspondente: 12, 15, 18, 21). Os lotes seguem 8, 8, 7 e 7 produtos, com intervalo de 5 minutos no Telegram. Os canais novos só serão ativados após credenciais, imagens e destinatários consentidos estarem prontos.

## Segurança e ativação
- Não cole tokens ou senhas no chat, no painel ou em arquivos versionados.
- Guardar credenciais em GitHub Settings → Secrets and variables → Actions.
- Começar com modo de teste/prévia e uma publicação de teste autorizada.
- Não ativar publicação em produção antes da validação da conta, mídia e permissões.

## Teste local/CI
```bash
SLOT_UTC="0 12 * * *" python planejador_canais.py
```
O script apenas imprime a prévia do lote; não envia mensagens.
