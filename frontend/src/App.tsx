import { useCallback, useEffect, useState } from "react";
import { api, AutonomyCompare, CareEvaluation, CrewMember, Drug } from "./api/client";

type ChatLine = { role: "user" | "assistant"; content: string; mode?: string };

export default function App() {
  const [crew, setCrew] = useState<CrewMember[]>([]);
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [selectedCrew, setSelectedCrew] = useState("elisa");
  const [message, setMessage] = useState("");
  const [chat, setChat] = useState<ChatLine[]>([]);
  const [lastEval, setLastEval] = useState<CareEvaluation | null>(null);
  const [autonomy, setAutonomy] = useState<AutonomyCompare | null>(null);
  const [triage, setTriage] = useState<
    { crew_member_code: string; full_name: string; triage_priority: number; severity_score: number }[]
  >([]);
  const [journal, setJournal] = useState<{ summary: string; created_at: string }[]>([]);
  const [alerts, setAlerts] = useState<{ source: string; payload: Record<string, unknown> }[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setError("");
      const [c, d, a, t, j, s] = await Promise.all([
        api.crew(),
        api.drugs(),
        api.autonomy(),
        api.triage(),
        api.journal(),
        api.securityAlerts(),
      ]);
      setCrew(c);
      setDrugs(d);
      setAutonomy(a);
      setTriage(t);
      setJournal(j.slice(0, 8));
      setAlerts(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur chargement");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function sendChat() {
    if (!message.trim()) return;
    setLoading(true);
    setChat((prev) => [...prev, { role: "user", content: message }]);
    try {
      const res = await api.chat(selectedCrew, message);
      setChat((prev) => [
        ...prev,
        { role: "assistant", content: res.content, mode: res.llm_mode },
      ]);
      setLastEval(res.evaluation);
      setMessage("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur chat");
    } finally {
      setLoading(false);
    }
  }

  async function confirmCare() {
    if (!lastEval?.recommendation) return;
    const r = lastEval.recommendation;
    await api.confirm(selectedCrew, r.drug_code, r.dose_mg);
    await refresh();
  }

  return (
    <div className="app-shell">
      <header>
        <h1>EIR Medichat</h1>
        <p>
          Pharmacie embarquee Yggdrasil — aide a la decision (prototype workshop, pas dispositif medical).
        </p>
      </header>

      <div className="crisis-bar">
        <button
          type="button"
          className="block-mobile"
          onClick={async () => {
            await api.triggerCrisis();
            await refresh();
          }}
        >
          Crise 15 %
        </button>
        <button
          type="button"
          className="secondary block-mobile"
          onClick={async () => {
            await api.rationing();
            await refresh();
          }}
        >
          Rationnement / quarantaine
        </button>
        <button
          type="button"
          className="danger block-mobile"
          onClick={async () => {
            await api.forceStockZero("paracetamol");
            await refresh();
          }}
        >
          Stock paracetamol a 0
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="grid">
        <section className="panel">
          <h2>Chat infirmerie</h2>
          <label htmlFor="crew">Profil equipage</label>
          <select
            id="crew"
            value={selectedCrew}
            onChange={(e) => setSelectedCrew(e.target.value)}
          >
            {crew.map((m) => (
              <option key={m.code} value={m.code}>
                {m.full_name} ({m.code})
              </option>
            ))}
          </select>

          <div className="chat-log" aria-live="polite">
            {chat.map((line, i) => (
              <div key={i} className={`msg ${line.role}`}>
                {line.content}
                {line.mode && <span className="badge">{line.mode}</span>}
              </div>
            ))}
          </div>

          <label htmlFor="msg">Symptomes</label>
          <textarea
            id="msg"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ex: mal de tete depuis ce matin"
          />
          <div className="btn-row">
            <button type="button" className="block-mobile" disabled={loading} onClick={sendChat}>
              Envoyer
            </button>
            <button
              type="button"
              className="secondary block-mobile"
              disabled={!lastEval?.recommendation}
              onClick={confirmCare}
            >
              Confirmer proposition
            </button>
          </div>
        </section>

        <section className="panel">
          <h2>Dashboard</h2>
          {autonomy && (
            <div className="metrics">
              <div className="metric">
                <span>Autonomie (demande)</span>
                <strong>{autonomy.on_demand.global_days} j</strong>
              </div>
              <div className="metric">
                <span>Autonomie (rationnement)</span>
                <strong>{autonomy.rationing_quarantine.global_days} j</strong>
              </div>
            </div>
          )}

          <h2 style={{ marginTop: "1rem" }}>Stocks critiques</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Medicament</th>
                  <th>Stock</th>
                  <th>Jours</th>
                </tr>
              </thead>
              <tbody>
                {autonomy?.on_demand.drugs.map((d) => (
                  <tr key={d.drug_code}>
                    <td>{d.drug_name}</td>
                    <td>{d.stock_units}</td>
                    <td>{d.days_remaining}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2 style={{ marginTop: "1rem" }}>Triage</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Patient</th>
                  <th>Gravite</th>
                </tr>
              </thead>
              <tbody>
                {triage.map((t) => (
                  <tr key={t.crew_member_code}>
                    <td>{t.triage_priority}</td>
                    <td>{t.full_name}</td>
                    <td>{t.severity_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <section className="panel" style={{ marginTop: "1rem" }}>
        <h2>Journal et alertes</h2>
        <div className="btn-row">
          <button type="button" className="secondary" onClick={() => api.resetDemo().then(refresh)}>
            Reset demo
          </button>
        </div>
        <ul>
          {journal.map((j, i) => (
            <li key={i}>
              {j.summary} <span className="badge">{j.created_at}</span>
            </li>
          ))}
        </ul>
        {alerts.length > 0 && (
          <>
            <h3>Alertes securite (MIMIR)</h3>
            <ul>
              {alerts.map((a, i) => (
                <li key={i}>
                  {a.source}: {JSON.stringify(a.payload)}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}
