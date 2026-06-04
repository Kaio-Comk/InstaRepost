# InstaRepost

Sistema modular que **descobre Reels de um perfil autorizado, baixa, gera uma legenda
original com IA local (Ollama) e publica automaticamente na sua própria conta** —
24/7, com renovação automática de token e cadência controlada.

Construído com Clean Architecture, SOLID e foco em produção: configuração por ambiente,
logging estruturado, testes e camadas desacopladas e substituíveis.

---

## ⚠️ Aviso de compliance (leia antes)

O sistema combina **dois caminhos** com níveis de risco diferentes:

| Etapa | Como é feito | Oficial? | Risco |
|---|---|---|---|
| **Descoberta + download** dos Reels de outro perfil | `instagrapi` / `instaloader` (API privada, conta logada) | ❌ Não-oficial | Pode violar o ToS da Meta; a conta usada pode ser **limitada/banida** |
| **Publicação** na sua conta | Instagram Content Publishing API (login por Instagram) | ✅ Oficial | Estável; respeita políticas da Meta |

A ingestão de conteúdo de terceiros, mesmo "autorizado", é **responsabilidade sua** perante
a Meta e o autor original. Use uma conta **descartável** para a descoberta/download, nunca a
conta principal. O núcleo (IA, publicação oficial, token, banco) é independente da ingestão.

---

## Fluxo final (24/7, totalmente automático)

```
┌─ a cada POLL_INTERVAL_SECONDS ─────────────────────────────────────────┐
│ 1. Descoberta: busca Reels novos do TARGET_USERNAME (instagrapi)        │
│    e enche data/queue.txt — sem repetir (dedup contra fila/done/banco)  │
│ 2. Pega 1 URL da fila → baixa o vídeo (instaloader) → valida            │
│ 3. IA local (Ollama) gera legenda original:                            │
│      • começa com o TÍTULO do filme/série                              │
│      • inclui "link para assistir na bio"                              │
│      • sem aspas, com hashtags                                         │
│ 4. Publica 1 vídeo via Graph API oficial (trava de intervalo mínimo    │
│    evita rajada ao reiniciar)                                          │
│ 5. Renova o token automaticamente quando falta < 10 dias               │
└────────────────────────────────────────────────────────────────────────┘
```

A **descoberta não é mágica**: ela depende da conta logada conseguir listar o feed do alvo
(API privada). Se a conta cair, a fila para de encher — mas você pode alimentar
`data/queue.txt` manualmente a qualquer momento.

---

## 📊 Quantos posts por dia? (cadência segura)

| Nível | Reels/dia | Intervalo (`POLL_INTERVAL_SECONDS`) |
|---|---|---|
| **Limite técnico da API** | 100/24h | — (recusa acima disso) |
| ✅ **Seguro (recomendado)** | 3–6 | `14400` (4h) a `28800` (8h) |
| ⚠️ Agressivo | 7–10 | `8640` (2.4h) a `12342` (3.4h) |
| 🚫 Arriscado (spam/queda de alcance) | 12+ | < `7200` (2h) |

**Importante:** o limite que importa não é o da API (100) e sim a **saúde da conta**. Postar
demais faz o algoritmo reduzir seu alcance e pode marcar a conta como spam — sobretudo em
contas novas. Comece conservador (4–6/dia) e suba aos poucos observando o alcance.

---

## Arquitetura

```
project/
├── app/
│   ├── config/        # settings (pydantic) + estilos de legenda (YAML)
│   ├── models/        # SQLAlchemy 2.0: Profile, Video, Caption, Job
│   ├── repositories/  # acesso a dados isolado
│   ├── services/      # monitor, download, caption, publish, pipeline
│   ├── sources/       # ingestão: manual | instaloader | discovery (instagrapi)
│   ├── ai/            # gerador de legendas (Ollama) atrás de interface
│   ├── publishers/    # dry_run | instagram_graph (oficial) | instagrapi + token_store
│   ├── schedulers/    # loop 24/7 (1 post/ciclo, fila, trava de intervalo)
│   ├── web/           # painel FastAPI + rota /media (servida ao túnel)
│   └── utils/         # logging, validação/sanitização (remove aspas)
├── tools/             # helpers de setup (token, sessões de login)
├── deploy/            # instarepost.service (systemd)
├── iniciar_auto.sh    # launcher 24/7 (painel + túnel + scheduler)
├── iniciar_painel.sh  # só o painel de aprovação
├── cli.py  requirements.txt  .env.example  pytest.ini
```

**Substituíveis por interface:** `SourceProvider`, `CaptionGenerator`, `Publisher`.

---

## Instalação

```bash
cd InstaRepost
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # ajuste as variáveis
python cli.py init          # cria diretórios + schema

# IA local:
ollama pull llama3.2:3b      # ou qwen3 / mistral; ajuste OLLAMA_MODEL no .env
python cli.py health
```

---

## Configuração da publicação OFICIAL (uma vez)

1. **@suaconta** convertida para **Professional** (Business/Creator).
2. App em developers.facebook.com → **Create App** → use case **Other** → tipo **Business**.
3. No app: produto **Instagram → "API setup with Instagram business login"**.
4. Em **App roles → Papéis → Instagram Testers**, adicione sua conta e **aceite o convite**
   no app (Configurações → Apps e sites → Convites de testador).
5. **Generate token** ao lado da conta → copie o token (já dura 60 dias).
6. Gere as linhas do `.env`:
   ```bash
   ./venv/bin/python tools/ig_instagram_setup.py --token TOKEN_DO_PAINEL
   ```
   Cole `IG_API_BASE`, `IG_USER_ID`, `IG_ACCESS_TOKEN` no `.env` e `PUBLISHER=instagram_graph`.

### Mídia pública (túnel Cloudflare)
A API oficial **baixa o vídeo de uma URL pública**. O `iniciar_auto.sh` sobe o túnel e
preenche `PUBLIC_MEDIA_BASE_URL` automaticamente. Manual:
```bash
cloudflared tunnel --url http://localhost:8021
# PUBLIC_MEDIA_BASE_URL=https://<sub>.trycloudflare.com/media
```

### Token: renovação automática
O token é gerenciado em `data/ig_token.json` (semeado do `.env`) e **renovado sozinho**
(`ig_refresh_token`) quando faltam < 10 dias. Para trocar manualmente: atualize o `.env`
**e** apague `data/ig_token.json`.
```bash
./venv/bin/python cli.py token            # status (dias restantes)
./venv/bin/python cli.py token --refresh  # força a renovação
```

---

## Configuração da descoberta/download (não-oficial)

```bash
# .env:
SOURCE_PROVIDER=instaloader
TARGET_USERNAME=perfil_alvo
INSTALOADER_USER=conta_descartavel
INSTALOADER_PASSWORD=...        # usado pelo instagrapi (descoberta)
AUTO_DISCOVERY=true

# Sessão do instaloader (download) a partir do Firefox logado na conta descartável:
./venv/bin/python tools/import_firefox_session.py conta_descartavel
```
A descoberta (instagrapi) salva sua própria sessão em `data/discovery_session.json`.

---

## Rodar 24/7

### Serviço systemd (recomendado — sobrevive a reboot)
```bash
cp deploy/instarepost.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now instarepost.service
loginctl enable-linger "$USER"     # roda mesmo sem login
```
> Edite os caminhos no `.service` e no `iniciar_auto.sh` se o projeto não estiver em
> `/home/kaio/Área de trabalho/InstaRepost`.

### Ou manual
```bash
./iniciar_auto.sh     # painel + túnel + scheduler em um terminal
```

### Gerenciar
```bash
systemctl --user status instarepost     # estado
systemctl --user stop instarepost        # PAUSAR (para de postar)
systemctl --user start instarepost       # retomar
tail -f logs/instarepost.log             # acompanhar
```

---

## Uso manual (sem o loop)

```bash
python cli.py fetch <url_reel> [url...]   # baixa Reels específicos e processa
python cli.py publish                     # publica os pendentes/aprovados
python cli.py web                         # painel de aprovação (http://127.0.0.1:8000)
python cli.py token                       # status do token
```

Alimentar a fila do scheduler: cole URLs (1 por linha) em `data/queue.txt`.

---

## Variáveis de ambiente (principais)

| Variável | Padrão | Descrição |
|---|---|---|
| `SOURCE_PROVIDER` | `manual` | `manual` / `instaloader` |
| `TARGET_USERNAME` | — | Perfil de origem |
| `AUTO_DISCOVERY` | `false` | Enche a fila sozinho via instagrapi |
| `DISCOVERY_AMOUNT` | `8` | Quantos Reels buscar por ciclo |
| `INSTALOADER_USER/PASSWORD` | — | Conta descartável (descoberta/download) |
| `OLLAMA_MODEL` | `qwen3` | Modelo local de legenda |
| `REQUIRE_MANUAL_APPROVAL` | `true` | `false` = publica sozinho |
| `PUBLISHER` | `dry_run` | `dry_run` / `instagram_graph` / `instagrapi` |
| `IG_API_BASE` | `https://graph.instagram.com/v25.0` | Base da API oficial |
| `IG_USER_ID` / `IG_ACCESS_TOKEN` | — | Credenciais (helper gera) |
| `PUBLIC_MEDIA_BASE_URL` | — | URL pública (túnel) p/ `/media` |
| `POLL_INTERVAL_SECONDS` | `900` | Intervalo entre posts (ver cadência segura) |
| `URL_QUEUE_FILE` | `data/queue.txt` | Fila de URLs |

---

## Testes

```bash
pytest      # banco em memória + IA mockada; não depende de Ollama/rede/Instagram
```

---

## Riscos e manutenção

- **Conta de descoberta** pode ser limitada/banida pela Meta → a fila para de encher
  (aparece erro no log). A publicação oficial segue funcionando se você alimentar a fila.
- **Sem revisão humana** (`REQUIRE_MANUAL_APPROVAL=false`): reposta tudo do alvo. Para algo
  específico, use `systemctl --user stop instarepost` ou `REQUIRE_MANUAL_APPROVAL=true`.
- **Cadência:** não exagere (ver tabela). Conta nova = comece com 4–6/dia.
- **Túnel Cloudflare** (quick tunnel) muda de URL a cada start — o `iniciar_auto.sh`
  resolve sozinho. Para URL fixa, configure um túnel nomeado do Cloudflare.
- **Token** renova sozinho; só falha se ficar > 60 dias sem o serviço rodar.
