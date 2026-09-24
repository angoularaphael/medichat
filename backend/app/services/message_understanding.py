"""Comprehension du message patient: sujet, clauses, negations, motifs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.services.clinical_topics import topic_for_label
from app.services.symptom_catalog import ISOLATION_SYMPTOM_LABELS, labels_from_text

CREW_ALIASES: list[tuple[str, re.Pattern[str]]] = [
    ("elisa", re.compile(r"\belisa\b", re.I)),
    ("elsa", re.compile(r"\belsa\b", re.I)),
    ("raphael", re.compile(r"\braphael\b", re.I)),
    ("jovani", re.compile(r"\bjovani\b", re.I)),
    ("carine", re.compile(r"\bcarine\b", re.I)),
]

CLAUSE_SPLIT = re.compile(
    r"\s*,\s*|\s+et\s+(?=[^,]{0,80}(?:fievre|fi[eè]vre|vomir|touss|toux|mal |nause|diarrh|dors|fatigu))",
    re.I,
)

NEGATION_BEFORE_SYMPTOM = re.compile(
    r"(?:pas de|sans|aucune?|aucun|plus de)\s+([^.,;]+)",
    re.I,
)

LABEL_INDICATION: dict[str, str] = {
    "mal de tete": "pain",
    "mal de dos": "pain",
    "mal au rein": "pain_renal",
    "mal de ventre": "pain",
    "mal oreille": "pain",
    "douleur": "pain",
    "douleur thoracique": "isolation",
    "difficulte respiratoire": "isolation",
    "perte de connaissance": "isolation",
    "convulsion": "isolation",
    "hemorragie severe": "isolation",
    "choc anaphylactique": "isolation",
    "accident vasculaire": "isolation",
    "contamination toxique": "isolation",
    "fievre": "fever",
    "nausee": "nausea",
    "diarrhee": "diarrhea",
    "constipation": "constipation",
    "reflux": "reflux",
    "infection": "infection",
    "insomnie": "sleep",
    "fatigue": "fatigue",
    "perte appetit": "appetite",
    "congestion": "congestion",
    "toux": "toux",
    "vertige": "vertigo",
    "deshydratation": "dehydration",
    "prurit": "prurit",
    "brulure": "brulure",
    "anxiete": "anxiety",
    "mal de gorge": "infection",
    "mal de l'espace": "motion",
}

SPECIFIC_PAIN_LABELS = frozenset(
    {"mal de tete", "mal de dos", "mal au rein", "mal de ventre", "mal oreille", "douleur thoracique"}
)

ALLOWED_LABELS = frozenset(LABEL_INDICATION.keys())


@dataclass
class ClinicalFinding:
    symptom_label: str
    source_text: str
    topic_fr: str = ""

    def __post_init__(self) -> None:
        if not self.topic_fr:
            self.topic_fr = topic_for_label(self.symptom_label)


@dataclass
class MessageUnderstanding:
    active_crew_code: str
    care_crew_code: str
    third_person: bool
    findings: list[ClinicalFinding] = field(default_factory=list)
    symptom_labels: list[str] = field(default_factory=list)
    extraction_mode: str = "rules"
    narrative_summary: str = ""

    def to_api_dict(self, care_name: str | None = None) -> dict:
        return {
            "care_crew_code": self.care_crew_code,
            "care_crew_name": care_name,
            "third_person": self.third_person,
            "findings": [
                {
                    "symptom_label": f.symptom_label,
                    "source_text": f.source_text,
                    "topic_fr": f.topic_fr,
                }
                for f in self.findings
            ],
            "extraction_mode": self.extraction_mode,
            "narrative_summary": self.narrative_summary,
        }


def resolve_care_subject(message: str, active_crew: str) -> tuple[str, bool]:
    lower = message.lower()
    mentioned: list[str] = []
    for code, pattern in CREW_ALIASES:
        if pattern.search(lower):
            mentioned.append(code)
    if not mentioned:
        return active_crew, False
    subject = mentioned[0]
    third = subject != active_crew.lower()
    if len(mentioned) == 1:
        return subject, third
    return mentioned[0], third


def _negated_fragment(text: str) -> set[str]:
    negated: set[str] = set()
    for match in NEGATION_BEFORE_SYMPTOM.finditer(text):
        fragment = match.group(1)
        for label in labels_from_text(fragment):
            negated.add(label)
    return negated


def _labels_in_clause(clause: str) -> list[str]:
    negated = _negated_fragment(clause)
    labels = labels_from_text(clause)
    return [label for label in labels if label not in negated]


def _distill_labels(labels: list[str]) -> list[str]:
    if not labels:
        return []
    if any(label in ISOLATION_SYMPTOM_LABELS for label in labels):
        return [label for label in labels if label in ISOLATION_SYMPTOM_LABELS]
    has_specific_pain = any(label in SPECIFIC_PAIN_LABELS for label in labels)
    seen_indications: set[str] = set()
    out: list[str] = []
    for label in labels:
        if label == "douleur" and has_specific_pain:
            continue
        indication = LABEL_INDICATION.get(label, label)
        if indication in seen_indications:
            continue
        seen_indications.add(indication)
        out.append(label)
    return out


def _split_clauses(message: str) -> list[str]:
    parts = [part.strip() for part in CLAUSE_SPLIT.split(message) if part.strip()]
    return parts or [message.strip()]


def build_narrative_summary(u: MessageUnderstanding, care_name: str) -> str:
    if not u.findings:
        return ""
    who = care_name if u.third_person else "toi"
    bits = [f.topic_fr for f in u.findings]
    joined = ", ".join(bits)
    return f"Pour {who} : {joined}."


def understand_message_rules(message: str, active_crew: str) -> MessageUnderstanding:
    care_crew, third = resolve_care_subject(message, active_crew)
    clauses = _split_clauses(message)
    ordered_labels: list[str] = []
    findings: list[ClinicalFinding] = []

    for clause in clauses:
        for label in _labels_in_clause(clause):
            if label not in ordered_labels:
                ordered_labels.append(label)
                findings.append(
                    ClinicalFinding(
                        symptom_label=label,
                        source_text=clause[:160],
                    )
                )

    if not ordered_labels:
        for label in _labels_in_clause(message):
            if label not in ordered_labels:
                ordered_labels.append(label)
                findings.append(
                    ClinicalFinding(symptom_label=label, source_text=message[:160])
                )

    distilled = _distill_labels(ordered_labels)
    findings = [f for f in findings if f.symptom_label in distilled]

    understanding = MessageUnderstanding(
        active_crew_code=active_crew,
        care_crew_code=care_crew,
        third_person=third,
        findings=findings,
        symptom_labels=distilled,
        extraction_mode="rules",
    )
    return understanding


def _merge_ollama_findings(
    base: MessageUnderstanding, labels: list[str], message: str
) -> MessageUnderstanding:
    valid = [label for label in labels if label in ALLOWED_LABELS]
    combined = list(dict.fromkeys(base.symptom_labels + valid))
    distilled = _distill_labels(combined)
    if distilled == base.symptom_labels:
        return base
    findings = [
        ClinicalFinding(symptom_label=label, source_text=message[:160]) for label in distilled
    ]
    return MessageUnderstanding(
        active_crew_code=base.active_crew_code,
        care_crew_code=base.care_crew_code,
        third_person=base.third_person,
        findings=findings,
        symptom_labels=distilled,
        extraction_mode="rules+ollama",
    )


async def refine_with_ollama(message: str, base: MessageUnderstanding) -> MessageUnderstanding:
    catalog = ", ".join(sorted(ALLOWED_LABELS))
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Tu extrais les symptomes medicaux d'un message en francais. "
                    "Reponds UNIQUEMENT en JSON: "
                    '{"symptoms":["label1","label2"],"about_crew":"elisa"|null}. '
                    f"Labels autorises (copie exacte): {catalog}. "
                    "Liste chaque probleme distinct (fievre, nausee, toux, etc.). "
                    "about_crew = code equipier concerne si un autre membre est nomme, sinon null."
                ),
            },
            {"role": "user", "content": message},
        ],
    }
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw = str(data.get("message", {}).get("content") or "").strip()
            parsed = json.loads(raw)
            labels = [str(s).lower().strip() for s in parsed.get("symptoms") or []]
            about = parsed.get("about_crew")
            updated = base
            if isinstance(about, str) and about.lower() in {c for c, _ in CREW_ALIASES}:
                code = about.lower()
                updated = MessageUnderstanding(
                    active_crew_code=base.active_crew_code,
                    care_crew_code=code,
                    third_person=code != base.active_crew_code.lower(),
                    findings=base.findings,
                    symptom_labels=base.symptom_labels,
                    extraction_mode=base.extraction_mode,
                )
            return _merge_ollama_findings(updated, labels, message)
    except Exception:
        return base


async def understand_message(
    message: str,
    active_crew: str,
    *,
    use_ollama: bool | None = None,
) -> MessageUnderstanding:
    base = understand_message_rules(message, active_crew)
    if use_ollama is None:
        use_ollama = settings.ollama_extract_symptoms
    if use_ollama:
        base = await refine_with_ollama(message, base)
    return base


def labels_for_eval(history: str, message: str, understanding: MessageUnderstanding | None) -> list[str]:
    if understanding and understanding.symptom_labels:
        return understanding.symptom_labels
    from app.services.ollama_client import extract_symptoms_for_eval

    return extract_symptoms_for_eval(history, message)
