from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import CrewMember, Drug, StockMovement
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
    SecurityAlertOut,
    TriageEntry,
)
from app.services import autonomy, crisis, journal, mqtt_service, ollama_client, rules_engine, triage
from app.seed import demo_data
from app.models.entities import ChatMessage

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok", "service": "eir-api"}


@router.get("/crew")
def list_crew(db: Session = Depends(get_db)):
    members = db.query(CrewMember).order_by(CrewMember.id).all()
    return [
        {
            "code": m.code,
            "full_name": m.full_name,
            "age": m.age,
            "allergies": m.allergies,
            "health_status": m.health_status.value,
        }
        for m in members
    ]


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
def care_evaluate(body: CareEvaluateRequest, db: Session = Depends(get_db)):
    return rules_engine.evaluate_care(
        db,
        crew_member_code=body.crew_member_code,
        symptoms=body.symptoms,
        requested_drug_code=body.requested_drug_code,
        requested_dose_mg=body.requested_dose_mg,
    )


@router.post("/care/confirm")
def care_confirm(body: CareConfirmRequest, db: Session = Depends(get_db)):
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
async def chat_message(body: ChatMessageRequest, db: Session = Depends(get_db)):
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
def trigger_crisis(db: Session = Depends(get_db)):
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
def activate_rationing(db: Session = Depends(get_db)):
    data = crisis.activate_rationing(db)
    return AutonomyCompareResponse(
        on_demand=_map_autonomy(data["on_demand"]),
        rationing_quarantine=_map_autonomy(data["rationing_quarantine"]),
        crisis_active=data["crisis_active"],
        rationing_active=data["rationing_active"],
    )


@router.post("/demo/force-stock-zero/{drug_code}")
def force_stock_zero(drug_code: str, db: Session = Depends(get_db)):
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
    return {"ok": True}


@router.post("/demo/reset")
def reset_demo(db: Session = Depends(get_db)):
    demo_data.reset_demo(db)
    journal.log_decision(db, action="demo_reset", summary="Jeu de donnees demo reinitialise")
    return {"ok": True}


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
def security_alerts(db: Session = Depends(get_db)):
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
