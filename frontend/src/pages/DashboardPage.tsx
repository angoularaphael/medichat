import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowUpRight,
  Boxes,
  Clock3,
  Gauge,
  ShieldAlert,
  Sparkles,
  Users,
} from "lucide-react";
import type { CSSProperties } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

const reveal = {
  hidden: { opacity: 0, y: 18 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: index * 0.07, duration: 0.45 },
  }),
};

export default function DashboardPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const autonomy = useQuery({ queryKey: ["autonomy"], queryFn: api.autonomy });
  const crew = useQuery({ queryKey: ["crew"], queryFn: api.crew });
  const triage = useQuery({ queryKey: ["triage"], queryFn: api.triage });
  const drugs = useQuery({ queryKey: ["drugs"], queryFn: api.drugs });

  const refreshMission = () =>
    queryClient.invalidateQueries({ predicate: (query) => query.queryKey[0] !== "journal" });

  const runAction = async (action: () => Promise<unknown>) => {
    await action();
    await refreshMission();
  };

  const days = autonomy.data?.on_demand.global_days ?? 0;
  const rationedDays = autonomy.data?.rationing_quarantine.global_days ?? 0;
  const criticalStocks = drugs.data?.filter((drug) => drug.is_critical).length ?? 0;
  const sick = autonomy.data?.on_demand.sick_count ?? 0;

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Vue mission / Temps réel</span>
          <h1>Centre de commande médical</h1>
          <p>Surveillance de l'équipage et des ressources thérapeutiques.</p>
        </div>
        <div className={`mission-state ${autonomy.data?.crisis_active ? "alert" : ""}`}>
          <span />
          {autonomy.data?.crisis_active ? "Protocole de crise actif" : "Mission nominale"}
        </div>
      </div>

      <section className="metric-grid" aria-label="Indicateurs mission">
        {[
          { label: "Autonomie médicale", value: `${days} j`, detail: "Au rythme actuel", icon: Gauge },
          { label: "Équipage suivi", value: crew.data?.length ?? "--", detail: `${sick} sous surveillance`, icon: Users },
          { label: "Références critiques", value: criticalStocks, detail: `${drugs.data?.length ?? 0} médicaments à bord`, icon: Boxes },
          { label: "Gain rationnement", value: `+${Math.max(0, rationedDays - days).toFixed(1)} j`, detail: "Projection optimisée", icon: Clock3 },
        ].map((metric, index) => (
          <motion.article
            className="metric-card glass-panel"
            key={metric.label}
            custom={index}
            variants={reveal}
            initial="hidden"
            animate="visible"
          >
            <div className="metric-icon"><metric.icon size={19} /></div>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.detail}</small>
            <ArrowUpRight className="metric-arrow" size={18} />
          </motion.article>
        ))}
      </section>

      <div className="dashboard-grid">
        <motion.section
          className="autonomy-panel glass-panel"
          variants={reveal}
          custom={4}
          initial="hidden"
          animate="visible"
        >
          <div className="section-title">
            <div>
              <span className="eyebrow">Projection des ressources</span>
              <h2>Autonomie thérapeutique</h2>
            </div>
            <span className="live-badge">Calcul actif</span>
          </div>
          <div className="autonomy-visual">
            <div
              className="orbital-gauge"
              style={{ "--progress": `${Math.min(100, days)}%` } as CSSProperties}
            >
              <div>
                <strong>{days}</strong>
                <span>jours</span>
              </div>
              <i className="gauge-orbit" />
            </div>
            <div className="projection-list">
              <div>
                <span>Politique actuelle</span>
                <strong>{days} jours</strong>
                <div className="progress-track"><i style={{ width: `${Math.min(100, days)}%` }} /></div>
              </div>
              <div>
                <span>Rationnement contrôlé</span>
                <strong>{rationedDays} jours</strong>
                <div className="progress-track violet"><i style={{ width: `${Math.min(100, rationedDays)}%` }} /></div>
              </div>
            </div>
          </div>
          <div className="stock-list">
            {autonomy.data?.on_demand.drugs.slice(0, 5).map((drug) => (
              <div key={drug.drug_code}>
                <span>{drug.drug_name}</span>
                <div className="stock-bar">
                  <i style={{ width: `${Math.min(100, drug.days_remaining)}%` }} />
                </div>
                <strong>{drug.stock_units}</strong>
              </div>
            ))}
          </div>
        </motion.section>

        <motion.section
          className="crew-panel glass-panel"
          variants={reveal}
          custom={5}
          initial="hidden"
          animate="visible"
        >
          <div className="section-title">
            <div>
              <span className="eyebrow">Biomonitoring</span>
              <h2>État de l'équipage</h2>
            </div>
            <Users size={20} />
          </div>
          <div className="crew-list">
            {crew.data?.map((member, index) => {
              const triageEntry = triage.data?.find((entry) => entry.crew_member_code === member.code);
              return (
                <div className="crew-row" key={member.code}>
                  <div className="crew-avatar">{member.full_name.charAt(0)}</div>
                  <div>
                    <strong>{member.full_name}</strong>
                    <span>{member.age} ans / Profil {String(index + 1).padStart(2, "0")}</span>
                  </div>
                  <span className={`health-state ${member.health_status}`}>
                    {member.health_status === "healthy" ? "Stable" : `Priorité ${triageEntry?.triage_priority ?? "-"}`}
                  </span>
                </div>
              );
            })}
          </div>
        </motion.section>
      </div>

      {user?.role === "admin" && (
        <motion.section
          className="crisis-panel glass-panel"
          variants={reveal}
          custom={6}
          initial="hidden"
          animate="visible"
        >
          <div>
            <span className="eyebrow">Commandement / Simulation</span>
            <h2>Protocoles de mission</h2>
            <p>Actions réservées au commandant médical pour la démonstration.</p>
          </div>
          <div className="crisis-actions">
            <button type="button" onClick={() => runAction(api.triggerCrisis)}>
              <ShieldAlert size={18} /> Déclencher crise 15 %
            </button>
            <button type="button" onClick={() => runAction(api.rationing)}>
              <Sparkles size={18} /> Activer rationnement
            </button>
            <button className="danger-ghost" type="button" onClick={() => runAction(() => api.forceStockZero("paracetamol"))}>
              <AlertTriangle size={18} /> Simuler rupture
            </button>
          </div>
        </motion.section>
      )}
    </div>
  );
}
