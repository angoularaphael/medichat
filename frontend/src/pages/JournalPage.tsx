import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { BellRing, FileClock, FileDown, RotateCcw, Satellite, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function JournalPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const journal = useQuery({ queryKey: ["journal"], queryFn: api.journal, refetchInterval: 5000 });
  const alerts = useQuery({
    queryKey: ["security-alerts"],
    queryFn: api.securityAlerts,
    enabled: user?.role === "admin",
    refetchInterval: 5000,
  });
  const operations = [
    ...(journal.data ?? []).map((entry) => ({
      id: `decision-${entry.id}`,
      at: entry.created_at,
      title: entry.summary,
      meta: entry.action.replace(/_/g, " "),
    })),
    ...(alerts.data ?? []).map((alert) => ({
      id: `alert-${alert.id}`,
      at: alert.created_at,
      title: String(alert.payload.message || alert.payload.alert || "Alerte MIMIR"),
      meta: "Alerte MIMIR",
    })),
  ].sort((left, right) => new Date(right.at).getTime() - new Date(left.at).getTime());
  const [exportError, setExportError] = useState("");
  const [exporting, setExporting] = useState<"csv" | "pdf" | null>(null);

  async function download(format: "csv" | "pdf") {
    setExportError("");
    setExporting(format);
    try {
      await api.downloadJournal(format);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Export impossible");
    } finally {
      setExporting(null);
    }
  }

  const reset = useMutation({
    mutationFn: api.resetDemo,
    onSuccess: async () => {
      await queryClient.invalidateQueries();
    },
  });

  return (
    <div className="journal-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Traçabilité / Mémoire de mission</span>
          <h1>Journal des décisions</h1>
          <p>Historique inviolable des soins, alertes et changements de protocole. L'export reste sur cette machine.</p>
        </div>
        <div className="journal-exports">
          <button className="outline-action" type="button" disabled={exporting !== null} onClick={() => download("csv")}>
            <FileDown size={17} /> {exporting === "csv" ? "Export CSV..." : "Exporter en CSV"}
          </button>
          <button className="outline-action" type="button" disabled={exporting !== null} onClick={() => download("pdf")}>
            <FileDown size={17} /> {exporting === "pdf" ? "Export PDF..." : "Exporter en PDF"}
          </button>
          {user?.role === "admin" && (
            <button className="outline-action" type="button" onClick={() => reset.mutate()}>
              <RotateCcw size={17} /> Réinitialiser la démo
            </button>
          )}
        </div>
        {exportError && <p className="form-error" role="alert">{exportError}</p>}
      </div>

      <div className="journal-grid">
        <section className="timeline-panel glass-panel">
          <div className="section-title">
            <div><span className="eyebrow">Flux d'événements</span><h2>Dernières opérations</h2></div>
            <FileClock size={20} />
          </div>
          <div className="timeline">
            {operations.map((entry, index) => (
              <motion.article
                key={entry.id}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <i />
                <time>{formatDate(entry.at)}</time>
                <div>
                  <strong>{entry.title}</strong>
                  <span>{entry.meta}</span>
                </div>
              </motion.article>
            ))}
            {!operations.length && <p className="empty-copy">Aucune décision enregistrée pour cette session.</p>}
          </div>
        </section>

        <aside className="alerts-panel glass-panel">
          <div className="section-title">
            <div><span className="eyebrow">Canal MIMIR</span><h2>Alertes sécurité</h2></div>
            <Satellite size={20} />
          </div>
          {user?.role !== "admin" ? (
            <div className="locked-alerts">
              <ShieldAlert size={28} />
              <strong>Accès commandement</strong>
              <p>Les données de sécurité MIMIR sont réservées à l'administrateur.</p>
            </div>
          ) : alerts.data?.length ? (
            <div className="alert-list">
              {alerts.data.map((alert) => (
                <article key={alert.id}>
                  <BellRing size={17} />
                  <div>
                    <strong>{alert.source}</strong>
                    <p>{Object.entries(alert.payload).map(([key, value]) => `${key}: ${String(value)}`).join(" / ")}</p>
                    <time>{formatDate(alert.created_at)}</time>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="all-clear">
              <span><i /></span>
              <strong>Aucune menace détectée</strong>
              <p>Le canal de surveillance est actif.</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
