def test_generic_pain_asks_before_prescribing(client):
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["douleur"]},
    )
    data = response.json()
    assert data["needs_clarification"] is True
    assert data["recommendation"] is None
    assert "intensite" in data["non_drug_protocol"]


def test_t01_elisa_headache(client):
    r = client.post(
        "/api/care/evaluate",
        json={
            "crew_member_code": "elisa",
            "symptoms": ["mal de tete"],
        },
    )
    data = r.json()
    assert r.status_code == 200
    codes = [o["drug_code"] for o in data["excluded_options"]]
    assert "ibuprofen" in codes
    assert data["recommendation"]["drug_code"] == "paracetamol"


def test_t02_elisa_requests_ibuprofen(client):
    r = client.post(
        "/api/care/evaluate",
        json={
            "crew_member_code": "elisa",
            "symptoms": ["mal de tete"],
            "requested_drug_code": "ibuprofen",
        },
    )
    data = r.json()
    assert data["recommendation"] is None or data["recommendation"]["drug_code"] != "ibuprofen"


def test_t03_raphael_interaction(client):
    r = client.post(
        "/api/care/evaluate",
        json={
            "crew_member_code": "raphael",
            "symptoms": ["mal de tete"],
            "requested_drug_code": "ibuprofen",
        },
    )
    data = r.json()
    assert any(o["reason_code"] == "interaction" for o in data["excluded_options"])


def test_t04_paracetamol_zero_substitution(client):
    client.post("/api/demo/reset")
    client.post("/api/demo/force-stock-zero/paracetamol")
    r = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elisa", "symptoms": ["mal de tete"]},
    )
    data = r.json()
    assert data["recommendation"] is None or data["non_drug_protocol"]


def test_t05_chest_pain_escalation(client):
    r = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elisa", "symptoms": ["douleur thoracique"]},
    )
    data = r.json()
    assert data["escalate_to_physician"] is True
    assert data["recommendation"] is None


def test_t06_unknown_patient(client):
    r = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "unknown", "symptoms": ["mal de tete"]},
    )
    data = r.json()
    assert "patient_unknown" in data["rules_fired"]


def test_t07_dose_too_high(client):
    r = client.post(
        "/api/care/evaluate",
        json={
            "crew_member_code": "elsa",
            "symptoms": ["mal de tete"],
            "requested_drug_code": "paracetamol",
            "requested_dose_mg": 5000,
        },
    )
    data = r.json()
    assert any(o["reason_code"] == "dose" for o in data["excluded_options"])


def test_t08_crisis_trigger(client):
    client.post("/api/demo/reset")
    r = client.post("/api/crisis/trigger")
    assert r.status_code == 200
    triage = client.get("/api/triage").json()
    assert len(triage) > 0


def test_t09_rationing_improves_autonomy(client):
    client.post("/api/demo/reset")
    client.post("/api/crisis/trigger")
    before = client.get("/api/autonomy").json()
    client.post("/api/crisis/rationing")
    after = client.get("/api/autonomy").json()
    assert (
        after["rationing_quarantine"]["global_days"]
        >= before["on_demand"]["global_days"] * 0.9
    )


def test_t10_triage_order(client):
    client.post("/api/demo/reset")
    client.post("/api/crisis/trigger")
    triage = client.get("/api/triage").json()
    priorities = [t["triage_priority"] for t in triage]
    assert priorities == sorted(priorities)


def test_confirm_updates_stock(client):
    drugs = client.get("/api/drugs").json()
    before = next(row for row in drugs if row["code"] == "paracetamol")["stock_units"]
    ors_before = next(row for row in drugs if row["code"] == "ors")["stock_units"]
    response = client.post(
        "/api/care/confirm",
        json={"crew_member_code": "elisa", "drug_code": "paracetamol", "dose_mg": 500},
    )
    assert response.status_code == 200
    assert response.json()["stock_remaining"] == before - 1
    after = client.get("/api/drugs").json()
    assert next(row for row in after if row["code"] == "paracetamol")["stock_units"] == before - 1

    ors = client.post(
        "/api/care/confirm",
        json={"crew_member_code": "elisa", "drug_code": "ors", "dose_mg": 1},
    )
    assert ors.status_code == 200
    gastro = client.get("/api/clinical/gastro-estimate").json()
    row = next(item for item in gastro["rows"] if item["drug_code"] == "ors")
    assert row["stock_units"] == ors_before - 1
