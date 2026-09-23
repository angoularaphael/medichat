import re

import httpx

from app.config import settings
from app.schemas.api import CareEvaluationResult


SYMPTOM_PATTERNS = [
    (re.compile(r"mal de t[êe]te|cephalee|headache", re.I), "mal de tete"),
    (re.compile(r"douleur thoracique|chest pain", re.I), "douleur thoracique"),
    (re.compile(r"mal au rein|reins?|colique n[eé]phr|flanc", re.I), "mal au rein"),
    (re.compile(r"fi[eè]vre|fever", re.I), "fievre"),
    (re.compile(r"naus[ée]e?|envie de vomir|vomissement", re.I), "nausee"),
    (re.compile(r"diarrh[ée]e|selles liquides|gastro", re.I), "diarrhee"),
    (re.compile(r"constip|pas de selle|ventre bloqu", re.I), "constipation"),
    (re.compile(r"reflux|br[uû]lure d[' ]estomac|aigreur", re.I), "reflux"),
    (re.compile(r"mal de dos|lombalgie|dorsalgie", re.I), "mal de dos"),
    (re.compile(r"mal de l[' ]espace|cin[eé]tose|mal des transports", re.I), "mal de l'espace"),
    (re.compile(r"congestion|nez bouch|sinus", re.I), "congestion"),
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
    (re.compile(r"j[' ]ai mal|mal (au|a la|à la|de)|douleur", re.I), "douleur"),
]


def extract_symptoms(text: str) -> list[str]:
    found: list[str] = []
    for pattern, label in SYMPTOM_PATTERNS:
        if pattern.search(text):
            found.append(label)
    if not found and text.strip():
        found.append(text.strip()[:120])
    return found


def template_reply(evaluation: CareEvaluationResult, user_message: str = "") -> str:
    felt = " ".join(user_message.split())
    if felt:
        opener = f"Ok, j'entends: {felt}."
    else:
        opener = "Ok, je te prends en charge."

    if evaluation.escalate_to_physician:
        detail = evaluation.non_drug_protocol or ""
        return f"{opener} La c'est grave: on passe en urgence cabine. {detail}"

    if evaluation.recommendation:
        rec = evaluation.recommendation
        return (
            f"{opener} Avec ton dossier et le stock, je te propose {rec.drug_name} "
            f"({rec.dose_mg:.0f} mg). {rec.rationale} Dis-moi si ca se calme."
        )
    if evaluation.plant_recommendation:
        plant = evaluation.plant_recommendation
        protocol = plant.protocol
        if protocol.startswith("Les flacons sont en stock"):
            lead = "Ton profil ecarte les flacons disponibles."
        elif protocol.startswith("Stock medicamenteux epuise"):
            lead = "Les flacons sont vides pour ce symptome."
        else:
            lead = "On bascule sur la serre."
        return f"{opener} {lead} {protocol}"
    if evaluation.non_drug_protocol:
        return f"{opener} {evaluation.non_drug_protocol}"
    return f"{opener} Je reste avec toi: on surveille, tu me dis si ca bouge."


async def reformulate_with_ollama(
    user_message: str,
    evaluation: CareEvaluationResult,
    history: str = "",
) -> tuple[str, str]:
    system = (
        "Tu es EIR Medichat, collegue de bord. Tu tutoies. "
        "Tu restes dans le fil de conversation: tu tiens compte de l'historique. "
        "Tu reformules UNIQUEMENT la decision JSON. "
        "Ne prescris jamais un medicament absent du JSON. "
        "Reponds vraiment au mal decrit, de facon humaine et concrete. "
        "N'invente pas de latence terrestre, de coupure, ni d'isolement "
        "sauf si le JSON dit urgence critique. "
        "Francais court, vivant, sans emoji."
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
            if not content:
                return template_reply(evaluation, user_message), "template"
            return content, "ollama"
    except Exception:
        return template_reply(evaluation, user_message), "template"
