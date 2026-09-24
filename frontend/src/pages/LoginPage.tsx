import { motion } from "framer-motion";
import { ArrowRight, Camera, Eye, EyeOff, Orbit, Scan, ShieldCheck } from "lucide-react";
import { FormEvent, lazy, Suspense, useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import ArrivalIntro from "../components/ArrivalIntro";
import { faceDescriptorFromSource } from "../face/descriptor";

const crew = ["raphael", "elisa", "elsa", "jovani", "carine"];
const SpaceScene = lazy(() => import("../components/SpaceScene"));

export default function LoginPage() {
  const { login, loginFace, user } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"password" | "face">("password");
  const [username, setUsername] = useState("raphael");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [introDone, setIntroDone] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

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

  async function startCamera() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: 480, height: 480 },
        audio: false,
      });
      streamRef.current = stream;
      setCameraOn(true);
      if (videoRef.current) videoRef.current.srcObject = stream;
    } catch {
      setError("Camera inaccessible. Autorisez-la ou utilisez le mot de passe.");
    }
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraOn(false);
  }

  async function handleFaceLogin() {
    const video = videoRef.current;
    if (!video) {
      await startCamera();
      return;
    }
    setLoading(true);
    setError("");
    try {
      const descriptor = faceDescriptorFromSource(video);
      await loginFace(descriptor);
      stopCamera();
      navigate("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Visage non reconnu");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      {!introDone && <ArrivalIntro onDone={() => setIntroDone(true)} />}
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
        <div className="login-modes" role="tablist" aria-label="Mode de connexion">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "password"}
            className={mode === "password" ? "selected" : ""}
            onClick={() => {
              setMode("password");
              stopCamera();
              setError("");
            }}
          >
            Mot de passe
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "face"}
            className={mode === "face" ? "selected" : ""}
            onClick={() => {
              setMode("face");
              setError("");
            }}
          >
            Reconnaissance faciale
          </button>
        </div>

        {mode === "password" ? (
          <>
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
          </>
        ) : (
          <div className="face-login">
            <p>
              Cadrez votre visage. Raphael enregistre les identites dans le profil.
              Aucune photo n'est stockee, seulement une empreinte locale.
            </p>
            {cameraOn ? (
              <video ref={videoRef} className="face-preview" autoPlay playsInline muted />
            ) : (
              <div className="face-placeholder">
                <Scan size={36} />
                <span>Camera eteinte</span>
              </div>
            )}
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <div className="face-login-actions">
              {cameraOn ? (
                <>
                  <button className="primary-action" type="button" onClick={handleFaceLogin} disabled={loading}>
                    <Scan size={18} />
                    <span>{loading ? "Verification..." : "Verifier le visage"}</span>
                  </button>
                  <button type="button" className="ghost-action" onClick={stopCamera}>
                    Eteindre la camera
                  </button>
                </>
              ) : (
                <button className="primary-action" type="button" onClick={startCamera}>
                  <Camera size={18} />
                  <span>Ouvrir la camera</span>
                </button>
              )}
            </div>
          </div>
        )}
        <div className="secure-caption">
          <span className="pulse-dot" />
          Canal chiffré / Session locale EIR
        </div>
      </motion.section>
    </div>
  );
}
