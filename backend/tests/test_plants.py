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
    assert data["recommendation"]["drug_code"] == "paracetamol"
    protocol = (data["non_drug_protocol"] or data["recommendation"]["rationale"] or "").lower()
    assert "latence" not in protocol
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
    assert data["plant_recommendation"]["plant_code"] in {"thymus", "allium"}
    protocol = data["non_drug_protocol"].lower()
    assert "fermentation" in protocol
    assert "amoxicilline" in protocol


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


def test_depleted_paracetamol_still_uses_other_analgesic(client):
    client.post("/api/demo/reset")
    client.post("/api/demo/force-stock-zero/paracetamol")
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["mal de dos"]},
    )
    data = response.json()
    assert data["recommendation"]["drug_code"] == "ibuprofen"
    assert data["plant_recommendation"] is None


def test_raphael_back_pain_uses_paracetamol_with_stock(client):
    client.post("/api/demo/reset")
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "raphael", "symptoms": ["mal de dos"]},
    )
    data = response.json()
    assert data["recommendation"]["drug_code"] == "paracetamol"
    assert data["plant_recommendation"] is None


def test_paracetamol_allergy_does_not_use_plant_while_stock_remains(client):
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
    assert data["plant_recommendation"] is None
    assert "stock" in data["non_drug_protocol"].lower()


def test_plant_only_when_analgesic_stock_is_empty(client):
    client.post("/api/demo/reset")
    for code in ("paracetamol", "ibuprofen", "aspirin"):
        client.post(f"/api/demo/force-stock-zero/{code}")
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["mal de tete"]},
    )
    data = response.json()
    assert data["recommendation"] is None
    assert data["plant_recommendation"]["plant_code"] == "salix"
    assert "aspirine" in data["non_drug_protocol"].lower()
    assert "extraction" in data["non_drug_protocol"].lower()


def test_diarrhea_recommends_smecta(client):
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["diarrhee", "vomissement"]},
    )
    data = response.json()
    assert data["recommendation"]["drug_code"] == "smecta"
    assert "riz" in data["recommendation"]["rationale"].lower()


def test_vomiting_recommends_ondansetron(client):
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["vomissement"]},
    )
    assert response.json()["recommendation"]["drug_code"] == "ondansetron"


def test_constipation_recommends_macrogol(client):
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "jovani", "symptoms": ["constipation"]},
    )
    assert response.json()["recommendation"]["drug_code"] == "macrogol"


def test_empty_smecta_falls_back_to_rice(client):
    client.post("/api/demo/reset")
    client.post("/api/demo/force-stock-zero/smecta")
    client.post("/api/demo/force-stock-zero/ors")
    client.post("/api/demo/force-stock-zero/loperamide")
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["diarrhee"]},
    )
    data = response.json()
    assert data["recommendation"] is None
    assert data["plant_recommendation"]["plant_code"] == "oryza"


def test_plants_exclude_probiotic_vat(client):
    plants = {item["code"]: item for item in client.get("/api/plants").json()}
    assert "lactobacillus" not in plants
    assert "oryza" in plants
    assert "zingiber" in plants


def test_bacteria_living_pharmacy(client):
    rows = {item["code"]: item for item in client.get("/api/bacteria").json()}
    assert len(rows) == 9
    assert rows["lactobacillus_acidophilus"]["categorie"] == "Probiotique"
    assert rows["lactobacillus_acidophilus"]["ready"] is True
    assert rows["bacillus_subtilis"]["categorie"] == "Probiotique"
    assert rows["bifidobacterium_longum"]["treatable"] is True
    assert rows["penicillium_chrysogenum"]["categorie"] == "Antibiotique"
    assert rows["saccharopolyspora_erythraea"]["treatable"] is False
    assert rows["streptomyces_griseus"]["categorie"] == "Reference"
    assert rows["staphylococcus_aureus"]["treatable"] is False
    assert rows["staphylococcus_aureus"]["ready"] is False


def test_staphylococcus_cannot_be_harvested(client):
    response = client.post("/api/bacteria/staphylococcus_aureus/harvest")
    assert response.status_code == 400
    assert "traitement" in response.json()["detail"].lower()


def test_staphylococcus_cannot_be_incubated(client):
    response = client.post("/api/bacteria/staphylococcus_aureus/incubate")
    assert response.status_code == 400
    assert "incubation" in response.json()["detail"].lower()


def test_reference_strains_are_not_cultured(client):
    response = client.post("/api/bacteria/saccharopolyspora_erythraea/incubate")
    assert response.status_code == 400
    plants = {item["code"]: item for item in client.get("/api/plants").json()}
    assert plants["cinchona"]["ready"] is False
    assert plants["artemisia"]["indication"] == "reference"
    blocked = client.post("/api/plants/cinchona/harvest")
    assert blocked.status_code == 400
    assert "reference" in blocked.json()["detail"].lower()


def test_empty_rice_falls_back_to_probiotic(client):
    client.post("/api/demo/reset")
    client.post("/api/demo/force-stock-zero/smecta")
    client.post("/api/demo/force-stock-zero/ors")
    client.post("/api/demo/force-stock-zero/loperamide")
    client.post("/api/plants/oryza/harvest")
    client.post("/api/plants/oryza/harvest")
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["diarrhee"]},
    )
    data = response.json()
    assert data["recommendation"] is None
    assert data["plant_recommendation"]["plant_code"] == "lactobacillus_acidophilus"


def test_empty_antibiotics_and_plants_use_penicillium(client):
    client.post("/api/demo/reset")
    client.post("/api/demo/force-stock-zero/amoxicillin")
    client.post("/api/demo/force-stock-zero/azithromycin")
    client.post("/api/plants/thymus/harvest")
    client.post("/api/plants/thymus/harvest")
    client.post("/api/plants/allium/harvest")
    client.post("/api/plants/artemisia/harvest")
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["infection"]},
    )
    data = response.json()
    assert data["recommendation"] is None
    assert data["plant_recommendation"]["plant_code"] == "penicillium_chrysogenum"
    assert "penicilline" in data["non_drug_protocol"].lower()
    assert "fermentation" in data["non_drug_protocol"].lower()


def test_para_allergy_uses_other_drug_if_available(client):
    client.patch("/api/crew/elsa/profile", json={"allergies": ["paracetamol"]})
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["mal de tete"]},
    )
    assert response.json()["recommendation"]["drug_code"] == "ibuprofen"


def test_mal_au_cran_maps_to_headache_analgesic(client, monkeypatch):
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
            "message": "j ai mal au cran",
            "session_id": "cran",
        },
    )
    assert response.json()["evaluation"]["recommendation"]["drug_code"] == "paracetamol"


def test_insomnia_no_paracetamol(client, monkeypatch):
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
            "message": "depuis hier je dors pas",
            "session_id": "sleep",
        },
    )
    data = response.json()
    assert data["evaluation"]["recommendation"] is None
    assert "sleep_non_pharm" in data["evaluation"]["rules_fired"]
    assert "paracetamol" not in (data["content"] or "").lower()


def test_fatigue_after_back_pain_does_not_reuse_analgesic(client, monkeypatch):
    from app.services import ollama_client

    async def _tpl(message, evaluation, history="", symptoms=None, meta_followup=False):
        return (
            ollama_client.template_reply(
                evaluation, message, symptoms=symptoms or [], meta_followup=meta_followup
            ),
            "template",
        )

    monkeypatch.setattr(ollama_client, "reformulate_with_ollama", _tpl)
    created = client.post("/api/conversations", json={"crew_member_code": "raphael"})
    cid = created.json()["id"]
    client.post(
        "/api/chat/message",
        json={"crew_member_code": "raphael", "message": "j ai mal au dos", "conversation_id": cid},
    )
    second = client.post(
        "/api/chat/message",
        json={
            "crew_member_code": "raphael",
            "message": "je me sens fatiguer",
            "conversation_id": cid,
        },
    )
    ev = second.json()["evaluation"]
    assert ev["recommendation"] is None
    assert "fatigue_non_pharm" in ev["rules_fired"]


def test_mal_a_dormir_recognized(client, monkeypatch):
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
            "crew_member_code": "raphael",
            "message": "j ai du mal a dormir",
            "session_id": "dormir2",
        },
    )
    assert "sleep_non_pharm" in response.json()["evaluation"]["rules_fired"]


def test_perte_appetit_non_pharm(client):
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "raphael", "symptoms": ["perte appetit"]},
    )
    assert "appetite_non_pharm" in response.json()["rules_fired"]


def test_raphael_para_allergy_blocks_with_clear_reasons(client):
    client.post("/api/demo/reset")
    client.patch(
        "/api/crew/raphael/profile",
        json={"allergies": ["paracetamol"], "current_treatments": [{"drug_code": "warfarin", "dose_mg": 5}]},
    )
    response = client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "raphael", "symptoms": ["mal de tete"]},
    )
    data = response.json()
    assert data["recommendation"] is None
    protocol = (data["non_drug_protocol"] or "").lower()
    assert "ibuprofen" in protocol or "warfarin" in protocol or "warfarine" in protocol
    assert "paracetamol" in protocol or "allergie" in protocol
