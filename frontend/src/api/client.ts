const base = import.meta.env.VITE_API_URL || "";
const TOKEN_KEY = "eir_access_token";

export const session = {
  getToken: () => localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY),
  setToken: (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    sessionStorage.removeItem(TOKEN_KEY);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  },
};

async function request<T>(path: string, init?: RequestInit, authenticated = true): Promise<T> {
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const token = session.getToken();
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authenticated && token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
  });
  if (res.status === 401 && authenticated) {
    session.clear();
    window.dispatchEvent(new Event("eir:unauthorized"));
  }
  if (!res.ok) {
    const raw = await res.text();
    let message = raw || res.statusText;
    try {
      const parsed = JSON.parse(raw) as { detail?: string };
      message = parsed.detail || message;
    } catch {
      // The API can return a plain-text reverse-proxy error.
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export type AuthUser = {
  username: string;
  full_name: string;
  role: "admin" | "crew";
  crew_member_code: string;
  allergies?: string[];
  avatar_data?: string | null;
  age?: number | null;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export type CrewMember = {
  code: string;
  full_name: string;
  age: number;
  allergies: string[];
  health_status: string;
  avatar_data?: string | null;
  face_enrolled?: boolean;
  face_samples?: number;
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
  plant_recommendation?: {
    plant_code: string;
    plant_name: string;
    protocol: string;
  } | null;
};

export type PlantCulture = {
  code: string;
  name: string;
  species: string;
  indication: string;
  replaces_drug_class: string;
  biomass_percent: number;
  growth_rate: number;
  status: string;
  notes: string;
  description: string;
  ready: boolean;
};

export type BacteriaCulture = {
  id_culture: number;
  code: string;
  nom_souche: string;
  categorie: string;
  temperature_celsius: number;
  quantite_boites: number;
  statut_viabilite: string;
  indication: string;
  treatable: boolean;
  notes: string;
  description: string;
  ready: boolean;
};

export type ChatResponse = {
  content: string;
  conversation_id?: string | null;
  session_id?: string;
  evaluation: CareEvaluation | null;
  llm_mode: string;
};

export type Conversation = {
  id: string;
  crew_member_code: string;
  created_by: string;
  title: string;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ConversationMessage = {
  id: number;
  conversation_id: string | null;
  role: "user" | "assistant";
  content: string;
  meta?: { llm_mode?: string; evaluation?: CareEvaluation } | null;
  created_at?: string | null;
};

export type TriageEntry = {
  crew_member_code: string;
  full_name: string;
  health_status: string;
  severity_score: number;
  triage_priority: number;
};

export type JournalEntry = {
  id: number;
  action: string;
  summary: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type SecurityAlert = {
  id: number;
  source: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type AutonomyCompare = {
  on_demand: { global_days: number; drugs: { drug_code: string; drug_name: string; stock_units: number; days_remaining: number }[]; sick_count: number; crew_size: number };
  rationing_quarantine: { global_days: number; drugs: { drug_code: string; drug_name: string; stock_units: number; days_remaining: number }[]; sick_count: number; crew_size: number };
  crisis_active: boolean;
  rationing_active: boolean;
};

export const api = {
  login: (username: string, password: string) =>
    request<LoginResponse>(
      "/api/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ username, password }),
      },
      false
    ),
  loginFace: (descriptor: number[]) =>
    request<LoginResponse>(
      "/api/auth/face",
      {
        method: "POST",
        body: JSON.stringify({ descriptor }),
      },
      false
    ),
  me: () => request<AuthUser>("/api/auth/me"),
  enrollFace: (code: string, descriptors: number[][]) =>
    request<{ ok: boolean; samples: number }>(`/api/crew/${code}/face`, {
      method: "POST",
      body: JSON.stringify({ descriptors }),
    }),
  clearFace: (code: string) =>
    request<{ ok: boolean }>(`/api/crew/${code}/face`, { method: "DELETE" }),
  conversations: (status = "open") =>
    request<Conversation[]>(`/api/conversations?status=${encodeURIComponent(status)}`),
  createConversation: (crew_member_code: string) =>
    request<Conversation>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({ crew_member_code }),
    }),
  conversationMessages: (id: string) =>
    request<ConversationMessage[]>(`/api/conversations/${id}/messages`),
  archiveConversation: (id: string) =>
    request<Conversation>(`/api/conversations/${id}/archive`, { method: "POST" }),
  crew: () => request<CrewMember[]>("/api/crew"),
  crewMember: (code: string) => request<CrewMember>(`/api/crew/${code}`),
  updateProfile: (code: string, body: { allergies: string[]; avatar_data?: string | null; full_name?: string }) =>
    request<CrewMember>(`/api/crew/${code}/profile`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  drugs: () => request<Drug[]>("/api/drugs"),
  chat: (crew_member_code: string, message: string, conversation_id?: string) =>
    request<ChatResponse>("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({
        crew_member_code,
        message,
        conversation_id: conversation_id || undefined,
        session_id: conversation_id || "default",
      }),
    }),
  confirm: (crew_member_code: string, drug_code: string, dose_mg: number) =>
    request<{ ok: boolean }>("/api/care/confirm", {
      method: "POST",
      body: JSON.stringify({ crew_member_code, drug_code, dose_mg }),
    }),
  autonomy: () => request<AutonomyCompare>("/api/autonomy"),
  triage: () => request<TriageEntry[]>("/api/triage"),
  triggerCrisis: () => request("/api/crisis/trigger", { method: "POST" }),
  rationing: () => request<AutonomyCompare>("/api/crisis/rationing", { method: "POST" }),
  forceStockZero: (code: string) =>
    request("/api/demo/force-stock-zero/" + code, { method: "POST" }),
  restock: () => request("/api/demo/restock", { method: "POST" }),
  resetDemo: () => request("/api/demo/reset", { method: "POST" }),
  plants: () => request<PlantCulture[]>("/api/plants"),
  irrigatePlant: (code: string) =>
    request<PlantCulture>(`/api/plants/${code}/irrigate`, { method: "POST" }),
  boostPlant: (code: string) =>
    request<PlantCulture>(`/api/plants/${code}/boost`, { method: "POST" }),
  harvestPlant: (code: string) =>
    request<PlantCulture>(`/api/plants/${code}/harvest`, { method: "POST" }),
  bacteria: () => request<BacteriaCulture[]>("/api/bacteria"),
  incubateBacteria: (code: string) =>
    request<BacteriaCulture>(`/api/bacteria/${code}/incubate`, { method: "POST" }),
  harvestBacteria: (code: string) =>
    request<BacteriaCulture>(`/api/bacteria/${code}/harvest`, { method: "POST" }),
  journal: () => request<JournalEntry[]>("/api/journal"),
  securityAlerts: () => request<SecurityAlert[]>("/api/security/alerts"),
};
