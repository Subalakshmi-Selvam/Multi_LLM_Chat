def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_list_sessions(client):
    create_response = client.post("/sessions", json={"title": "Test session"})
    assert create_response.status_code == 200
    body = create_response.json()
    assert body["title"] == "Test session"
    assert "id" in body

    list_response = client.get("/sessions")
    assert list_response.status_code == 200
    sessions = list_response.json()
    assert any(s["id"] == body["id"] for s in sessions)


def test_get_messages_for_unknown_session_returns_404(client):
    response = client.get("/sessions/does-not-exist/messages")
    assert response.status_code == 404


def test_delete_unknown_session_returns_404(client):
    response = client.delete("/sessions/does-not-exist")
    assert response.status_code == 404


def test_delete_session(client):
    create_response = client.post("/sessions", json={"title": "To delete"})
    session_id = create_response.json()["id"]

    delete_response = client.delete(f"/sessions/{session_id}")
    assert delete_response.status_code == 200

    messages_response = client.get(f"/sessions/{session_id}/messages")
    assert messages_response.status_code == 404
