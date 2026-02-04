# Regelebot

AI-powered conversational agent for a WhatsApp cinema club. Powered by **Gemini**, it acts as a knowledgeable film buddy that chats naturally in French, recommends movies based on the group's taste, tracks watch history, and runs polls with native WhatsApp integration.

## Features

- **Natural conversation** — mention `@Regelebot` and chat about movies like you would with a friend
- **Smart recommendations** — personalized suggestions by genre, mood, or similarity to a reference film
- **Film info** — synopsis, cast, ratings, streaming platforms via TMDb
- **Watch tracking** — log watched movies and rate them (1-5 stars)
- **Club statistics** — total movies watched, average ratings, top genres
- **Native WhatsApp polls** — create polls with `/sondage`, vote by tapping the native poll or via `/vote`
- **Bidirectional poll sync** — native WhatsApp poll taps and `/vote` text commands both count in `/resultats`
- **Slash commands** — quick actions without going through the LLM

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Bot Core | Python 3.11 / FastAPI |
| LLM | Gemini (via google-generativeai) |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 (async) |
| WhatsApp | whatsapp-web.js (Node.js gateway) |
| Film Data | TMDb API |
| Infra | Docker Compose |

## Security

- **Webhook authentication** — all `/webhook/*` endpoints require `X-Webhook-Secret` header
- **Rate limiting** — 10 requests/minute per group (sliding window) to prevent abuse
- **Token budget** — conversation history auto-trimmed to 4000 tokens to control LLM costs
- **CORS** — restricted to internal Docker network
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, etc.
- **Internal bot service** — bot port not exposed externally, only accessible via gateway

## Prerequisites

- Docker & Docker Compose
- A Google Gemini API key ([get one here](https://aistudio.google.com/apikey))
- A TMDb API key ([sign up here](https://www.themoviedb.org/signup))
- A WhatsApp account to link the bot

## Quick Start

1. **Clone and configure**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys, DB password, and a random WEBHOOK_SECRET
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

5. **Get your group ID**
   - Send any message in your WhatsApp group
   - The gateway logs the group ID (format: `XXXXXXXXXX@g.us`)
   - Add it to `.env` as `WHATSAPP_GROUP_ID`
   - Restart: `docker compose restart gateway`

## Usage

### Conversational (via LLM)

Mention `@Regelebot` in the group to chat:

```
@Regelebot un thriller comme Seven mais en francais
@Regelebot c'est quoi le film avec DiCaprio dans les reves ?
@Regelebot on veut un truc feel-good pour ce soir
@Regelebot pourquoi Tarantino filme autant les pieds ?
```

The bot uses a ReAct loop with Gemini function calling to search films, check the club's history, and generate contextual recommendations.

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
      |        CommandHandlers            MainAgent (Gemini)
      |           (no LLM)                    ReAct loop
      |                                           |
      |                          +--------+-------+-------+--------+
      |                          v        v               v        v
      |                     MovieAgent RecoAgent     StatsAgent PollAgent
      |                        |         |               |        |
      |                     TMDb API  TMDb+Gemini    PostgreSQL  PostgreSQL
```

### Multi-Agent Design

| Agent | Purpose | Data Source |
|-------|---------|-------------|
| **MainAgent** | Orchestrator, understands intent, generates responses | Gemini LLM |
| **MovieAgent** | Film search & metadata | TMDb API |
| **RecommendationAgent** | Smart suggestions (genre, mood, similar) | TMDb API + Gemini |
| **StatsAgent** | Club history, ratings, analytics | PostgreSQL |
| **PollAgent** | Polls, voting, results | PostgreSQL |

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
# In Docker (recommended)
docker build -t regelebot-test ./bot
docker run --rm \
  -e GEMINI_API_KEY=test -e TMDB_API_KEY=test \
  -e DATABASE_URL=sqlite+aiosqlite:///test.db \
  -e WEBHOOK_SECRET=test -e BOT_NAME=Regelebot \
  regelebot-test python -m pytest tests/ -v

# Locally
cd bot
pip install -r requirements.txt
GEMINI_API_KEY=test TMDB_API_KEY=test DATABASE_URL=sqlite+aiosqlite:///test.db \
  WEBHOOK_SECRET=test python -m pytest tests/ -v
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
│   │   ├── config.py           # Pydantic settings
│   │   ├── agents/
│   │   │   ├── base.py         # BaseSubAgent abstract class
│   │   │   ├── main_agent.py   # Gemini orchestrator (ReAct loop)
│   │   │   └── subagents/      # Movie, Stats, Recommendation, Poll
│   │   ├── commands/           # Slash command handlers (no LLM)
│   │   ├── api/
│   │   │   ├── webhook.py      # /webhook/message, /poll-created, /poll-vote
│   │   │   ├── health.py       # GET /health
│   │   │   └── dependencies.py # Auth dependency (webhook secret verification)
│   │   ├── models/             # SQLAlchemy models (Member, Movie, Poll, etc.)
│   │   ├── prompts/            # System prompt with personality & context
│   │   ├── tools/              # Gemini function calling definitions
│   │   └── core/               # MessageRouter, DB, rate_limiter, token_budget
│   ├── tests/                  # pytest test suite (27 tests)
│   └── alembic/                # Database migrations
├── gateway/                    # Node.js WhatsApp gateway
│   └── src/index.js            # Message listener, poll sync, vote_update
├── scripts/
│   └── seed.py                 # Sample data seeder
├── prompts/                    # Product & design docs
│   ├── PRD_Regelebot.md
│   └── Design_Technique_Regelebot.md
├── docker-compose.yml
├── .env.example
├── ARCHITECTURE.md
└── PROGRESS.md
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
