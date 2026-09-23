import re

import httpx

from app.config import settings
from app.schemas.api import CareEvaluationResult
from app.services.symptom_catalog import ALL_SYMPTOM_PATTERNS, labels_from_text


SYMPTOM_PATTERNS = ALL_SYMPTOM_PATTERNS

CLINICAL_LABELS = {label for _, label in SYMPTOM_PATTERNS}

META_QUESTION = re.compile(
    r"qu['']est-ce|ce que j['']ai|tu peux me dire|explique|pourquoi|c'est quoi|"
    r"tu penses|diagnostic|grave\s*\?|c'est grave",
    re.I,
)

EPISODE_FOLLOWUP = re.compile(
    r"pas mieux|toujours|encore\b|pareil|idem|ca persiste|toujours mal|aggrave",
    re.I,
)


def extract_symptoms(text: str) -> list[str]:
    return labels_from_text(text)


def clinical_symptoms(text: str) -> list[str]:
    return [label for label in extract_symptoms(text) if label in CLINICAL_LABELS]


def _symptoms_from_history(history: str) -> list[str]:
    for line in reversed(history.splitlines()):
        if not line.lower().startswith("user:"):
            continue
        text = line.split(":", 1)[1].strip()
        clinical = clinical_symptoms(text)
        if clinical:
            return clinical
    return []


def is_meta_question(message: str) -> bool:
    return bool(META_QUESTION.search(message))


def extract_symptoms_for_eval(history: str, message: str) -> list[str]:
    clinical = clinical_symptoms(message)
    if clinical:
        return clinical
    if history and (is_meta_question(message) or EPISODE_FOLLOWUP.search(message)):
        return _symptoms_from_history(history)
    return []


def _symptom_label_fr(symptoms: list[str]) -> str:
    if not symptoms:
        return "ce que tu ressens"
    primary = symptoms[0]
    mapping = {
        "mal de tete": "ton mal de tete",
        "mal de dos": "ton mal de dos",
        "mal au rein": "ton mal au rein",
        "douleur": "ta douleur",
        "fievre": "ta fievre",
        "nausee": "tes nausees",
        "diarrhee": "ta diarrhee",
        "constipation": "ta constipation",
        "infection": "cette infection",
        "insomnie": "ton sommeil",
        "fatigue": "ta fatigue",
        "perte appetit": "ta perte d'appetit",
        "congestion": "ta congestion",
        "toux": "ta toux",
        "mal de ventre": "ton mal de ventre",
        "vertige": "tes vertiges",
        "deshydratation": "ta deshydratation",
        "prurit": "tes demangeaisons",
        "brulure": "ta brulure",
        "anxiete": "ton stress",
        "mal oreille": "ton oreille",
    }
    label = mapping.get(primary)
    if label:
        return label
    if primary in CLINICAL_LABELS:
        return f"ce symptome ({primary})"
    return "ce que tu ressens"


def _template_structured(evaluation: CareEvaluationResult) -> str | None:
    items = evaluation.symptom_items
    if not items:
        return None
    understanding = evaluation.understanding
    multi = len(items) > 1
    third = bool(understanding and understanding.third_person)
    if not multi and not third:
        return None

    intro = ""
    if understanding and understanding.narrative_summary:
        intro = understanding.narrative_summary + " "
    elif understanding and third:
        who = understanding.care_crew_name or understanding.care_crew_code
        intro = f"Pour {who}, voici ce qu'on fait pour chaque point. "

    parts: list[str] = []
    for item in items:
        if item.recommendation:
            rec = item.recommendation
            parts.append(
                f"Pour {item.topic_fr}, {rec.drug_name} ({rec.dose_mg:.0f} mg). "
                f"{rec.rationale.strip()}"
            )
        elif item.plant_recommendation:
            parts.append(f"Pour {item.topic_fr}, {item.plant_recommendation.protocol}")
        elif item.non_drug_protocol:
            parts.append(f"Pour {item.topic_fr}: {item.non_drug_protocol}")

    if not parts:
        return None
    return (intro + " ".join(parts)).strip() + " Dis-moi si ca evolue."


def template_reply(
    evaluation: CareEvaluationResult,
    user_message: str = "",
    *,
    symptoms: list[str] | None = None,
    meta_followup: bool = False,
) -> str:
    topic = _symptom_label_fr(symptoms or [])
    if evaluation.escalate_to_physician:
        detail = evaluation.non_drug_protocol or "On passe en urgence cabine tout de suite."
        return f"La c'est serieux. {detail}"

    structured = _template_structured(evaluation)
    if structured and not meta_followup:
        return structured

    if meta_followup:
        if evaluation.recommendation:
            rec = evaluation.recommendation
            return (
                f"On reste sur le meme episode. Pour {topic}, "
                f"je te conseille {rec.drug_name} ({rec.dose_mg:.0f} mg). "
                f"{rec.rationale} Dis-moi si ca evolue."
            )
        if evaluation.plant_recommendation:
            plant = evaluation.plant_recommendation
            return f"On reste sur le meme episode. {plant.protocol}"
        if evaluation.non_drug_protocol:
            return f"On reste sur le meme episode. {evaluation.non_drug_protocol}"
        return "Je te suis. Decris-moi encore ce que tu ressens ou ce qui a change."

    if evaluation.recommendation:
        rec = evaluation.recommendation
        return (
            f"Pour {topic}, prends {rec.drug_name} ({rec.dose_mg:.0f} mg). "
            f"{rec.rationale} Dis-moi si ca va mieux."
        )
    if evaluation.plant_recommendation:
        return evaluation.plant_recommendation.protocol
    if evaluation.non_drug_protocol:
        return evaluation.non_drug_protocol
    return "Je reste avec toi. Surveille comment ca evolue et redis-moi si ca s'aggrave."


async def reformulate_with_ollama(
    user_message: str,
    evaluation: CareEvaluationResult,
    history: str = "",
    symptoms: list[str] | None = None,
    meta_followup: bool = False,
) -> tuple[str, str]:
    system = (
        "Tu es EIR Medichat, collegue de bord. Tu tutoies avec des mots simples. "
        "Ne recopies jamais le message du patient mot pour mot. Pas de formule du type j'entends. "
        "Tu reformules UNIQUEMENT la decision JSON. "
        "Ne prescris jamais un medicament absent du JSON. "
        "Reponds a CHAQUE point dans symptom_items du JSON si present. "
        "Reponds au mal ou a la question, en phrases courtes. "
        "N'invente pas de latence terrestre, de coupure, ni d'isolement "
        "sauf urgence critique dans le JSON. Francais clair, sans emoji."
    )
    history_block = f"\nHistorique du fil:\n{history}\n" if history else ""
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"{history_block}Message patient: {user_message}\n"
                    f"Decision JSON:\n{evaluation.model_dump_json()}"
                ),
            },
        ],
    }
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = str(data.get("message", {}).get("content") or "").strip()
            if not content or "j'entends" in content.lower() or "j entends" in content.lower():
                return (
                    template_reply(
                        evaluation,
                        user_message,
                        symptoms=symptoms,
                        meta_followup=meta_followup,
                    ),
                    "template",
                )
            return content, "ollama"
    except Exception:
        return template_reply(
            evaluation,
            user_message,
            symptoms=symptoms,
            meta_followup=meta_followup,
        ), "template"
