# Architecture

## Overview

Regelebot follows a **multi-agent architecture** with a hub-and-spoke model. A central MainAgent orchestrates specialized SubAgents via Gemini's function calling.

```
WhatsApp Group
      │
      ▼
┌─────────────┐     HTTP POST      ┌──────────────┐
│  Gateway    │ ──────────────────► │  Bot API     │
│  (Node.js)  │                     │  (FastAPI)   │
│  Port 3000  │ ◄────────────────── │  Port 8000   │
└─────────────┘     JSON reply      └──────┬───────┘
                                           │
                                    ┌──────▼───────┐
                                    │ MessageRouter │
                                    └──────┬───────┘
                                           │
                              ┌────────────┼────────────┐
                              ▼                         ▼
                     /command route              @mention route
                              │                         │
                              ▼                         ▼
                    ┌─────────────┐           ┌─────────────────┐
                    │ CommandHandlers │        │   MainAgent     │
                    │ (no LLM)    │           │  (Gemini LLM)   │
                    └─────────────┘           └────────┬────────┘
                                                       │
                                              ReAct Loop (function calling)
                                                       │
                                    ┌──────────┬───────┴────┬──────────┐
                                    ▼          ▼            ▼          ▼
                              MovieAgent  RecoAgent   StatsAgent  PollAgent
                                 │           │            │          │
                                 ▼           ▼            ▼          ▼
                              TMDb API   TMDb+Gemini  PostgreSQL  PostgreSQL
```

## Components

### Gateway (Node.js)

- **Tech**: whatsapp-web.js + Express
- **Role**: Bridge between WhatsApp and the bot API
- **Responsibilities**:
  - Authenticate with WhatsApp via QR code
  - Filter messages (only respond to `/commands` and `@Regelebot` mentions)
  - Forward relevant messages to the bot API via HTTP POST
  - Send bot responses back to WhatsApp

### Bot API (Python/FastAPI)

- **Entrypoint**: `POST /webhook/message`
- **MessageRouter**: Determines if a message is a command or a mention
  - `/command` → dispatched to CommandHandler (no LLM involved)
  - `@Regelebot ...` → dispatched to MainAgent (uses Gemini)
  - Other messages → ignored

### MainAgent (Orchestrator)

- **LLM**: Gemini 1.5 Flash with function calling
- **Pattern**: ReAct (Reason + Act) loop
- **Flow**:
  1. Build system prompt with club context (recent films, ratings, preferences)
  2. Send user message + system prompt to Gemini
  3. If Gemini requests a tool call → execute via SubAgent → return result → loop
  4. If Gemini returns text → that's the final response
  5. Max 5 iterations to prevent infinite loops

### SubAgents

| Agent | Purpose | External Dependency |
|-------|---------|-------------------|
| **MovieAgent** | Search films, get details, cast, streaming | TMDb API |
| **RecommendationAgent** | Personalized recommendations | TMDb API + Gemini (mood mapping) |
| **StatsAgent** | Club history, ratings, statistics | PostgreSQL |
| **PollAgent** | Create/manage polls and votes | PostgreSQL |

### Database (PostgreSQL)

```
members ──┐
           ├── ratings (member_id, watchlist_id, score)
movies ───┤
           ├── watchlist (movie_id, watched_at)
           │
           ├── polls (question, options, created_by)
           └── poll_votes (poll_id, member_id, option_id)
```

- Movies table caches TMDb data with JSONB metadata
- Ratings are per-member per-watchlist entry
- Polls support multiple options stored as JSONB

## Key Design Decisions

1. **Two-process architecture** (Node.js + Python) because whatsapp-web.js only runs on Node, while Python is better for the AI/DB stack.

2. **Commands bypass the LLM** to reduce latency and API costs for simple operations.

3. **Function calling over prompt engineering** — SubAgents are exposed as Gemini tools, letting the LLM decide when and how to use them.

4. **Context injection** — The system prompt is rebuilt on each request with fresh club stats, so the LLM always has current data.

5. **Docker Compose** for simple single-machine deployment. No Kubernetes needed for a 5-15 person group.
