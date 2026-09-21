const base = import.meta.env.VITE_API_URL || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type CrewMember = {
  code: string;
  full_name: string;
  age: number;
  allergies: string[];
  health_status: string;
};

export type Drug = {
  code: string;
  name: string;
  stock_units: number;
  therapeutic_class: string;
  is_critical: boolean;
};

export type CareEvaluation = {
  excluded_options: { drug_code: string; reason_code: string; reason_text: string }[];
  recommendation: {
    drug_code: string;
    drug_name: string;
    dose_mg: number;
    rationale: string;
  } | null;
  escalate_to_physician: boolean;
  urgency: string;
  rules_fired: string[];
  non_drug_protocol?: string | null;
};

export type ChatResponse = {
  content: string;
  evaluation: CareEvaluation | null;
  llm_mode: string;
};

export type AutonomyCompare = {
  on_demand: { global_days: number; drugs: { drug_code: string; drug_name: string; stock_units: number; days_remaining: number }[]; sick_count: number; crew_size: number };
  rationing_quarantine: { global_days: number; drugs: { drug_code: string; drug_name: string; stock_units: number; days_remaining: number }[]; sick_count: number; crew_size: number };
  crisis_active: boolean;
  rationing_active: boolean;
};

export const api = {
  crew: () => request<CrewMember[]>("/api/crew"),
  drugs: () => request<Drug[]>("/api/drugs"),
  chat: (crew_member_code: string, message: string, session_id = "default") =>
    request<ChatResponse>("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({ crew_member_code, message, session_id }),
    }),
  confirm: (crew_member_code: string, drug_code: string, dose_mg: number) =>
    request<{ ok: boolean }>("/api/care/confirm", {
      method: "POST",
      body: JSON.stringify({ crew_member_code, drug_code, dose_mg }),
    }),
  autonomy: () => request<AutonomyCompare>("/api/autonomy"),
  triage: () =>
    request<
      {
        crew_member_code: string;
        full_name: string;
        health_status: string;
        severity_score: number;
        triage_priority: number;
      }[]
    >("/api/triage"),
  triggerCrisis: () => request("/api/crisis/trigger", { method: "POST" }),
  rationing: () => request<AutonomyCompare>("/api/crisis/rationing", { method: "POST" }),
  forceStockZero: (code: string) =>
    request("/api/demo/force-stock-zero/" + code, { method: "POST" }),
  resetDemo: () => request("/api/demo/reset", { method: "POST" }),
  journal: () =>
    request<{ id: number; action: string; summary: string; created_at: string }[]>("/api/journal"),
  securityAlerts: () =>
    request<{ id: number; source: string; payload: Record<string, unknown>; created_at: string }[]>(
      "/api/security/alerts"
    ),
};
