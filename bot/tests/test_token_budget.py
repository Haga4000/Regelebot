from types import SimpleNamespace

from core.token_budget import estimate_tokens, extract_movie_titles, prepare_history


def _msg(content: str, role: str = "user", sender_name: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(content=content, role=role, sender_name=sender_name)


# --- estimate_tokens ---


def test_estimate_tokens_short():
    assert estimate_tokens("hi") == 1  # len=2, 2//4=0, min 1


def test_estimate_tokens_longer():
    assert estimate_tokens("a" * 100) == 25


# --- extract_movie_titles ---


def test_extract_titles_year_pattern():
    msg = _msg("Je te recommande Inception (2010) et Interstellar (2014)", role="bot")
    titles = extract_movie_titles([msg])
    assert "Inception" in titles
    assert "Interstellar" in titles


def test_extract_titles_bold_pattern():
    msg = _msg("Voici mes suggestions : **The Matrix**, **Fight Club**", role="bot")
    titles = extract_movie_titles([msg])
    assert "The Matrix" in titles
    assert "Fight Club" in titles


def test_extract_titles_no_duplicates():
    msgs = [
        _msg("Inception (2010) est genial", role="bot"),
        _msg("Inception (2010) encore une fois", role="bot"),
    ]
    titles = extract_movie_titles(msgs)
    assert titles.count("Inception") == 1


def test_extract_titles_empty():
    assert extract_movie_titles([]) == []


def test_extract_titles_no_movies():
    msg = _msg("Salut, comment ca va ?", role="bot")
    assert extract_movie_titles([msg]) == []


# --- prepare_history ---


def test_prepare_empty():
    user_msgs, excluded = prepare_history([])
    assert user_msgs == []
    assert excluded == []


def test_prepare_splits_user_and_bot():
    msgs = [
        _msg("Recommande un film", role="user", sender_name="Alice"),
        _msg("Je te recommande Inception (2010)", role="bot"),
        _msg("Autre chose", role="user", sender_name="Alice"),
    ]
    user_msgs, excluded = prepare_history(msgs)
    assert len(user_msgs) == 2
    assert all(m.role == "user" for m in user_msgs)
    assert "Inception" in excluded


def test_prepare_limits_user_messages():
    msgs = [
        _msg(f"msg {i}", role="user", sender_name="Alice")
        for i in range(10)
    ]
    user_msgs, _ = prepare_history(msgs, max_user_messages=3)
    assert len(user_msgs) == 3
    # Should keep the last 3
    assert user_msgs[0].content == "msg 7"
    assert user_msgs[2].content == "msg 9"


def test_prepare_extracts_from_multiple_bot_messages():
    msgs = [
        _msg("Je recommande Inception (2010)", role="bot"),
        _msg("non merci", role="user", sender_name="Bob"),
        _msg("Ok alors **The Matrix**", role="bot"),
        _msg("toujours pas", role="user", sender_name="Bob"),
    ]
    user_msgs, excluded = prepare_history(msgs)
    assert len(user_msgs) == 2
    assert "Inception" in excluded
    assert "The Matrix" in excluded
