from app.services.gastro_estimate import gastro_six_month_estimate


def test_six_month_gastro_stock_is_insufficient():
    data = gastro_six_month_estimate()
    assert data["crew_size"] == 20
    assert data["sick_at_once"] == 3
    ors = next(row for row in data["rows"] if row["drug_code"] == "ors")
    assert ors["need_6_months"] > ors["stock_units"]
    assert ors["shortage_units"] == ors["need_6_months"] - ors["stock_units"]


def test_gastro_estimate_route(client):
    response = client.get("/api/clinical/gastro-estimate")
    assert response.status_code == 200
    assert len(response.json()["rows"]) == 4
