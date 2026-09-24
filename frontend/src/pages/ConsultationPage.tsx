import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  Archive,
  Check,
  ChevronRight,
  HeartPulse,
  Leaf,
  MessageSquarePlus,
  Send,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UserRound,
  Volume2,
  VolumeX,
} from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { api, CareEvaluation } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import PlantPortrait from "../components/PlantPortrait";
import { primeSpeech, setVoiceEnabled, speak, stopSpeaking, voiceEnabled, welcomeText } from "../speech/speak";

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
const CONV_KEY = "eir_conversation_id";

function patientName(
  members: { code: string; full_name: string }[] | undefined,
  code: string,
): string | null {
  return members?.find((member) => member.code === code)?.full_name ?? null;
}

export default function ConsultationPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const crew = useQuery({ queryKey: ["crew"], queryFn: api.crew });
  const isolationGuide = useQuery({ queryKey: ["isolation-guide"], queryFn: api.isolationGuide });
  const [selectedCrew, setSelectedCrew] = useState(user?.crew_member_code ?? "elisa");
  const [conversationId, setConversationId] = useState<string | null>(() => localStorage.getItem(CONV_KEY));
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatLine[]>([]);
  const [evaluation, setEvaluation] = useState<CareEvaluation | null>(null);
  const [confirmedCodes, setConfirmedCodes] = useState<string[]>([]);
  const [stockLeft, setStockLeft] = useState<Record<string, number>>({});
  const [plantHarvested, setPlantHarvested] = useState(false);
  const threadEnd = useRef<HTMLDivElement>(null);
  const bootstrapped = useRef(false);
  const welcomed = useRef<string | null>(null);
  const [voiceOn, setVoiceOn] = useState(() => voiceEnabled());
  const [speaking, setSpeaking] = useState(false);

  const conversationsQuery = useQuery({
    queryKey: ["conversations"],
    queryFn: () => api.conversations("open"),
  });

  const historyQuery = useQuery({
    queryKey: ["conversation-messages", conversationId],
    queryFn: () => api.conversationMessages(conversationId as string),
    enabled: Boolean(conversationId),
  });

  useEffect(() => {
    threadEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => () => stopSpeaking(), []);

  const spokenWelcome = welcomeText(patientName(crew.data, selectedCrew));

  useEffect(() => {
    if (!voiceOn || !conversationId || !historyQuery.isSuccess || !historyQuery.data) return;
    if (!patientName(crew.data, selectedCrew)) return;
    if (historyQuery.data.length > 0) return;
    if (welcomed.current === conversationId) return;
    welcomed.current = conversationId;
    speak(spokenWelcome, {
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
    });
  }, [voiceOn, conversationId, historyQuery.isSuccess, historyQuery.data, spokenWelcome]);

  useEffect(() => {
    if (!conversationsQuery.data || bootstrapped.current) return;
    bootstrapped.current = true;
    const open = conversationsQuery.data.filter((row) => row.status === "open");
    const stored = localStorage.getItem(CONV_KEY);
    const found =
      open.find((row) => row.id === stored && row.crew_member_code === selectedCrew) ||
      open.find((row) => row.crew_member_code === selectedCrew);
    if (found) {
      setConversationId(found.id);
      localStorage.setItem(CONV_KEY, found.id);
      return;
    }
    api.createConversation(selectedCrew).then((row) => {
      setConversationId(row.id);
      localStorage.setItem(CONV_KEY, row.id);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    });
  }, [conversationsQuery.data, selectedCrew, queryClient]);

  useEffect(() => {
    if (!historyQuery.data) return;
    setMessages(
      historyQuery.data.map((row) => ({
        id: String(row.id),
        role: row.role,
        content: row.content,
        mode: row.meta?.llm_mode,
      })),
    );
    const last = [...historyQuery.data].reverse().find((row) => row.role === "assistant" && row.meta?.evaluation);
    setEvaluation(last?.meta?.evaluation ?? null);
  }, [historyQuery.data]);

  const chat = useMutation({
    mutationFn: (text: string) => api.chat(selectedCrew, text, conversationId || undefined),
    onSuccess: async (response) => {
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
        localStorage.setItem(CONV_KEY, response.conversation_id);
      }
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
      setConfirmedCodes([]);
      setStockLeft({});
      setPlantHarvested(false);
      speak(response.content, {
        onStart: () => setSpeaking(true),
        onEnd: () => setSpeaking(false),
      });
      await queryClient.invalidateQueries({ queryKey: ["journal"] });
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
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
    mutationFn: async (item: { drug_code: string; dose_mg: number }) => {
      const target = evaluation?.understanding?.care_crew_code ?? selectedCrew;
      const result = await api.confirm(target, item.drug_code, item.dose_mg);
      return { drug_code: item.drug_code, stock_remaining: result.stock_remaining };
    },
    onSuccess: async (result) => {
      if (!result) return;
      setConfirmedCodes((current) => [...current, result.drug_code]);
      setStockLeft((current) => ({ ...current, [result.drug_code]: result.stock_remaining }));
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["autonomy"] }),
        queryClient.invalidateQueries({ queryKey: ["drugs"] }),
        queryClient.invalidateQueries({ queryKey: ["gastro-estimate"] }),
        queryClient.invalidateQueries({ queryKey: ["journal"] }),
      ]);
    },
  });

  async function startNewChat() {
    const row = await api.createConversation(selectedCrew);
    welcomed.current = row.id;
    setConversationId(row.id);
    localStorage.setItem(CONV_KEY, row.id);
    setMessages([]);
    setEvaluation(null);
    setConfirmedCodes([]);
    setStockLeft({});
    setPlantHarvested(false);
    primeSpeech();
    speak(spokenWelcome, {
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
    });
    await queryClient.invalidateQueries({ queryKey: ["conversations"] });
  }

  function toggleVoice() {
    const next = !voiceOn;
    setVoiceEnabled(next);
    setVoiceOn(next);
    setSpeaking(false);
    if (next) {
      primeSpeech();
      if (messages.length === 0) {
        welcomed.current = conversationId;
        speak(spokenWelcome, {
          onStart: () => setSpeaking(true),
          onEnd: () => setSpeaking(false),
        });
      }
    }
  }

  function listen(text: string) {
    if (!voiceOn) {
      setVoiceEnabled(true);
      setVoiceOn(true);
    }
    primeSpeech();
    speak(text, {
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
    });
  }

  async function closeChat() {
    if (conversationId) {
      await api.archiveConversation(conversationId);
    }
    await startNewChat();
  }

  function submit(event?: FormEvent, suggested?: string) {
    event?.preventDefault();
    const text = (suggested ?? message).trim();
    if (!text || chat.isPending) return;
    primeSpeech();
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content: text },
    ]);
    setMessage("");
    setEvaluation(null);
    setConfirmedCodes([]);
    chat.mutate(text);
  }

  const selectedMember = crew.data?.find((member) => member.code === selectedCrew);
  const currentTitle =
    conversationsQuery.data?.find((row) => row.id === conversationId)?.title || "Nouvelle conversation";

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
          <div className="chat-toolbar">
            <strong>{currentTitle}</strong>
            <div>
              <button
                type="button"
                aria-pressed={voiceOn}
                onClick={toggleVoice}
              >
                {voiceOn ? <Volume2 size={16} /> : <VolumeX size={16} />}
                {voiceOn ? "Voix active" : "Voix coupee"}
              </button>
              <button type="button" onClick={startNewChat}>
                <MessageSquarePlus size={16} /> Nouveau chat
              </button>
              <button type="button" onClick={closeChat}>
                <Archive size={16} /> Fermer
              </button>
            </div>
          </div>
          <div className="patient-strip">
            <div className="patient-icon"><UserRound size={20} /></div>
            <div>
              <span>Patient actif</span>
              {user?.role === "admin" ? (
                <select
                  aria-label="Profil équipage"
                  value={selectedCrew}
                  onChange={(event) => {
                    bootstrapped.current = false;
                    setSelectedCrew(event.target.value);
                    setMessages([]);
                    setEvaluation(null);
                  }}
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
                <span>{speaking ? "EIR parle" : "Systeme EIR pret"}</span>
                <h2>Comment vous sentez-vous ?</h2>
                <p>{spokenWelcome}</p>
                <button type="button" className="listen-btn" onClick={() => listen(spokenWelcome)}>
                  <Volume2 size={16} /> Ecouter le message
                </button>
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
                    {line.role === "assistant" && (
                      <button type="button" className="listen-btn" onClick={() => listen(line.content)}>
                        <Volume2 size={16} /> Ecouter
                      </button>
                    )}
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
                {evaluation.understanding && evaluation.understanding.findings.length > 0 && (
                  <div className="recommendation-card glass-panel">
                    <div className="recommendation-top">
                      <span><Sparkles size={17} /> Compréhension EIR</span>
                      <i>{evaluation.understanding.extraction_mode}</i>
                    </div>
                    {evaluation.understanding.narrative_summary && (
                      <p className="rationale">{evaluation.understanding.narrative_summary}</p>
                    )}
                    <ul className="finding-list">
                      {evaluation.understanding.findings.map((row) => (
                        <li key={row.symptom_label}>
                          <strong>{row.topic_fr}</strong>
                          <span>{row.source_text}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {evaluation.escalate_to_physician && (
                  <div className="urgent-card">
                    <AlertCircle size={24} />
                    <div><span>Priorité critique</span><strong>Protocole d'urgence embarque</strong><p>{evaluation.non_drug_protocol}</p></div>
                  </div>
                )}

                {evaluation.symptom_items && evaluation.symptom_items.length > 1 && (
                  <div className="recommendation-card glass-panel">
                    <div className="recommendation-top">
                      <span><HeartPulse size={17} /> Plan par symptôme</span>
                    </div>
                    <ul className="finding-list">
                      {evaluation.symptom_items.map((item) => (
                        <li key={item.symptom_label}>
                          <strong>{item.topic_fr}</strong>
                          <span>
                            {item.recommendation
                              ? `${item.recommendation.drug_name} ${item.recommendation.dose_mg} mg`
                              : item.non_drug_protocol || item.plant_recommendation?.protocol || "Surveillance"}
                          </span>
                          {item.recommendation && (
                            <button
                              type="button"
                              disabled={
                                confirmation.isPending ||
                                confirmedCodes.includes(item.recommendation.drug_code)
                              }
                              onClick={() =>
                                confirmation.mutate({
                                  drug_code: item.recommendation!.drug_code,
                                  dose_mg: item.recommendation!.dose_mg,
                                })
                              }
                            >
                              {confirmedCodes.includes(item.recommendation.drug_code)
                                ? `Prise enregistree, stock ${stockLeft[item.recommendation.drug_code] ?? item.recommendation.stock_units ?? "-"}`
                                : `Confirmer cette prise (stock ${stockLeft[item.recommendation.drug_code] ?? item.recommendation.stock_units ?? "-"})`}
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {evaluation.recommendation && (
                  <div className="recommendation-card glass-panel">
                    <div className="recommendation-top">
                      <span><ShieldCheck size={17} /> Proposition validée</span>
                      <i>
                        Stock {stockLeft[evaluation.recommendation.drug_code] ?? evaluation.recommendation.stock_units ?? "-"}
                      </i>
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
                      className={confirmedCodes.includes(evaluation.recommendation.drug_code) ? "confirmed" : ""}
                      type="button"
                      disabled={
                        confirmation.isPending ||
                        confirmedCodes.includes(evaluation.recommendation.drug_code)
                      }
                      onClick={() =>
                        confirmation.mutate({
                          drug_code: evaluation.recommendation!.drug_code,
                          dose_mg: evaluation.recommendation!.dose_mg,
                        })
                      }
                    >
                      {confirmedCodes.includes(evaluation.recommendation.drug_code) ? (
                        <><Check size={18} /> Prise enregistrée</>
                      ) : (
                        "Confirmer la prise"
                      )}
                    </button>
                    {confirmation.isError && (
                      <p className="form-error" role="alert">
                        {confirmation.error instanceof Error ? confirmation.error.message : "Le stock n'a pas ete mis a jour."}
                      </p>
                    )}
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

          {isolationGuide.data && (
            <details className="isolation-guide glass-panel">
              <summary>Quand l isolement cabine est declenche</summary>
              <p>{isolationGuide.data.summary}</p>
              <ul className="finding-list">
                {isolationGuide.data.isolation_cases.map((row) => (
                  <li key={row.title}>
                    <strong>{row.title}</strong>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </aside>
      </div>
    </div>
  );
}
