def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def trim_history_to_budget(
    messages: list,
    budget: int,
) -> list:
    if not messages:
        return []

    messages = list(messages)  # avoid mutating the original

    while len(messages) > 1:
        total = sum(estimate_tokens(m.content) for m in messages)
        if total <= budget:
            break
        messages.pop(0)

    return messages
