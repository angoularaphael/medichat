from datetime import timedelta

from app.services import surveillance


def test_fever_alone_does_not_isolate():
    scored = surveillance.score_vitals(38.7, 98, 78, 16)
    assert scored["level"] == "low"
    assert surveillance.needs_isolation(38.7, 98, 78, 16) is False


def test_fever_with_low_oxygen_isolates():
    assert surveillance.needs_isolation(38.7, 93, 78, 16) is True


def test_false_alarm_scenario(client):
    data = client.post("/api/surveillance/scenario/false-alarm").json()
    raphael = next(row for row in data["subjects"] if row["code"] == "raphael")
    assert data["crew_count"] == 40
    assert raphael["level"] == "low"
    assert raphael["isolated"] is False
    assert data["isolated_count"] == 0
    assert data["contacts"] == []


def test_contamination_fills_zones_and_records_contacts(client):
    data = client.post("/api/surveillance/scenario/contamination").json()
    assert data["isolated_count"] == 6
    assert data["waiting"] == []
    assert any(row["open"] for row in data["contacts"])
    assert any(zone["occupants"] for zone in data["zones"])
    assert any(not zone["full"] for zone in data["zones"])


def test_slow_burn_marks_last_level_change(client):
    data = client.post("/api/surveillance/scenario/slow-burn").json()
    elisa = next(row for row in data["subjects"] if row["code"] == "elisa")
    assert len(elisa["samples"]) >= 8
    assert elisa["level_change_at"]
    assert elisa["isolated"] is True


def test_chat_does_not_change_watch_score(client):
    before = client.get("/api/surveillance").json()
    client.post(
        "/api/care/evaluate",
        json={"crew_member_code": "elsa", "symptoms": ["mal de tete"]},
    )
    after = client.get("/api/surveillance").json()
    assert before["subjects"] == after["subjects"]


def test_release_needs_two_clears_and_two_minutes(client):
    from datetime import datetime, timezone

    from app.db.session import SessionLocal
    from app.models.entities import WatchSubject

    start = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        surveillance.ensure_subjects(db)
        surveillance.observe(db, "elsa", (39.2, 92, 124, 26), start)
        db.commit()
        row = db.query(WatchSubject).filter(WatchSubject.code == "elsa").one()
        assert row.zone_code
        surveillance.observe(db, "elsa", (36.8, 98, 74, 15), start + timedelta(seconds=5))
        surveillance.observe(db, "elsa", (36.8, 98, 74, 15), start + timedelta(seconds=20))
        db.commit()
        db.refresh(row)
        assert row.zone_code
        surveillance.observe(db, "elsa", (39.2, 92, 124, 26), start + timedelta(seconds=40))
        db.commit()
        db.refresh(row)
        assert row.clear_streak == 0
        surveillance.observe(db, "elsa", (36.8, 98, 74, 15), start + timedelta(seconds=50))
        surveillance.observe(db, "elsa", (36.8, 98, 74, 15), start + timedelta(seconds=130))
        db.commit()
        db.refresh(row)
        assert row.zone_code is None
    finally:
        db.close()
