import json
import re

import httpx

from app.config import settings
from app.schemas.api import CareEvaluationResult


SYMPTOM_PATTERNS = [
    (re.compile(r"mal de t[êe]te|cephalee|headache", re.I), "mal de tete"),
    (re.compile(r"douleur thoracique|chest pain", re.I), "douleur thoracique"),
    (re.compile(r"fi[eè]vre|fever", re.I), "fievre"),
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
    parts = ["Analyse EIR (moteur de regles deterministe):"]
    if evaluation.excluded_options:
        parts.append("Options ecartees:")
        for opt in evaluation.excluded_options:
            parts.append(f"- {opt.drug_code}: {opt.reason_text}")
    if evaluation.escalate_to_physician:
        parts.append("Escalade medecin de bord recommandee.")
        if evaluation.non_drug_protocol:
            parts.append(evaluation.non_drug_protocol)
        return "\n".join(parts)
    if evaluation.recommendation:
        r = evaluation.recommendation
        parts.append(
            f"Proposition: {r.drug_name} ({r.drug_code}), dose {r.dose_mg} mg. {r.rationale}"
        )
    elif evaluation.non_drug_protocol:
        parts.append(f"Aucun medicament. {evaluation.non_drug_protocol}")
    else:
        parts.append("Aucune proposition medicamenteuse.")
    return "\n".join(parts)


async def reformulate_with_ollama(
    user_message: str,
    evaluation: CareEvaluationResult,
) -> tuple[str, str]:
    system = (
        "Tu es l'interface EIR. Reformule UNIQUEMENT la decision JSON fournie. "
        "Ne prescris jamais un medicament absent du JSON. Reponses courtes en francais."
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
            content = data.get("message", {}).get("content") or template_reply(evaluation)
            return content.strip(), "ollama"
    except Exception:
        return template_reply(evaluation), "template"
