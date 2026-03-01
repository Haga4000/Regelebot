# Regelebot

AI-powered conversational agent for a WhatsApp cinema club. Supports multiple LLM providers (**Gemini**, **Mistral**, **OpenAI**, **Claude**, **Ollama**) — switch via a single env var. It acts as a knowledgeable film buddy that chats naturally in French, recommends movies based on the group's taste, tracks watch history, and runs polls with native WhatsApp integration.

## Features

- **Natural conversation** — mention `@Regelebot` and chat about movies like you would with a friend
- **Smart recommendations** — personalized suggestions by genre, mood, or similarity to a reference film
- **Movie discovery** — natural-language catalog browsing with combinable filters (genre, year, platform, rating, language)
- **Trending movies** — what's hot right now (daily or weekly)
- **Film info** — synopsis, cast, ratings, streaming platforms via TMDb
- **Watch tracking** — log watched movies and rate them (1-5 stars)
- **Club statistics** — total movies watched, average ratings, top genres
- **Native WhatsApp polls** — create polls with `/sondage`, vote by tapping the native poll or via `/vote`
- **Bidirectional poll sync** — native WhatsApp poll taps and `/vote` text commands both count in `/resultats`
- **Slash commands** — quick actions without going through the LLM
- **Multi-provider LLM** — swap between Gemini, Mistral, OpenAI, Claude, or Ollama with env vars

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Bot Core | Python 3.13 / FastAPI |
| LLM | Multi-provider: Gemini, Mistral, OpenAI, Anthropic, Ollama |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 (async) |
| WhatsApp | whatsapp-web.js (Node.js gateway) |
| Film Data | TMDb API |
| Infra | Docker Compose |

## LLM Providers

| Provider | Default Model | SDK | Notes |
|----------|--------------|-----|-------|
| `gemini` | `gemini-2.5-flash-lite` | `google-genai` | Default provider |
| `mistral` | `mistral-small-latest` | `mistralai` | |
| `openai` | `gpt-4o-mini` | `openai` | |
| `anthropic` | `claude-sonnet-4-5-20250929` | `anthropic` | |
| Ollama | (set `LLM_MODEL`) | `openai` | Use `openai` provider + `LLM_BASE_URL` |

Only the selected provider's SDK needs to be installed. The factory uses lazy imports.

### Switching providers

```bash
# Mistral
LLM_PROVIDER=mistral
LLM_API_KEY=your_mistral_key

# OpenAI
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_key

# Anthropic (Claude)
LLM_PROVIDER=anthropic
LLM_API_KEY=your_anthropic_key

# Ollama (local)
LLM_PROVIDER=openai
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=ministral-8b
```

## Security

- **Webhook authentication** — all `/webhook/*` endpoints require `X-Webhook-Secret` header
- **Rate limiting** — 10 requests/minute per group (sliding window) to prevent abuse
- **Token budget** — conversation history auto-trimmed to 4000 tokens to control LLM costs
- **CORS** — restricted to internal Docker network
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, etc.
- **Internal bot service** — bot port not exposed externally, only accessible via gateway

## Prerequisites

- Docker & Docker Compose
- An API key for your chosen LLM provider (e.g. [Gemini](https://aistudio.google.com/apikey), [Mistral](https://console.mistral.ai/), [OpenAI](https://platform.openai.com/api-keys), [Anthropic](https://console.anthropic.com/))
- A TMDb API key ([sign up here](https://www.themoviedb.org/signup))
- A WhatsApp account to link the bot

## Quick Start

1. **Clone and configure**
   ```bash
   cp .env.example .env
   # Edit .env: set LLM_PROVIDER, LLM_API_KEY, TMDB_API_KEY, DB_PASSWORD, WEBHOOK_SECRET
   ```

2. **Start the stack**
   ```bash
   docker compose up --build
   ```

3. **Run database migrations**
   ```bash
   docker compose exec bot alembic upgrade head
   ```

4. **Link WhatsApp**
   - A QR code appears in the gateway logs
   - Scan it with your phone: WhatsApp > Linked Devices > Link a Device

5. **Get your chat IDs**
   - Send a message in each WhatsApp chat you want the bot to monitor (group or 1-to-1)
   - The gateway logs each chat ID (groups: `XXXXX@g.us`, 1-to-1: `XXXXX@c.us`)
   - Add them to `.env` as `WHATSAPP_CHAT_IDS=id1,id2` (comma-separated)
   - In 1-to-1 chats, every message is sent to the bot (no `@mention` needed)
   - Restart: `docker compose restart gateway`

## Usage

### Conversational (via LLM)

Mention `@Regelebot` in the group to chat:

```
@Regelebot un thriller comme Seven mais en francais
@Regelebot c'est quoi le film avec DiCaprio dans les reves ?
@Regelebot on veut un truc feel-good pour ce soir
@Regelebot un bon thriller sur Netflix sorti apres 2020
@Regelebot les meilleurs films des annees 80
@Regelebot quoi de chaud en ce moment ?
@Regelebot un film coreen bien note
@Regelebot pourquoi Tarantino filme autant les pieds ?
```

The bot uses a ReAct loop with function calling to search films, check the club's history, and generate contextual recommendations.

### Slash Commands (direct, no LLM)

| Command | Description |
|---------|------------|
| `/film [title]` | Quick film info (director, cast, synopsis) |
| `/vu [film]` | Mark a movie as watched by the club |
| `/noter [film] [1-5]` | Rate a movie |
| `/historique` | Last 10 watched movies with ratings |
| `/stats` | Club statistics (total films, avg rating, top genres) |
| `/sondage Question ? \| A \| B \| C` | Create a native WhatsApp poll |
| `/vote [number]` | Vote on the active poll via text |
| `/resultats` | Show poll results (native + text votes combined) |
| `/aide` | List available commands |

### Poll System

Polls support two ways to vote:
- **Native WhatsApp tap** — tap an option on the poll message, synced to DB automatically
- **Text command** — type `/vote 2` to vote for option 2

Both methods are reflected in `/resultats`.

## Architecture

```
WhatsApp Group
      |
      v
+-----------+     HTTP POST     +------------+
|  Gateway  | ----------------> |  Bot API   |
|  (Node.js)| X-Webhook-Secret  |  (FastAPI) |
|  Port 3000| <---------------- |  internal  |
+-----------+     JSON reply    +-----+------+
      |                               |
      |  vote_update -----> /webhook/poll-vote
      |  poll sent -------> /webhook/poll-created
      |                               |
      |                        +------v-------+
      |                        | MessageRouter|
      |                        +------+-------+
      |                               |
      |                  +------------+------------+
      |                  v                         v
      |         /command route              @mention route
      |                  |                         |
      |                  v                         v
      |        CommandHandlers             MainAgent (LLM)
      |           (no LLM)                    ReAct loop
      |                                           |
      |                          +--------+-------+-------+--------+
      |                          v        v               v        v
      |                     MovieAgent RecoAgent     StatsAgent PollAgent
      |                        |         |               |        |
      |                     TMDb API  TMDb+LLM       PostgreSQL  PostgreSQL
```

### Multi-Agent Design

| Agent | Purpose | Data Source |
|-------|---------|-------------|
| **MainAgent** | Orchestrator, understands intent, generates responses | LLM (any provider) |
| **MovieAgent** | Film search, discovery & trending | TMDb API |
| **RecommendationAgent** | Smart suggestions (genre, mood, similar) | TMDb API + LLM |
| **StatsAgent** | Club history, ratings, analytics | PostgreSQL |
| **PollAgent** | Polls, voting, results | PostgreSQL |

### LLM Abstraction Layer

```
bot/src/llm/
├── __init__.py              # Factory create_llm_provider() + re-exports
├── base.py                  # Abstract LLMProvider class
├── types.py                 # ChatMessage, ToolCall, ToolDefinition, LLMResponse
└── providers/
    ├── gemini.py            # Google Gemini (role alternation, function_response)
    ├── mistral.py           # Mistral API (OpenAI-like format)
    ├── openai.py            # OpenAI + Ollama (via base_url)
    └── anthropic.py         # Claude (system param, input_schema, tool_result blocks)
```

Each provider translates the generic `ChatMessage`/`ToolDefinition` types to its native API format. The factory reads `LLM_PROVIDER` from config and lazy-imports only the selected SDK.

### Database Schema

```
members ----+
            |--- ratings (member_id, watchlist_id, score, comment)
movies -----+
            |--- watchlist (movie_id, suggested_by, watched_at)
            |
            |--- polls (question, options[JSONB], wa_message_id, is_closed)
            +--- poll_votes (poll_id, member_id, option_id)
```

## Development

### Run locally (without Docker)

```bash
# Bot (Python)
cd bot
pip install -r requirements.txt
PYTHONPATH=src uvicorn main:app --reload --port 8000

# Gateway (Node.js)
cd gateway
npm install
node src/index.js
```

### Database migrations

```bash
# Apply pending migrations
docker compose exec bot alembic upgrade head

# Create a new migration after model changes
docker compose exec bot alembic revision --autogenerate -m "description"
```

### Run tests

```bash
cd bot
PYTHONPATH=src \
  LLM_API_KEY=test TMDB_API_KEY=test \
  DATABASE_URL=sqlite+aiosqlite:///test.db \
  WEBHOOK_SECRET=test \
  python3 -m pytest tests/ -v
```

### Rebuild after code changes

```bash
docker compose build bot gateway && docker compose up -d
```

## Project Structure

```
regelebot/
├── bot/                        # Python bot core
│   ├── src/
│   │   ├── main.py             # FastAPI app + startup (auto-migration)
│   │   ├── config.py           # Pydantic settings (LLM_PROVIDER, etc.)
│   │   ├── agents/
│   │   │   ├── base.py         # BaseSubAgent abstract class
│   │   │   ├── main_agent.py   # LLM orchestrator (ReAct loop)
│   │   │   └── subagents/      # Movie, Stats, Recommendation, Poll
│   │   ├── constants/          # Shared constants (TMDb genre/provider maps)
│   │   ├── llm/                # Multi-provider LLM abstraction
│   │   │   ├── __init__.py     # Factory + re-exports
│   │   │   ├── base.py         # Abstract LLMProvider
│   │   │   ├── types.py        # ChatMessage, ToolCall, LLMResponse
│   │   │   └── providers/      # gemini, mistral, openai, anthropic
│   │   ├── commands/           # Slash command handlers (no LLM)
│   │   ├── api/
│   │   │   ├── webhook.py      # /webhook/message, /poll-created, /poll-vote
│   │   │   ├── health.py       # GET /health
│   │   │   └── dependencies.py # Auth dependency (webhook secret verification)
│   │   ├── models/             # SQLAlchemy models (Member, Movie, Poll, etc.)
│   │   ├── prompts/            # System prompt with personality & context
│   │   ├── tools/              # Function calling definitions (JSON Schema)
│   │   └── core/               # MessageRouter, DB, rate_limiter, token_budget
│   ├── tests/                  # pytest test suite
│   └── alembic/                # Database migrations
├── gateway/                    # Node.js WhatsApp gateway
│   └── src/index.js            # Message listener, poll sync, vote_update
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/webhook/message` | `X-Webhook-Secret` | Incoming WhatsApp messages (commands + mentions) |
| `POST` | `/webhook/poll-created` | `X-Webhook-Secret` | Link a DB poll to its WhatsApp message ID |
| `POST` | `/webhook/poll-vote` | `X-Webhook-Secret` | Record a native WhatsApp poll vote |
| `GET` | `/health` | None | Bot health check (port 8000) |
| `GET` | `/health` | None | Gateway health check (port 3000) |

## License

Private project.
