from types import SimpleNamespace

from llm.providers.gemini import GeminiProvider


def _content(role: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(role=role, parts=[text])


def test_empty():
    assert GeminiProvider._consolidate_contents([]) == []


def test_alternating():
    contents = [_content("user", "a"), _content("model", "b"), _content("user", "c")]
    result = GeminiProvider._consolidate_contents(contents)
    assert len(result) == 3


def test_consecutive_merge():
    contents = [_content("user", "a"), _content("user", "b"), _content("model", "c")]
    result = GeminiProvider._consolidate_contents(contents)
    assert len(result) == 2
    assert result[0].role == "user"
    assert result[0].parts == ["a", "b"]
    assert result[1].role == "model"


def test_single_entry():
    contents = [_content("user", "hello")]
    result = GeminiProvider._consolidate_contents(contents)
    assert len(result) == 1
    assert result[0].parts == ["hello"]
