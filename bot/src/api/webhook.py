import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from agents.main_agent import MainAgent
from agents.subagents.poll import PollAgent
from api.dependencies import verify_webhook_secret
from config import settings
from core.database import get_db
from core.rate_limiter import rate_limiter
from core.router import MessageRouter
from core.token_budget import trim_history_to_budget
from services.conversation import ConversationService

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_webhook_secret)])


class WhatsAppMessage(BaseModel):
    from_: str = Field(alias="from_")
    sender: str
    sender_name: str
    body: str
    timestamp: int


class PollCreatedEvent(BaseModel):
    poll_id: str
    wa_message_id: str


class PollVoteEvent(BaseModel):
    wa_message_id: str
    voter: str
    voter_name: str
    selected_options: list[str]


@router.post("/webhook/message")
async def receive_message(message: WhatsAppMessage):
    if not rate_limiter.is_allowed(message.from_):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    async with get_db() as db:
        agent = MainAgent(db)
        msg_router = MessageRouter(agent, db)
        conv_service = ConversationService(db)
        group_id = message.from_

        # Fetch history before storing the current message
        history = await conv_service.get_recent_history(group_id)
        history = trim_history_to_budget(history, settings.TOKEN_BUDGET)

        # Store the incoming user message
        if msg_router.should_respond(message.body):
            await conv_service.store_message(
                group_id=group_id,
                role="user",
                content=message.body,
                sender_name=message.sender_name,
            )

        response = await msg_router.route(
            message=message.body,
            sender={"name": message.sender_name, "phone_hash": message.sender},
            conversation_history=history,
        )

        # Store the bot response
        if response:
            response_text = _extract_response_text(response)
            if response_text:
                await conv_service.store_message(
                    group_id=group_id,
                    role="bot",
                    content=response_text,
                )

    if response:
        if isinstance(response, dict):
            result = {"reply": _format_as_code_block(response["text"], message.body, message.sender_name)}
            if "poll" in response:
                result["poll"] = response["poll"]
            return result
        return {"reply": _format_as_code_block(response, message.body, message.sender_name)}
    return {"reply": None}


def _extract_response_text(response) -> str | None:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return response.get("text")
    return None


def _format_as_code_block(text: str, original_message: str = "", sender_name: str = "") -> str:
    """Wrap text in WhatsApp monospace code block formatting."""
    if not text:
        return text
    # Remove any quoted original message the AI might have added
    text = _strip_quoted_message(text, original_message, sender_name)
    return f"```{text.strip()}```"


def _strip_quoted_message(text: str, original_message: str, sender_name: str) -> str:
    """Remove quoted original message from AI responses."""
    import re

    # Remove "[Message de Name]" prefix pattern
    pattern = r'^\s*\[Message de [^\]]+\]\s*'
    text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Remove the original message if it appears at the start of the response
    if original_message:
        # Clean the original message (remove @mentions)
        clean_original = re.sub(r'@\w+\s*', '', original_message).strip()
        if clean_original and text.strip().startswith(clean_original):
            text = text.strip()[len(clean_original):].strip()

    return text.strip()


@router.post("/webhook/poll-created")
async def poll_created(event: PollCreatedEvent):
    async with get_db() as db:
        agent = PollAgent(db)
        result = await agent.set_wa_message_id(event.poll_id, event.wa_message_id)
    if "error" in result:
        logger.error("poll-created error: %s", result["error"])
        return {"success": False, "error": result["error"]}
    logger.info("Linked poll %s to WA message %s", event.poll_id, event.wa_message_id)
    return {"success": True}


@router.post("/webhook/poll-vote")
async def poll_vote(event: PollVoteEvent):
    async with get_db() as db:
        agent = PollAgent(db)
        result = await agent.vote_by_label(
            wa_message_id=event.wa_message_id,
            selected_options=event.selected_options,
            member_name=event.voter_name,
        )
    if "error" in result:
        logger.error("poll-vote error: %s", result["error"])
        return {"success": False, "error": result["error"]}
    logger.info("Native vote recorded: %s -> %s", event.voter_name, event.selected_options)
    return {"success": True}
