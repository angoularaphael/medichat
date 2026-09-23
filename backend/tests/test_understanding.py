from app.services import message_understanding


def test_elisa_vomit_cough_fever_understanding():
    msg = "il y a elisa elle fait que vomir, elle tousse beaucoup en plus elle a de la fievre"
    u = message_understanding.understand_message_rules(msg, "raphael")
    assert u.care_crew_code == "elisa"
    assert u.third_person is True
    labels = set(u.symptom_labels)
    assert "nausee" in labels
    assert "toux" in labels
    assert "fievre" in labels


def test_elisa_multi_eval(client, monkeypatch):
    from app.services import ollama_client

    async def _tpl(message, evaluation, history="", symptoms=None, meta_followup=False):
        return (
            ollama_client.template_reply(
                evaluation, message, symptoms=symptoms or [], meta_followup=meta_followup
            ),
            "template",
        )

    monkeypatch.setattr(ollama_client, "reformulate_with_ollama", _tpl)

    async def _noop_refine(_message, base):
        return base

    monkeypatch.setattr(message_understanding, "refine_with_ollama", _noop_refine)
    response = client.post(
        "/api/chat/message",
        json={
            "crew_member_code": "raphael",
            "message": "il y a elisa elle fait que vomir, elle tousse beaucoup en plus elle a de la fievre",
            "session_id": "elisa-triple",
        },
    )
    assert response.status_code == 200
    data = response.json()
    ev = data["evaluation"]
    assert ev["understanding"]["care_crew_code"] == "elisa"
    assert len(ev["symptom_items"]) >= 3
    content = data["content"].lower()
    assert "fievre" in content or "paracetamol" in content
    assert "toux" in content or "repos" in content or "hydratation" in content
