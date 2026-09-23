"""Veille deterministe. Ce module n'importe pas le chat ni Ollama.

Le score vient uniquement des constantes. Une reponse de Medichat ne le modifie pas.
Les seuils sont une convention de demonstration, pas une validation NEWS2.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.entities import CrisisState, VitalSample, WatchSubject, ZoneContact

ZONES = (("Q1", 2), ("Q2", 2), ("Q3", 2), ("Q4", 2))
NAMED = (
    ("raphael", "Raphael"),
    ("elisa", "Elisa"),
    ("elsa", "Elsa"),
    ("jovani", "Jovani"),
    ("carine", "Carine"),
)
NORMAL = (36.8, 98.0, 74.0, 15.0)
SICK = (39.2, 92.0, 124.0, 26.0)
FEVER_ONLY = (38.7, 98.0, 78.0, 16.0)
WINDOW = timedelta(minutes=10)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def temperature_points(value: float) -> int:
    if value <= 35:
        return 3
    if value <= 36:
        return 1
    if value <= 38:
        return 0
    if value <= 39:
        return 1
    return 2


def spo2_points(value: float) -> int:
    if value <= 91:
        return 3
    if value <= 93:
        return 2
    if value <= 95:
        return 1
    return 0


def pulse_points(value: float) -> int:
    if value <= 40:
        return 3
    if value <= 50:
        return 1
    if value <= 90:
        return 0
    if value <= 110:
        return 1
    if value <= 130:
        return 2
    return 3


def respiration_points(value: float) -> int:
    if value <= 8:
        return 3
    if value <= 11:
        return 1
    if value <= 20:
        return 0
    if value <= 24:
        return 2
    return 3


def score_vitals(
    temperature: float | None,
    spo2: float | None,
    pulse: float | None,
    respiration: float | None,
) -> dict:
    if None in (temperature, spo2, pulse, respiration):
        return {"total": 0, "level": "missing", "parts": []}
    parts = [
        temperature_points(temperature),
        spo2_points(spo2),
        pulse_points(pulse),
        respiration_points(respiration),
    ]
    total = sum(parts)
    if total >= 7:
        level = "high"
    elif total >= 5 or any(part == 3 for part in parts):
        level = "medium"
    elif total >= 1:
        level = "low"
    else:
        level = "routine"
    return {"total": total, "level": level, "parts": parts}


def needs_isolation(
    temperature: float | None,
    spo2: float | None,
    pulse: float | None,
    respiration: float | None,
) -> bool:
    scored = score_vitals(temperature, spo2, pulse, respiration)
    if scored["level"] == "missing":
        return False
    fever = temperature is not None and temperature > 38
    desaturation = spo2 is not None and spo2 <= 95
    high_respiration = respiration is not None and respiration > 20
    medium_or_more = scored["level"] in {"medium", "high"}
    return fever and (desaturation or high_respiration or medium_or_more)


def _roster() -> list[tuple[str, str]]:
    rows = list(NAMED)
    for index in range(6, 41):
        rows.append((f"cabine-{index:02d}", f"Cabine {index:02d}"))
    return rows


def ensure_subjects(db: Session) -> None:
    existing = {row.code for row in db.query(WatchSubject).all()}
    for code, name in _roster():
        if code in existing:
            continue
        db.add(WatchSubject(code=code, full_name=name))
    db.flush()


def _clear_board(db: Session) -> None:
    db.query(VitalSample).delete()
    db.query(ZoneContact).delete()
    for row in db.query(WatchSubject).all():
        row.zone_code = None
        row.zone_since = None
        row.clear_streak = 0
        row.last_clear_at = None
        row.waiting_place = False
    db.flush()


def _occupy(db: Session, subject: WatchSubject, moment: datetime) -> None:
    if subject.zone_code:
        return
    for code, capacity in ZONES:
        occupants = (
            db.query(WatchSubject)
            .filter(WatchSubject.zone_code == code)
            .filter(WatchSubject.code != subject.code)
            .all()
        )
        if len(occupants) >= capacity:
            continue
        subject.zone_code = code
        subject.zone_since = moment
        subject.clear_streak = 0
        subject.last_clear_at = None
        subject.waiting_place = False
        for other in occupants:
            left, right = sorted((subject.code, other.code))
            db.add(
                ZoneContact(
                    zone_code=code,
                    subject_a=left,
                    subject_b=right,
                    started_at=moment,
                )
            )
        return
    subject.waiting_place = True


def _release(db: Session, subject: WatchSubject, moment: datetime) -> None:
    zone = subject.zone_code
    subject.zone_code = None
    subject.zone_since = None
    subject.clear_streak = 0
    subject.last_clear_at = None
    subject.waiting_place = False
    if not zone:
        return
    open_rows = (
        db.query(ZoneContact)
        .filter(ZoneContact.zone_code == zone)
        .filter(ZoneContact.ended_at.is_(None))
        .filter((ZoneContact.subject_a == subject.code) | (ZoneContact.subject_b == subject.code))
        .all()
    )
    for row in open_rows:
        row.ended_at = moment


def observe(
    db: Session,
    code: str,
    reading: tuple[float | None, float | None, float | None, float | None],
    moment: datetime | None = None,
) -> WatchSubject:
    ensure_subjects(db)
    subject = db.query(WatchSubject).filter(WatchSubject.code == code).first()
    if subject is None:
        raise ValueError(code)
    moment = _aware(moment) or _utcnow()
    temperature, spo2, pulse, respiration = reading
    scored = score_vitals(temperature, spo2, pulse, respiration)
    db.add(
        VitalSample(
            subject_code=code,
            recorded_at=moment,
            temperature_c=temperature,
            spo2=spo2,
            pulse=pulse,
            respiration=respiration,
            score=scored["total"],
            level=scored["level"],
        )
    )
    if temperature is not None:
        subject.temperature_c = temperature
    if spo2 is not None:
        subject.spo2 = spo2
    if pulse is not None:
        subject.pulse = pulse
    if respiration is not None:
        subject.respiration = respiration
    subject.score = scored["total"]
    subject.level = scored["level"]

    if scored["level"] == "missing":
        if subject.zone_code:
            subject.clear_streak = 0
            subject.last_clear_at = None
        db.flush()
        return subject

    if needs_isolation(temperature, spo2, pulse, respiration):
        subject.clear_streak = 0
        subject.last_clear_at = None
        if not subject.zone_code:
            _occupy(db, subject, moment)
        db.flush()
        return subject

    subject.waiting_place = False
    if subject.zone_code and subject.zone_since is not None:
        previous = _aware(subject.last_clear_at)
        if previous is None or (moment - previous).total_seconds() >= 2:
            subject.clear_streak += 1
            subject.last_clear_at = moment
        held = (moment - _aware(subject.zone_since)).total_seconds()
        if subject.clear_streak >= 2 and held >= 120:
            _release(db, subject, moment)
    db.flush()
    return subject


def _write_all(db: Session, readings: dict[str, tuple], moment: datetime) -> None:
    for code, _name in _roster():
        observe(db, code, readings.get(code, NORMAL), moment)


def run_scenario(db: Session, name: str) -> dict:
    ensure_subjects(db)
    _clear_board(db)
    end = _utcnow()
    if name == "false-alarm":
        readings = {code: NORMAL for code, _name in _roster()}
        readings["raphael"] = FEVER_ONLY
        _write_all(db, readings, end)
    elif name == "contamination":
        sick_codes = ["elisa", "elsa", "cabine-06", "cabine-07", "cabine-08", "cabine-09"]
        readings = {code: (SICK if code in sick_codes else NORMAL) for code, _name in _roster()}
        _write_all(db, readings, end)
    elif name == "slow-burn":
        end_stamp = end - timedelta(minutes=9)
        for code, _name in _roster():
            if code == "elisa":
                continue
            observe(db, code, NORMAL, end_stamp)
        curve = [
            (9, (37.1, 98, 76, 15)),
            (8, (37.3, 98, 78, 16)),
            (7, (37.6, 97, 82, 16)),
            (6, (37.9, 97, 84, 17)),
            (5, (38.4, 97, 88, 18)),
            (4, (38.6, 94, 102, 22)),
            (3, (38.8, 93, 110, 24)),
            (2, (39.0, 92, 118, 26)),
            (1, (39.1, 92, 120, 26)),
            (0, (39.2, 91, 124, 28)),
        ]
        for minutes_ago, reading in curve:
            observe(db, "elisa", reading, end - timedelta(minutes=minutes_ago))
    else:
        name = "nominal"
        _write_all(db, {}, end)
    state = db.query(CrisisState).filter(CrisisState.id == 1).first()
    if state is None:
        state = CrisisState(id=1, watch_scenario=name)
        db.add(state)
    else:
        state.watch_scenario = name
    db.commit()
    payload = snapshot(db)
    payload["scenario"] = name
    return payload


def reset_watch(db: Session) -> None:
    ensure_subjects(db)
    run_scenario(db, "nominal")


def _samples(db: Session, code: str, moment: datetime) -> list[VitalSample]:
    start = moment - WINDOW
    rows = (
        db.query(VitalSample)
        .filter(VitalSample.subject_code == code)
        .order_by(VitalSample.recorded_at.asc())
        .all()
    )
    return [row for row in rows if _aware(row.recorded_at) and _aware(row.recorded_at) >= start]


def snapshot(db: Session) -> dict:
    ensure_subjects(db)
    moment = _utcnow()
    subjects = db.query(WatchSubject).order_by(WatchSubject.code).all()
    zones = []
    for code, capacity in ZONES:
        occupants = [row.full_name for row in subjects if row.zone_code == code]
        zones.append(
            {
                "code": code,
                "capacity": capacity,
                "occupants": occupants,
                "full": len(occupants) >= capacity,
            }
        )
    contacts = []
    for row in db.query(ZoneContact).order_by(ZoneContact.started_at.desc()).all():
        contacts.append(
            {
                "zone_code": row.zone_code,
                "subject_a": row.subject_a,
                "subject_b": row.subject_b,
                "started_at": _aware(row.started_at).isoformat() if row.started_at else None,
                "ended_at": _aware(row.ended_at).isoformat() if row.ended_at else None,
                "open": row.ended_at is None,
            }
        )
    rows = []
    for subject in subjects:
        history = _samples(db, subject.code, moment)
        change_at = None
        for index, sample in enumerate(history):
            if index and sample.level != history[index - 1].level:
                change_at = _aware(sample.recorded_at).isoformat()
        rows.append(
            {
                "code": subject.code,
                "full_name": subject.full_name,
                "temperature_c": subject.temperature_c,
                "spo2": subject.spo2,
                "pulse": subject.pulse,
                "respiration": subject.respiration,
                "score": subject.score,
                "level": subject.level,
                "zone_code": subject.zone_code,
                "waiting_place": subject.waiting_place,
                "isolated": subject.zone_code is not None,
                "level_change_at": change_at,
                "samples": [
                    {
                        "recorded_at": _aware(sample.recorded_at).isoformat(),
                        "score": sample.score,
                        "level": sample.level,
                    }
                    for sample in history
                ],
            }
        )
    isolated = sum(1 for row in rows if row["isolated"])
    waiting = [row["full_name"] for row in rows if row["waiting_place"]]
    state = db.query(CrisisState).filter(CrisisState.id == 1).first()
    return {
        "scenario": state.watch_scenario if state and state.watch_scenario else "nominal",
        "note": (
            "Score calcule seulement sur les constantes. "
            "Medichat n'entre pas dans ce calcul. Convention de demonstration, pas un score clinique valide."
        ),
        "crew_count": len(rows),
        "isolated_count": isolated,
        "zones": zones,
        "waiting": waiting,
        "contacts": contacts,
        "subjects": rows,
    }
