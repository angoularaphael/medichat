from app.services import ollama_client


async def _template_response(message, evaluation):
    return ollama_client.template_reply(evaluation), "template"


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
    assert data["evaluation"]["recommendation"]["drug_code"] == "paracetamol"


def test_unknown_symptom_returns_assessment_protocol(client, monkeypatch):
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
    evaluation = response.json()["evaluation"]
    assert evaluation["recommendation"] is None
    assert evaluation["non_drug_protocol"]
    assert "symptom_requires_assessment" in evaluation["rules_fired"]


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
