"""Estimation logistique d'une epidemie de gastro sur 6 mois.

Hypotheses pedagogiques, pas une prescription. Sources de cadrage :
- OMS : la rehydratation orale est le traitement de premiere ligne des diarrhees aigues.
- Episode aigu adulte courant : environ 3 a 5 jours.
- Equipage de demonstration : 20 personnes, prevalence simultanee 15 %.
"""

CREW_SIZE = 20
PREVALENCE = 0.15
EPIDEMIC_DAYS = 182
WAVE_DAYS = 5
WAVES = 6
SICK_AT_ONCE = round(CREW_SIZE * PREVALENCE)

PLAN = [
    {
        "drug_code": "ors",
        "label": "Sels de rehydratation",
        "units_per_sick_day": 2,
        "stock_units": 90,
        "use_days_per_wave": WAVE_DAYS,
        "basis": "2 preparations ORS par adulte malade et par jour de diarrhee aigue.",
    },
    {
        "drug_code": "smecta",
        "label": "Smecta",
        "units_per_sick_day": 3,
        "stock_units": 48,
        "use_days_per_wave": WAVE_DAYS,
        "basis": "3 sachets par jour pendant l'episode, pas pendant 6 mois continus.",
    },
    {
        "drug_code": "loperamide",
        "label": "Loperamide",
        "units_per_sick_day": 4,
        "stock_units": 36,
        "use_days_per_wave": 2,
        "basis": "Court traitement seulement, jamais si fievre, sang ou suspicion invasive.",
    },
    {
        "drug_code": "ondansetron",
        "label": "Ondansetron",
        "units_per_sick_day": 1,
        "stock_units": 40,
        "use_days_per_wave": 2,
        "basis": "1 dose par jour si vomissements importants, sur 2 jours.",
    },
]


def _cover_days(stock: int, daily: float) -> float:
    if daily <= 0:
        return 0.0
    return round(stock / daily, 1)


def gastro_six_month_estimate() -> dict:
    daily_need = SICK_AT_ONCE
    rows = []
    for item in PLAN:
        per_wave = item["units_per_sick_day"] * item["use_days_per_wave"] * daily_need
        six_month_need = per_wave * WAVES
        daily = item["units_per_sick_day"] * daily_need
        rows.append(
            {
                "drug_code": item["drug_code"],
                "label": item["label"],
                "stock_units": item["stock_units"],
                "need_6_months": six_month_need,
                "shortage_units": max(0, six_month_need - item["stock_units"]),
                "days_covered_at_peak": _cover_days(item["stock_units"], daily),
                "basis": item["basis"],
            }
        )
    return {
        "scenario": "Epidemie de gastro, 6 mois, prevalence 15 %",
        "crew_size": CREW_SIZE,
        "sick_at_once": SICK_AT_ONCE,
        "waves": WAVES,
        "rows": rows,
        "conclusion": (
            "Le stock de demonstration ne couvre pas 6 mois au pic. "
            "Le rationnement, l'ORS en priorite et les cultures locales deviennent indispensables."
        ),
    }
