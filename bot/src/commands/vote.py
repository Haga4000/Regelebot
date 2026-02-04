from sqlalchemy.ext.asyncio import AsyncSession

from agents.subagents.poll import PollAgent


async def cmd_sondage(args: str, sender: dict, db: AsyncSession) -> str | dict:
    """Create a poll. Usage: /sondage Question ? | Option1 | Option2 | ..."""
    if not args or "|" not in args:
        return (
            "Usage : /sondage Question ? | Option 1 | Option 2 | ...\n"
            "Exemple : /sondage Quel film ce samedi ? | Inception | Parasite | Interstellar"
        )

    parts = [p.strip() for p in args.split("|")]
    question = parts[0]
    options = [p for p in parts[1:] if p]

    if len(options) < 2:
        return "Il faut au moins 2 options pour creer un sondage."

    agent = PollAgent(db)
    result = await agent.create_poll(
        question=question,
        options=options,
        member_name=sender.get("name", "Membre"),
    )

    if "error" in result:
        return result["error"]

    lines = [f"*{result['question']}*\n"]
    for opt_id, label in result["options"].items():
        lines.append(f"  {opt_id}. {label}")
    lines.append(f"\nPour voter : /vote {opt_id}")
    lines.append(f"ID du sondage : {result['poll_id'][:8]}...")

    return {
        "text": "\n".join(lines),
        "poll": {
            "poll_id": result["poll_id"],
            "question": result["question"],
            "options": list(result["options"].values()),
        },
    }


async def cmd_vote(args: str, sender: dict, db: AsyncSession) -> str:
    """Vote on the current poll. Usage: /vote <option_number>"""
    if not args:
        return "Usage : /vote <numero>\nExemple : /vote 2"

    parts = args.strip().split()
    option_id = parts[0]

    agent = PollAgent(db)

    # If only option number given, find the latest open poll
    if len(parts) == 1 and option_id.isdigit():
        # Get latest poll to vote on
        latest = await agent.get_results()
        if "error" in latest:
            return "Aucun sondage en cours. Cree-en un avec /sondage"
        poll_id = latest["poll_id"]
    else:
        return "Usage : /vote <numero>\nExemple : /vote 2"

    result = await agent.vote(
        poll_id=poll_id,
        option_id=option_id,
        member_name=sender.get("name", "Membre"),
    )

    if "error" in result:
        return result["error"]

    return result["message"]


async def cmd_resultats(args: str, sender: dict, db: AsyncSession) -> str:
    """Show poll results. Usage: /resultats"""
    agent = PollAgent(db)
    result = await agent.get_results()

    if "error" in result:
        return result["error"]

    status = "CLOS" if result["is_closed"] else "En cours"
    lines = [f"*{result['question']}* ({status})\n"]

    for item in result["results"]:
        bar = "█" * item["votes"]
        lines.append(f"  {item['option_id']}. {item['label']} — {item['votes']} vote(s) {bar}")

    lines.append(f"\nTotal : {result['total_votes']} vote(s)")
    return "\n".join(lines)
