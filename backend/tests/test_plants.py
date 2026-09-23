def test_raphael_is_nineteen(client):
    crew = client.get("/api/crew").json()
    raphael = next(member for member in crew if member["code"] == "raphael")
    assert raphael["age"] == 19


def test_unknown_symptom_does_not_wait_for_earth(client):
    r = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["douleur testiculaire"]},
    )
    data = r.json()
    protocol = (data["non_drug_protocol"] or "").lower()
    assert "bord" in protocol
    assert "latence" in protocol or "file" in protocol
    assert "medecin de bord" not in protocol


def test_infection_recommends_antibiotic(client):
    r = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["infection", "mal de gorge"]},
    )
    data = r.json()
    assert data["recommendation"]["drug_code"] == "amoxicillin"


def test_empty_antibiotics_use_plant_relay(client):
    client.post("/api/demo/reset")
    client.post("/api/demo/force-stock-zero/amoxicillin")
    client.post("/api/demo/force-stock-zero/azithromycin")
    r = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["infection"]},
    )
    data = r.json()
    assert data["recommendation"] is None
    assert data["plant_recommendation"]["plant_code"] in {"thymus", "allium", "artemisia"}


def test_plants_list_and_harvest(client):
    plants = client.get("/api/plants").json()
    assert len(plants) >= 5
    ready = next(plant for plant in plants if plant["ready"])
    harvested = client.post(f"/api/plants/{ready['code']}/harvest")
    assert harvested.status_code == 200
    assert harvested.json()["biomass_percent"] < ready["biomass_percent"]


def test_restock_restores_paracetamol(client):
    client.post("/api/demo/force-stock-zero/paracetamol")
    client.post("/api/demo/restock")
    drugs = {item["code"]: item for item in client.get("/api/drugs").json()}
    assert drugs["paracetamol"]["stock_units"] == 600


def test_reset_restores_plants_and_health(client):
    client.post("/api/crisis/trigger")
    client.post("/api/plants/thymus/harvest")
    client.post("/api/demo/reset")
    plants = {item["code"]: item for item in client.get("/api/plants").json()}
    assert plants["thymus"]["biomass_percent"] == 82.0
    crew = client.get("/api/crew").json()
    assert all(member["health_status"] == "healthy" for member in crew)


def test_profile_allergies_saved(client):
    response = client.patch(
        "/api/crew/elsa/profile",
        json={"allergies": ["paracetamol", "pollen"]},
    )
    assert response.status_code == 200
    assert response.json()["allergies"] == ["paracetamol", "pollen"]
    stored = client.get("/api/crew/elsa").json()
    assert "paracetamol" in stored["allergies"]


def test_paracetamol_allergy_falls_back_to_plant(client):
    client.post("/api/demo/reset")
    client.patch(
        "/api/crew/elisa/profile",
        json={"allergies": ["ibuprofen", "AINS", "paracetamol"]},
    )
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elisa", "symptoms": ["mal de tete"]},
    )
    data = response.json()
    excluded = [item["drug_code"] for item in data["excluded_options"]]
    assert "paracetamol" in excluded
    assert data["recommendation"] is None
    assert data["plant_recommendation"]["plant_code"] == "salix"


def test_para_allergy_uses_other_drug_if_available(client):
    client.patch("/api/crew/elsa/profile", json={"allergies": ["paracetamol"]})
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["mal de tete"]},
    )
    assert response.json()["recommendation"]["drug_code"] == "ibuprofen"
