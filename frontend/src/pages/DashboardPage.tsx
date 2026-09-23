import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Boxes,
  Gauge,
  Leaf,
  PackagePlus,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  Users,
} from "lucide-react";
import type { CSSProperties } from "react";
import { Link, useNavigate } from "react-router-dom";
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
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const autonomy = useQuery({ queryKey: ["autonomy"], queryFn: api.autonomy });
  const crew = useQuery({ queryKey: ["crew"], queryFn: api.crew });
  const triage = useQuery({ queryKey: ["triage"], queryFn: api.triage });
  const drugs = useQuery({ queryKey: ["drugs"], queryFn: api.drugs });
  const plants = useQuery({ queryKey: ["plants"], queryFn: api.plants });
  const status = useQuery({ queryKey: ["system-status"], queryFn: api.systemStatus, refetchInterval: 15000 });
  const gastro = useQuery({ queryKey: ["gastro-estimate"], queryFn: api.gastroEstimate });

  const refreshMission = () => queryClient.invalidateQueries();

  const runAction = async (action: () => Promise<unknown>) => {
    await action();
    await refreshMission();
  };

  const days = autonomy.data?.on_demand.global_days ?? 0;
  const rationedDays = autonomy.data?.rationing_quarantine.global_days ?? 0;
  const criticalStocks = drugs.data?.filter((drug) => drug.is_critical).length ?? 0;
  const sick = autonomy.data?.on_demand.sick_count ?? 0;
  const readyPlants = plants.data?.filter((plant) => plant.ready).length ?? 0;

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Vue mission / Temps réel</span>
          <h1>Centre de commande médical</h1>
          <p>
            EIR est le pilier sante du vaisseau Yggdrasil. Il reste autonome si le lien Terre coupe,
            et echange avec MIMIR, le projet DeepTech, via MQTT.
          </p>
        </div>
        <div className="resilience-strip" aria-label="Etat des services locaux">
          {[
            ["API", status.data?.api],
            ["Base", status.data?.database],
            ["MQTT", status.data?.mqtt],
            ["Ollama", status.data?.ollama],
          ].map(([label, ok]) => (
            <span key={String(label)} className={ok ? "service-ok" : "service-down"}>
              {label}: {ok ? "en ligne" : "hors ligne"}
            </span>
          ))}
        </div>
        <div className={`mission-state ${autonomy.data?.crisis_active ? "alert" : ""}`}>
          <span />
          {autonomy.data?.crisis_active ? "Protocole de crise actif" : "Mission nominale"}
        </div>
      </div>

      {gastro.data && (
        <section className="glass-panel gastro-panel">
          <span className="eyebrow">Annexe logistique</span>
          <h2>{gastro.data.scenario}</h2>
          <p>{gastro.data.conclusion}</p>
          <ul className="finding-list">
            {gastro.data.rows.map((row) => (
              <li key={row.drug_code}>
                <strong>{row.label}</strong>
                <span>
                  Stock {row.stock_units}, besoin 6 mois {row.need_6_months}, manque {row.shortage_units}.
                  Couverture au pic: {row.days_covered_at_peak} jours.
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="metric-grid" aria-label="Indicateurs mission">
        {[
          {
            label: "Autonomie médicale",
            value: `${days} j`,
            detail: "Jours restants si on continue au rythme actuel",
            icon: Gauge,
          },
          {
            label: "Équipage suivi",
            value: crew.data?.length ?? "--",
            detail: sick ? `${sick} malade(s) a bord` : "Personne n'est marque malade",
            icon: Users,
          },
          {
            label: "Stocks critiques",
            value: criticalStocks,
            detail: `${drugs.data?.length ?? 0} medicaments synthetiques a bord`,
            icon: Boxes,
          },
          {
            label: "Cultures pretes",
            value: readyPlants,
            detail: "Plantes assez matures pour remplacer un stock epuise",
            icon: Leaf,
          },
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
          <p className="panel-hint">
            Compare deux facons de gerer les stocks: tout donner tout de suite, ou rationner pour durer plus longtemps.
          </p>
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
                <span>Si on soigne sans limite</span>
                <strong>{days} jours</strong>
                <div className="progress-track"><i style={{ width: `${Math.min(100, days)}%` }} /></div>
              </div>
              <div>
                <span>Si on rationne et isole</span>
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
              const canOpen = user?.role === "admin" || user?.crew_member_code === member.code;
              return (
                <button
                  className="crew-row"
                  type="button"
                  key={member.code}
                  onClick={() => canOpen && navigate(`/profil/${member.code}`)}
                >
                  <div className="crew-avatar">
                    {member.avatar_data ? <img src={member.avatar_data} alt="" /> : member.full_name.charAt(0)}
                  </div>
                  <div>
                    <strong>{member.full_name}</strong>
                    <span>{member.age} ans / {canOpen ? "Ouvrir le profil" : `Profil ${String(index + 1).padStart(2, "0")}`}</span>
                  </div>
                  <span className={`health-state ${member.health_status}`}>
                    {member.health_status === "healthy" ? "Stable" : `Priorité ${triageEntry?.triage_priority ?? "-"}`}
                  </span>
                </button>
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
            <p>Ces boutons servent a tester la demo. Ils changent la sante et les stocks, puis le tableau se met a jour.</p>
          </div>
          <div className="protocol-grid">
            <article>
              <h3>Crise 15 %</h3>
              <p>Simule une epidemie: 15 % de l'equipage tombe malade. Ici, 1 personne sur 5. Les stocks baissent plus vite.</p>
              <button type="button" onClick={() => runAction(api.triggerCrisis)}>
                <ShieldAlert size={18} /> Declencher
              </button>
            </article>
            <article>
              <h3>Rationnement</h3>
              <p>On isole une partie des malades et on distille les doses. Objectif: faire durer les stocks plus longtemps.</p>
              <button type="button" onClick={() => runAction(api.rationing)}>
                <Sparkles size={18} /> Activer
              </button>
            </article>
            <article>
              <h3>Rupture de stock</h3>
              <p>Met tous les medicaments a 0. Medichat bascule sur serre, cuves ou protocoles de bord.</p>
              <button className="danger-ghost" type="button" onClick={() => runAction(api.forceAllStockZero)}>
                <AlertTriangle size={18} /> Simuler
              </button>
            </article>
            <article>
              <h3>Reapprovisionnement</h3>
              <p>Remet uniquement les medicaments a leur niveau de depart, sans annuler une crise en cours.</p>
              <button type="button" onClick={() => runAction(api.restock)}>
                <PackagePlus size={18} /> Restaurer les stocks
              </button>
            </article>
            <article>
              <h3>Remettre a zero</h3>
              <p>Efface tout: sante de l'equipage, crise, stocks et cultures. Pour recommencer la demo proprement.</p>
              <button type="button" onClick={() => runAction(api.resetDemo)}>
                <RotateCcw size={18} /> Reset mission
              </button>
            </article>
            <article>
              <h3>Serre de bord</h3>
              <p>Plantes et cuves. En rupture, EIR explique l'origine du medicament et le relais de confort, sans mode de fabrication.</p>
              <Link className="protocol-link" to="/cultures">
                <Leaf size={18} /> Ouvrir les cultures
              </Link>
            </article>
          </div>
        </motion.section>
      )}
    </div>
  );
}
