from types import SimpleNamespace

from core.token_budget import estimate_tokens, trim_history_to_budget


def _msg(content: str) -> SimpleNamespace:
    return SimpleNamespace(content=content)


def test_estimate_tokens_short():
    assert estimate_tokens("hi") == 1  # len=2, 2//4=0, min 1


def test_estimate_tokens_longer():
    assert estimate_tokens("a" * 100) == 25


def test_trim_empty():
    assert trim_history_to_budget([], 100) == []


def test_trim_within_budget():
    msgs = [_msg("hello"), _msg("world")]
    result = trim_history_to_budget(msgs, 100)
    assert len(result) == 2


def test_trim_over_budget():
    # Each message has 400 chars = 100 tokens
    msgs = [_msg("a" * 400), _msg("b" * 400), _msg("c" * 400)]
    result = trim_history_to_budget(msgs, 200)
    assert len(result) == 2
    assert result[0].content == "b" * 400
    assert result[1].content == "c" * 400


def test_keeps_at_least_one():
    msgs = [_msg("a" * 40000)]  # 10000 tokens, way over budget
    result = trim_history_to_budget(msgs, 10)
    assert len(result) == 1


def test_no_mutation():
    original = [_msg("a" * 400), _msg("b" * 400)]
    trim_history_to_budget(original, 50)
    assert len(original) == 2
