from api import history


def test_create_session_and_get_it():
    session_id = history.create_session(title="Hello")
    session = history.get_session(session_id)
    assert session is not None
    assert session["title"] == "Hello"


def test_add_and_get_messages():
    session_id = history.create_session()
    history.add_message(session_id, "user", "Hi there")
    history.add_message(session_id, "assistant", "Hello!", provider="OpenAI", model_name="gpt-5-nano")

    messages = history.get_messages(session_id)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hi there"
    assert messages[1]["provider"] == "OpenAI"


def test_delete_session_cascades_messages():
    session_id = history.create_session()
    history.add_message(session_id, "user", "Hi")

    history.delete_session(session_id)

    assert history.get_session(session_id) is None
    assert history.get_messages(session_id) == []


def test_list_sessions_orders_most_recent_first():
    first_id = history.create_session(title="First")
    second_id = history.create_session(title="Second")

    sessions = history.list_sessions()
    ids_in_order = [s["id"] for s in sessions]
    assert ids_in_order.index(second_id) < ids_in_order.index(first_id)
