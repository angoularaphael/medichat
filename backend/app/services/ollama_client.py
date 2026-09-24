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

FEELING_BETTER = re.compile(
    r"\b(va mieux|vais mieux|me sens mieux|c'est mieux|tout va bien|ca va bien)\b",
    re.I,
)


def _plain(text: str) -> str:
    return (
        text.lower()
        .replace("ç", "c")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ù", "u")
        .replace("'", " ")
    )


def _last_assistant(history: str) -> str:
    role = None
    chunks: list[str] = []
    last = ""
    for line in history.splitlines():
        if line.startswith("user:") or line.startswith("assistant:"):
            if role == "assistant":
                last = "\n".join(chunks).strip()
            role = "assistant" if line.startswith("assistant:") else "user"
            chunks = [line.split(":", 1)[1].strip()]
        elif role:
            chunks.append(line)
    if role == "assistant":
        last = "\n".join(chunks).strip()
    return last


def _asked_about(asked: str, *needles: str) -> bool:
    return any(needle in asked for needle in needles)


def reply_to_what_i_asked(history: str, message: str) -> str | None:
    from app.services.symptom_catalog import isolation_labels_from_text

    if isolation_labels_from_text(message):
        return None
    asked = _plain(_last_assistant(history))
    text = _plain(message)
    if not asked or not text:
        return None

    if _asked_about(asked, "sang") and re.search(r"pas de sang|aucun sang|sans sang|pas de saign", text):
        return (
            "D'accord, pas de sang.\n\n"
            "On continue comme je t'ai dit. Bois par petites gorgees.\n\n"
            "Si du sang apparait, redis-le moi."
        )
    if _asked_about(asked, "fievre") and re.search(r"pas de fievre|sans fievre|pas fievre", text):
        return (
            "D'accord, pas de fievre.\n\n"
            "On continue comme je t'ai dit.\n\n"
            "Si elle monte, redis-le moi."
        )
    if _asked_about(asked, "fievre") and re.search(r"\bfievre\b|temperature|tres chaud|la fievre monte", text):
        return (
            "D'accord, tu as de la fievre.\n\n"
            "Repose-toi et bois souvent. On surveille si elle monte.\n\n"
            "Si tu as du mal a respirer, du sang, ou si tu te sens faible, dis-le moi tout de suite."
        )
    if re.search(r"\b(ca dure|ca continue|depuis longtemps)\b", text):
        return (
            "D'accord, ca dure.\n\n"
            "On reste sur ce que tu m'as dit. Continue le repos et bois souvent.\n\n"
            "Si du sang apparait ou si tu as de la fievre, redis-le moi."
        )
    if re.search(r"\b(ca empire|c est pire|aggrav|moins bien|pas mieux)\b", text):
        return (
            "D'accord, ca empire.\n\n"
            "On laisse le geste simple. Repose-toi, bois par petites gorgees, "
            "et previens un coequipier.\n\n"
            "Si tu as du mal a respirer, mal a la poitrine, ou si tu te sens faible, "
            "dis-le moi tout de suite."
        )
    if _asked_about(asked, "vomis") and re.search(r"vomis|vomir|vomissement", text):
        return (
            "D'accord, tu vomis encore.\n\n"
            "Bois seulement par petites gorgees. Pas de gros repas.\n\n"
            "Si tu vomis du sang, ou si tu n'arrives plus a boire, dis-le moi tout de suite."
        )
    if _asked_about(asked, "brulure") and re.search(r"grand|profond|etendue", text):
        return (
            "D'accord, la brulure est grande ou profonde.\n\n"
            "On arrete le gel. Passe de l'eau tiede, couvre proprement, "
            "et previens un coequipier."
        )
    if _asked_about(asked, "etend", "coule") and re.search(r"etend|coule|suint", text):
        return (
            "D'accord, ca s'etend ou ca coule.\n\n"
            "N'y remets pas de plante. Lave a l'eau et previens un coequipier."
        )
    if _asked_about(asked, "rougit") and re.search(r"rougit|ca rouge|c est rouge", text):
        return (
            "D'accord, ca rougit.\n\n"
            "Lave a l'eau et n'y touche plus.\n\n"
            "Si la fievre monte, redis-le moi."
        )
    if _asked_about(asked, "faible") and re.search(r"faible|malaise|vertige", text):
        return (
            "D'accord, tu te sens faible.\n\n"
            "Allonge-toi, bois par petites gorgees, et previens un coequipier."
        )
    if clinical_symptoms(message):
        return None

    themes = [
        name
        for name, needle in (
            ("le sang", "sang"),
            ("la fievre", "fievre"),
            ("le fait que ca dure", "dure"),
            ("le fait que ca empire", "empire"),
            ("les vomissements", "vomis"),
        )
        if needle in asked
    ]
    if re.fullmatch(r"oui|ouais|yes", text) and themes:
        if len(themes) > 1:
            listed = ", ".join(themes[:-1]) + " ou " + themes[-1]
            return (
                "Tu me dis oui.\n\n"
                f"C'est {listed} ?\n\n"
                "Dis-moi lequel."
            )
        only = themes[0]
        if only == "le sang":
            return (
                "D'accord, il y a du sang.\n\n"
                "On arrete le geste simple. Reste au calme, bois par petites gorgees, "
                "et previens un coequipier."
            )
        if only == "la fievre":
            return (
                "D'accord, tu as de la fievre.\n\n"
                "Repose-toi et bois souvent.\n\n"
                "Si elle monte encore, redis-le moi."
            )
        if only == "le fait que ca dure":
            return (
                "D'accord, ca dure.\n\n"
                "On reste sur ce que tu m'as dit. Continue le repos et bois souvent."
            )
        if only == "le fait que ca empire":
            return (
                "D'accord, ca empire.\n\n"
                "Previens un coequipier et redis-moi si tu te sens faible."
            )
        return (
            "D'accord, tu vomis encore.\n\n"
            "Bois par petites gorgees.\n\n"
            "Si tu n'arrives plus a boire, dis-le moi."
        )
    if re.fullmatch(r"non|nan|rien", text) and themes:
        return (
            "D'accord, rien de tout ca.\n\n"
            "On continue comme je t'ai dit.\n\n"
            "Si ca change, redis-le moi."
        )
    return None


def is_feeling_better(message: str) -> bool:
    text = _plain(message)
    if re.search(r"pas mieux|moins bien|pire|aggrav", text):
        return False
    if clinical_symptoms(message):
        return False
    return bool(FEELING_BETTER.search(text))


def feeling_better_reply() -> str:
    return (
        "Tant mieux.\n\n"
        "Repose-toi encore un peu et bois de l'eau. "
        "Mange leger si tu as faim.\n\n"
        "Si la douleur, la fievre ou les nausees reviennent, redis-le moi."
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
        intro = understanding.narrative_summary.strip() + "\n\n"
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
    return (intro + "\n\n".join(parts)).strip()


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
                f"{rec.rationale} Dis-moi si ca revient."
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
        "Tu reformules UNIQUEMENT la decision JSON, en phrases courtes. "
        "Un paragraphe par idee, separe par une ligne vide. "
        "Langage simple, comme a un coequipier. "
        "Ne dis pas fermentation, extraction, purification, ni poste medical. "
        "Ne prescris jamais un medicament absent du JSON. "
        "Si un relais plante ou cuve est dans le JSON, repete son origine et sa limite. "
        "N'invente aucun milieu de culture, aucune extraction, aucune purification, aucune dose de plante brute. "
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
