import logging
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.member import Member
from models.poll import Poll, PollVote

logger = logging.getLogger(__name__)


class PollAgent:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_poll(
        self, question: str, options: list[str], member_name: str
    ) -> dict:
        if len(options) < 2:
            return {"error": "Un sondage doit avoir au moins 2 options."}
        if len(options) > 10:
            return {"error": "Un sondage ne peut pas avoir plus de 10 options."}

        # Build options dict: {"1": "Film A", "2": "Film B", ...}
        options_dict = {str(i + 1): opt for i, opt in enumerate(options)}

        # Find or create member
        member = await self._get_or_create_member(member_name)

        poll = Poll(
            question=question,
            options=options_dict,
            created_by=member.id,
        )
        self.db.add(poll)
        await self.db.flush()

        return {
            "success": True,
            "poll_id": str(poll.id),
            "question": question,
            "options": options_dict,
            "message": f"Sondage cree ! Utilisez /vote {poll.id} <numero> pour voter.",
        }

    async def vote(
        self, poll_id: Optional[str], option_id: str, member_name: str
    ) -> dict:
        if poll_id:
            poll = await self.db.scalar(
                select(Poll).where(Poll.id == poll_id)
            )
        else:
            poll = await self.db.scalar(
                select(Poll)
                .where(Poll.is_closed.is_(False))
                .order_by(Poll.created_at.desc())
            )
        if not poll:
            return {"error": "Sondage non trouve."}
        if poll.is_closed:
            return {"error": "Ce sondage est clos."}
        if option_id not in poll.options:
            valid = ", ".join(
                f"{k}: {v}" for k, v in poll.options.items()
            )
            return {"error": f"Option invalide. Options disponibles : {valid}"}

        member = await self._get_or_create_member(member_name)

        # Check if already voted
        existing = await self.db.scalar(
            select(PollVote).where(
                PollVote.poll_id == poll.id,
                PollVote.member_id == member.id,
            )
        )
        if existing:
            existing.option_id = option_id
            await self.db.flush()
            return {
                "success": True,
                "message": f"{member_name} a change son vote pour : {poll.options[option_id]}",
            }

        vote = PollVote(
            poll_id=poll.id,
            member_id=member.id,
            option_id=option_id,
        )
        self.db.add(vote)
        await self.db.flush()

        return {
            "success": True,
            "message": f"{member_name} a vote pour : {poll.options[option_id]}",
        }

    async def get_results(self, poll_id: Optional[str] = None) -> dict:
        if poll_id:
            poll = await self.db.scalar(
                select(Poll).where(Poll.id == poll_id)
            )
        else:
            # Get the latest open poll
            poll = await self.db.scalar(
                select(Poll)
                .where(Poll.is_closed.is_(False))
                .order_by(Poll.created_at.desc())
            )

        if not poll:
            return {"error": "Aucun sondage trouve."}

        # Count votes per option
        vote_counts = await self.db.execute(
            select(PollVote.option_id, func.count(PollVote.id))
            .where(PollVote.poll_id == poll.id)
            .group_by(PollVote.option_id)
        )
        counts = {row[0]: row[1] for row in vote_counts.all()}

        total_votes = sum(counts.values())

        results = []
        for opt_id, opt_label in poll.options.items():
            vote_count = counts.get(opt_id, 0)
            results.append({
                "option_id": opt_id,
                "label": opt_label,
                "votes": vote_count,
            })

        # Sort by votes descending
        results.sort(key=lambda x: x["votes"], reverse=True)

        return {
            "poll_id": str(poll.id),
            "question": poll.question,
            "is_closed": poll.is_closed,
            "total_votes": total_votes,
            "results": results,
        }

    async def close_poll(self, poll_id: Optional[str] = None) -> dict:
        if poll_id:
            poll = await self.db.scalar(
                select(Poll).where(Poll.id == poll_id)
            )
        else:
            poll = await self.db.scalar(
                select(Poll)
                .where(Poll.is_closed.is_(False))
                .order_by(Poll.created_at.desc())
            )

        if not poll:
            return {"error": "Aucun sondage trouve."}
        if poll.is_closed:
            return {"error": "Ce sondage est deja clos."}

        poll.is_closed = True
        await self.db.flush()

        # Get final results
        return await self.get_results(str(poll.id))

    async def set_wa_message_id(self, poll_id: str, wa_message_id: str) -> dict:
        poll = await self.db.scalar(
            select(Poll).where(Poll.id == poll_id)
        )
        if not poll:
            return {"error": "Sondage non trouve."}
        poll.wa_message_id = wa_message_id
        await self.db.flush()
        return {"success": True}

    async def vote_by_label(
        self, wa_message_id: str, selected_options: list[str], member_name: str
    ) -> dict:
        poll = await self.db.scalar(
            select(Poll).where(Poll.wa_message_id == wa_message_id)
        )
        if not poll:
            return {"error": "Sondage non trouve pour ce message WhatsApp."}
        if poll.is_closed:
            return {"error": "Ce sondage est clos."}

        # Reverse lookup: label -> option_id
        label_to_id = {v: k for k, v in poll.options.items()}

        for label in selected_options:
            option_id = label_to_id.get(label)
            if not option_id:
                continue
            result = await self.vote(
                poll_id=str(poll.id),
                option_id=option_id,
                member_name=member_name,
            )
            if "error" in result:
                return result
            return result

        return {"error": "Aucune option valide selectionnee."}

    async def _get_or_create_member(self, member_name: str) -> Member:
        member = await self.db.scalar(
            select(Member).where(Member.display_name == member_name)
        )
        if not member:
            member = Member(
                phone_hash=member_name.lower().replace(" ", "_"),
                display_name=member_name,
            )
            self.db.add(member)
            await self.db.flush()
        return member
