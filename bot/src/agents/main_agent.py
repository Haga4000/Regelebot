import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agents.subagents import MovieAgent, PollAgent, RecommendationAgent, StatsAgent
from config import settings
from core.sanitization import (
    detect_leaked_system_prompt,
    sanitize_sender_name,
    wrap_user_content,
)
from llm import ChatMessage, ToolDefinition, create_llm_provider
from prompts.main_agent import MAIN_AGENT_SYSTEM_PROMPT, build_club_context
from tools.definitions import TOOLS_DEFINITIONS

logger = logging.getLogger(__name__)


class MainAgent:
    def __init__(self, db_session: AsyncSession):
        self.llm = create_llm_provider()

        self.subagents = {
            "movie": MovieAgent(settings.TMDB_API_KEY),
            "recommendation": RecommendationAgent(settings.TMDB_API_KEY, db_session),
            "stats": StatsAgent(db_session, settings.TMDB_API_KEY),
            "poll": PollAgent(db_session),
        }

        self.db = db_session

    async def process(
        self,
        user_message: str,
        sender_name: str,
        conversation_history: list | None = None,
    ) -> str:
        # Build system prompt with club context
        club_context = await build_club_context(self.subagents["stats"])
        system_prompt = MAIN_AGENT_SYSTEM_PROMPT.format(club_context=club_context)

        # Sanitize and wrap user content in XML tags for clear separation
        full_message = wrap_user_content(sender_name, user_message)

        # Build tool definitions
        tools = [
            ToolDefinition(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"],
            )
            for t in TOOLS_DEFINITIONS
        ]

        # Build messages: system + history + current
        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=system_prompt),
        ]

        if conversation_history:
            for msg in conversation_history:
                if msg.role == "user":
                    wrapped = wrap_user_content(msg.sender_name or "Membre", msg.content)
                    messages.append(ChatMessage(role="user", content=wrapped))
                else:
                    messages.append(ChatMessage(role="assistant", content=msg.content))

        messages.append(ChatMessage(role="user", content=full_message))

        try:
            response = await self.llm.generate(
                messages=messages,
                tools=tools,
                temperature=0.7,
                max_tokens=1024,
            )
        except Exception as e:
            logger.error("LLM API error: %s", e)
            return "Oups, j'ai eu un souci technique. Reessaie dans quelques secondes !"

        # ReAct loop: handle tool calls
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            if not response.has_tool_calls:
                break

            tool_call = response.tool_calls[0]
            logger.info("Tool call: %s(%s)", tool_call.name, tool_call.arguments)

            tool_result = await self._execute_tool(tool_call.name, tool_call.arguments)

            # Add assistant's tool call and tool result to conversation
            messages.append(
                ChatMessage(
                    role="assistant",
                    tool_calls=response.tool_calls,
                    content=response.content,
                )
            )
            messages.append(
                ChatMessage(
                    role="tool",
                    content=json.dumps(tool_result, default=str),
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                )
            )

            try:
                response = await self.llm.generate(
                    messages=messages,
                    tools=tools,
                    temperature=0.7,
                    max_tokens=1024,
                )
            except Exception as e:
                logger.error("LLM API error during tool loop: %s", e)
                return "J'ai eu un probleme en cherchant les infos. Reessaie !"

        try:
            response_text = response.content
            if not response_text:
                return "Hmm, j'ai pas reussi a formuler ma reponse. Tu peux reformuler ?"

            # Output filtering: check for leaked system prompt
            if detect_leaked_system_prompt(response_text):
                logger.warning("Potential system prompt leak detected, filtering response")
                return "Je suis la pour parler cinema avec toi ! Qu'est-ce qui te ferait plaisir ?"

            return response_text
        except (IndexError, AttributeError):
            return "Hmm, j'ai pas reussi a formuler ma reponse. Tu peux reformuler ?"

    async def _execute_tool(self, tool_name: str, args: dict) -> Any:
        if tool_name == "movie_search":
            return await self.subagents["movie"].search(
                query=args["query"], year=args.get("year")
            )
        elif tool_name == "get_recommendations":
            return await self.subagents["recommendation"].get(
                rec_type=args["rec_type"],
                reference=args.get("reference"),
                genre=args.get("genre"),
                mood=args.get("mood"),
            )
        elif tool_name == "get_club_history":
            return await self.subagents["stats"].get_history(
                limit=int(args.get("limit", 10))
            )
        elif tool_name == "get_club_stats":
            return await self.subagents["stats"].get_stats()
        elif tool_name == "mark_as_watched":
            return await self.subagents["stats"].mark_watched(
                movie_title=args["movie_title"]
            )
        elif tool_name == "rate_movie":
            return await self.subagents["stats"].rate(
                movie_title=args["movie_title"],
                score=int(args["score"]),
                member_name=args["member_name"],
            )
        elif tool_name == "create_poll":
            return await self.subagents["poll"].create_poll(
                question=args["question"],
                options=list(args["options"]),
                member_name=args["member_name"],
            )
        elif tool_name == "vote_on_poll":
            return await self.subagents["poll"].vote(
                poll_id=args.get("poll_id") or None,
                option_id=args["option_id"],
                member_name=args["member_name"],
            )
        elif tool_name == "get_poll_results":
            return await self.subagents["poll"].get_results(
                poll_id=args.get("poll_id"),
            )
        elif tool_name == "close_poll":
            return await self.subagents["poll"].close_poll(
                poll_id=args.get("poll_id"),
            )
        elif tool_name == "get_now_playing":
            return await self.subagents["movie"].now_playing()
        elif tool_name == "discover_movies":
            return await self.subagents["movie"].discover(
                genre=args.get("genre"),
                year_min=args.get("year_min"),
                year_max=args.get("year_max"),
                platform=args.get("platform"),
                sort_by=args.get("sort_by", "popularity.desc"),
                min_rating=args.get("min_rating"),
                language=args.get("language"),
            )
        elif tool_name == "get_trending":
            return await self.subagents["movie"].trending(
                window=args.get("window", "week"),
            )
        return {"error": f"Outil inconnu: {tool_name}"}
