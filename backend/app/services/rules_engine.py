from sqlalchemy.orm import Session

from app.models.entities import Drug, DrugInteraction, CrewMember
from app.schemas.api import CareEvaluationResult, ExcludedOption, Recommendation
from app.services import substitution


AINS_CLASS = "AINS"
RED_FLAG_SYMPTOMS = {"chest_pain", "douleur_thoracique", "douleur thoracique"}


def _symptom_indication(symptoms: list[str]) -> str:
    s = " ".join(symptoms).lower()
    if "headache" in s or "mal de tete" in s or "mal de tête" in s or "cephalee" in s:
        return "pain_mild"
    if "fievre" in s or "fever" in s:
        return "fever"
    return "general"


def _candidate_drugs(db: Session, indication: str) -> list[Drug]:
    if indication == "pain_mild":
        codes = ["paracetamol", "ibuprofen", "aspirin"]
    elif indication == "fever":
        codes = ["paracetamol", "ibuprofen"]
    else:
        codes = ["paracetamol"]
    drugs = db.query(Drug).filter(Drug.code.in_(codes)).all()
    return sorted(drugs, key=lambda d: codes.index(d.code) if d.code in codes else 99)


def _has_allergy(member: CrewMember, drug: Drug) -> bool:
    allergies = [a.lower() for a in (member.allergies or [])]
    if drug.substance.lower() in allergies:
        return True
    if drug.code.lower() in allergies:
        return True
    if AINS_CLASS.lower() in allergies and drug.therapeutic_class == AINS_CLASS:
        return True
    if "ibuprofen" in allergies and drug.code == "ibuprofen":
        return True
    return False


def _interaction_blocks(db: Session, member: CrewMember, drug: Drug) -> str | None:
    active_codes = [t.get("drug_code") for t in (member.current_treatments or [])]
    active_ids = [
        d.id for d in db.query(Drug).filter(Drug.code.in_(active_codes)).all()
    ] if active_codes else []
    if not active_ids:
        return None
    for other_id in active_ids:
        inter = (
            db.query(DrugInteraction)
            .filter(
                ((DrugInteraction.drug_a_id == drug.id) & (DrugInteraction.drug_b_id == other_id))
                | ((DrugInteraction.drug_a_id == other_id) & (DrugInteraction.drug_b_id == drug.id))
            )
            .first()
        )
        if inter:
            return inter.description
    return None


def evaluate_care(
    db: Session,
    *,
    crew_member_code: str,
    symptoms: list[str],
    requested_drug_code: str | None = None,
    requested_dose_mg: float | None = None,
) -> CareEvaluationResult:
    rules: list[str] = []
    excluded: list[ExcludedOption] = []

    member = db.query(CrewMember).filter(CrewMember.code == crew_member_code).first()
    if not member:
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="unknown",
            rules_fired=["patient_unknown"],
            non_drug_protocol="Identification requise avant toute proposition.",
        )

    normalized = {s.lower().replace(" ", "_") for s in symptoms}
    if normalized & RED_FLAG_SYMPTOMS or any("thorac" in s for s in symptoms):
        rules.append("red_flag_escalation")
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=True,
            urgency="critical",
            rules_fired=rules,
            non_drug_protocol="Protocole d'urgence: contact medecin de bord immediat.",
        )

    indication = _symptom_indication(symptoms)
    candidates = _candidate_drugs(db, indication)

    if requested_drug_code:
        req = db.query(Drug).filter(Drug.code == requested_drug_code).first()
        if req:
            candidates = [req] + [d for d in candidates if d.id != req.id]

    excluded_codes: set[str] = set()

    for drug in candidates:
        if _has_allergy(member, drug):
            rules.append(f"allergy_{drug.code}")
            excluded.append(
                ExcludedOption(
                    drug_code=drug.code,
                    reason_code="allergy",
                    reason_text=f"Allergie ou classe contre-indiquee ({drug.name}).",
                )
            )
            excluded_codes.add(drug.code)
            continue

        inter = _interaction_blocks(db, member, drug)
        if inter:
            rules.append(f"interaction_{drug.code}")
            excluded.append(
                ExcludedOption(
                    drug_code=drug.code,
                    reason_code="interaction",
                    reason_text=inter,
                )
            )
            excluded_codes.add(drug.code)
            continue

        dose = requested_dose_mg if requested_drug_code == drug.code else min(drug.dose_max_mg, 500.0)
        if requested_dose_mg and requested_drug_code == drug.code and dose > drug.dose_max_mg:
            rules.append("dose_exceeded")
            excluded.append(
                ExcludedOption(
                    drug_code=drug.code,
                    reason_code="dose",
                    reason_text=f"Dose demandee {dose} mg > max {drug.dose_max_mg} mg.",
                )
            )
            excluded_codes.add(drug.code)

    for drug in candidates:
        if drug.code in excluded_codes:
            continue

        dose = requested_dose_mg if requested_drug_code == drug.code else min(drug.dose_max_mg, 500.0)

        if drug.stock_units <= 0:
            if drug.code not in excluded_codes:
                rules.append(f"stock_empty_{drug.code}")
                excluded.append(
                    ExcludedOption(
                        drug_code=drug.code,
                        reason_code="stock",
                        reason_text=f"Stock epuise pour {drug.name}.",
                    )
                )
                excluded_codes.add(drug.code)
            subs = substitution.find_substitutes(db, drug.id, indication)
            for sub in subs:
                if sub.code in excluded_codes or _has_allergy(member, sub):
                    continue
                rules.append(f"substitution_{sub.code}")
                return CareEvaluationResult(
                    excluded_options=excluded,
                    recommendation=Recommendation(
                        drug_code=sub.code,
                        drug_name=sub.name,
                        dose_mg=min(dose, sub.dose_max_mg),
                        rationale=f"Substitution de {drug.name} (stock ou exclusion).",
                    ),
                    escalate_to_physician=False,
                    urgency="routine",
                    rules_fired=rules,
                )
            continue

        rules.append(f"recommend_{drug.code}")
        return CareEvaluationResult(
            excluded_options=excluded,
            recommendation=Recommendation(
                drug_code=drug.code,
                drug_name=drug.name,
                dose_mg=dose,
                rationale=f"Indication {indication}, stock OK.",
            ),
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
        )

    rules.append("no_option")
    return CareEvaluationResult(
        excluded_options=excluded,
        recommendation=None,
        escalate_to_physician=False,
        urgency="routine",
        rules_fired=rules,
        non_drug_protocol="Repos, hydratation, surveillance. Reevaluation sous 24 h.",
    )
