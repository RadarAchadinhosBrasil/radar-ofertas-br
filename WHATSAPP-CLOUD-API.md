# WhatsApp Cloud API — integração segura do Radar

## Objetivo e limites
Esta integração prepara o envio de ofertas **no privado, para um único destinatário de teste por execução**. Não envia para grupos do WhatsApp. Não usa WhatsApp Web nem bibliotecas não oficiais.

O número principal não deve ser migrado, desconectado ou registrado em outro lugar durante esta preparação. A coexistência (app WhatsApp Business + Cloud API) precisa ser oferecida no fluxo oficial de Embedded Signup para esta conta. A elegibilidade só fica confirmada quando a Meta/um parceiro oficial apresenta e conclui esse fluxo para o número.

## O que já está no repositório
- `whatsapp_cloud.py`: prévia por padrão; envio somente com `--send` e confirmações explícitas.
- Workflow manual: um teste individual, sem agendamento e sem listas de contatos.
- Nenhuma credencial ou número pessoal deve ser colocado no repositório.

## Etapas que dependem da conta Meta
1. No Meta Business Suite/Business Manager, abrir a área de WhatsApp e iniciar a configuração da WhatsApp Business Platform pelo fluxo oficial.
2. Verificar se a opção de coexistência está disponível para o número do WhatsApp Business que já usamos. **Não apagar a conta do app, não desinstalar o app e não concluir migração padrão que peça para remover o número do aplicativo.** Se a tela não oferecer coexistência, parar e não avançar com esse número.
3. Obter o Phone Number ID, um token com permissão `whatsapp_business_messaging` e a versão Graph API disponibilizada para a conta.
4. Criar e submeter para aprovação um template de categoria Marketing, em português (Brasil), com exatamente três variáveis no corpo:
   ```
   🔥 {{1}}
   💰 Por: {{2}}
   🛒 Ver oferta: {{3}}
   ⚠️ Preço e disponibilidade podem mudar. Confira no anúncio.
   ```
   Nome sugerido: `radar_oferta_teste`. O nome final configurado na Meta deve ser igual ao secret `WA_TEMPLATE_NAME`.
5. Guardar os dados somente em GitHub → Settings → Secrets and variables → Actions:
   - Secrets: `WA_ACCESS_TOKEN`, `WA_PHONE_NUMBER_ID`, `WA_TEST_RECIPIENT`.
   - Variables: `WA_GRAPH_API_VERSION`, `WA_TEMPLATE_NAME`, `WA_TEMPLATE_LANGUAGE` (opcional; padrão `pt_BR`).
   - Para o teste, o workflow exige ainda `WA_TEST_RECIPIENT_OPT_IN=SIM` e `WA_CONFIRM_SEND=SIM`. Configure ambos como secrets apenas na hora do teste.
6. O destinatário de teste deve ser um número controlado por nós ou de alguém que tenha autorizado expressamente receber a mensagem. O opt-in deve ser registrado fora do repositório.

## Como testar
- Execute o workflow **WhatsApp — teste individual (manual)** com `confirmar_envio=false` para validar a prévia.
- Só depois de concluir a coexistência, ter token/ID, template aprovado e opt-in, execute com `confirmar_envio=true`.
- O workflow envia no máximo uma mensagem por execução. Não existe cron, disparo em massa ou publicação em grupo.
- A Meta exige template aprovado para iniciar conversas e fora da janela de atendimento de 24 horas. Mensagens de marketing têm cobrança e limites/controles de qualidade aplicáveis.

## Segurança
- Nunca cole tokens no chat, CSV, código, logs ou painel.
- Não envie mensagens para contatos sem opt-in.
- Não ativar campanhas ou agendamento antes de testar e revisar custos, qualidade e conformidade.
- A coexistência não habilita o acesso aos grupos comuns do WhatsApp pela Cloud API.
