# InstaRepost

Sistema modular para **monitorar um perfil autorizado do Instagram, detectar novos Reels,
baixar o conteúdo autorizado, gerar uma legenda original com IA local (Ollama) e preparar
a publicação na sua própria conta** — com painel de aprovação humana e publicação via API
oficial da Meta.

Construído com Clean Architecture, SOLID e foco em produção: configuração por ambiente,
logging estruturado, testes e camadas desacopladas e substituíveis.

---

## ⚠️ Aviso importante de compliance (leia antes)

O requisito "monitorar um perfil e baixar Reels" entra em conflito direto com "usar apenas
APIs oficiais". A realidade técnica:

| Operação | API oficial da Meta? |
|---|---|
| Baixar o arquivo de Reels de **outro** perfil | ❌ Não existe caminho oficial |
| Ler metadados públicos de outro perfil (Business Discovery) | ⚠️ Parcial, sem o arquivo de vídeo |
| **Publicar** Reels na **sua** conta (Content Publishing API) | ✅ Sim (conta Professional + App Meta) |

Por isso a **ingestão é uma camada plugável** (`SourceProvider`):

- **`manual`** (default, **ToS-safe**): você/o dono coloca os vídeos autorizados numa pasta.
- **`instaloader`** (opt-in, **NÃO-oficial**): baixa de um perfil público via engenharia
  reversa. **Pode violar os Termos da Meta** — use somente para conteúdo que você está
  **expressamente autorizado** a redistribuir, assumindo o risco.

O **núcleo** (IA, aprovação, publicação oficial, banco, logs) é independente da origem.

---

## Arquitetura

```
project/
├── app/
│   ├── config/        # settings (pydantic) + estilos de legenda (YAML)
│   ├── models/        # SQLAlchemy 2.0: Profile, Video, Caption, Job
│   ├── repositories/  # acesso a dados isolado (Repository pattern)
│   ├── services/      # regras de negócio: monitor, download, caption, publish, pipeline
│   ├── sources/       # ingestão plugável (manual | instaloader)  <- ponto de extensão
│   ├── ai/            # gerador de legendas (Ollama) atrás de interface
│   ├── publishers/    # dry_run | instagram_graph (oficial)       <- ponto de extensão
│   ├── schedulers/    # APScheduler (ingestão periódica)
│   ├── web/           # painel de aprovação (FastAPI + HTML)
│   ├── utils/         # logging, validadores/sanitização
│   └── db.py          # engine, sessões, init
├── data/ downloads/ logs/ database/
├── tests/             # unitários + integração (IA e banco mockados)
├── cli.py             # entrypoint único
├── requirements.txt   .env.example   pytest.ini   README.md
```

**Princípios aplicados:**
- *Dependency Inversion*: serviços dependem de interfaces (`SourceProvider`, `CaptionGenerator`,
  `Publisher`), não de implementações.
- *Open/Closed*: trocar origem, IA ou publicador = adicionar uma classe + uma linha na fábrica.
- *Single Responsibility*: cada serviço faz uma coisa; o `PipelineService` apenas orquestra.
- *Fail-safe por padrão*: `PUBLISHER=dry_run` e `REQUIRE_MANUAL_APPROVAL=true` não publicam nada
  sem ação humana explícita.

### Fluxo

```
SourceProvider → MonitorService (dedup) → DownloadService (valida) →
CaptionService (IA local) → [Painel: aprovação humana] → PublishService → Publisher
                                  ▲ tudo registrado em Jobs + logs
```

---

## Banco de dados

SQLAlchemy 2.0 (SQLite por padrão; troque para Postgres só mudando `DATABASE_URL`).

- **profiles** — `id, username (unique, idx), active, created_at`
- **videos** — `id, profile_id (fk, idx), source_post_id (idx), source_url, local_file,
  size_bytes, source_caption, processed (idx), published (idx), created_at`
  · `UNIQUE(profile_id, source_post_id)` garante a deduplicação no nível do banco.
- **captions** — `id, video_id (fk, idx), generated_caption, style, model, approved (idx), created_at`
- **jobs** — `id, kind, status (idx), started_at, finished_at, logs, created_at`

---

## Instalação

```bash
cd InstaRepost
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # ajuste as variáveis
python cli.py init          # cria diretórios + schema
```

### IA local (Ollama)

```bash
# instale o Ollama (https://ollama.com) e baixe um modelo:
ollama pull llama3.2:3b      # ou: qwen3, llama3, mistral
# ajuste OLLAMA_MODEL no .env de acordo
python cli.py health         # deve mostrar Banco: OK | IA local: OK
```

---

## Configuração (.env)

| Variável | Default | Descrição |
|---|---|---|
| `DATABASE_URL` | `sqlite:///database/instarepost.db` | Conexão do banco |
| `LOG_LEVEL` | `INFO` | DEBUG/INFO/WARNING/ERROR |
| `SOURCE_PROVIDER` | `manual` | `manual` (ToS-safe) ou `instaloader` (opt-in) |
| `TARGET_USERNAME` | `perfil_autorizado` | Perfil monitorado |
| `WATCH_DIR` | `data/inbox` | Pasta observada no modo manual |
| `MAX_VIDEO_MB` / `MIN_VIDEO_MB` | `300` / `0.05` | Limites de validação |
| `ALLOWED_EXTENSIONS` | `.mp4,.mov` | Extensões aceitas (CSV) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint do Ollama |
| `OLLAMA_MODEL` | `qwen3` | Modelo local |
| `DEFAULT_CAPTION_STYLE` | `viral` | `viral`/`informativo`/`profissional`/`entretenimento` |
| `REQUIRE_MANUAL_APPROVAL` | `true` | Exige aprovação no painel antes de publicar |
| `PUBLISHER` | `dry_run` | `dry_run` ou `instagram_graph` (oficial) |
| `IG_USER_ID` / `IG_ACCESS_TOKEN` | — | Credenciais da Graph API |
| `PUBLIC_MEDIA_BASE_URL` | — | URL pública onde a mídia fica acessível (exigida pela API) |
| `POLL_INTERVAL_SECONDS` | `900` | Intervalo do scheduler |
| `WEB_HOST` / `WEB_PORT` | `127.0.0.1` / `8000` | Painel |

Os **prompts da IA** ficam em `app/config/caption_styles.yaml` — edite/adicione estilos sem
tocar no código. Há regras globais anti-cópia aplicadas a todos os estilos.

---

## Uso

```bash
# Modo manual: coloque o conteúdo autorizado em data/inbox/
#   meu_reel.mp4            (o vídeo)
#   meu_reel.txt            (opcional: contexto/legenda original p/ a IA)

python cli.py ingest                 # monitora → baixa → valida → gera legenda
python cli.py web                    # painel de aprovação em http://127.0.0.1:8000
python cli.py publish                # publica os aprovados (respeita o PUBLISHER)
python cli.py scheduler              # roda em loop a cada POLL_INTERVAL_SECONDS
python cli.py health                 # checa banco + IA
```

### Painel de aprovação

`python cli.py web` abre uma interface onde você pode, por vídeo: assistir, **editar** a
legenda, **aprovar**, **rejeitar**, **reprocessar** (regenerar com outro estilo) e
**publicar os aprovados**. Só vídeos com legenda aprovada são publicados quando
`REQUIRE_MANUAL_APPROVAL=true`.

---

## Publicação oficial (Instagram Graph API)

Para `PUBLISHER=instagram_graph` você precisa de:

1. Conta Instagram **Professional** (Business/Creator) ligada a uma Página do Facebook.
2. App da Meta com `instagram_basic` + `instagram_content_publish`.
3. `IG_USER_ID` e `IG_ACCESS_TOKEN` (token de longa duração) no `.env`.
4. A mídia acessível por **URL pública** (`PUBLIC_MEDIA_BASE_URL`) — a API baixa o vídeo
   a partir dessa URL; ela não aceita upload binário direto.

Fluxo implementado: cria container de REELS → aguarda processamento → `media_publish`.

---

## Testes

```bash
pytest                # 10 testes: repositórios, legendas (IA mockada),
                      # download/validação e pipeline ponta-a-ponta
```

Banco roda em SQLite **em memória** e a IA é substituída por um `FakeCaptionGenerator` —
nenhum teste depende de Ollama, rede ou Instagram.

---

## Deploy

- **Processo de ingestão:** rode `python cli.py scheduler` sob `systemd` ou `supervisor`.
- **Painel:** `uvicorn app.web.api:app` atrás de um reverse proxy (Nginx) com TLS.
- **Banco:** troque `DATABASE_URL` para Postgres em produção.
- **Mídia pública** (se publicar via API oficial): sirva `downloads/` por uma URL HTTPS e
  aponte `PUBLIC_MEDIA_BASE_URL` para ela.
- **Segredos:** nunca versione `.env`; use o gestor de segredos do seu ambiente.

Exemplo de unit `systemd`:

```ini
[Unit]
Description=InstaRepost scheduler
After=network.target

[Service]
WorkingDirectory=/opt/InstaRepost
ExecStart=/opt/InstaRepost/venv/bin/python cli.py scheduler
Restart=on-failure
EnvironmentFile=/opt/InstaRepost/.env

[Install]
WantedBy=multi-user.target
```

---

## Decisões técnicas (resumo)

- **Ingestão plugável** — resolve o conflito ToS vs. requisito mantendo o núcleo limpo.
- **IA atrás de interface** — Ollama hoje; trocar de backend não toca nos serviços.
- **`dry_run` + aprovação manual como default** — nada é publicado por acidente.
- **Jobs auditáveis + logging em arquivo/console** — rastreabilidade ponta a ponta.
- **Repository pattern** — serviços testáveis sem banco real.
- **Sanitização de legenda** — remove cercas markdown e blocos `<think>` de modelos.

## Roadmap

- Coluna dedicada de status/erro por vídeo e retry com backoff.
- Múltiplos perfis simultâneos (o schema já suporta; falta o agendamento por perfil).
- Métricas (Prometheus) e fila (Celery/RQ) para escala horizontal.
```
