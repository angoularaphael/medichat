from app.services import ollama_client


async def _template_response(message, evaluation, history="", symptoms=None, meta_followup=False):
    return (
        ollama_client.template_reply(
            evaluation,
            message,
            symptoms=symptoms or [],
            meta_followup=meta_followup,
        ),
        "template",
    )


def test_chat_always_returns_visible_recommendation(client, monkeypatch):
    monkeypatch.setattr(
        ollama_client,
        "reformulate_with_ollama",
        _template_response,
    )
    response = client.post(
        "/api/chat/message",
        json={
            "crew_member_code": "elisa",
            "message": "J'ai mal de tete depuis ce matin",
            "session_id": "test",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"].strip()
    assert data["conversation_id"]
    assert data["evaluation"]["recommendation"]["drug_code"] == "paracetamol"


def test_unknown_symptom_is_treated_from_stock(client, monkeypatch):
    monkeypatch.setattr(
        ollama_client,
        "reformulate_with_ollama",
        _template_response,
    )
    response = client.post(
        "/api/chat/message",
        json={
            "crew_member_code": "elsa",
            "message": "Je ressens quelque chose d'inhabituel dans le bras",
            "session_id": "test-assessment",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    evaluation = payload["evaluation"]
    assert evaluation["recommendation"] is None
    assert "symptoms_unclear" in evaluation["rules_fired"] or "indication_unspecified" in evaluation[
        "rules_fired"
    ]
    content = payload["content"].lower()
    assert "latence" not in content
    assert "isolement" not in content


def test_kidney_pain_uses_paracetamol(client, monkeypatch):
    monkeypatch.setattr(
        ollama_client,
        "reformulate_with_ollama",
        _template_response,
    )
    response = client.post(
        "/api/chat/message",
        json={
            "crew_member_code": "elisa",
            "message": "j ai un mal au rein",
            "session_id": "test-kidney",
        },
    )
    assert response.status_code == 200
    evaluation = response.json()["evaluation"]
    assert evaluation["recommendation"]["drug_code"] == "paracetamol"
    assert evaluation["recommendation"]["drug_code"] != "ibuprofen"


def test_conversation_history_survives(client, monkeypatch):
    monkeypatch.setattr(
        ollama_client,
        "reformulate_with_ollama",
        _template_response,
    )
    created = client.post("/api/conversations", json={"crew_member_code": "elisa"})
    assert created.status_code == 200
    conversation_id = created.json()["id"]
    first = client.post(
        "/api/chat/message",
        json={
            "crew_member_code": "elisa",
            "message": "J'ai mal de tete",
            "conversation_id": conversation_id,
        },
    )
    assert first.status_code == 200
    listed = client.get(f"/api/conversations/{conversation_id}/messages")
    assert listed.status_code == 200
    roles = [row["role"] for row in listed.json()]
    assert roles == ["user", "assistant"]
    archived = client.post(f"/api/conversations/{conversation_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    blocked = client.post(
        "/api/chat/message",
        json={
            "crew_member_code": "elisa",
            "message": "suite",
            "conversation_id": conversation_id,
        },
    )
    assert blocked.status_code == 400


def test_respiratory_difficulty_escalates(client, monkeypatch):
    monkeypatch.setattr(
        ollama_client,
        "reformulate_with_ollama",
        _template_response,
    )
    response = client.post(
        "/api/chat/message",
        json={
            "crew_member_code": "carine",
            "message": "J'ai du mal a respirer et je suis essoufflee",
            "session_id": "test-critical",
        },
    )
    assert response.status_code == 200
    evaluation = response.json()["evaluation"]
    assert evaluation["escalate_to_physician"] is True
    assert evaluation["urgency"] == "critical"
