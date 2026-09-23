from sqlalchemy.orm import Session

from app.models.entities import Drug, DrugInteraction, CrewMember
from app.schemas.api import CareEvaluationResult, ExcludedOption, PlantRecommendation, Recommendation
from app.services import plants, substitution


AINS_CLASS = "AINS"
RED_FLAG_SYMPTOMS = {
    "chest_pain",
    "douleur_thoracique",
    "douleur thoracique",
    "difficulte_respiratoire",
}

ALLERGY_ALIASES = {
    "para": "paracetamol",
    "paracetamol": "paracetamol",
    "paracetamole": "paracetamol",
    "doliprane": "paracetamol",
    "acetaminophen": "paracetamol",
    "ibuprofene": "ibuprofen",
    "ibuprofen": "ibuprofen",
    "advil": "ibuprofen",
    "aspirine": "aspirin",
    "aspirin": "aspirin",
    "amoxicilline": "amoxicillin",
    "amoxicillin": "amoxicillin",
    "azithromycine": "azithromycin",
    "azithromycin": "azithromycin",
    "smecta": "smecta",
    "diosmectite": "smecta",
    "imodium": "loperamide",
    "loperamide": "loperamide",
}


def _normalize_token(value: str) -> str:
    table = str.maketrans("éèêëàâäùûüôöîïç", "eeeeaaauuuooiic")
    return value.lower().translate(table).strip()


def _allergy_tokens(member: CrewMember) -> set[str]:
    tokens: set[str] = set()
    for raw in member.allergies or []:
        normalized = _normalize_token(str(raw))
        if not normalized:
            continue
        tokens.add(normalized)
        for piece in normalized.replace("/", " ").replace(",", " ").split():
            tokens.add(piece)
            mapped = ALLERGY_ALIASES.get(piece)
            if mapped:
                tokens.add(mapped)
        mapped = ALLERGY_ALIASES.get(normalized)
        if mapped:
            tokens.add(mapped)
    return tokens


def _has_allergy(member: CrewMember, drug: Drug) -> bool:
    tokens = _allergy_tokens(member)
    if not tokens:
        return False
    substance = _normalize_token(drug.substance)
    code = _normalize_token(drug.code)
    name = _normalize_token(drug.name)
    if substance in tokens or code in tokens or name in tokens:
        return True
    if "ains" in tokens and drug.therapeutic_class == AINS_CLASS:
        return True
    return False


ONBOARD_WATCH = (
    "Symptome enregistre a bord. Repos, hydratation et surveillance des constantes. "
    "Une demande d'avis sol est mise en file, mais la latence et les coupures interdisent d'attendre. "
    "Si aggravation: protocole d'urgence EIR (isolement, oxygene, monitoring)."
)
ONBOARD_EMERGENCY = (
    "Protocole d'urgence embarque: immobilisation, oxygene, monitoring continu. "
    "Message sol en file, sans attendre: le lien Terre est lent et peut se couper. "
    "Decision immediate EIR."
)
ONBOARD_WATCH_24H = (
    "Repos, hydratation, surveillance a bord. Reevaluation EIR sous 24 h. "
    "Avis sol demande en arriere-plan, non bloquant."
)


def _symptom_indication(symptoms: list[str]) -> str:
    s = " ".join(symptoms).lower()
    if "headache" in s or "mal de tete" in s or "mal de tête" in s or "cephalee" in s or "mal de dos" in s:
        return "pain_mild"
    if "diarrh" in s or "selles liquides" in s or "gastro" in s:
        return "diarrhea"
    if "constip" in s or "pas de selle" in s or "ventre bloque" in s:
        return "constipation"
    if "reflux" in s or "brulure d'estomac" in s or "brûlure d'estomac" in s or "aigreur" in s:
        return "reflux"
    if "infection" in s or "plaie" in s or "mal de gorge" in s or "angine" in s:
        return "infection"
    if "fievre" in s or "fever" in s:
        return "fever"
    if "mal de l'espace" in s or "cinetose" in s or "cinétose" in s or "mal des transports" in s:
        return "motion"
    if "nausee" in s or "nausée" in s or "vomissement" in s or "envie de vomir" in s:
        return "nausea"
    if "asthme" in s or "sifflement" in s:
        return "asthma"
    if "congestion" in s or "nez bouche" in s or "sinus" in s:
        return "congestion"
    return "general"


def _support_text(indication: str) -> str:
    if indication == "diarrhea":
        return " Hydratation obligatoire (sels de rehydration). Relais alimentaire: riz nature de la serre (oryza)."
    if indication in {"nausea", "motion"}:
        return " Petites gorgees, gingembre de bord si disponible, eviter les repas gras."
    if indication == "constipation":
        return " Hydratation et mobilite cabine en complement du laxatif."
    return ""


def _plant_fallback(db: Session, indication: str, excluded: list[ExcludedOption], rules: list[str]) -> CareEvaluationResult | None:
    plant = plants.find_ready_plant(db, indication)
    if not plant:
        return None
    rules.append(f"plant_relay_{plant.code}")
    protocol = (
        f"Stocks synthetiques epuises ou contre-indiques pour cette indication. "
        f"Relais de bord: recolter {plant.name} ({plant.species}). {plant.notes}"
        f"{_support_text(indication)}"
    )
    return CareEvaluationResult(
        excluded_options=excluded,
        recommendation=None,
        escalate_to_physician=False,
        urgency="routine",
        rules_fired=rules,
        non_drug_protocol=protocol,
        plant_recommendation=PlantRecommendation(
            plant_code=plant.code,
            plant_name=plant.name,
            protocol=protocol,
        ),
    )


def _default_dose(drug: Drug, indication: str, requested_drug_code: str | None, requested_dose_mg: float | None) -> float:
    if requested_dose_mg and requested_drug_code == drug.code:
        return requested_dose_mg
    if indication in {"pain_mild", "fever"}:
        return min(drug.dose_max_mg, 500.0)
    return drug.dose_max_mg


def _candidate_drugs(db: Session, indication: str) -> list[Drug]:
    if indication == "pain_mild":
        codes = ["paracetamol", "ibuprofen", "aspirin"]
    elif indication == "fever":
        codes = ["paracetamol", "ibuprofen"]
    elif indication == "nausea":
        codes = ["ondansetron", "meclizine"]
    elif indication == "motion":
        codes = ["meclizine", "ondansetron"]
    elif indication == "diarrhea":
        codes = ["smecta", "ors", "loperamide"]
    elif indication == "constipation":
        codes = ["macrogol"]
    elif indication == "reflux":
        codes = ["omeprazole"]
    elif indication == "asthma":
        codes = ["salbutamol"]
    elif indication == "infection":
        codes = ["amoxicillin", "azithromycin"]
    else:
        codes = []
    drugs = db.query(Drug).filter(Drug.code.in_(codes)).all()
    return sorted(drugs, key=lambda d: codes.index(d.code) if d.code in codes else 99)


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
            non_drug_protocol="Identification equipage requise avant toute proposition EIR.",
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
            non_drug_protocol=ONBOARD_EMERGENCY,
        )

    indication = _symptom_indication(symptoms)
    candidates = _candidate_drugs(db, indication)

    if not candidates and not requested_drug_code:
        rules.append("symptom_requires_assessment")
        protocol = ONBOARD_WATCH
        if indication == "congestion":
            protocol = (
                "Congestion typique de microgravite (liquides vers la tete). "
                "Hydratation, air cabine, compresses tiedes sinus. "
                "Pas de vasoconstricteur en boucle. Avis sol en file, non bloquant."
            )
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="assessment",
            rules_fired=rules,
            non_drug_protocol=protocol,
        )

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

        dose = _default_dose(drug, indication, requested_drug_code, requested_dose_mg)
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

        dose = _default_dose(drug, indication, requested_drug_code, requested_dose_mg)

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
            plant_result = _plant_fallback(db, indication, excluded, rules)
            if plant_result:
                return plant_result
            continue

        rules.append(f"recommend_{drug.code}")
        return CareEvaluationResult(
            excluded_options=excluded,
            recommendation=Recommendation(
                drug_code=drug.code,
                drug_name=drug.name,
                dose_mg=dose,
                rationale=f"Indication {indication}, stock OK.{_support_text(indication)}",
            ),
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
        )

    plant_result = _plant_fallback(db, indication, excluded, rules)
    if plant_result:
        return plant_result

    rules.append("no_option")
    return CareEvaluationResult(
        excluded_options=excluded,
        recommendation=None,
        escalate_to_physician=False,
        urgency="routine",
        rules_fired=rules,
        non_drug_protocol=ONBOARD_WATCH_24H,
    )
