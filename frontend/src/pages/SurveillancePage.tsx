import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, WatchSubject } from "../api/client";

const SCENARIOS = [
  { id: "nominal", label: "Nominal" },
  { id: "false-alarm", label: "Fausse alerte" },
  { id: "contamination", label: "Contamination 15 %" },
  { id: "slow-burn", label: "Degradation 10 min" },
];

const LEVELS: Record<string, string> = {
  routine: "Routine",
  low: "Bas",
  medium: "Moyen",
  high: "Haut",
  missing: "Mesure absente",
};

export default function SurveillancePage() {
  const queryClient = useQueryClient();
  const board = useQuery({ queryKey: ["surveillance"], queryFn: api.surveillance });
  const [picked, setPicked] = useState("elisa");
  const scenario = useMutation({
    mutationFn: api.surveillanceScenario,
    onSuccess: async (data) => {
      queryClient.setQueryData(["surveillance"], data);
      const focus = data.subjects.find((row) => row.isolated) || data.subjects.find((row) => row.code === "raphael");
      if (focus) setPicked(focus.code);
    },
  });

  const subjects = board.data?.subjects ?? [];
  const current = subjects.find((row) => row.code === picked) ?? subjects[0];

  return (
    <div className="watch-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Veille / Constantes simulees</span>
          <h1>Surveillance d'equipage</h1>
          <p>
            Quarante membres, mesures synthetiques. Le score et la quarantaine ne lisent pas Medichat.
            {board.data ? ` ${board.data.note}` : ""}
          </p>
        </div>
      </div>

      <div className="watch-actions">
        {SCENARIOS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={board.data?.scenario === item.id ? "selected" : ""}
            disabled={scenario.isPending}
            onClick={() => scenario.mutate(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {scenario.error && <p className="form-error" role="alert">{scenario.error.message}</p>}

      <section className="watch-summary glass-panel">
        <p>
          {board.data?.crew_count ?? 0} personnes suivies, {board.data?.isolated_count ?? 0} en zone,
          {board.data?.waiting.length ? ` ${board.data.waiting.length} en attente de place.` : " aucune attente de place."}
        </p>
      </section>

      <section className="watch-zones" aria-label="Zones de quarantaine">
        {board.data?.zones.map((zone) => (
          <article key={zone.code} className={`glass-panel ${zone.full ? "full" : ""}`}>
            <strong>{zone.code}</strong>
            <span>{zone.full ? "Zone fermee" : `${zone.occupants.length} / ${zone.capacity}`}</span>
            <p>{zone.occupants.length ? zone.occupants.join(", ") : "Libre"}</p>
          </article>
        ))}
      </section>

      <section className="watch-detail glass-panel">
        <label htmlFor="watch-subject">Personne</label>
        <select
          id="watch-subject"
          value={current?.code ?? ""}
          onChange={(event) => setPicked(event.target.value)}
        >
          {subjects.map((row) => (
            <option key={row.code} value={row.code}>
              {row.full_name} - {LEVELS[row.level] ?? row.level}
            </option>
          ))}
        </select>
        {current && <SubjectDetail subject={current} />}
      </section>

      <section className="watch-contacts glass-panel">
        <h2>Contacts de zone</h2>
        <p>Paires presentes dans la meme zone. Cela ne prouve pas une contamination.</p>
        {board.data?.contacts.length ? (
          <ul>
            {board.data.contacts.map((row) => (
              <li key={`${row.zone_code}-${row.subject_a}-${row.subject_b}-${row.started_at}`}>
                {row.zone_code}: {row.subject_a} et {row.subject_b}
                {row.open ? " - en cours" : " - termine"}
              </li>
            ))}
          </ul>
        ) : (
          <p>Aucun contact enregistre.</p>
        )}
      </section>
    </div>
  );
}

function SubjectDetail({ subject }: { subject: WatchSubject }) {
  return (
    <div>
      <p className={`watch-level ${subject.level}`}>
        Priorite {LEVELS[subject.level] ?? subject.level}, score {subject.score}.
        {subject.isolated ? ` Zone ${subject.zone_code}.` : " Pas d'isolement."}
        {subject.waiting_place ? " En attente de place." : ""}
      </p>
      <div className="watch-vitals">
        <span>Temperature <strong>{subject.temperature_c.toFixed(1)} C</strong></span>
        <span>SpO2 <strong>{subject.spo2.toFixed(0)} %</strong></span>
        <span>Pouls <strong>{subject.pulse.toFixed(0)}</strong></span>
        <span>Respiration <strong>{subject.respiration.toFixed(0)}</strong></span>
      </div>
      <ScoreCurve samples={subject.samples} changeAt={subject.level_change_at} />
    </div>
  );
}

function ScoreCurve({
  samples,
  changeAt,
}: {
  samples: { recorded_at: string; score: number; level: string }[];
  changeAt: string | null;
}) {
  if (samples.length === 0) {
    return <p>Aucune mesure sur les dix dernieres minutes.</p>;
  }
  const width = 320;
  const height = 120;
  const pad = 12;
  const max = Math.max(7, ...samples.map((row) => row.score));
  const point = (index: number, score: number) => {
    const x = samples.length === 1 ? width / 2 : pad + (index / (samples.length - 1)) * (width - pad * 2);
    const y = height - pad - (score / max) * (height - pad * 2);
    return { x, y };
  };
  const line = samples.map((row, index) => {
    const spot = point(index, row.score);
    return `${spot.x},${spot.y}`;
  }).join(" ");
  const changeIndex = samples.findIndex((row) => row.recorded_at === changeAt);

  return (
    <figure className="watch-curve">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Score des dix dernieres minutes">
        <polyline fill="none" stroke="currentColor" strokeWidth="2" points={line} />
        {changeIndex > 0 && (
          <line
            x1={point(changeIndex, 0).x}
            x2={point(changeIndex, 0).x}
            y1={pad}
            y2={height - pad}
            stroke="#e2c15a"
            strokeWidth="2"
          />
        )}
      </svg>
      <figcaption>
        Dix dernieres minutes. Le trait jaune marque le dernier changement de niveau.
      </figcaption>
    </figure>
  );
}
