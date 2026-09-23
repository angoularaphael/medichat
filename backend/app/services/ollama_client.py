import json
import re

import httpx

from app.config import settings
from app.schemas.api import CareEvaluationResult


SYMPTOM_PATTERNS = [
    (re.compile(r"mal de t[êe]te|cephalee|headache", re.I), "mal de tete"),
    (re.compile(r"douleur thoracique|chest pain", re.I), "douleur thoracique"),
    (re.compile(r"fi[eè]vre|fever", re.I), "fievre"),
    (re.compile(r"naus[ée]e?|envie de vomir|vomissement", re.I), "nausee"),
    (re.compile(r"toux|cough", re.I), "toux"),
    (re.compile(r"mal au ventre|douleur abdominale|abdominal", re.I), "douleur abdominale"),
    (re.compile(r"vertige|[ée]tourdissement|dizzy", re.I), "vertige"),
    (
        re.compile(
            r"essouffl(?:e|ee|é|ée)|difficult[ée] [àa] respirer|mal [àa] respirer|dyspn[ée]e",
            re.I,
        ),
        "difficulte respiratoire",
    ),
    (re.compile(r"mal de gorge|gorge.*mal|sore throat|angine", re.I), "mal de gorge"),
    (re.compile(r"infection|infecte|plaie|antibiot", re.I), "infection"),
]


def extract_symptoms(text: str) -> list[str]:
    found: list[str] = []
    for pattern, label in SYMPTOM_PATTERNS:
        if pattern.search(text):
            found.append(label)
    if not found and text.strip():
        found.append(text.strip()[:120])
    return found


def template_reply(evaluation: CareEvaluationResult) -> str:
    parts = ["Analyse EIR (moteur de regles deterministe, decision a bord):"]
    if evaluation.excluded_options:
        parts.append("Options ecartees:")
        for opt in evaluation.excluded_options:
            parts.append(f"- {opt.drug_code}: {opt.reason_text}")
    if evaluation.escalate_to_physician:
        parts.append("Protocole d'urgence embarque. Avis sol non bloquant (latence / coupure).")
        if evaluation.non_drug_protocol:
            parts.append(evaluation.non_drug_protocol)
        return "\n".join(parts)
    if evaluation.recommendation:
        r = evaluation.recommendation
        parts.append(
            f"Proposition: {r.drug_name} ({r.drug_code}), dose {r.dose_mg} mg. {r.rationale}"
        )
    elif evaluation.plant_recommendation:
        plant = evaluation.plant_recommendation
        parts.append(f"Relais botanique: {plant.plant_name}. {plant.protocol}")
    elif evaluation.non_drug_protocol:
        parts.append(f"Aucun medicament synthetique. {evaluation.non_drug_protocol}")
    else:
        parts.append("Aucune proposition medicamenteuse. Protocole de surveillance a bord.")
    return "\n".join(parts)


async def reformulate_with_ollama(
    user_message: str,
    evaluation: CareEvaluationResult,
) -> tuple[str, str]:
    system = (
        "Tu es l'interface EIR a bord du vaisseau Yggdrasil. "
        "Un lien Terre existe mais avec latence et coupures frequentes. "
        "Reformule UNIQUEMENT la decision JSON fournie. "
        "Ne prescris jamais un medicament absent du JSON. "
        "N'attends jamais un avis medical terrestre pour agir. "
        "Tu peux dire qu'un message est envoye au sol, mais la decision locale prime. "
        "Reponses courtes en francais."
    )
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Message patient: {user_message}\nDecision JSON:\n{evaluation.model_dump_json()}",
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
            if not content:
                return template_reply(evaluation), "template"
            return content, "ollama"
    except Exception:
        return template_reply(evaluation), "template"
