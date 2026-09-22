import { motion } from "framer-motion";
import { ArrowRight, Eye, EyeOff, Orbit, ShieldCheck } from "lucide-react";
import { FormEvent, lazy, Suspense, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const crew = ["raphael", "elisa", "elsa", "jovani", "carine"];
const SpaceScene = lazy(() => import("../components/SpaceScene"));

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("raphael");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Connexion impossible");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="star-layer stars-a" aria-hidden="true" />
      <div className="star-layer stars-b" aria-hidden="true" />
      <Suspense fallback={<div className="space-fallback" aria-hidden="true" />}>
        <SpaceScene />
      </Suspense>

      <motion.div
        className="login-brand"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
      >
        <Orbit />
        <span>EIR / MEDICHAT</span>
      </motion.div>

      <section className="login-copy">
        <motion.span
          className="eyebrow"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25 }}
        >
          Mission Yggdrasil / Horizon 2080
        </motion.span>
        <motion.h1
          initial={{ opacity: 0, y: 22 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1 }}
        >
          La sante de l'equipage,
          <em> au-dela de la Terre.</em>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
        >
          Intelligence médicale embarquée, suivi des ressources et aide à la décision en temps réel.
        </motion.p>
        <div className="orbit-readout">
          <span>Distance Terre</span>
          <strong>18.4 M km</strong>
          <i />
          <span>Signal</span>
          <strong>Stable</strong>
        </div>
      </section>

      <motion.section
        className="login-panel glass-panel"
        initial={{ opacity: 0, x: 35, scale: 0.97 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        transition={{ duration: 0.65, delay: 0.2 }}
      >
        <div className="panel-kicker">
          <ShieldCheck size={18} />
          Accès sécurisé
        </div>
        <h2>Identification équipage</h2>
        <p>Sélectionnez votre profil puis entrez votre clé d'accès.</p>

        <div className="crew-pills" aria-label="Profils équipage">
          {crew.map((name) => (
            <button
              key={name}
              className={username === name ? "selected" : ""}
              type="button"
              onClick={() => setUsername(name)}
            >
              {name}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit}>
          <label htmlFor="username">Identifiant mission</label>
          <input
            id="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value.toLowerCase())}
          />
          <label htmlFor="password">Clé d'accès</label>
          <div className="password-field">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Mot de passe"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword((value) => !value)}
              aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="primary-action" type="submit" disabled={loading}>
            <span>{loading ? "Synchronisation..." : "Entrer dans la station"}</span>
            <ArrowRight size={19} />
          </button>
        </form>
        <div className="secure-caption">
          <span className="pulse-dot" />
          Canal chiffré / Session locale EIR
        </div>
      </motion.section>
    </div>
  );
}
