from typing import Any

from pydantic import BaseModel, Field


class ExcludedOption(BaseModel):
    drug_code: str
    reason_code: str
    reason_text: str


class Recommendation(BaseModel):
    drug_code: str
    drug_name: str
    dose_mg: float
    rationale: str


class CareEvaluationResult(BaseModel):
    excluded_options: list[ExcludedOption] = Field(default_factory=list)
    recommendation: Recommendation | None = None
    escalate_to_physician: bool = False
    urgency: str = "routine"
    rules_fired: list[str] = Field(default_factory=list)
    non_drug_protocol: str | None = None


class CareEvaluateRequest(BaseModel):
    crew_member_code: str
    symptoms: list[str]
    requested_drug_code: str | None = None
    requested_dose_mg: float | None = None


class CareConfirmRequest(BaseModel):
    crew_member_code: str
    drug_code: str
    dose_mg: float


class ChatMessageRequest(BaseModel):
    session_id: str = "default"
    crew_member_code: str
    message: str


class ChatMessageResponse(BaseModel):
    session_id: str
    role: str
    content: str
    evaluation: CareEvaluationResult | None = None
    llm_mode: str = "template"


class AutonomyDrugRow(BaseModel):
    drug_code: str
    drug_name: str
    stock_units: int
    days_remaining: float


class AutonomyResponse(BaseModel):
    policy: str
    global_days: float
    drugs: list[AutonomyDrugRow]
    sick_count: int = 0
    crew_size: int = 0


class AutonomyCompareResponse(BaseModel):
    on_demand: AutonomyResponse
    rationing_quarantine: AutonomyResponse
    crisis_active: bool
    rationing_active: bool


class TriageEntry(BaseModel):
    crew_member_code: str
    full_name: str
    health_status: str
    severity_score: int
    triage_priority: int


class CrisisTriggerResponse(BaseModel):
    sick_count: int
    sick_ratio: float
    autonomy_before: AutonomyCompareResponse


class DecisionLogEntry(BaseModel):
    id: int
    action: str
    summary: str
    payload: dict[str, Any]
    created_at: str

    model_config = {"from_attributes": True}


class SecurityAlertOut(BaseModel):
    id: int
    source: str
    payload: dict[str, Any]
    created_at: str

    model_config = {"from_attributes": True}
