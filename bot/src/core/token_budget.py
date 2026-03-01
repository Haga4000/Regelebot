import re

# Common French sentence words that precede movie titles but aren't part of them
_FILLER_PREFIX = re.compile(
    r"^(?:je\s+|tu\s+|il\s+|on\s+|nous\s+|vous\s+|"
    r"te\s+|me\s+|se\s+|"
    r"recommande\s+|conseille\s+|propose\s+|suggere\s+|"
    r"voici\s+|voila\s+|aussi\s+|alors\s+|et\s+|ou\s+|"
    r"comme\s+|avec\s+|pour\s+|dans\s+|sur\s+|par\s+)+",
    re.IGNORECASE,
)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _clean_title(raw: str) -> str:
    """Strip leading filler words that are sentence context, not title."""
    return _FILLER_PREFIX.sub("", raw).strip()


def extract_movie_titles(bot_messages: list) -> list[str]:
    """Extract movie titles from bot responses to build an exclusion list.

    Looks for patterns like:
    - "Film Title (2023)"
    - Markdown bold "**Film Title**"
    """
    titles: list[str] = []
    for msg in bot_messages:
        content = msg.content if hasattr(msg, "content") else str(msg)

        # "Title (year)" pattern — most common in recommendations
        for m in re.finditer(r"([\w][\w\s'':\-&!,]{0,60}?)\s*\(\d{4}\)", content):
            title = _clean_title(m.group(1).strip())
            if title and title not in titles and len(title) > 1:
                titles.append(title)

        # **Bold Title** pattern
        for match in re.finditer(r"\*\*(.+?)\*\*", content):
            title = match.group(1).strip()
            if title and title not in titles and len(title) > 2:
                titles.append(title)

    return titles


def prepare_history(
    messages: list,
    max_user_messages: int = 3,
) -> tuple[list, list[str]]:
    """Split history into user-only messages and an exclusion list.

    Returns:
        (user_messages, excluded_titles)
    """
    if not messages:
        return [], []

    bot_messages = [m for m in messages if getattr(m, "role", None) in ("bot", "assistant")]
    user_messages = [m for m in messages if getattr(m, "role", None) == "user"]

    # Keep only the last N user messages
    user_messages = user_messages[-max_user_messages:]

    # Extract titles from bot responses to avoid repeating
    excluded_titles = extract_movie_titles(bot_messages)

    return user_messages, excluded_titles
