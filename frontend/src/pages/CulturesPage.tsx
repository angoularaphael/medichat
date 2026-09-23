import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Droplets, FlaskConical, Leaf, SunMedium } from "lucide-react";
import { useState } from "react";
import { api, BacteriaCulture, PlantCulture } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import PlantPortrait from "../components/PlantPortrait";

const statusLabel: Record<string, string> = {
  ready: "Prete a recolter",
  growing: "En croissance",
  depleted: "Epuisee",
};

const viabilityLabel: Record<string, string> = {
  Actif: "Actif",
  "En sommeil": "En sommeil",
  Contamine: "Contamine",
};

export default function CulturesPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const plants = useQuery({ queryKey: ["plants"], queryFn: api.plants });
  const bacteria = useQuery({ queryKey: ["bacteria"], queryFn: api.bacteria });
  const isAdmin = user?.role === "admin";
  const [openPlant, setOpenPlant] = useState<string | null>(null);
  const [openBacteria, setOpenBacteria] = useState<string | null>(null);

  const refreshPlants = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["plants"] }),
      queryClient.invalidateQueries({ queryKey: ["journal"] }),
    ]);
  const refreshBacteria = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["bacteria"] }),
      queryClient.invalidateQueries({ queryKey: ["journal"] }),
    ]);

  const irrigate = useMutation({ mutationFn: api.irrigatePlant, onSuccess: refreshPlants });
  const boost = useMutation({ mutationFn: api.boostPlant, onSuccess: refreshPlants });
  const harvestPlant = useMutation({ mutationFn: api.harvestPlant, onSuccess: refreshPlants });
  const incubate = useMutation({ mutationFn: api.incubateBacteria, onSuccess: refreshBacteria });
  const harvestBacteria = useMutation({ mutationFn: api.harvestBacteria, onSuccess: refreshBacteria });

  return (
    <div className="cultures-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Bioregeneration / Pharmacie vivante</span>
          <h1>Cultures de bord</h1>
          <p>
            Serre pour les plantes, cuves pour les souches. Photos de face des cultures.
            Sans livraison terrestre, ces stocks synthetisent ou testent les traitements a bord.
          </p>
        </div>
      </div>

      <section className="cultures-section" aria-labelledby="plantes-title">
        <div className="section-heading">
          <h2 id="plantes-title">Plantes</h2>
          <p>Relais botaniques quand un flacon est interdit ou vide. Riz et gingembre inclus.</p>
        </div>
        <div className="plant-grid">
          {plants.data?.map((plant, index) => (
            <PlantCard
              key={plant.code}
              plant={plant}
              index={index}
              open={openPlant === plant.code}
              onOpen={() => setOpenPlant(plant.code === openPlant ? null : plant.code)}
              isAdmin={isAdmin}
              busy={irrigate.isPending || boost.isPending || harvestPlant.isPending}
              onIrrigate={() => irrigate.mutate(plant.code)}
              onBoost={() => boost.mutate(plant.code)}
              onHarvest={() => harvestPlant.mutate(plant.code)}
            />
          ))}
        </div>
        {harvestPlant.error && <p className="form-error" role="alert">{harvestPlant.error.message}</p>}
      </section>

      <section className="cultures-section" aria-labelledby="bacteries-title">
        <div className="section-heading">
          <h2 id="bacteries-title">Bacteries</h2>
          <p>
            Table stock_cultures_biologiques: souches, categorie, temperature, boites de Petri, viabilite.
            La cuve Lactobacillus est ici. Staphylococcus aureus sert de cobaye, jamais de traitement.
          </p>
        </div>
        <div className="plant-grid">
          {bacteria.data?.map((row, index) => (
            <BacteriaCard
              key={row.code}
              row={row}
              index={index}
              open={openBacteria === row.code}
              onOpen={() => setOpenBacteria(row.code === openBacteria ? null : row.code)}
              isAdmin={isAdmin}
              busy={incubate.isPending || harvestBacteria.isPending}
              onIncubate={() => incubate.mutate(row.code)}
              onHarvest={() => harvestBacteria.mutate(row.code)}
            />
          ))}
        </div>
        {harvestBacteria.error && <p className="form-error" role="alert">{harvestBacteria.error.message}</p>}
        {incubate.error && <p className="form-error" role="alert">{incubate.error.message}</p>}
      </section>
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
      transition={{ delay: index * 0.05 }}
    >
      <PlantPortrait code={plant.code} name={plant.name} />
      <button className="plant-open" type="button" onClick={onOpen}>
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

function BacteriaCard({
  row,
  index,
  open,
  onOpen,
  isAdmin,
  busy,
  onIncubate,
  onHarvest,
}: {
  row: BacteriaCulture;
  index: number;
  open: boolean;
  onOpen: () => void;
  isAdmin: boolean;
  busy: boolean;
  onIncubate: () => void;
  onHarvest: () => void;
}) {
  const dishClass = row.categorie.toLowerCase().replace(" ", "-");
  return (
    <motion.article
      className={`plant-card glass-panel ${open ? "open" : ""}`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <div className={`bacteria-dish ${dishClass} ${row.code === "lactobacillus_acidophilus" ? "cuve" : ""}`} aria-hidden="true">
        <span />
      </div>
      <button className="plant-open" type="button" onClick={onOpen}>
        <span className={`plant-status ${row.statut_viabilite === "Actif" ? "ready" : "depleted"}`}>
          {viabilityLabel[row.statut_viabilite] ?? row.statut_viabilite}
        </span>
        <strong>{row.nom_souche}</strong>
        <small>{row.categorie}</small>
      </button>
      <p>{open ? row.description || row.notes : row.notes}</p>
      <div className="plant-meta">
        <span>Temperature</span>
        <strong>{row.temperature_celsius.toFixed(1)} C</strong>
      </div>
      <div className="plant-biomass">
        <div>
          <span>Boites de Petri</span>
          <strong>{row.quantite_boites}</strong>
        </div>
        <div className="stock-bar">
          <i style={{ width: `${Math.min(100, (row.quantite_boites / 40) * 100)}%` }} />
        </div>
      </div>
      <div className="plant-actions">
        {isAdmin && (
          <button type="button" disabled={busy || row.statut_viabilite === "Contamine"} onClick={onIncubate}>
            <FlaskConical size={16} /> Incuber
          </button>
        )}
        <button type="button" disabled={busy || !row.ready} onClick={onHarvest}>
          <Leaf size={16} /> Prelever
        </button>
      </div>
    </motion.article>
  );
}
