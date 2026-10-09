# Como contribuir

Obrigado por querer melhorar o InstaRepost! Toda ajuda é bem-vinda: correção de bug,
melhoria de documentação, novos adaptadores, testes.

## Antes de começar
- Procure nas [issues](../../issues) se o assunto já está sendo discutido.
- Para mudanças grandes (um adaptador novo, mudança de arquitetura), abra uma issue
  primeiro e explique a ideia. Assim ninguém perde tempo com algo que não vai entrar.
- Leia o **aviso de compliance** do [README](README.md). Contribuições precisam manter os
  padrões seguros: `PUBLISHER=dry_run`, `SOURCE_PROVIDER=manual` e
  `REQUIRE_MANUAL_APPROVAL=true`.

## Ambiente de desenvolvimento
```bash
git clone https://github.com/Kaio-Comk/InstaRepost.git
cd InstaRepost
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # os padrões já são seguros para desenvolver
```

## Testes
```bash
python -m pytest -q
```
Todo pull request precisa deixar a suíte passando. Código novo vem com teste.

## Arquitetura (onde cada coisa entra)
O projeto segue Clean Architecture, com camadas substituíveis:

| pasta | papel |
|---|---|
| `app/sources/` | de onde vêm os vídeos (`SourceProvider`) |
| `app/publishers/` | para onde vão (`Publisher`) |
| `app/ai/` | geração de legenda |
| `app/services/` | regras do fluxo (download, legenda, publicação, pipeline) |
| `app/repositories/` | acesso ao banco |
| `app/web/` | painel de aprovação (FastAPI) |

Um adaptador novo implementa a interface em `base.py` da sua pasta e entra por configuração,
sem mudar os serviços.

## Pull requests
1. Faça um fork e crie um branch a partir de `main` (`feat/minha-ideia`, `fix/o-bug`).
2. Commits pequenos e com mensagem clara. Usamos o estilo `feat: …`, `fix: …`, `docs: …`.
3. Descreva **o que** mudou e **por quê**, e como você testou.
4. **Nunca** inclua `.env`, sessões (`*.session`), tokens, vídeos baixados ou bancos.

## Licença
Ao contribuir, você concorda que sua contribuição será distribuída sob a
[GPL-3.0](LICENSE), a mesma licença do projeto.
