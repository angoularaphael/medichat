import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  Check,
  ChevronRight,
  HeartPulse,
  Leaf,
  Send,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UserRound,
} from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { api, CareEvaluation } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import PlantPortrait from "../components/PlantPortrait";

type ChatLine = {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode?: string;
};

const suggestions = [
  "J'ai mal à la tête depuis ce matin",
  "Je vomis depuis ce matin",
  "J'ai la diarrhée et le ventre liquide",
  "Je n'arrive plus à aller à la selle",
];

export default function ConsultationPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const crew = useQuery({ queryKey: ["crew"], queryFn: api.crew });
  const [selectedCrew, setSelectedCrew] = useState(user?.crew_member_code ?? "elisa");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatLine[]>([]);
  const [evaluation, setEvaluation] = useState<CareEvaluation | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [plantHarvested, setPlantHarvested] = useState(false);
  const threadEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    threadEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const chat = useMutation({
    mutationFn: (text: string) => api.chat(selectedCrew, text, `${user?.username}-${Date.now()}`),
    onSuccess: async (response) => {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.content,
          mode: response.llm_mode,
        },
      ]);
      setEvaluation(response.evaluation);
      setConfirmed(false);
      setPlantHarvested(false);
      await queryClient.invalidateQueries({ queryKey: ["journal"] });
    },
  });

  const plantHarvest = useMutation({
    mutationFn: async () => {
      if (!evaluation?.plant_recommendation) return;
      await api.harvestPlant(evaluation.plant_recommendation.plant_code);
    },
    onSuccess: async () => {
      setPlantHarvested(true);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["plants"] }),
        queryClient.invalidateQueries({ queryKey: ["bacteria"] }),
        queryClient.invalidateQueries({ queryKey: ["journal"] }),
      ]);
    },
  });

  const confirmation = useMutation({
    mutationFn: async () => {
      if (!evaluation?.recommendation) return;
      const item = evaluation.recommendation;
      await api.confirm(selectedCrew, item.drug_code, item.dose_mg);
    },
    onSuccess: async () => {
      setConfirmed(true);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["autonomy"] }),
        queryClient.invalidateQueries({ queryKey: ["drugs"] }),
        queryClient.invalidateQueries({ queryKey: ["journal"] }),
      ]);
    },
  });

  function submit(event?: FormEvent, suggested?: string) {
    event?.preventDefault();
    const text = (suggested ?? message).trim();
    if (!text || chat.isPending) return;
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content: text },
    ]);
    setMessage("");
    setEvaluation(null);
    chat.mutate(text);
  }

  const selectedMember = crew.data?.find((member) => member.code === selectedCrew);

  return (
    <div className="consultation-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Assistant clinique / Moteur EIR</span>
          <h1>Consultation de bord</h1>
          <p>Decrivez vos symptomes. EIR decide a bord: allergies, stocks, puis cultures si les flacons sont vides.</p>
        </div>
        <span className="ai-status"><i /> IA locale connectable</span>
      </div>

      <div className="consultation-grid">
        <section className="chat-panel glass-panel">
          <div className="patient-strip">
            <div className="patient-icon"><UserRound size={20} /></div>
            <div>
              <span>Patient actif</span>
              {user?.role === "admin" ? (
                <select
                  aria-label="Profil équipage"
                  value={selectedCrew}
                  onChange={(event) => setSelectedCrew(event.target.value)}
                >
                  {crew.data?.map((member) => (
                    <option value={member.code} key={member.code}>{member.full_name}</option>
                  ))}
                </select>
              ) : (
                <strong>{selectedMember?.full_name ?? user?.full_name}</strong>
              )}
            </div>
            <div className="patient-meta">
              <span>Allergies</span>
              <strong>{selectedMember?.allergies.length ? selectedMember.allergies.join(", ") : "Aucune connue"}</strong>
            </div>
          </div>

          <div className="chat-thread" aria-live="polite">
            {messages.length === 0 && (
              <motion.div className="chat-welcome" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="assistant-orb"><HeartPulse size={28} /></div>
                <span>Système EIR prêt</span>
                <h2>Comment vous sentez-vous ?</h2>
                <p>Decrivez votre ressenti. EIR agit tout de suite; l'avis sol, s'il arrive, vient en retard.</p>
                <div className="suggestion-grid">
                  {suggestions.map((suggestion) => (
                    <button type="button" key={suggestion} onClick={() => submit(undefined, suggestion)}>
                      {suggestion}<ChevronRight size={15} />
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            <AnimatePresence initial={false}>
              {messages.map((line) => (
                <motion.div
                  className={`chat-message ${line.role}`}
                  key={line.id}
                  initial={{ opacity: 0, y: 12, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                >
                  {line.role === "assistant" && <div className="message-avatar"><Sparkles size={16} /></div>}
                  <div>
                    <span>{line.role === "assistant" ? "EIR Medichat" : selectedMember?.full_name}</span>
                    <p>{line.content}</p>
                    {line.mode && <small>{line.mode === "ollama" ? "Reformulation IA locale" : "Réponse sécurisée hors ligne"}</small>}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {chat.isPending && (
              <div className="analysis-loader">
                <div className="scan-orb"><i /><i /><i /></div>
                <div><strong>Analyse en cours</strong><span>Vérification du profil, des allergies et du stock...</span></div>
              </div>
            )}
            {chat.error && <p className="form-error" role="alert">{chat.error.message}</p>}
            <div ref={threadEnd} />
          </div>

          <form className="chat-composer" onSubmit={submit}>
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Décrivez vos symptômes, leur intensité et depuis quand..."
              aria-label="Description des symptômes"
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submit();
                }
              }}
            />
            <button type="submit" disabled={!message.trim() || chat.isPending} aria-label="Envoyer">
              <Send size={19} />
            </button>
          </form>
        </section>

        <aside className="decision-column">
          <div className="decision-header">
            <span className="eyebrow">Décision structurée</span>
            <h2>Rapport clinique</h2>
          </div>

          {!evaluation && (
            <div className="decision-empty glass-panel">
              <Stethoscope size={30} />
              <strong>En attente d'analyse</strong>
              <p>Le rapport de sécurité apparaîtra ici après votre message.</p>
            </div>
          )}

          <AnimatePresence mode="wait">
            {evaluation && (
              <motion.div
                className="decision-result"
                key={evaluation.rules_fired.join("-")}
                initial={{ opacity: 0, x: 18 }}
                animate={{ opacity: 1, x: 0 }}
              >
                {evaluation.escalate_to_physician && (
                  <div className="urgent-card">
                    <AlertCircle size={24} />
                    <div><span>Priorité critique</span><strong>Protocole d'urgence embarque</strong><p>{evaluation.non_drug_protocol}</p></div>
                  </div>
                )}

                {evaluation.recommendation && (
                  <div className="recommendation-card glass-panel">
                    <div className="recommendation-top">
                      <span><ShieldCheck size={17} /> Proposition validée</span>
                      <i>Stock disponible</i>
                    </div>
                    <div className="drug-name">
                      <span>{evaluation.recommendation.drug_name.charAt(0)}</span>
                      <div>
                        <h3>{evaluation.recommendation.drug_name}</h3>
                        <p>{evaluation.recommendation.drug_code}</p>
                      </div>
                    </div>
                    <div className="dose-readout">
                      <span>Dose proposée</span>
                      <strong>{evaluation.recommendation.dose_mg} <small>mg</small></strong>
                    </div>
                    <p className="rationale">{evaluation.recommendation.rationale}</p>
                    <button
                      className={confirmed ? "confirmed" : ""}
                      type="button"
                      disabled={confirmation.isPending || confirmed}
                      onClick={() => confirmation.mutate()}
                    >
                      {confirmed ? <><Check size={18} /> Prise enregistrée</> : "Confirmer la prise"}
                    </button>
                  </div>
                )}

                {evaluation.plant_recommendation && (
                  <div className="recommendation-card glass-panel">
                    <div className="recommendation-top">
                      <span><Leaf size={17} /> Relais botanique</span>
                      <i>Serre de bord</i>
                    </div>
                    <div className="drug-name">
                      <PlantPortrait
                        compact
                        code={evaluation.plant_recommendation.plant_code}
                        name={evaluation.plant_recommendation.plant_name}
                      />
                      <div>
                        <h3>{evaluation.plant_recommendation.plant_name}</h3>
                        <p>{evaluation.plant_recommendation.plant_code}</p>
                      </div>
                    </div>
                    <p className="rationale">{evaluation.plant_recommendation.protocol}</p>
                    <button
                      className={plantHarvested ? "confirmed" : ""}
                      type="button"
                      disabled={plantHarvest.isPending || plantHarvested}
                      onClick={() => plantHarvest.mutate()}
                    >
                      {plantHarvested ? <><Check size={18} /> Recolte enregistree</> : "Recolter la culture"}
                    </button>
                    {plantHarvest.error && <p className="form-error" role="alert">{plantHarvest.error.message}</p>}
                  </div>
                )}

                {!evaluation.recommendation && !evaluation.escalate_to_physician && !evaluation.plant_recommendation && (
                  <div className="protocol-card glass-panel">
                    <ShieldCheck size={22} />
                    <span>Protocole de surveillance a bord</span>
                    <p>{evaluation.non_drug_protocol || "Aucune proposition medicamenteuse. Surveillance EIR uniquement."}</p>
                  </div>
                )}

                {evaluation.excluded_options.length > 0 && (
                  <div className="excluded-card glass-panel">
                    <span>Options écartées</span>
                    {evaluation.excluded_options.map((option) => (
                      <div key={`${option.drug_code}-${option.reason_code}`}>
                        <AlertCircle size={16} />
                        <p><strong>{option.drug_code}</strong>{option.reason_text}</p>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </aside>
      </div>
    </div>
  );
}
