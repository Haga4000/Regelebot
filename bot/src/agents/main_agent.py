import json
import logging
from typing import Any

from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from agents.subagents import MovieAgent, PollAgent, RecommendationAgent, StatsAgent
from config import settings
from core.sanitization import (
    detect_leaked_system_prompt,
    sanitize_sender_name,
    wrap_user_content,
)
from prompts.main_agent import MAIN_AGENT_SYSTEM_PROMPT, build_club_context
from tools.definitions import TOOLS_DEFINITIONS

logger = logging.getLogger(__name__)


class MainAgent:
    def __init__(self, db_session: AsyncSession):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash-lite"

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

        # Build tool declarations
        tools = [types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"],
            )
            for t in TOOLS_DEFINITIONS
        ])]

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=tools,
            temperature=0.7,
            max_output_tokens=1024,
        )

        # Build contents: history + current message
        contents: list[types.Content] = []

        if conversation_history:
            for msg in conversation_history:
                if msg.role == "user":
                    # Wrap historical user messages with same XML protection
                    wrapped = wrap_user_content(msg.sender_name or "Membre", msg.content)
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=wrapped)],
                    ))
                else:
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=msg.content)],
                    ))

        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=full_message)])
        )

        contents = self._consolidate_contents(contents)

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return "Oups, j'ai eu un souci technique. Reessaie dans quelques secondes !"

        # ReAct loop: handle tool calls
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            if not response.candidates or not response.candidates[0].content.parts:
                break

            part = response.candidates[0].content.parts[0]

            if part.function_call:
                tool_name = part.function_call.name
                tool_args = dict(part.function_call.args) if part.function_call.args else {}

                logger.info("Tool call: %s(%s)", tool_name, tool_args)

                tool_result = await self._execute_tool(tool_name, tool_args)

                # Add model's response and function result to conversation
                contents.append(response.candidates[0].content)
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=tool_name,
                        response={"result": json.loads(json.dumps(tool_result, default=str))},
                    )],
                ))

                try:
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=config,
                    )
                except Exception as e:
                    logger.error("Gemini API error during tool loop: %s", e)
                    return "J'ai eu un probleme en cherchant les infos. Reessaie !"
            else:
                break

        try:
            response_text = response.candidates[0].content.parts[0].text

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
        return {"error": f"Outil inconnu: {tool_name}"}

    @staticmethod
    def _consolidate_contents(contents: list[types.Content]) -> list[types.Content]:
        """Merge consecutive same-role entries to satisfy Gemini's strict user/model alternation."""
        if not contents:
            return contents

        consolidated: list[types.Content] = [contents[0]]
        for entry in contents[1:]:
            if entry.role == consolidated[-1].role:
                consolidated[-1].parts.extend(entry.parts)
            else:
                consolidated.append(entry)
        return consolidated
