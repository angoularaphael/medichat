import re

import httpx

from app.config import settings
from app.schemas.api import CareEvaluationResult


SYMPTOM_PATTERNS = [
    (re.compile(r"mal de t[êe]te|cephalee|headache", re.I), "mal de tete"),
    (
        re.compile(
            r"mal au cr[âa]ne|mal au cran\b|mal a la tete|mal à la tête|mal dans la tete",
            re.I,
        ),
        "mal de tete",
    ),
    (
        re.compile(
            r"insomnie|dors pas|ne dors|pas dormir|mal dormir|nuit blanche|"
            r"arrive pas a dormir|arrive pas à dormir|sommeil",
            re.I,
        ),
        "insomnie",
    ),
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
    (re.compile(r"mal au ventre|douleur abdominale|abdominal", re.I), "mal de ventre"),
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

CLINICAL_LABELS = {label for _, label in SYMPTOM_PATTERNS}

META_QUESTION = re.compile(
    r"qu['']est-ce|ce que j['']ai|tu peux me dire|explique|pourquoi|c'est quoi|"
    r"tu penses|diagnostic|grave\s*\?|c'est grave",
    re.I,
)


def extract_symptoms(text: str) -> list[str]:
    found: list[str] = []
    for pattern, label in SYMPTOM_PATTERNS:
        if pattern.search(text):
            found.append(label)
    return found


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
    if history:
        from_history = _symptoms_from_history(history)
        if from_history:
            return from_history
    if is_meta_question(message) and history:
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
    }
    label = mapping.get(primary)
    if label:
        return label
    if primary in CLINICAL_LABELS:
        return f"ce symptome ({primary})"
    return "ce que tu ressens"


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
        "Reponds au mal ou a la question, en une ou deux phrases courtes. "
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
