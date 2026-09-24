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
    stock_units: int = 0


class PlantRecommendation(BaseModel):
    plant_code: str
    plant_name: str
    protocol: str


class ClinicalFindingOut(BaseModel):
    symptom_label: str
    source_text: str
    topic_fr: str


class MessageUnderstandingOut(BaseModel):
    care_crew_code: str
    care_crew_name: str | None = None
    third_person: bool = False
    findings: list[ClinicalFindingOut] = Field(default_factory=list)
    extraction_mode: str = "rules"
    narrative_summary: str = ""


class SymptomCareItem(BaseModel):
    symptom_label: str
    topic_fr: str
    recommendation: Recommendation | None = None
    non_drug_protocol: str | None = None
    plant_recommendation: PlantRecommendation | None = None
    escalate_to_physician: bool = False


class CareEvaluationResult(BaseModel):
    excluded_options: list[ExcludedOption] = Field(default_factory=list)
    recommendation: Recommendation | None = None
    escalate_to_physician: bool = False
    urgency: str = "routine"
    rules_fired: list[str] = Field(default_factory=list)
    non_drug_protocol: str | None = None
    plant_recommendation: PlantRecommendation | None = None
    symptom_items: list[SymptomCareItem] = Field(default_factory=list)
    understanding: MessageUnderstandingOut | None = None
    needs_clarification: bool = False


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
    conversation_id: str | None = None
    crew_member_code: str
    message: str


class ChatMessageResponse(BaseModel):
    session_id: str
    conversation_id: str | None = None
    role: str
    content: str
    evaluation: CareEvaluationResult | None = None
    llm_mode: str = "template"


class FaceLoginRequest(BaseModel):
    descriptor: list[float]


class FaceEnrollRequest(BaseModel):
    crew_member_code: str
    descriptors: list[list[float]] = Field(min_length=1, max_length=8)


class FaceDescriptorsBody(BaseModel):
    descriptors: list[list[float]] = Field(min_length=1, max_length=8)


class ConversationCreate(BaseModel):
    crew_member_code: str


class ConversationOut(BaseModel):
    id: str
    crew_member_code: str
    created_by: str
    title: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    username: str
    full_name: str
    role: str
    crew_member_code: str
    allergies: list[str] = Field(default_factory=list)
    avatar_data: str | None = None
    age: int | None = None


class ProfileUpdate(BaseModel):
    allergies: list[str] = Field(default_factory=list, max_length=20)
    avatar_data: str | None = None
    full_name: str | None = Field(default=None, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


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
