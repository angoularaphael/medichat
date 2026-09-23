import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Droplets, Leaf, SunMedium } from "lucide-react";
import { useState } from "react";
import { api, PlantCulture } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import PlantPortrait from "../components/PlantPortrait";

const statusLabel: Record<string, string> = {
  ready: "Prete a recolter",
  growing: "En croissance",
  depleted: "Epuisee",
};

export default function CulturesPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const plants = useQuery({ queryKey: ["plants"], queryFn: api.plants });
  const isAdmin = user?.role === "admin";
  const [openCode, setOpenCode] = useState<string | null>(null);

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["plants"] }),
      queryClient.invalidateQueries({ queryKey: ["journal"] }),
    ]);

  const irrigate = useMutation({ mutationFn: api.irrigatePlant, onSuccess: refresh });
  const boost = useMutation({ mutationFn: api.boostPlant, onSuccess: refresh });
  const harvest = useMutation({ mutationFn: api.harvestPlant, onSuccess: refresh });

  return (
    <div className="cultures-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Bioregeneration / Serre de bord</span>
          <h1>Cultures medicinales</h1>
          <p>
            Photos reelles des cultures, fond retire. Cliquez une fiche pour le protocole.
            Quand un medicament est interdit ou epuise, Medichat pioche ici.
            La cuve bacterienne est un probiotique (Lactobacillus), jamais un pathogene.
          </p>
        </div>
      </div>

      <div className="plant-grid">
        {plants.data?.map((plant, index) => (
          <PlantCard
            key={plant.code}
            plant={plant}
            index={index}
            open={openCode === plant.code}
            onOpen={() => setOpenCode(plant.code === openCode ? null : plant.code)}
            isAdmin={isAdmin}
            busy={irrigate.isPending || boost.isPending || harvest.isPending}
            onIrrigate={() => irrigate.mutate(plant.code)}
            onBoost={() => boost.mutate(plant.code)}
            onHarvest={() => harvest.mutate(plant.code)}
          />
        ))}
      </div>
      {harvest.error && <p className="form-error" role="alert">{harvest.error.message}</p>}
    </div>
  );
}

function PlantCard({
  plant,
  index,
  open,
  onOpen,
  isAdmin,
  busy,
  onIrrigate,
  onBoost,
  onHarvest,
}: {
  plant: PlantCulture;
  index: number;
  open: boolean;
  onOpen: () => void;
  isAdmin: boolean;
  busy: boolean;
  onIrrigate: () => void;
  onBoost: () => void;
  onHarvest: () => void;
}) {
  return (
    <motion.article
      className={`plant-card glass-panel ${open ? "open" : ""}`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
    >
      <button className="plant-open" type="button" onClick={onOpen}>
        <PlantPortrait code={plant.code} name={plant.name} />
        <span className={`plant-status ${plant.status}`}>{statusLabel[plant.status] ?? plant.status}</span>
        <strong>{plant.name}</strong>
        <small>{plant.species}</small>
      </button>
      <p>{open ? plant.description || plant.notes : plant.notes}</p>
      <div className="plant-meta">
        <span>Relais</span>
        <strong>{plant.replaces_drug_class}</strong>
      </div>
      <div className="plant-biomass">
        <div>
          <span>Biomasse</span>
          <strong>{plant.biomass_percent} %</strong>
        </div>
        <div className="stock-bar">
          <i style={{ width: `${Math.min(100, plant.biomass_percent)}%` }} />
        </div>
      </div>
      <div className="plant-actions">
        {isAdmin && (
          <>
            <button type="button" disabled={busy} onClick={onIrrigate}>
              <Droplets size={16} /> Irriguer
            </button>
            <button type="button" disabled={busy} onClick={onBoost}>
              <SunMedium size={16} /> Lumiere
            </button>
          </>
        )}
        <button type="button" disabled={busy || !plant.ready} onClick={onHarvest}>
          <Leaf size={16} /> Recolter
        </button>
      </div>
    </motion.article>
  );
}
