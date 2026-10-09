# Segurança

## Reportar uma vulnerabilidade
**Não abra uma issue pública** para falhas de segurança, como vazamento de token, execução
de código pelo painel ou acesso indevido a sessões.

Use o [aviso privado de vulnerabilidade do GitHub](../../security/advisories/new). Descreva:
- o que acontece e como reproduzir;
- qual versão ou commit;
- o impacto que você imagina.

Você recebe uma resposta assim que possível. A correção é publicada antes de qualquer
divulgação.

## Cuidados para quem usa
- O `.env` guarda tokens da Meta e senhas: **nunca** versione nem compartilhe.
- Os arquivos `*.session` valem como login da conta. Trate como senha.
- O painel web escuta em `127.0.0.1` por padrão. Não exponha para a internet sem autenticação;
  o túnel serve só a rota `/media`, para a Meta baixar o vídeo.
- Para a ingestão não-oficial, use uma conta **descartável**, nunca a principal.
