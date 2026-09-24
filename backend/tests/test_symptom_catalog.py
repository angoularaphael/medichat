from app.services.symptom_catalog import (
    ISOLATION_CASES_FR,
    check_isolation,
    labels_from_text,
)


def test_isolation_chest_pain():
    symptoms = labels_from_text("j'ai une oppression dans la poitrine")
    assert "douleur thoracique" in symptoms
    ok, rule = check_isolation(symptoms)
    assert ok is True
    assert rule and rule.startswith("isolation_")


def test_isolation_convulsion():
    symptoms = labels_from_text("mon collegue fait une convulsion")
    assert "convulsion" in symptoms
    assert check_isolation(symptoms)[0] is True


def test_blood_in_stool_is_not_full_isolation():
    symptoms = labels_from_text("il y a du sang")
    assert "sang" in symptoms
    assert check_isolation(symptoms)[0] is False


def test_isolation_hemorrhage():
    symptoms = labels_from_text("je vomis du sang")
    assert "hemorragie severe" in symptoms
    assert check_isolation(symptoms)[0] is True


def test_routine_fatigue_not_isolation():
    symptoms = labels_from_text("je me sens fatigue")
    assert "fatigue" in symptoms
    assert check_isolation(symptoms)[0] is False


def test_routine_deshydratation_not_isolation():
    symptoms = labels_from_text("soif intense depuis hier")
    assert "deshydratation" in symptoms
    assert check_isolation(symptoms)[0] is False


def test_isolation_catalog_covers_examples():
    for _title, phrases in ISOLATION_CASES_FR:
        assert any(check_isolation(labels_from_text(p))[0] for p in phrases)


def test_chat_convulsion_escalates(client, monkeypatch):
    from app.services import ollama_client

    async def _tpl(message, evaluation, history="", symptoms=None, meta_followup=False):
        return (
            ollama_client.template_reply(
                evaluation, message, symptoms=symptoms or [], meta_followup=meta_followup
            ),
            "template",
        )

    monkeypatch.setattr(ollama_client, "reformulate_with_ollama", _tpl)
    response = client.post(
        "/api/chat/message",
        json={
            "crew_member_code": "elsa",
            "message": "je fais une convulsion",
            "session_id": "conv",
        },
    )
    ev = response.json()["evaluation"]
    assert ev["escalate_to_physician"] is True
    assert "isolement" in (ev["non_drug_protocol"] or "").lower() or "isole" in (
        ev["non_drug_protocol"] or ""
    ).lower()
