from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.entities import CrewMember, Drug, StockMovement, User
from app.schemas.api import (
    AutonomyCompareResponse,
    AutonomyDrugRow,
    AutonomyResponse,
    CareConfirmRequest,
    CareEvaluateRequest,
    CareEvaluationResult,
    ChatMessageRequest,
    ChatMessageResponse,
    CrisisTriggerResponse,
    DecisionLogEntry,
    ProfileUpdate,
    SecurityAlertOut,
    TriageEntry,
)
from app.services import autonomy, crisis, journal, mqtt_service, ollama_client, plants, rules_engine, triage
from app.seed import demo_data
from app.models.entities import ChatMessage

router = APIRouter(prefix="/api")


def _assert_profile_access(user: User, crew_member_code: str) -> None:
    if user.role != "admin" and user.crew_member_code != crew_member_code:
        raise HTTPException(403, "Ce profil equipage ne vous appartient pas")


@router.get("/health")
def health():
    return {"status": "ok", "service": "eir-api"}


def _crew_payload(member: CrewMember) -> dict:
    return {
        "code": member.code,
        "full_name": member.full_name,
        "age": member.age,
        "allergies": member.allergies or [],
        "health_status": member.health_status.value,
        "avatar_data": member.avatar_data,
    }


@router.get("/crew")
def list_crew(db: Session = Depends(get_db)):
    members = db.query(CrewMember).order_by(CrewMember.id).all()
    return [_crew_payload(member) for member in members]


@router.get("/crew/{code}")
def get_crew_member(
    code: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    _assert_profile_access(user, code)
    member = db.query(CrewMember).filter(CrewMember.code == code).first()
    if not member:
        raise HTTPException(404, "Profil equipage inconnu")
    return _crew_payload(member)


@router.patch("/crew/{code}/profile")
def update_crew_profile(
    code: str,
    body: ProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    _assert_profile_access(user, code)
    member = db.query(CrewMember).filter(CrewMember.code == code).first()
    if not member:
        raise HTTPException(404, "Profil equipage inconnu")
    cleaned: list[str] = []
    for item in body.allergies:
        value = " ".join(str(item).split())[:64]
        if value and value not in cleaned:
            cleaned.append(value)
    member.allergies = cleaned
    if body.full_name:
        member.full_name = body.full_name.strip()[:128]
        owner = db.query(User).filter(User.crew_member_code == code).first()
        if owner:
            owner.full_name = member.full_name
    if body.avatar_data:
        if not body.avatar_data.startswith("data:image/") or len(body.avatar_data) > 900_000:
            raise HTTPException(400, "Photo trop lourde ou format invalide")
        member.avatar_data = body.avatar_data
    else:
        member.avatar_data = None
    db.commit()
    journal.log_decision(
        db,
        action="profile_update",
        summary=f"Profil {member.full_name} mis a jour",
        crew_member_id=member.id,
        payload={"allergies": member.allergies},
    )
    return _crew_payload(member)


@router.get("/drugs")
def list_drugs(db: Session = Depends(get_db)):
    drugs = db.query(Drug).order_by(Drug.name).all()
    return [
        {
            "code": d.code,
            "name": d.name,
            "stock_units": d.stock_units,
            "therapeutic_class": d.therapeutic_class,
            "is_critical": d.is_critical,
        }
        for d in drugs
    ]


@router.post("/care/evaluate", response_model=CareEvaluationResult)
def care_evaluate(
    body: CareEvaluateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    _assert_profile_access(user, body.crew_member_code)
    return rules_engine.evaluate_care(
        db,
        crew_member_code=body.crew_member_code,
        symptoms=body.symptoms,
        requested_drug_code=body.requested_drug_code,
        requested_dose_mg=body.requested_dose_mg,
    )


@router.post("/care/confirm")
def care_confirm(
    body: CareConfirmRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    _assert_profile_access(user, body.crew_member_code)
    member = db.query(CrewMember).filter(CrewMember.code == body.crew_member_code).first()
    if not member:
        raise HTTPException(404, "Patient inconnu")
    drug = db.query(Drug).filter(Drug.code == body.drug_code).first()
    if not drug:
        raise HTTPException(404, "Medicament inconnu")
    if drug.stock_units <= 0:
        raise HTTPException(400, "Stock insuffisant")

    before = drug.stock_units
    drug.stock_units -= 1
    db.add(
        StockMovement(
            drug_id=drug.id,
            delta=-1,
            reason="care_confirm",
            crew_member_id=member.id,
        )
    )
    db.commit()

    if drug.stock_units == 0:
        mqtt_service.publish_stock_low(drug.code, 0)

    journal.log_decision(
        db,
        action="care_confirm",
        summary=f"Sortie {drug.name} pour {member.full_name}",
        crew_member_id=member.id,
        payload={"drug_code": drug.code, "dose_mg": body.dose_mg},
        stock_snapshot={drug.code: {"before": before, "after": drug.stock_units}},
    )
    return {"ok": True, "stock_remaining": drug.stock_units}


@router.post("/chat/message", response_model=ChatMessageResponse)
async def chat_message(
    body: ChatMessageRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    _assert_profile_access(user, body.crew_member_code)
    symptoms = ollama_client.extract_symptoms(body.message)
    evaluation = rules_engine.evaluate_care(
        db,
        crew_member_code=body.crew_member_code,
        symptoms=symptoms,
    )
    content, mode = await ollama_client.reformulate_with_ollama(body.message, evaluation)

    db.add(ChatMessage(session_id=body.session_id, role="user", content=body.message))
    db.add(
        ChatMessage(
            session_id=body.session_id,
            role="assistant",
            content=content,
            meta={"llm_mode": mode, "evaluation": evaluation.model_dump()},
        )
    )
    db.commit()

    return ChatMessageResponse(
        session_id=body.session_id,
        role="assistant",
        content=content,
        evaluation=evaluation,
        llm_mode=mode,
    )


def _map_autonomy(data: dict) -> AutonomyResponse:
    return AutonomyResponse(
        policy=data["policy"],
        global_days=data["global_days"],
        sick_count=data["sick_count"],
        crew_size=data["crew_size"],
        drugs=[AutonomyDrugRow(**row) for row in data["drugs"]],
    )


@router.get("/autonomy", response_model=AutonomyCompareResponse)
def get_autonomy(db: Session = Depends(get_db)):
    data = autonomy.compare_policies(db)
    return AutonomyCompareResponse(
        on_demand=_map_autonomy(data["on_demand"]),
        rationing_quarantine=_map_autonomy(data["rationing_quarantine"]),
        crisis_active=data["crisis_active"],
        rationing_active=data["rationing_active"],
    )


@router.get("/triage", response_model=list[TriageEntry])
def get_triage(db: Session = Depends(get_db)):
    return [TriageEntry(**row) for row in triage.list_triage(db)]


@router.post("/crisis/trigger", response_model=CrisisTriggerResponse)
def trigger_crisis(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = crisis.trigger_crisis(db)
    auto = result["autonomy_before"]
    mqtt_service.publish_crisis(
        result["sick_ratio"],
        auto["on_demand"]["global_days"],
    )
    return CrisisTriggerResponse(
        sick_count=result["sick_count"],
        sick_ratio=result["sick_ratio"],
        autonomy_before=AutonomyCompareResponse(
            on_demand=_map_autonomy(auto["on_demand"]),
            rationing_quarantine=_map_autonomy(auto["rationing_quarantine"]),
            crisis_active=auto["crisis_active"],
            rationing_active=auto["rationing_active"],
        ),
    )


@router.post("/crisis/rationing", response_model=AutonomyCompareResponse)
def activate_rationing(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    data = crisis.activate_rationing(db)
    return AutonomyCompareResponse(
        on_demand=_map_autonomy(data["on_demand"]),
        rationing_quarantine=_map_autonomy(data["rationing_quarantine"]),
        crisis_active=data["crisis_active"],
        rationing_active=data["rationing_active"],
    )


@router.post("/demo/force-stock-zero/{drug_code}")
def force_stock_zero(
    drug_code: str,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    drug = db.query(Drug).filter(Drug.code == drug_code).first()
    if not drug:
        raise HTTPException(404, "Medicament inconnu")
    drug.stock_units = 0
    db.commit()
    mqtt_service.publish_stock_low(drug.code, 0)
    journal.log_decision(
        db,
        action="demo_stock_zero",
        summary=f"Demo: stock {drug.name} force a zero",
        payload={"drug_code": drug_code},
    )
    return {"ok": True, "stock_remaining": 0}


@router.post("/demo/restock")
def restock_demo(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    demo_data.restock_drugs(db)
    journal.log_decision(db, action="demo_restock", summary="Stocks medicaments restaures")
    return {"ok": True}


@router.post("/demo/reset")
def reset_demo(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    demo_data.reset_demo(db)
    journal.log_decision(db, action="demo_reset", summary="Mission reinitialisee: sante, stocks et cultures")
    return {"ok": True}


@router.get("/plants")
def list_plants(db: Session = Depends(get_db)):
    return [plants.serialize(row) for row in plants.list_plants(db)]


@router.post("/plants/{plant_code}/irrigate")
def irrigate_plant(
    plant_code: str,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    plant = plants.irrigate(db, plant_code)
    if not plant:
        raise HTTPException(404, "Culture inconnue")
    return plants.serialize(plant)


@router.post("/plants/{plant_code}/boost")
def boost_plant(
    plant_code: str,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    plant = plants.boost_light(db, plant_code)
    if not plant:
        raise HTTPException(404, "Culture inconnue")
    return plants.serialize(plant)


@router.post("/plants/{plant_code}/harvest")
def harvest_plant(
    plant_code: str,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
):
    plant, error = plants.harvest(db, plant_code)
    if plant is None:
        raise HTTPException(404, "Culture inconnue")
    if error:
        raise HTTPException(400, error)
    return plants.serialize(plant)


@router.get("/journal", response_model=list[DecisionLogEntry])
def get_journal(db: Session = Depends(get_db)):
    entries = journal.list_recent(db)
    return [
        DecisionLogEntry(
            id=e.id,
            action=e.action,
            summary=e.summary,
            payload=e.payload or {},
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]


@router.get("/security/alerts", response_model=list[SecurityAlertOut])
def security_alerts(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    alerts = mqtt_service.list_security_alerts(db)
    return [
        SecurityAlertOut(
            id=a.id,
            source=a.source,
            payload=a.payload,
            created_at=a.created_at.isoformat(),
        )
        for a in alerts
    ]
