from sqlalchemy.orm import Session

from app.models.entities import Drug, DrugInteraction, CrewMember
from app.schemas.api import (
    CareEvaluationResult,
    ClinicalFindingOut,
    ExcludedOption,
    MessageUnderstandingOut,
    PlantRecommendation,
    Recommendation,
    SymptomCareItem,
)
from app.services.clinical_topics import topic_for_label
from app.services.message_understanding import MessageUnderstanding, build_narrative_summary
from app.services import bacteria, plants, substitution
from app.services.symptom_catalog import check_isolation


AINS_CLASS = "AINS"

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


ONBOARD_EMERGENCY = (
    "La, on ne joue plus. Immobilisation, oxygene, monitoring en continu. "
    "C'est le dernier recours: cabine medicale, on t'isole pour te proteger "
    "et on agit tout de suite."
)
LAST_RESORT_WATCH = (
    "On n'a plus de molecule sure pour ce que tu decris. "
    "Repos, hydratation, tu surveilles comment ca evolue. "
    "Si ca s'aggrave vraiment (gene a respirer, douleur dans la poitrine, malaise): "
    "isolement cabine medicale. C'est le dernier recours, pas la reponse par defaut."
)
SYMPTOMS_CLARIFY = (
    "Decris plus precisement ce que tu as (mal de tete, ventre, fievre, sommeil, etc.). "
    "Sans ca je ne peux pas proposer un medicament."
)
SLEEP_PROTOCOL = (
    "Pour le sommeil on ne part pas sur un analgesique par defaut. "
    "Lumiere basse, pas d'ecrans, routine calme. "
    "Si tu as aussi mal quelque part (tete, dos...), dis-le moi."
)
FATIGUE_PROTOCOL = (
    "Pour la fatigue on ne part pas sur un analgesique sans douleur associee. "
    "Repos, hydratation, et dis-moi si tu as fievre, mal de tete ou nausees."
)
APPETITE_PROTOCOL = (
    "Pour la perte d'appetit: petites portions, bois regulierement, repos. "
    "Si tu as nausees ou vomissements en plus, dis-le moi."
)
DEHYDRATION_PROTOCOL = (
    "Pense deshydratation: bois par petites gorgees, sels de rehydration si tu en as. "
    "Si vomissements ou diarrhee en plus, dis-le moi."
)
PRURIT_PROTOCOL = (
    "Demangeaisons: evite de gratter, douche tiede, vetements amples. "
    "Si gorge qui serre ou essoufflement, alerte tout de suite."
)
BRULURE_PROTOCOL = (
    "Brulure legere: eau tiede 10-15 min, pas de glace directe, couvre proprement. "
    "Brulure chimique ou grande surface: alerte medicale."
)
ANXIETE_PROTOCOL = (
    "Stress a bord: respiration lente, ancrage, parle-moi. "
    "Si douleur poitrine ou essoufflement en plus, ce n'est plus que du stress."
)


def _symptom_indication(symptoms: list[str]) -> str:
    s = " ".join(symptoms).lower()
    if "insomnie" in s:
        return "sleep"
    if (
        "headache" in s
        or "mal de tete" in s
        or "mal de tête" in s
        or "cephalee" in s
        or "mal au cr" in s
        or "cran" in s.split()
    ):
        return "pain_mild"
    if "rein" in s or "flanc" in s or "lombair" in s or "renal" in s:
        return "pain_renal"
    if "mal de dos" in s or "lombalgie" in s:
        return "pain_mild"
    if "fatigue" in s:
        return "fatigue"
    if "perte appetit" in s or "appetit" in s:
        return "appetite"
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
    if "congestion" in s or "nez bouche" in s or "sinus" in s or "rhume" in s:
        return "congestion"
    if "toux" in s:
        return "toux"
    if "deshydratation" in s:
        return "dehydration"
    if "prurit" in s:
        return "prurit"
    if "brulure" in s:
        return "brulure"
    if "anxiete" in s:
        return "anxiety"
    if "mal oreille" in s:
        return "pain_mild"
    if "mal de ventre" in s:
        return "pain_mild"
    if "vertige" in s:
        return "vertigo"
    if "mal" in s or "douleur" in s or "souffre" in s:
        return "pain_mild"
    return "unspecified"


def _profile_blocked_protocol(excluded: list[ExcludedOption], indication: str) -> str:
    reasons: list[str] = []
    for opt in excluded:
        if opt.reason_code not in {"allergy", "interaction"}:
            continue
        short = opt.drug_code
        if opt.reason_code == "allergy":
            reasons.append(f"{short}: allergie")
        else:
            reasons.append(f"{short}: {opt.reason_text}")
    detail = " ".join(reasons[:4])
    intro = (
        "Il reste des medicaments en stock pour ce symptome, "
        "mais ton profil les exclut tous."
    )
    if detail:
        intro = f"{intro} ({detail})"
    if indication == "pain_mild":
        intro += (
            " Avec un anticoagulant, les AINS (ibuprofene, aspirine) sont en general "
            "contre-indiques; le paracetamol reste l'option si tu n'y es pas allergique."
        )
    return f"{intro} Surveille tes signes et previens le poste medical."


def _support_text(indication: str) -> str:
    if indication == "diarrhea":
        return (
            " Bois par petites gorgees, sels de rehydration si tu en as. "
            "Le riz de la serre aide a lier. Ensuite la cuve Lactobacillus pour la flore."
        )
    if indication in {"nausea", "motion"}:
        return " Petites gorgees, gingembre de cabine si tu en as, repas leger."
    if indication == "constipation":
        return " Bois, bouge un peu dans la cabine, et le laxatif si besoin."
    if indication == "pain_renal":
        return " Bois bien. J'evite les AINS sur un mal de rein: on reste sur le paracetamol."
    return ""


def _expanded_candidates(db: Session, candidates: list[Drug], indication: str) -> list[Drug]:
    expanded: list[Drug] = []
    seen: set[str] = set()
    for drug in candidates:
        if drug.code not in seen:
            expanded.append(drug)
            seen.add(drug.code)
        for sub in substitution.find_substitutes(db, drug.id, indication):
            if sub.code not in seen:
                expanded.append(sub)
                seen.add(sub.code)
    return expanded


def _indication_stock_depleted(db: Session, candidates: list[Drug], indication: str) -> bool:
    pool = _expanded_candidates(db, candidates, indication)
    if not pool:
        return True
    return all(drug.stock_units <= 0 for drug in pool)


def _plant_fallback(
    db: Session,
    indication: str,
    excluded: list[ExcludedOption],
    rules: list[str],
) -> CareEvaluationResult | None:
    plant = plants.find_ready_plant(db, indication)
    if plant:
        rules.append(f"plant_relay_{plant.code}")
        protocol = (
            f"Il n'y a plus de medicament en stock pour ca. "
            f"Utilise {plant.name} dans la serre: {plant.notes}"
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
    culture = bacteria.find_ready(db, indication)
    if not culture:
        return None
    rules.append(f"bacteria_relay_{culture.code}")
    protocol = (
        f"Il n'y a plus de medicament en stock. "
        f"Pharmacie vivante: {culture.nom_souche} ({culture.quantite_boites} boites). "
        f"{culture.notes}{_support_text(indication)}"
    )
    return CareEvaluationResult(
        excluded_options=excluded,
        recommendation=None,
        escalate_to_physician=False,
        urgency="routine",
        rules_fired=rules,
        non_drug_protocol=protocol,
        plant_recommendation=PlantRecommendation(
            plant_code=culture.code,
            plant_name=culture.nom_souche,
            protocol=protocol,
        ),
    )


def _default_dose(drug: Drug, indication: str, requested_drug_code: str | None, requested_dose_mg: float | None) -> float:
    if requested_dose_mg and requested_drug_code == drug.code:
        return requested_dose_mg
    if indication in {"pain_mild", "fever", "pain_renal"}:
        return min(drug.dose_max_mg, 500.0)
    return drug.dose_max_mg


def _candidate_drugs(db: Session, indication: str) -> list[Drug]:
    if indication == "pain_mild":
        codes = ["paracetamol", "ibuprofen", "aspirin"]
    elif indication == "pain_renal":
        codes = ["paracetamol"]
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
        codes = ["paracetamol", "ibuprofen", "aspirin"]
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

    isolated, isolation_rule = check_isolation(symptoms)
    if isolated:
        rules.append(isolation_rule or "red_flag_escalation")
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=True,
            urgency="critical",
            rules_fired=rules,
            non_drug_protocol=ONBOARD_EMERGENCY,
        )

    if not symptoms or not any(str(s).strip() for s in symptoms):
        rules.append("symptoms_unclear")
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
            non_drug_protocol=SYMPTOMS_CLARIFY,
        )

    indication = _symptom_indication(symptoms)
    if indication == "unspecified":
        rules.append("indication_unspecified")
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
            non_drug_protocol=SYMPTOMS_CLARIFY,
        )
    if indication == "sleep":
        rules.append("sleep_non_pharm")
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
            non_drug_protocol=SLEEP_PROTOCOL,
        )
    if indication == "fatigue":
        rules.append("fatigue_non_pharm")
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
            non_drug_protocol=FATIGUE_PROTOCOL,
        )
    if indication == "appetite":
        rules.append("appetite_non_pharm")
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
            non_drug_protocol=APPETITE_PROTOCOL,
        )
    if indication == "dehydration":
        rules.append("dehydration_support")
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
            non_drug_protocol=DEHYDRATION_PROTOCOL,
        )
    if indication == "prurit":
        rules.append("prurit_non_pharm")
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
            non_drug_protocol=PRURIT_PROTOCOL,
        )
    if indication == "brulure":
        rules.append("brulure_non_pharm")
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
            non_drug_protocol=BRULURE_PROTOCOL,
        )
    if indication == "anxiety":
        rules.append("anxiety_non_pharm")
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
            non_drug_protocol=ANXIETE_PROTOCOL,
        )
    if indication in {"toux", "vertigo", "congestion"}:
        rules.append(f"{indication}_non_pharm")
        protocol = (
            "Repos, hydratation, air de la cabine si possible. "
            "Pas d'antibiotique automatique. Si fievre haute, essoufflement ou douleur poitrine, dis-le."
        )
        return CareEvaluationResult(
            excluded_options=[],
            recommendation=None,
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
            non_drug_protocol=protocol,
        )

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
                if sub.code in excluded_codes or sub.stock_units <= 0:
                    continue
                if _has_allergy(member, sub):
                    continue
                if _interaction_blocks(db, member, sub):
                    continue
                rules.append(f"substitution_{sub.code}")
                return CareEvaluationResult(
                    excluded_options=excluded,
                    recommendation=Recommendation(
                        drug_code=sub.code,
                        drug_name=sub.name,
                        dose_mg=min(dose, sub.dose_max_mg),
                        rationale=f"On en a encore en stock (remplace {drug.name}).{_support_text(indication)}",
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
                        rationale=f"On en a encore en stock.{_support_text(indication)}",
            ),
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=rules,
        )

    stock_depleted = _indication_stock_depleted(db, candidates, indication)
    if stock_depleted:
        plant_result = _plant_fallback(db, indication, excluded, rules)
        if plant_result:
            return plant_result

    rules.append("no_option")
    still_on_shelf = any(drug.stock_units > 0 for drug in _expanded_candidates(db, candidates, indication))
    if still_on_shelf:
        protocol = _profile_blocked_protocol(excluded, indication)
    else:
        protocol = LAST_RESORT_WATCH
    return CareEvaluationResult(
        excluded_options=excluded,
        recommendation=None,
        escalate_to_physician=False,
        urgency="routine",
        rules_fired=rules,
        non_drug_protocol=protocol,
    )


def _attach_understanding(
    result: CareEvaluationResult,
    understanding: MessageUnderstanding,
    care_name: str | None,
) -> CareEvaluationResult:
    summary = build_narrative_summary(understanding, care_name or understanding.care_crew_code)
    result.understanding = MessageUnderstandingOut(
        care_crew_code=understanding.care_crew_code,
        care_crew_name=care_name,
        third_person=understanding.third_person,
        findings=[
            ClinicalFindingOut(
                symptom_label=f.symptom_label,
                source_text=f.source_text,
                topic_fr=f.topic_fr,
            )
            for f in understanding.findings
        ],
        extraction_mode=understanding.extraction_mode,
        narrative_summary=summary,
    )
    return result


def _symptom_item_from_eval(label: str, sub: CareEvaluationResult) -> SymptomCareItem:
    return SymptomCareItem(
        symptom_label=label,
        topic_fr=topic_for_label(label),
        recommendation=sub.recommendation,
        non_drug_protocol=sub.non_drug_protocol,
        plant_recommendation=sub.plant_recommendation,
        escalate_to_physician=sub.escalate_to_physician,
    )


def evaluate_from_understanding(
    db: Session,
    *,
    understanding: MessageUnderstanding,
    care_crew_name: str | None = None,
) -> CareEvaluationResult:
    labels = understanding.symptom_labels
    crew = understanding.care_crew_code

    if not labels:
        result = evaluate_care(db, crew_member_code=crew, symptoms=[])
        return _attach_understanding(result, understanding, care_crew_name)

    isolated, _rule = check_isolation(labels)
    if isolated:
        result = evaluate_care(db, crew_member_code=crew, symptoms=labels)
        return _attach_understanding(result, understanding, care_crew_name)

    if len(labels) == 1:
        result = evaluate_care(db, crew_member_code=crew, symptoms=labels)
        result.symptom_items = [_symptom_item_from_eval(labels[0], result)]
        return _attach_understanding(result, understanding, care_crew_name)

    items: list[SymptomCareItem] = []
    all_excluded: list[ExcludedOption] = []
    all_rules: list[str] = ["multi_symptom_eval"]
    primary_rec: Recommendation | None = None
    primary_plant: PlantRecommendation | None = None
    seen_excluded: set[tuple[str, str]] = set()

    for label in labels:
        sub = evaluate_care(db, crew_member_code=crew, symptoms=[label])
        if sub.escalate_to_physician:
            return _attach_understanding(sub, understanding, care_crew_name)
        items.append(_symptom_item_from_eval(label, sub))
        all_rules.extend(sub.rules_fired)
        for opt in sub.excluded_options:
            key = (opt.drug_code, opt.reason_code)
            if key not in seen_excluded:
                seen_excluded.add(key)
                all_excluded.append(opt)
        if not primary_rec and sub.recommendation:
            primary_rec = sub.recommendation
        if not primary_plant and sub.plant_recommendation:
            primary_plant = sub.plant_recommendation

    return _attach_understanding(
        CareEvaluationResult(
            excluded_options=all_excluded,
            recommendation=primary_rec,
            plant_recommendation=primary_plant,
            escalate_to_physician=False,
            urgency="routine",
            rules_fired=all_rules,
            symptom_items=items,
        ),
        understanding,
        care_crew_name,
    )
